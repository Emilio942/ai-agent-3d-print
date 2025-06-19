#!/usr/bin/env python3
"""
WebSocket Manager for Real-time Communication
AI Agent 3D Print System

Provides real-time bidirectional communication between the web interface
and the backend system for live updates, status monitoring, and interactive features.
"""

import asyncio
import json
import time
from typing import Dict, List, Set, Any, Optional
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from enum import Enum
import uuid

from core.logger import get_logger

logger = get_logger(__name__)


class MessageType(Enum):
    """WebSocket message types"""
    # Status updates
    STATUS_UPDATE = "status_update"
    WORKFLOW_PROGRESS = "workflow_progress"
    SYSTEM_HEALTH = "system_health"
    
    # Print job updates
    PRINT_STARTED = "print_started"
    PRINT_PROGRESS = "print_progress"
    PRINT_COMPLETED = "print_completed"
    PRINT_ERROR = "print_error"
    
    # Batch processing
    BATCH_STARTED = "batch_started"
    BATCH_PROGRESS = "batch_progress"
    BATCH_COMPLETED = "batch_completed"
    
    # System alerts
    SYSTEM_ALERT = "system_alert"
    PERFORMANCE_WARNING = "performance_warning"
    
    # User interactions
    USER_CONNECT = "user_connect"
    USER_DISCONNECT = "user_disconnect"
    HEARTBEAT = "heartbeat"
    
    # Analytics
    ANALYTICS_UPDATE = "analytics_update"
    REAL_TIME_METRICS = "real_time_metrics"


class WebSocketConnection:
    """Individual WebSocket connection wrapper"""
    
    def __init__(self, websocket: WebSocket, client_id: str = None):
        self.websocket = websocket
        self.client_id = client_id or str(uuid.uuid4())
        self.connected_at = datetime.now()
        self.last_heartbeat = time.time()
        self.subscriptions: Set[str] = set()
        self.user_info: Dict[str, Any] = {}
    
    async def send_message(self, message_type: MessageType, data: Dict[str, Any]):
        """Send a message to the client"""
        try:
            message = {
                "type": message_type.value,
                "timestamp": datetime.now().isoformat(),
                "client_id": self.client_id,
                "data": data
            }
            await self.websocket.send_text(json.dumps(message))
            return True
        except Exception as e:
            logger.error(f"Failed to send message to {self.client_id}: {e}")
            return False
    
    async def receive_message(self) -> Optional[Dict[str, Any]]:
        """Receive a message from the client"""
        try:
            data = await self.websocket.receive_text()
            return json.loads(data)
        except WebSocketDisconnect:
            raise
        except Exception as e:
            logger.error(f"Failed to receive message from {self.client_id}: {e}")
            return None
    
    def update_heartbeat(self):
        """Update the last heartbeat timestamp"""
        self.last_heartbeat = time.time()
    
    def is_alive(self, timeout: int = 60) -> bool:
        """Check if connection is still alive based on heartbeat"""
        return (time.time() - self.last_heartbeat) < timeout


class WebSocketManager:
    """Manage all WebSocket connections and broadcasting"""
    
    def __init__(self):
        self.connections: Dict[str, WebSocketConnection] = {}
        self.subscriptions: Dict[str, Set[str]] = {}  # topic -> client_ids
        self.logger = get_logger(f"{__name__}.WebSocketManager")
        self.heartbeat_task = None
        self.cleanup_task = None
        
        # Statistics
        self.stats = {
            "total_connections": 0,
            "active_connections": 0,
            "messages_sent": 0,
            "messages_received": 0,
            "last_activity": None
        }
    
    async def connect(self, websocket: WebSocket, client_id: str = None) -> WebSocketConnection:
        """Accept and register a new WebSocket connection"""
        await websocket.accept()
        
        connection = WebSocketConnection(websocket, client_id)
        self.connections[connection.client_id] = connection
        
        self.stats["total_connections"] += 1
        self.stats["active_connections"] = len(self.connections)
        self.stats["last_activity"] = datetime.now()
        
        # Send welcome message
        await connection.send_message(MessageType.USER_CONNECT, {
            "client_id": connection.client_id,
            "connected_at": connection.connected_at.isoformat(),
            "message": "Connected to AI Agent 3D Print System"
        })
        
        # Start heartbeat if first connection
        if len(self.connections) == 1:
            await self._start_background_tasks()
        
        self.logger.info(f"🔌 WebSocket connected: {connection.client_id} (Total: {len(self.connections)})")
        return connection
    
    async def disconnect(self, client_id: str):
        """Disconnect and cleanup a WebSocket connection"""
        if client_id in self.connections:
            connection = self.connections[client_id]
            
            # Remove from all subscriptions
            for topic_clients in self.subscriptions.values():
                topic_clients.discard(client_id)
            
            # Remove connection
            del self.connections[client_id]
            self.stats["active_connections"] = len(self.connections)
            
            # Stop background tasks if no connections
            if len(self.connections) == 0:
                await self._stop_background_tasks()
            
            self.logger.info(f"🔌 WebSocket disconnected: {client_id} (Remaining: {len(self.connections)})")
    
    async def subscribe(self, client_id: str, topic: str):
        """Subscribe a client to a specific topic"""
        if topic not in self.subscriptions:
            self.subscriptions[topic] = set()
        
        self.subscriptions[topic].add(client_id)
        self.logger.debug(f"📡 Client {client_id} subscribed to {topic}")
    
    async def unsubscribe(self, client_id: str, topic: str):
        """Unsubscribe a client from a topic"""
        if topic in self.subscriptions:
            self.subscriptions[topic].discard(client_id)
        self.logger.debug(f"📡 Client {client_id} unsubscribed from {topic}")
    
    async def broadcast(self, message_type: MessageType, data: Dict[str, Any], topic: str = None):
        """Broadcast a message to all clients or clients subscribed to a topic"""
        if topic and topic in self.subscriptions:
            target_clients = self.subscriptions[topic]
        else:
            target_clients = set(self.connections.keys())
        
        if not target_clients:
            return
        
        successful_sends = 0
        failed_connections = []
        
        for client_id in target_clients:
            if client_id in self.connections:
                connection = self.connections[client_id]
                success = await connection.send_message(message_type, data)
                if success:
                    successful_sends += 1
                else:
                    failed_connections.append(client_id)
        
        # Cleanup failed connections
        for client_id in failed_connections:
            await self.disconnect(client_id)
        
        self.stats["messages_sent"] += successful_sends
        self.stats["last_activity"] = datetime.now()
        
        if successful_sends > 0:
            self.logger.debug(f"📢 Broadcast {message_type.value} to {successful_sends} clients" + 
                            (f" (topic: {topic})" if topic else ""))
    
    async def send_to_client(self, client_id: str, message_type: MessageType, data: Dict[str, Any]) -> bool:
        """Send a message to a specific client"""
        if client_id not in self.connections:
            return False
        
        connection = self.connections[client_id]
        success = await connection.send_message(message_type, data)
        
        if success:
            self.stats["messages_sent"] += 1
            self.stats["last_activity"] = datetime.now()
        else:
            await self.disconnect(client_id)
        
        return success
    
    async def handle_client_message(self, client_id: str, message: Dict[str, Any]):
        """Handle incoming message from a client"""
        if client_id not in self.connections:
            return
        
        connection = self.connections[client_id]
        self.stats["messages_received"] += 1
        self.stats["last_activity"] = datetime.now()
        
        message_type = message.get("type")
        data = message.get("data", {})
        
        # Handle different message types
        if message_type == "heartbeat":
            connection.update_heartbeat()
            await connection.send_message(MessageType.HEARTBEAT, {"status": "alive"})
        
        elif message_type == "subscribe":
            topic = data.get("topic")
            if topic:
                await self.subscribe(client_id, topic)
        
        elif message_type == "unsubscribe":
            topic = data.get("topic")
            if topic:
                await self.unsubscribe(client_id, topic)
        
        elif message_type == "user_info":
            connection.user_info.update(data)
            self.logger.debug(f"👤 Updated user info for {client_id}: {data}")
        
        else:
            self.logger.warning(f"❓ Unknown message type from {client_id}: {message_type}")
    
    async def _start_background_tasks(self):
        """Start background tasks for heartbeat and cleanup"""
        if not self.heartbeat_task:
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        if not self.cleanup_task:
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def _stop_background_tasks(self):
        """Stop background tasks"""
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            self.heartbeat_task = None
        if self.cleanup_task:
            self.cleanup_task.cancel()
            self.cleanup_task = None
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeat to all connections"""
        try:
            while True:
                await asyncio.sleep(30)  # Heartbeat every 30 seconds
                if self.connections:
                    await self.broadcast(MessageType.HEARTBEAT, {
                        "timestamp": datetime.now().isoformat(),
                        "active_connections": len(self.connections)
                    })
        except asyncio.CancelledError:
            pass
    
    async def _cleanup_loop(self):
        """Cleanup dead connections"""
        try:
            while True:
                await asyncio.sleep(60)  # Check every minute
                dead_connections = []
                
                for client_id, connection in self.connections.items():
                    if not connection.is_alive():
                        dead_connections.append(client_id)
                
                for client_id in dead_connections:
                    await self.disconnect(client_id)
                    self.logger.info(f"🧹 Cleaned up dead connection: {client_id}")
        
        except asyncio.CancelledError:
            pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get WebSocket statistics"""
        return {
            **self.stats,
            "subscriptions": {topic: len(clients) for topic, clients in self.subscriptions.items()},
            "connection_details": [
                {
                    "client_id": conn.client_id,
                    "connected_at": conn.connected_at.isoformat(),
                    "last_heartbeat": conn.last_heartbeat,
                    "subscriptions": list(conn.subscriptions),
                    "user_info": conn.user_info
                }
                for conn in self.connections.values()
            ]
        }
    
    async def shutdown(self):
        """Shutdown the WebSocket manager"""
        # Notify all clients
        await self.broadcast(MessageType.SYSTEM_ALERT, {
            "message": "Server shutting down",
            "level": "info"
        })
        
        # Close all connections
        for client_id in list(self.connections.keys()):
            await self.disconnect(client_id)
        
        # Stop background tasks
        await self._stop_background_tasks()
        
        self.logger.info("🔌 WebSocket manager shutdown complete")


# Global instance
websocket_manager = WebSocketManager()
