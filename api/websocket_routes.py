#!/usr/bin/env python3
"""
Real-time WebSocket Routes for AI Agent 3D Print System

Provides WebSocket endpoints for real-time communication, live updates,
and interactive features between the web interface and backend system.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, Any
import asyncio
import json
from datetime import datetime

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from core.websocket_manager import websocket_manager, MessageType
from core.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/connect")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for client connections"""
    connection = None
    try:
        # Accept the connection
        connection = await websocket_manager.connect(websocket)
        client_id = connection.client_id
        
        logger.info(f"🔌 WebSocket client connected: {client_id}")
        
        # Message handling loop
        while True:
            try:
                # Receive message from client
                message = await connection.receive_message()
                if message:
                    await websocket_manager.handle_client_message(client_id, message)
                
            except WebSocketDisconnect:
                logger.info(f"🔌 WebSocket client disconnected: {client_id}")
                break
            except Exception as e:
                logger.error(f"❌ Error handling WebSocket message for {client_id}: {e}")
                await connection.send_message(MessageType.SYSTEM_ALERT, {
                    "level": "error",
                    "message": f"Message handling error: {str(e)}"
                })
    
    except Exception as e:
        logger.error(f"❌ WebSocket connection error: {e}")
    
    finally:
        # Cleanup on disconnect
        if connection:
            await websocket_manager.disconnect(connection.client_id)


@router.websocket("/progress")
async def progress_websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint specifically for progress updates"""
    connection = None
    try:
        # Accept the connection
        connection = await websocket_manager.connect(websocket)
        client_id = connection.client_id
        
        logger.info(f"🔌 Progress WebSocket client connected: {client_id}")
        
        # Send initial connection confirmation
        await connection.send_message(MessageType.SYSTEM_ALERT, {
            "type": "connection_established",
            "message": "Progress WebSocket connected successfully",
            "client_id": client_id
        })
        
        # Message handling loop for progress updates
        while True:
            try:
                # Receive message from client (mostly keep-alive pings)
                message = await connection.receive_message()
                
                # Handle specific progress-related messages
                if message and isinstance(message, dict):
                    if message.get("type") == "subscribe_job":
                        job_id = message.get("job_id")
                        if job_id:
                            # Subscribe client to specific job progress
                            await connection.send_message(MessageType.WORKFLOW_PROGRESS, {
                                "job_id": job_id,
                                "subscribed": True,
                                "message": f"Subscribed to job {job_id} progress updates"
                            })
                    
                    elif message.get("type") == "ping":
                        # Respond to ping with pong
                        await connection.send_message(MessageType.SYSTEM_ALERT, {
                            "type": "pong",
                            "timestamp": datetime.now().isoformat()
                        })
                
            except WebSocketDisconnect:
                logger.info(f"🔌 Progress WebSocket client disconnected: {client_id}")
                break
            except Exception as e:
                logger.error(f"❌ Error handling progress WebSocket message for {client_id}: {e}")
                await connection.send_message(MessageType.SYSTEM_ALERT, {
                    "type": "error",
                    "message": f"Error processing message: {str(e)}"
                })
                
    except Exception as e:
        logger.error(f"❌ Progress WebSocket connection error: {e}")
        if connection:
            try:
                await connection.send_message(MessageType.SYSTEM_ALERT, {
                    "type": "connection_error",
                    "message": f"Connection error: {str(e)}"
                })
            except:
                pass
    finally:
        if connection:
            await websocket_manager.disconnect(connection.client_id)


@router.get("/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics"""
    try:
        stats = websocket_manager.get_stats()
        return JSONResponse(content={
            "success": True,
            "data": stats
        })
    except Exception as e:
        logger.error(f"❌ Error getting WebSocket stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/broadcast")
async def broadcast_message(
    message_type: str,
    data: Dict[str, Any],
    topic: str = None
):
    """Broadcast a message to all connected clients or specific topic subscribers"""
    try:
        # Validate message type
        try:
            msg_type = MessageType(message_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid message type: {message_type}")
        
        # Broadcast the message
        await websocket_manager.broadcast(msg_type, data, topic)
        
        return JSONResponse(content={
            "success": True,
            "message": f"Message broadcasted to {topic if topic else 'all clients'}"
        })
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error broadcasting message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send/{client_id}")
async def send_message_to_client(
    client_id: str,
    message_type: str,
    data: Dict[str, Any]
):
    """Send a message to a specific client"""
    try:
        # Validate message type
        try:
            msg_type = MessageType(message_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid message type: {message_type}")
        
        # Send the message
        success = await websocket_manager.send_to_client(client_id, msg_type, data)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Client {client_id} not found or unreachable")
        
        return JSONResponse(content={
            "success": True,
            "message": f"Message sent to client {client_id}"
        })
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error sending message to client {client_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Helper functions for integration with other parts of the system

async def notify_workflow_progress(job_id: str, stage: str, progress: float, details: Dict[str, Any] = None):
    """Notify all clients about workflow progress"""
    await websocket_manager.broadcast(MessageType.WORKFLOW_PROGRESS, {
        "job_id": job_id,
        "stage": stage,
        "progress": progress,
        "details": details or {}
    }, topic="workflow_updates")


async def notify_print_status(job_id: str, status: str, details: Dict[str, Any] = None):
    """Notify all clients about print status changes"""
    message_type_map = {
        "started": MessageType.PRINT_STARTED,
        "progress": MessageType.PRINT_PROGRESS,
        "completed": MessageType.PRINT_COMPLETED,
        "error": MessageType.PRINT_ERROR
    }
    
    msg_type = message_type_map.get(status, MessageType.STATUS_UPDATE)
    
    await websocket_manager.broadcast(msg_type, {
        "job_id": job_id,
        "status": status,
        "details": details or {}
    }, topic="print_updates")


async def notify_batch_progress(batch_id: str, progress: Dict[str, Any]):
    """Notify all clients about batch processing progress"""
    await websocket_manager.broadcast(MessageType.BATCH_PROGRESS, {
        "batch_id": batch_id,
        "progress": progress
    }, topic="batch_updates")


async def notify_system_alert(level: str, message: str, details: Dict[str, Any] = None):
    """Send system alert to all clients"""
    msg_type = MessageType.PERFORMANCE_WARNING if level == "warning" else MessageType.SYSTEM_ALERT
    
    await websocket_manager.broadcast(msg_type, {
        "level": level,
        "message": message,
        "details": details or {}
    })


async def send_real_time_metrics(metrics: Dict[str, Any]):
    """Send real-time system metrics to subscribed clients"""
    await websocket_manager.broadcast(MessageType.REAL_TIME_METRICS, metrics, topic="metrics_updates")


async def notify_analytics_update(analytics_data: Dict[str, Any]):
    """Send analytics updates to subscribed clients"""
    await websocket_manager.broadcast(MessageType.ANALYTICS_UPDATE, analytics_data, topic="analytics_updates")


# Health check function
async def websocket_health_check():
    """Check WebSocket manager health"""
    try:
        stats = websocket_manager.get_stats()
        return {
            "status": "healthy",
            "active_connections": stats["active_connections"],
            "total_connections": stats["total_connections"],
            "last_activity": stats["last_activity"]
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


# Startup and shutdown handlers
async def websocket_startup():
    """Initialize WebSocket manager on startup"""
    logger.info("🚀 Starting WebSocket manager...")


async def websocket_shutdown():
    """Cleanup WebSocket manager on shutdown"""
    logger.info("🔌 Shutting down WebSocket manager...")
    await websocket_manager.shutdown()
