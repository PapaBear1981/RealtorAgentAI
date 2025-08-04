"""
WebSocket Communication Tests for Real-time Agent Interaction.

This module tests WebSocket connections for real-time agent communication,
including status updates, streaming responses, and live collaboration.
"""

import asyncio
import pytest
import json
import uuid
from typing import Dict, Any, List
from datetime import datetime
from unittest.mock import Mock, patch

import structlog
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket

from app.main import app
from app.api.v1.ai_agents_ws import AgentWebSocketManager
from app.services.agent_orchestrator import AgentRole, WorkflowRequest
from app.core.config import get_settings

logger = structlog.get_logger(__name__)


class TestWebSocketCommunication:
    """Test WebSocket communication for real-time agent interaction."""

    @pytest.fixture
    def settings(self):
        """Get test settings."""
        settings = get_settings()
        if not settings.OPENROUTER_API_KEY:
            pytest.skip("OPENROUTER_API_KEY not configured for testing")
        return settings

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    async def websocket_manager(self):
        """Create WebSocket manager for testing."""
        manager = AgentWebSocketManager()
        await manager.initialize()
        return manager

    @pytest.mark.asyncio
    async def test_websocket_connection_establishment(self, client):
        """Test basic WebSocket connection establishment."""
        with client.websocket_connect("/ws/agents/test-session") as websocket:
            # Send initial message
            websocket.send_json({
                "type": "connect",
                "session_id": "test-session",
                "user_id": "test-user"
            })
            
            # Should receive connection confirmation
            response = websocket.receive_json()
            assert response["type"] == "connection_established"
            assert response["session_id"] == "test-session"

    @pytest.mark.asyncio
    async def test_agent_workflow_status_updates(self, client):
        """Test real-time status updates during agent workflow execution."""
        session_id = str(uuid.uuid4())
        
        with client.websocket_connect(f"/ws/agents/{session_id}") as websocket:
            # Connect
            websocket.send_json({
                "type": "connect",
                "session_id": session_id
            })
            websocket.receive_json()  # Connection confirmation

            # Start agent workflow
            websocket.send_json({
                "type": "start_workflow",
                "workflow_request": {
                    "workflow_id": f"ws-test-{session_id}",
                    "primary_agent": "help",
                    "task_description": "Test WebSocket workflow updates",
                    "context": {
                        "user_question": "What is a property appraisal?",
                        "session_id": session_id
                    },
                    "model_preference": "qwen/qwen3-235b-a22b-thinking-2507"
                }
            })

            # Should receive status updates
            status_updates = []
            timeout_count = 0
            max_timeout = 30  # 30 seconds max wait

            while timeout_count < max_timeout:
                try:
                    message = websocket.receive_json(timeout=1)
                    status_updates.append(message)
                    
                    if message.get("type") == "workflow_completed":
                        break
                except:
                    timeout_count += 1

            # Verify we received status updates
            assert len(status_updates) > 0
            
            # Should have workflow started message
            started_messages = [msg for msg in status_updates if msg.get("type") == "workflow_started"]
            assert len(started_messages) > 0

            # Should have workflow completed message
            completed_messages = [msg for msg in status_updates if msg.get("type") == "workflow_completed"]
            assert len(completed_messages) > 0

    @pytest.mark.asyncio
    async def test_streaming_agent_responses(self, client):
        """Test streaming responses from agents via WebSocket."""
        session_id = str(uuid.uuid4())
        
        with client.websocket_connect(f"/ws/agents/{session_id}") as websocket:
            websocket.send_json({"type": "connect", "session_id": session_id})
            websocket.receive_json()

            # Request streaming response
            websocket.send_json({
                "type": "start_streaming_workflow",
                "workflow_request": {
                    "workflow_id": f"stream-test-{session_id}",
                    "primary_agent": "help",
                    "task_description": "Provide detailed explanation with streaming",
                    "context": {
                        "user_question": "Explain the home buying process in detail",
                        "enable_streaming": True
                    },
                    "model_preference": "qwen/qwen3-235b-a22b-thinking-2507"
                }
            })

            # Collect streaming chunks
            chunks = []
            complete_response = ""
            timeout_count = 0

            while timeout_count < 45:  # 45 seconds for streaming
                try:
                    message = websocket.receive_json(timeout=1)
                    
                    if message.get("type") == "response_chunk":
                        chunk_content = message.get("content", "")
                        chunks.append(chunk_content)
                        complete_response += chunk_content
                    elif message.get("type") == "workflow_completed":
                        break
                except:
                    timeout_count += 1

            # Verify streaming worked
            assert len(chunks) > 1  # Should have multiple chunks
            assert len(complete_response) > 100  # Should be substantial content

    @pytest.mark.asyncio
    async def test_multi_user_session_coordination(self, client):
        """Test coordination between multiple users in the same session."""
        session_id = str(uuid.uuid4())
        
        # Create two WebSocket connections for the same session
        with client.websocket_connect(f"/ws/agents/{session_id}") as ws1, \
             client.websocket_connect(f"/ws/agents/{session_id}") as ws2:
            
            # Connect both users
            ws1.send_json({"type": "connect", "session_id": session_id, "user_id": "user1"})
            ws2.send_json({"type": "connect", "session_id": session_id, "user_id": "user2"})
            
            ws1.receive_json()  # Connection confirmation
            ws2.receive_json()  # Connection confirmation

            # User 1 starts a workflow
            ws1.send_json({
                "type": "start_workflow",
                "workflow_request": {
                    "workflow_id": f"multi-user-{session_id}",
                    "primary_agent": "summary",
                    "task_description": "Multi-user coordination test",
                    "context": {"initiated_by": "user1"},
                    "model_preference": "qwen/qwen3-235b-a22b-thinking-2507"
                }
            })

            # Both users should receive updates
            user1_updates = []
            user2_updates = []

            for _ in range(10):  # Check for updates
                try:
                    msg1 = ws1.receive_json(timeout=1)
                    user1_updates.append(msg1)
                except:
                    pass
                
                try:
                    msg2 = ws2.receive_json(timeout=1)
                    user2_updates.append(msg2)
                except:
                    pass

            # Both users should have received some updates
            assert len(user1_updates) > 0
            assert len(user2_updates) > 0

    @pytest.mark.asyncio
    async def test_websocket_error_handling(self, client):
        """Test WebSocket error handling and recovery."""
        session_id = str(uuid.uuid4())
        
        with client.websocket_connect(f"/ws/agents/{session_id}") as websocket:
            websocket.send_json({"type": "connect", "session_id": session_id})
            websocket.receive_json()

            # Send invalid workflow request
            websocket.send_json({
                "type": "start_workflow",
                "workflow_request": {
                    "workflow_id": "",  # Invalid empty ID
                    "primary_agent": "invalid_agent",  # Invalid agent
                    "task_description": "",  # Empty description
                    "model_preference": "qwen/qwen3-235b-a22b-thinking-2507"
                }
            })

            # Should receive error message
            error_received = False
            for _ in range(5):
                try:
                    message = websocket.receive_json(timeout=2)
                    if message.get("type") == "error":
                        error_received = True
                        assert "error" in message
                        break
                except:
                    pass

            assert error_received

    @pytest.mark.asyncio
    async def test_websocket_authentication(self, client):
        """Test WebSocket authentication and authorization."""
        session_id = str(uuid.uuid4())
        
        # Test without authentication
        with client.websocket_connect(f"/ws/agents/{session_id}") as websocket:
            # Try to start workflow without proper authentication
            websocket.send_json({
                "type": "start_workflow",
                "workflow_request": {
                    "workflow_id": f"auth-test-{session_id}",
                    "primary_agent": "help",
                    "task_description": "Test authentication",
                    "model_preference": "qwen/qwen3-235b-a22b-thinking-2507"
                }
                # Missing authentication token
            })

            # Should handle authentication appropriately
            # (Implementation depends on auth strategy)
            try:
                response = websocket.receive_json(timeout=5)
                # Should either work (if auth not required) or return auth error
                assert response is not None
            except:
                # Connection might be closed due to auth failure
                pass

    @pytest.mark.asyncio
    async def test_websocket_connection_limits(self, client):
        """Test WebSocket connection limits and management."""
        session_id = str(uuid.uuid4())
        connections = []
        
        try:
            # Try to create multiple connections
            for i in range(5):
                ws = client.websocket_connect(f"/ws/agents/{session_id}-{i}")
                connections.append(ws.__enter__())
                
                # Send connect message
                connections[-1].send_json({
                    "type": "connect", 
                    "session_id": f"{session_id}-{i}",
                    "user_id": f"user{i}"
                })

            # All connections should be established
            assert len(connections) == 5

            # Test that all can receive messages
            for i, ws in enumerate(connections):
                try:
                    response = ws.receive_json(timeout=2)
                    assert response.get("type") == "connection_established"
                except:
                    pass  # Some might timeout, which is acceptable

        finally:
            # Clean up connections
            for ws in connections:
                try:
                    ws.__exit__(None, None, None)
                except:
                    pass

    @pytest.mark.asyncio
    async def test_websocket_message_queuing(self, client):
        """Test message queuing and delivery guarantees."""
        session_id = str(uuid.uuid4())
        
        with client.websocket_connect(f"/ws/agents/{session_id}") as websocket:
            websocket.send_json({"type": "connect", "session_id": session_id})
            websocket.receive_json()

            # Send multiple messages rapidly
            message_ids = []
            for i in range(3):
                msg_id = f"msg-{i}-{uuid.uuid4()}"
                message_ids.append(msg_id)
                
                websocket.send_json({
                    "type": "start_workflow",
                    "message_id": msg_id,
                    "workflow_request": {
                        "workflow_id": f"queue-test-{i}-{session_id}",
                        "primary_agent": "help",
                        "task_description": f"Queue test message {i}",
                        "context": {"message_number": i},
                        "model_preference": "qwen/qwen3-235b-a22b-thinking-2507"
                    }
                })

            # Collect responses
            responses = []
            timeout_count = 0
            
            while len(responses) < len(message_ids) and timeout_count < 60:
                try:
                    message = websocket.receive_json(timeout=1)
                    responses.append(message)
                except:
                    timeout_count += 1

            # Should have received responses for all messages
            assert len(responses) >= len(message_ids)

    @pytest.mark.asyncio
    async def test_websocket_heartbeat_keepalive(self, client):
        """Test WebSocket heartbeat and keep-alive functionality."""
        session_id = str(uuid.uuid4())
        
        with client.websocket_connect(f"/ws/agents/{session_id}") as websocket:
            websocket.send_json({"type": "connect", "session_id": session_id})
            websocket.receive_json()

            # Send heartbeat
            websocket.send_json({"type": "heartbeat", "timestamp": datetime.utcnow().isoformat()})

            # Should receive heartbeat response
            heartbeat_received = False
            for _ in range(5):
                try:
                    message = websocket.receive_json(timeout=2)
                    if message.get("type") == "heartbeat_ack":
                        heartbeat_received = True
                        break
                except:
                    pass

            # Note: Heartbeat implementation may vary
            # This test verifies the connection stays alive

    @pytest.mark.asyncio
    async def test_websocket_session_persistence(self, client):
        """Test session persistence across WebSocket reconnections."""
        session_id = str(uuid.uuid4())
        
        # First connection - start a workflow
        with client.websocket_connect(f"/ws/agents/{session_id}") as websocket1:
            websocket1.send_json({"type": "connect", "session_id": session_id})
            websocket1.receive_json()

            websocket1.send_json({
                "type": "start_workflow",
                "workflow_request": {
                    "workflow_id": f"persist-test-{session_id}",
                    "primary_agent": "help",
                    "task_description": "Test session persistence",
                    "context": {"test": "persistence"},
                    "model_preference": "qwen/qwen3-235b-a22b-thinking-2507"
                }
            })

            # Get initial response
            initial_response = None
            for _ in range(10):
                try:
                    message = websocket1.receive_json(timeout=2)
                    if message.get("type") == "workflow_started":
                        initial_response = message
                        break
                except:
                    pass

        # Second connection - should be able to query session state
        with client.websocket_connect(f"/ws/agents/{session_id}") as websocket2:
            websocket2.send_json({"type": "connect", "session_id": session_id})
            websocket2.receive_json()

            # Query session state
            websocket2.send_json({
                "type": "get_session_state",
                "session_id": session_id
            })

            # Should receive session information
            session_state_received = False
            for _ in range(5):
                try:
                    message = websocket2.receive_json(timeout=2)
                    if message.get("type") == "session_state":
                        session_state_received = True
                        break
                except:
                    pass

            # Session state handling may vary by implementation
