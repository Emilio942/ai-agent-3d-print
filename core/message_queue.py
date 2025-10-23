"""
Message Queue System with Priority Support for AI 3D Print System.

This module provides a priority-based message queue system that enables
asynchronous communication between agents with support for:
- Priority-based task scheduling
- Message persistence (optional Redis backend)
- WebSocket real-time notifications
- Dead letter queue for failed messages
- Message acknowledgment and retry mechanisms

Key Components:
- Message: Data structure for queue messages
- MessageQueue: In-memory priority queue implementation
- RedisMessageQueue: Redis-backed distributed queue
- QueueManager: High-level queue management interface
"""

import asyncio
import json
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from enum import Enum, IntEnum
from heapq import heappush, heappop
from typing import Dict, List, Optional, Any, Callable, Union
from threading import Lock, Event
import logging

try:
    from .exceptions import (
        MessageQueueError, MessageNotFoundError, QueueFullError,
        MessageExpiredError, InvalidMessageError
    )
    from .logger import AgentLogger
except ImportError:  # pragma: no cover - legacy fallback paths
    try:
        from core.exceptions import (  # type: ignore
            MessageQueueError, MessageNotFoundError, QueueFullError,
            MessageExpiredError, InvalidMessageError
        )
        from core.logger import AgentLogger  # type: ignore
    except ImportError:
        from exceptions import (  # type: ignore
            MessageQueueError, MessageNotFoundError, QueueFullError,
            MessageExpiredError, InvalidMessageError
        )
        from logger import AgentLogger  # type: ignore


class MessagePriority(IntEnum):
    """Message priority levels (lower values = higher priority)."""
    CRITICAL = 0    # System critical operations
    HIGH = 1        # Time-sensitive tasks
    NORMAL = 2      # Standard operations
    LOW = 3         # Background tasks
    BACKGROUND = 4  # Non-urgent maintenance


class MessageStatus(Enum):
    """Message processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"
    RETRYING = "retrying"


@dataclass
class Message:
    """
    Queue message with metadata and priority.
    
    Attributes:
        id: Unique message identifier
        sender: Agent that sent the message
        receiver: Target agent or queue
        message_type: Type of message/task
        payload: Message data/parameters
        priority: Message priority level
        created_at: Message creation timestamp
        expires_at: Message expiration time (optional)
        retry_count: Number of retry attempts
        max_retries: Maximum retry attempts allowed
        status: Current processing status
        result: Processing result (when completed)
        error: Error information (when failed)
    """
    sender: str
    receiver: str
    message_type: str
    payload: Dict[str, Any]
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    priority: MessagePriority = MessagePriority.NORMAL
    created_at: datetime = None
    expires_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    status: MessageStatus = MessageStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    def __post_init__(self):
        """Initialize computed fields."""
        if self.created_at is None:
            self.created_at = datetime.now()
        if not self.id:
            self.id = str(uuid.uuid4())
    
    def __lt__(self, other):
        """Priority comparison for heap queue."""
        if not isinstance(other, Message):
            return NotImplemented
        # Primary: priority (lower = higher priority)
        # Secondary: creation time (older = higher priority)
        return (self.priority, self.created_at) < (other.priority, other.created_at)
    
    def is_expired(self) -> bool:
        """Check if message has expired."""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
    
    def can_retry(self) -> bool:
        """Check if message can be retried."""
        return self.retry_count < self.max_retries
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        if data['created_at']:
            data['created_at'] = data['created_at'].isoformat()
        if data['expires_at']:
            data['expires_at'] = data['expires_at'].isoformat()
        # Convert enums to strings
        data['priority'] = data['priority'].name
        data['status'] = data['status'].value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create message from dictionary."""
        # Convert ISO strings back to datetime objects
        if data.get('created_at'):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data.get('expires_at'):
            data['expires_at'] = datetime.fromisoformat(data['expires_at'])
        # Convert strings back to enums
        if isinstance(data.get('priority'), str):
            data['priority'] = MessagePriority[data['priority']]
        if isinstance(data.get('status'), str):
            data['status'] = MessageStatus(data['status'])
        return cls(**data)


class QueueBackend(ABC):
    """Abstract base class for queue storage backends."""
    
    @abstractmethod
    async def put(self, message: Message) -> None:
        """Add message to queue."""
        pass
    
    @abstractmethod
    async def get(self, timeout: Optional[float] = None) -> Optional[Message]:
        """Get next message from queue."""
        pass
    
    @abstractmethod
    async def peek(self) -> Optional[Message]:
        """Peek at next message without removing it."""
        pass
    
    @abstractmethod
    async def ack(self, message_id: str) -> None:
        """Acknowledge message processing completion."""
        pass
    
    @abstractmethod
    async def nack(self, message_id: str, requeue: bool = True) -> None:
        """Negative acknowledge - mark message as failed."""
        pass
    
    @abstractmethod
    async def size(self) -> int:
        """Get queue size."""
        pass
    
    @abstractmethod
    async def clear(self) -> None:
        """Clear all messages from queue."""
        pass


class InMemoryQueueBackend(QueueBackend):
    """In-memory priority queue backend."""
    
    def __init__(self, max_size: Optional[int] = None):
        """
        Initialize in-memory queue.
        
        Args:
            max_size: Maximum queue size (None for unlimited)
        """
        self.max_size = max_size
        self._queue: List[Message] = []
        self._processing: Dict[str, Message] = {}
        self._lock = Lock()
        self._not_empty = Event()
        self.logger = AgentLogger("message_queue")
    
    async def put(self, message: Message) -> None:
        """Add message to priority queue."""
        with self._lock:
            if self.max_size and len(self._queue) >= self.max_size:
                raise QueueFullError(
                    f"Queue is full (max size: {self.max_size})",
                    error_code="QUEUE_FULL"
                )
            
            # Check for duplicates
            for existing in self._queue:
                if existing.id == message.id:
                    raise InvalidMessageError(
                        f"Message with ID {message.id} already exists",
                        error_code="DUPLICATE_MESSAGE"
                    )
            
            heappush(self._queue, message)
            self._not_empty.set()
            
            self.logger.info(
                "Message queued",
                extra={
                    "message_id": message.id,
                    "sender": message.sender,
                    "receiver": message.receiver,
                    "priority": message.priority.name,
                    "queue_size": len(self._queue)
                }
            )
    
    async def get(self, timeout: Optional[float] = None) -> Optional[Message]:
        """Get next highest priority message."""
        start_time = time.time()
        
        while True:
            with self._lock:
                # Remove expired messages
                self._cleanup_expired()
                
                if self._queue:
                    message = heappop(self._queue)
                    if not self._queue:
                        self._not_empty.clear()
                    
                    # Move to processing
                    self._processing[message.id] = message
                    message.status = MessageStatus.PROCESSING
                    
                    self.logger.info(
                        "Message dequeued",
                        extra={
                            "message_id": message.id,
                            "sender": message.sender,
                            "receiver": message.receiver,
                            "priority": message.priority.name,
                            "queue_size": len(self._queue)
                        }
                    )
                    
                    return message
            
            # Check timeout
            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    return None
                remaining = timeout - elapsed
            else:
                remaining = 1.0  # Check every second
            
            # Wait for new messages
            await asyncio.sleep(min(0.1, remaining))
    
    async def peek(self) -> Optional[Message]:
        """Peek at next message without removing it."""
        with self._lock:
            self._cleanup_expired()
            return self._queue[0] if self._queue else None
    
    async def ack(self, message_id: str) -> None:
        """Acknowledge successful message processing."""
        with self._lock:
            if message_id in self._processing:
                message = self._processing.pop(message_id)
                message.status = MessageStatus.COMPLETED
                
                self.logger.info(
                    "Message acknowledged",
                    extra={
                        "message_id": message_id,
                        "processing_time": (datetime.now() - message.created_at).total_seconds()
                    }
                )
            else:
                raise MessageNotFoundError(
                    f"Message {message_id} not found in processing queue",
                    error_code="MESSAGE_NOT_PROCESSING"
                )
    
    async def nack(self, message_id: str, requeue: bool = True) -> None:
        """Handle failed message processing."""
        with self._lock:
            if message_id not in self._processing:
                raise MessageNotFoundError(
                    f"Message {message_id} not found in processing queue",
                    error_code="MESSAGE_NOT_PROCESSING"
                )
            
            message = self._processing.pop(message_id)
            message.retry_count += 1
            
            if requeue and message.can_retry():
                # Re-queue for retry
                message.status = MessageStatus.RETRYING
                heappush(self._queue, message)
                self._not_empty.set()
                
                self.logger.warning(
                    "Message requeued for retry",
                    extra={
                        "message_id": message_id,
                        "retry_count": message.retry_count,
                        "max_retries": message.max_retries
                    }
                )
            else:
                # Mark as failed
                message.status = MessageStatus.FAILED
                
                self.logger.error(
                    "Message failed permanently",
                    extra={
                        "message_id": message_id,
                        "retry_count": message.retry_count,
                        "max_retries": message.max_retries
                    }
                )
    
    async def size(self) -> int:
        """Get total queue size (pending + processing)."""
        with self._lock:
            return len(self._queue) + len(self._processing)
    
    async def clear(self) -> None:
        """Clear all messages."""
        with self._lock:
            self._queue.clear()
            self._processing.clear()
            self._not_empty.clear()
            
            self.logger.info("Queue cleared")
    
    def _cleanup_expired(self) -> None:
        """Remove expired messages from queue."""
        current_time = datetime.now()
        expired_count = 0
        
        # Filter out expired messages
        new_queue = []
        for message in self._queue:
            if message.is_expired():
                message.status = MessageStatus.EXPIRED
                expired_count += 1
                self.logger.warning(
                    "Message expired",
                    extra={
                        "message_id": message.id,
                        "created_at": message.created_at.isoformat(),
                        "expires_at": message.expires_at.isoformat()
                    }
                )
            else:
                new_queue.append(message)
        
        if expired_count > 0:
            self._queue = new_queue
            # Rebuild heap property
            self._queue.sort()
            
    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        with self._lock:
            priority_counts = {}
            for priority in MessagePriority:
                priority_counts[priority.name] = 0
            
            for message in self._queue:
                priority_counts[message.priority.name] += 1
            
            return {
                "queue_size": len(self._queue),
                "processing_count": len(self._processing),
                "total_size": len(self._queue) + len(self._processing),
                "priority_breakdown": priority_counts,
                "max_size": self.max_size
            }


class MessageQueue:
    """
    High-level message queue interface with additional features.
    
    Provides a user-friendly interface for queue operations with:
    - Automatic message ID generation
    - Message filtering and search
    - Queue statistics and monitoring
    - Event callbacks for message lifecycle
    """
    
    def __init__(
        self, 
        backend: Optional[QueueBackend] = None,
        max_size: Optional[int] = None,
        name: str = "default"
    ):
        """
        Initialize message queue.
        
        Args:
            backend: Queue storage backend (defaults to in-memory)
            max_size: Maximum queue size
            name: Queue name for logging
        """
        self.name = name
        self.backend = backend or InMemoryQueueBackend(max_size)
        self.logger = AgentLogger(f"message_queue.{name}")
        
        # Event callbacks
        self.on_message_queued: Optional[Callable[[Message], None]] = None
        self.on_message_processed: Optional[Callable[[Message], None]] = None
        self.on_message_failed: Optional[Callable[[Message, str], None]] = None
        
        # Statistics
        self.stats = {
            "messages_queued": 0,
            "messages_processed": 0,
            "messages_failed": 0,
            "total_processing_time": 0.0
        }
        
        self.logger.info(f"Message queue '{name}' initialized")
    
    async def send_message(
        self,
        sender: str,
        receiver: str,
        message_type: str,
        payload: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
        expires_in: Optional[timedelta] = None,
        max_retries: int = 3
    ) -> str:
        """
        Send a message to the queue.
        
        Args:
            sender: Sending agent ID
            receiver: Target agent ID
            message_type: Type of message/task
            payload: Message data
            priority: Message priority
            expires_in: Message expiration time from now
            max_retries: Maximum retry attempts
            
        Returns:
            Message ID
        """
        expires_at = None
        if expires_in:
            expires_at = datetime.now() + expires_in
        
        message = Message(
            id=str(uuid.uuid4()),
            sender=sender,
            receiver=receiver,
            message_type=message_type,
            payload=payload,
            priority=priority,
            expires_at=expires_at,
            max_retries=max_retries
        )
        
        await self.backend.put(message)
        
        self.stats["messages_queued"] += 1
        
        if self.on_message_queued:
            self.on_message_queued(message)
        
        return message.id
    
    async def receive_message(self, timeout: Optional[float] = None) -> Optional[Message]:
        """
        Receive next message from queue.
        
        Args:
            timeout: Maximum wait time in seconds
            
        Returns:
            Next message or None if timeout
        """
        return await self.backend.get(timeout)
    
    async def acknowledge_message(self, message_id: str) -> None:
        """Mark message as successfully processed."""
        await self.backend.ack(message_id)
        self.stats["messages_processed"] += 1
        
        if self.on_message_processed:
            # Would need to store message reference for callback
            pass
    
    async def reject_message(self, message_id: str, error: str, requeue: bool = True) -> None:
        """Mark message as failed."""
        await self.backend.nack(message_id, requeue)
        self.stats["messages_failed"] += 1
        
        if self.on_message_failed:
            # Would need to store message reference for callback
            pass
    
    async def peek_next(self) -> Optional[Message]:
        """Peek at next message without removing it."""
        return await self.backend.peek()
    
    async def get_size(self) -> int:
        """Get queue size."""
        return await self.backend.size()
    
    async def clear(self) -> None:
        """Clear all messages."""
        await self.backend.clear()
        self.logger.warning(f"Queue '{self.name}' cleared")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get queue statistics."""
        base_stats = self.stats.copy()
        
        if hasattr(self.backend, 'get_stats'):
            backend_stats = self.backend.get_stats()
            base_stats.update(backend_stats)
        
        return base_stats


# Factory function for creating message queues
def create_message_queue(
    queue_type: str = "memory",
    name: str = "default",
    max_size: Optional[int] = None,
    **kwargs
) -> MessageQueue:
    """
    Factory function to create message queues.
    
    Args:
        queue_type: Type of queue backend ("memory", "redis")
        name: Queue name
        max_size: Maximum queue size
        **kwargs: Additional backend-specific parameters
        
    Returns:
        MessageQueue instance
    """
    if queue_type == "memory":
        backend = InMemoryQueueBackend(max_size)
    elif queue_type == "redis":
        # Redis backend not yet implemented - using in-memory fallback
        # Future enhancement: implement RedisQueueBackend with redis-py
        raise NotImplementedError("Redis backend not yet implemented. Use 'memory' queue type instead.")
    else:
        raise ValueError(f"Unknown queue type: {queue_type}")
    
    return MessageQueue(backend=backend, name=name)


# Utility functions
def create_test_message(
    sender: str = "test_sender",
    receiver: str = "test_receiver",
    message_type: str = "test_task",
    payload: Optional[Dict[str, Any]] = None,
    priority: MessagePriority = MessagePriority.NORMAL
) -> Message:
    """Create a test message for development and testing."""
    if payload is None:
        payload = {"test_data": "sample_value"}
    
    return Message(
        id=str(uuid.uuid4()),
        sender=sender,
        receiver=receiver,
        message_type=message_type,
        payload=payload,
        priority=priority
    )
