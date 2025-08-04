"""
AI Agents WebSocket Endpoints.

This module provides WebSocket endpoints for real-time progress tracking
and status updates for AI agent operations.
"""

import json
import asyncio
from typing import Dict, Any, Set
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.routing import APIRouter
import structlog

from ...core.auth import get_current_user_ws
from ...models.user import User
from ...services.agent_memory import get_memory_manager

logger = structlog.get_logger(__name__)

# WebSocket router
ws_router = APIRouter()

# Connection manager for WebSocket connections
class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_connections: Dict[str, Set[str]] = {}
        self.execution_subscribers: Dict[str, Set[str]] = {}
        self.workflow_subscribers: Dict[str, Set[str]] = {}
    
    async def connect(self, websocket: WebSocket, connection_id: str, user_id: str):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(connection_id)
        
        logger.info(f"WebSocket connected: {connection_id} for user {user_id}")
    
    def disconnect(self, connection_id: str, user_id: str):
        """Remove a WebSocket connection."""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        
        if user_id in self.user_connections:
            self.user_connections[user_id].discard(connection_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        # Remove from all subscriptions
        for execution_id in list(self.execution_subscribers.keys()):
            self.execution_subscribers[execution_id].discard(connection_id)
            if not self.execution_subscribers[execution_id]:
                del self.execution_subscribers[execution_id]
        
        for workflow_id in list(self.workflow_subscribers.keys()):
            self.workflow_subscribers[workflow_id].discard(connection_id)
            if not self.workflow_subscribers[workflow_id]:
                del self.workflow_subscribers[workflow_id]
        
        logger.info(f"WebSocket disconnected: {connection_id}")
    
    async def send_personal_message(self, message: Dict[str, Any], connection_id: str):
        """Send a message to a specific connection."""
        if connection_id in self.active_connections:
            try:
                await self.active_connections[connection_id].send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Failed to send message to {connection_id}: {e}")
                # Connection might be dead, remove it
                if connection_id in self.active_connections:
                    del self.active_connections[connection_id]
    
    async def send_to_user(self, message: Dict[str, Any], user_id: str):
        """Send a message to all connections for a user."""
        if user_id in self.user_connections:
            for connection_id in list(self.user_connections[user_id]):
                await self.send_personal_message(message, connection_id)
    
    def subscribe_to_execution(self, connection_id: str, execution_id: str):
        """Subscribe a connection to execution updates."""
        if execution_id not in self.execution_subscribers:
            self.execution_subscribers[execution_id] = set()
        self.execution_subscribers[execution_id].add(connection_id)
    
    def subscribe_to_workflow(self, connection_id: str, workflow_id: str):
        """Subscribe a connection to workflow updates."""
        if workflow_id not in self.workflow_subscribers:
            self.workflow_subscribers[workflow_id] = set()
        self.workflow_subscribers[workflow_id].add(connection_id)
    
    async def broadcast_execution_update(self, execution_id: str, update: Dict[str, Any]):
        """Broadcast execution update to all subscribers."""
        if execution_id in self.execution_subscribers:
            message = {
                "type": "execution_update",
                "execution_id": execution_id,
                "data": update,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            for connection_id in list(self.execution_subscribers[execution_id]):
                await self.send_personal_message(message, connection_id)
    
    async def broadcast_workflow_update(self, workflow_id: str, update: Dict[str, Any]):
        """Broadcast workflow update to all subscribers."""
        if workflow_id in self.workflow_subscribers:
            message = {
                "type": "workflow_update",
                "workflow_id": workflow_id,
                "data": update,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            for connection_id in list(self.workflow_subscribers[workflow_id]):
                await self.send_personal_message(message, connection_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        return {
            "total_connections": len(self.active_connections),
            "users_connected": len(self.user_connections),
            "execution_subscriptions": len(self.execution_subscribers),
            "workflow_subscriptions": len(self.workflow_subscribers)
        }


# Global connection manager
manager = ConnectionManager()


@ws_router.websocket("/ws/ai-agents/{connection_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    connection_id: str,
    token: str = None
):
    """WebSocket endpoint for real-time AI agent updates."""
    try:
        # Authenticate user (simplified - in production, use proper token validation)
        if not token:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        
        # For now, extract user_id from token (in production, validate JWT)
        user_id = token  # Simplified - replace with actual JWT validation
        
        await manager.connect(websocket, connection_id, user_id)
        
        # Send welcome message
        await manager.send_personal_message({
            "type": "connection_established",
            "connection_id": connection_id,
            "timestamp": datetime.utcnow().isoformat()
        }, connection_id)
        
        try:
            while True:
                # Receive messages from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                await handle_websocket_message(connection_id, user_id, message)
                
        except WebSocketDisconnect:
            manager.disconnect(connection_id, user_id)
            logger.info(f"WebSocket disconnected: {connection_id}")
        
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except:
            pass


async def handle_websocket_message(connection_id: str, user_id: str, message: Dict[str, Any]):
    """Handle incoming WebSocket messages."""
    try:
        message_type = message.get("type")
        
        if message_type == "subscribe_execution":
            execution_id = message.get("execution_id")
            if execution_id:
                manager.subscribe_to_execution(connection_id, execution_id)
                await manager.send_personal_message({
                    "type": "subscription_confirmed",
                    "subscription_type": "execution",
                    "execution_id": execution_id
                }, connection_id)
        
        elif message_type == "subscribe_workflow":
            workflow_id = message.get("workflow_id")
            if workflow_id:
                manager.subscribe_to_workflow(connection_id, workflow_id)
                await manager.send_personal_message({
                    "type": "subscription_confirmed",
                    "subscription_type": "workflow",
                    "workflow_id": workflow_id
                }, connection_id)
        
        elif message_type == "ping":
            await manager.send_personal_message({
                "type": "pong",
                "timestamp": datetime.utcnow().isoformat()
            }, connection_id)
        
        elif message_type == "get_stats":
            stats = manager.get_stats()
            await manager.send_personal_message({
                "type": "stats",
                "data": stats
            }, connection_id)
        
        else:
            await manager.send_personal_message({
                "type": "error",
                "message": f"Unknown message type: {message_type}"
            }, connection_id)
    
    except Exception as e:
        logger.error(f"Error handling WebSocket message: {e}")
        await manager.send_personal_message({
            "type": "error",
            "message": "Failed to process message"
        }, connection_id)


# Progress tracking functions that can be called from agent execution
async def notify_execution_progress(execution_id: str, progress: float, status: str, details: Dict[str, Any] = None):
    """Notify WebSocket subscribers about execution progress."""
    update = {
        "progress": progress,
        "status": status,
        "details": details or {},
        "updated_at": datetime.utcnow().isoformat()
    }
    
    await manager.broadcast_execution_update(execution_id, update)


async def notify_workflow_progress(workflow_id: str, progress: float, status: str, details: Dict[str, Any] = None):
    """Notify WebSocket subscribers about workflow progress."""
    update = {
        "progress": progress,
        "status": status,
        "details": details or {},
        "updated_at": datetime.utcnow().isoformat()
    }
    
    await manager.broadcast_workflow_update(workflow_id, update)


async def notify_agent_event(user_id: str, event_type: str, data: Dict[str, Any]):
    """Notify a specific user about an agent event."""
    message = {
        "type": "agent_event",
        "event_type": event_type,
        "data": data,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    await manager.send_to_user(message, user_id)


# Background task for periodic updates
async def start_progress_monitor():
    """Start background task for monitoring and broadcasting progress updates."""
    while True:
        try:
            # Check for any pending updates from the memory manager
            memory_manager = get_memory_manager()
            
            # Get collaboration summary
            summary = await memory_manager.get_collaboration_summary()
            
            # Broadcast system status to all connected users
            if manager.active_connections:
                system_status = {
                    "type": "system_status",
                    "data": {
                        "active_workflows": summary.get("workflow_states", 0),
                        "active_agents": summary.get("active_agents", 0),
                        "performance_metrics": summary.get("performance_metrics", 0),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
                
                # Send to all connections (could be optimized to send only to interested users)
                for connection_id in list(manager.active_connections.keys()):
                    await manager.send_personal_message(system_status, connection_id)
            
            # Wait before next update
            await asyncio.sleep(30)  # Update every 30 seconds
            
        except Exception as e:
            logger.error(f"Progress monitor error: {e}")
            await asyncio.sleep(60)  # Wait longer on error


# Function to get connection manager (for use in other modules)
def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager instance."""
    return manager


# Health check endpoint for WebSocket service
@ws_router.get("/ws/health")
async def websocket_health():
    """Health check for WebSocket service."""
    stats = manager.get_stats()
    return {
        "status": "healthy",
        "websocket_stats": stats,
        "timestamp": datetime.utcnow().isoformat()
    }
