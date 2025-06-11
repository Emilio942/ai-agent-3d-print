"""
Unit tests for Message Queue system.

Tests cover:
- Message creation and serialization
- Priority queue operations
- Message lifecycle (pending -> processing -> completed/failed)
- Retry mechanisms
- Message expiration
- Queue statistics and monitoring
- Backend implementations
"""

import asyncio
import pytest
import time
from datetime import datetime, timedelta
from typing import Dict, Any

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.message_queue import (
    Message, MessagePriority, MessageStatus, MessageQueue,
    InMemoryQueueBackend, create_message_queue, create_test_message
)
from core.exceptions import (
    MessageQueueError, MessageNotFoundError, QueueFullError,
    MessageExpiredError, InvalidMessageError
)


class TestMessage:
    """Test Message class functionality."""
    
    def test_message_creation(self):
        """Test basic message creation."""
        message = Message(
            id="test-123",
            sender="agent_a",
            receiver="agent_b", 
            message_type="test_task",
            payload={"key": "value"}
        )
        
        assert message.id == "test-123"
        assert message.sender == "agent_a"
        assert message.receiver == "agent_b"
        assert message.message_type == "test_task"
        assert message.payload == {"key": "value"}
        assert message.priority == MessagePriority.NORMAL
        assert message.status == MessageStatus.PENDING
        assert message.retry_count == 0
        assert message.max_retries == 3
        assert isinstance(message.created_at, datetime)
    
    def test_message_auto_id(self):
        """Test automatic ID generation."""
        message = Message(
            id="",
            sender="test",
            receiver="test",
            message_type="test",
            payload={}
        )
        
        assert message.id  # Should be automatically generated
        assert len(message.id) == 36  # UUID4 length
    
    def test_message_priority_comparison(self):
        """Test message priority ordering."""
        high_msg = Message(
            id="high",
            sender="test", receiver="test", message_type="test", payload={},
            priority=MessagePriority.HIGH
        )
        
        normal_msg = Message(
            id="normal", 
            sender="test", receiver="test", message_type="test", payload={},
            priority=MessagePriority.NORMAL
        )
        
        low_msg = Message(
            id="low",
            sender="test", receiver="test", message_type="test", payload={},
            priority=MessagePriority.LOW
        )
        
        # Higher priority (lower number) comes first
        assert high_msg < normal_msg
        assert normal_msg < low_msg
        assert high_msg < low_msg
    
    def test_message_time_ordering(self):
        """Test time-based ordering for same priority."""
        import time
        
        first_msg = Message(
            id="first",
            sender="test", receiver="test", message_type="test", payload={},
            priority=MessagePriority.NORMAL
        )
        
        time.sleep(0.001)  # Ensure different timestamps
        
        second_msg = Message(
            id="second",
            sender="test", receiver="test", message_type="test", payload={},
            priority=MessagePriority.NORMAL
        )
        
        # Older messages come first for same priority
        assert first_msg < second_msg
    
    def test_message_expiration(self):
        """Test message expiration logic."""
        # Non-expiring message
        message1 = Message(
            id="no-expire",
            sender="test", receiver="test", message_type="test", payload={}
        )
        assert not message1.is_expired()
        
        # Expired message
        message2 = Message(
            id="expired",
            sender="test", receiver="test", message_type="test", payload={},
            expires_at=datetime.now() - timedelta(seconds=1)
        )
        assert message2.is_expired()
        
        # Future expiration
        message3 = Message(
            id="future",
            sender="test", receiver="test", message_type="test", payload={},
            expires_at=datetime.now() + timedelta(seconds=10)
        )
        assert not message3.is_expired()
    
    def test_message_retry_logic(self):
        """Test retry count logic."""
        message = Message(
            id="retry-test",
            sender="test", receiver="test", message_type="test", payload={},
            max_retries=2
        )
        
        assert message.can_retry()  # 0 < 2
        
        message.retry_count = 1
        assert message.can_retry()  # 1 < 2
        
        message.retry_count = 2
        assert not message.can_retry()  # 2 >= 2
        
        message.retry_count = 3
        assert not message.can_retry()  # 3 >= 2
    
    def test_message_serialization(self):
        """Test message to/from dict conversion."""
        original = Message(
            id="serialize-test",
            sender="agent_a",
            receiver="agent_b",
            message_type="test_task",
            payload={"data": "test"},
            priority=MessagePriority.HIGH,
            expires_at=datetime.now() + timedelta(hours=1),
            max_retries=5
        )
        
        # Convert to dict
        data = original.to_dict()
        assert isinstance(data, dict)
        assert data['id'] == "serialize-test"
        assert data['sender'] == "agent_a"
        assert data['priority'] == "HIGH"
        assert data['status'] == "pending"
        assert isinstance(data['created_at'], str)
        assert isinstance(data['expires_at'], str)
        
        # Convert back from dict
        restored = Message.from_dict(data)
        assert restored.id == original.id
        assert restored.sender == original.sender
        assert restored.receiver == original.receiver
        assert restored.priority == original.priority
        assert restored.status == original.status
        assert restored.max_retries == original.max_retries
        assert isinstance(restored.created_at, datetime)
        assert isinstance(restored.expires_at, datetime)


class TestInMemoryQueueBackend:
    """Test in-memory queue backend."""
    
    @pytest.fixture
    def backend(self):
        """Create test backend."""
        return InMemoryQueueBackend(max_size=10)
    
    @pytest.fixture
    def messages(self):
        """Create test messages with different priorities."""
        return [
            create_test_message("sender1", "receiver1", "task1", priority=MessagePriority.LOW),
            create_test_message("sender2", "receiver2", "task2", priority=MessagePriority.HIGH),
            create_test_message("sender3", "receiver3", "task3", priority=MessagePriority.NORMAL),
            create_test_message("sender4", "receiver4", "task4", priority=MessagePriority.CRITICAL),
        ]
    
    @pytest.mark.asyncio
    async def test_basic_put_get(self, backend, messages):
        """Test basic put and get operations."""
        # Queue should be empty initially
        assert await backend.size() == 0
        
        # Add a message
        await backend.put(messages[0])
        assert await backend.size() == 1
        
        # Get the message
        retrieved = await backend.get()
        assert retrieved is not None
        assert retrieved.id == messages[0].id
        assert retrieved.status == MessageStatus.PROCESSING
        assert await backend.size() == 1  # Still in processing
    
    @pytest.mark.asyncio
    async def test_priority_ordering(self, backend, messages):
        """Test that messages are retrieved in priority order."""
        # Add messages in random order
        for msg in messages:
            await backend.put(msg)
        
        # Should get CRITICAL first
        msg1 = await backend.get()
        assert msg1.priority == MessagePriority.CRITICAL
        
        # Then HIGH
        msg2 = await backend.get()
        assert msg2.priority == MessagePriority.HIGH
        
        # Then NORMAL
        msg3 = await backend.get()
        assert msg3.priority == MessagePriority.NORMAL
        
        # Then LOW
        msg4 = await backend.get()
        assert msg4.priority == MessagePriority.LOW
    
    @pytest.mark.asyncio
    async def test_queue_size_limit(self, messages):
        """Test queue size limits."""
        backend = InMemoryQueueBackend(max_size=2)
        
        # Add up to limit
        await backend.put(messages[0])
        await backend.put(messages[1])
        assert await backend.size() == 2
        
        # Should raise error when full
        with pytest.raises(QueueFullError):
            await backend.put(messages[2])
    
    @pytest.mark.asyncio
    async def test_message_acknowledgment(self, backend, messages):
        """Test message acknowledgment."""
        await backend.put(messages[0])
        
        # Get message
        msg = await backend.get()
        assert msg.status == MessageStatus.PROCESSING
        assert await backend.size() == 1  # In processing
        
        # Acknowledge
        await backend.ack(msg.id)
        assert await backend.size() == 0  # Removed from processing
    
    @pytest.mark.asyncio
    async def test_message_nack_with_retry(self, backend, messages):
        """Test negative acknowledgment with retry."""
        msg = messages[0]
        msg.max_retries = 2
        await backend.put(msg)
        
        # Get and nack for retry
        retrieved = await backend.get()
        await backend.nack(retrieved.id, requeue=True)
        
        # Should be back in queue with incremented retry count
        assert await backend.size() == 1
        
        # Get again
        retry_msg = await backend.get()
        assert retry_msg.retry_count == 1
        assert retry_msg.status == MessageStatus.PROCESSING
    
    @pytest.mark.asyncio
    async def test_message_nack_max_retries(self, backend, messages):
        """Test message failure after max retries."""
        msg = messages[0]
        msg.max_retries = 2  # Allow 1 retry (initial + 1 retry = 2 total attempts)
        await backend.put(msg)
        
        # First attempt
        retrieved = await backend.get()
        await backend.nack(retrieved.id, requeue=True)
        
        # Second attempt (retry)
        retry_msg = await backend.get()
        assert retry_msg.retry_count == 1
        
        # Final failure
        await backend.nack(retry_msg.id, requeue=True)
        
        # Should not be requeued (exceeded max retries)
        assert await backend.size() == 0
    
    @pytest.mark.asyncio
    async def test_peek_operation(self, backend, messages):
        """Test peek without removing message."""
        await backend.put(messages[0])
        
        # Peek should return message without removing it
        peeked = await backend.peek()
        assert peeked is not None
        assert peeked.id == messages[0].id
        assert peeked.status == MessageStatus.PENDING  # Not processing yet
        assert await backend.size() == 1
        
        # Should still be able to get the message
        retrieved = await backend.get()
        assert retrieved.id == messages[0].id
    
    @pytest.mark.asyncio
    async def test_message_expiration(self, backend):
        """Test automatic cleanup of expired messages."""
        # Create expired message
        expired_msg = create_test_message("sender", "receiver", "task")
        expired_msg.expires_at = datetime.now() - timedelta(seconds=1)
        
        # Create valid message
        valid_msg = create_test_message("sender2", "receiver2", "task2")
        
        await backend.put(expired_msg)
        await backend.put(valid_msg)
        
        # Should only get the valid message (expired one cleaned up)
        retrieved = await backend.get()
        assert retrieved.id == valid_msg.id
    
    @pytest.mark.asyncio
    async def test_clear_operation(self, backend, messages):
        """Test clearing all messages."""
        # Add messages
        for msg in messages:
            await backend.put(msg)
        
        assert await backend.size() == len(messages)
        
        # Clear
        await backend.clear()
        assert await backend.size() == 0
    
    @pytest.mark.asyncio
    async def test_duplicate_message_prevention(self, backend, messages):
        """Test prevention of duplicate message IDs."""
        msg = messages[0]
        await backend.put(msg)
        
        # Should raise error for duplicate ID
        with pytest.raises(InvalidMessageError):
            await backend.put(msg)
    
    @pytest.mark.asyncio
    async def test_get_timeout(self, backend):
        """Test get operation with timeout."""
        # Should return None after timeout
        start_time = time.time()
        result = await backend.get(timeout=0.1)
        elapsed = time.time() - start_time
        
        assert result is None
        assert 0.1 <= elapsed <= 0.2  # Should respect timeout
    
    @pytest.mark.asyncio
    async def test_ack_unknown_message(self, backend):
        """Test acknowledging unknown message."""
        with pytest.raises(MessageNotFoundError):
            await backend.ack("unknown-id")
    
    @pytest.mark.asyncio
    async def test_nack_unknown_message(self, backend):
        """Test negative acknowledging unknown message."""
        with pytest.raises(MessageNotFoundError):
            await backend.nack("unknown-id")


class TestMessageQueue:
    """Test high-level MessageQueue interface."""
    
    @pytest.fixture
    def queue(self):
        """Create test message queue."""
        return MessageQueue(name="test_queue", max_size=10)
    
    @pytest.mark.asyncio
    async def test_send_receive_message(self, queue):
        """Test sending and receiving messages."""
        # Send message
        msg_id = await queue.send_message(
            sender="agent_a",
            receiver="agent_b", 
            message_type="test_task",
            payload={"data": "test"}
        )
        
        assert isinstance(msg_id, str)
        assert await queue.get_size() == 1
        
        # Receive message
        msg = await queue.receive_message()
        assert msg is not None
        assert msg.id == msg_id
        assert msg.sender == "agent_a"
        assert msg.receiver == "agent_b"
        assert msg.message_type == "test_task"
        assert msg.payload == {"data": "test"}
    
    @pytest.mark.asyncio
    async def test_message_with_expiration(self, queue):
        """Test message with expiration time."""
        msg_id = await queue.send_message(
            sender="agent_a",
            receiver="agent_b",
            message_type="test_task", 
            payload={},
            expires_in=timedelta(hours=1)
        )
        
        msg = await queue.receive_message()
        assert msg.expires_at is not None
        assert msg.expires_at > datetime.now()
    
    @pytest.mark.asyncio
    async def test_message_acknowledgment(self, queue):
        """Test acknowledging message."""
        msg_id = await queue.send_message(
            sender="agent_a", receiver="agent_b",
            message_type="test", payload={}
        )
        
        msg = await queue.receive_message()
        await queue.acknowledge_message(msg.id)
        
        # Should track statistics
        stats = queue.get_statistics()
        assert stats["messages_processed"] == 1
    
    @pytest.mark.asyncio
    async def test_message_rejection(self, queue):
        """Test rejecting message."""
        msg_id = await queue.send_message(
            sender="agent_a", receiver="agent_b",
            message_type="test", payload={}
        )
        
        msg = await queue.receive_message()
        await queue.reject_message(msg.id, "Test error", requeue=False)
        
        # Should track statistics
        stats = queue.get_statistics()
        assert stats["messages_failed"] == 1
    
    @pytest.mark.asyncio
    async def test_peek_next_message(self, queue):
        """Test peeking at next message."""
        msg_id = await queue.send_message(
            sender="agent_a", receiver="agent_b",
            message_type="test", payload={}
        )
        
        # Peek should not remove message
        peeked = await queue.peek_next()
        assert peeked is not None
        assert peeked.id == msg_id
        assert await queue.get_size() == 1
        
        # Should still be able to receive it
        received = await queue.receive_message()
        assert received.id == msg_id
    
    @pytest.mark.asyncio
    async def test_queue_statistics(self, queue):
        """Test queue statistics tracking."""
        # Send some messages
        await queue.send_message("a", "b", "test1", {})
        await queue.send_message("a", "b", "test2", {})
        
        stats = queue.get_statistics()
        assert stats["messages_queued"] == 2
        assert stats["messages_processed"] == 0
        assert stats["messages_failed"] == 0
        
        # Process one successfully
        msg = await queue.receive_message()
        await queue.acknowledge_message(msg.id)
        
        # Fail one
        msg = await queue.receive_message()
        await queue.reject_message(msg.id, "error")
        
        stats = queue.get_statistics()
        assert stats["messages_processed"] == 1
        assert stats["messages_failed"] == 1


class TestQueueFactory:
    """Test queue factory functions."""
    
    def test_create_memory_queue(self):
        """Test creating in-memory queue."""
        queue = create_message_queue(
            queue_type="memory",
            name="test",
            max_size=100
        )
        
        assert isinstance(queue, MessageQueue)
        assert queue.name == "test"
    
    def test_create_unknown_queue_type(self):
        """Test creating unknown queue type."""
        with pytest.raises(ValueError):
            create_message_queue(queue_type="unknown")


class TestUtilities:
    """Test utility functions."""
    
    def test_create_test_message(self):
        """Test test message creation utility."""
        msg = create_test_message(
            sender="test_sender",
            receiver="test_receiver", 
            message_type="test_type",
            payload={"key": "value"},
            priority=MessagePriority.HIGH
        )
        
        assert msg.sender == "test_sender"
        assert msg.receiver == "test_receiver"
        assert msg.message_type == "test_type"
        assert msg.payload == {"key": "value"}
        assert msg.priority == MessagePriority.HIGH
        assert isinstance(msg.id, str)
        assert len(msg.id) == 36  # UUID length
    
    def test_create_test_message_defaults(self):
        """Test test message with default values."""
        msg = create_test_message()
        
        assert msg.sender == "test_sender"
        assert msg.receiver == "test_receiver"
        assert msg.message_type == "test_task"
        assert msg.payload == {"test_data": "sample_value"}
        assert msg.priority == MessagePriority.NORMAL
