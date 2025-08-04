"""
Integration Tests for AI Agents API.

This module contains comprehensive integration tests for the AI agents API
including authentication, agent execution, workflows, and WebSocket functionality.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from typing import Dict, Any

from fastapi.testclient import TestClient
from fastapi import status
import websockets

from app.main import app
from app.core.ai_agent_auth import UserRole, AgentPermission, get_user_role
from app.models.user import User
from app.services.agent_orchestrator import AgentRole


class TestAIAgentsAPI:
    """Test cases for AI Agents API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_user(self):
        """Create mock user for testing."""
        user = Mock(spec=User)
        user.id = "test_user_123"
        user.email = "test@example.com"
        user.full_name = "Test User"
        user.is_active = True
        user.role = "basic_user"
        return user
    
    @pytest.fixture
    def admin_user(self):
        """Create mock admin user for testing."""
        user = Mock(spec=User)
        user.id = "admin_user_123"
        user.email = "admin@example.com"
        user.full_name = "Admin User"
        user.is_active = True
        user.role = "admin"
        return user
    
    @pytest.fixture
    def auth_headers(self):
        """Create authentication headers."""
        return {"Authorization": "Bearer test_token"}
    
    def test_get_agents_overview(self, client, mock_user, auth_headers):
        """Test getting agents overview."""
        with patch('app.core.auth.get_current_user', return_value=mock_user):
            response = client.get("/api/v1/ai-agents/", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert "agents" in data
            assert "total_agents" in data
            assert "system_status" in data
            assert data["system_status"] == "operational"
            assert data["user_id"] == mock_user.id
            
            # Check that all agent roles are present
            expected_roles = [role.value for role in AgentRole]
            for role in expected_roles:
                assert role in data["agents"]
                assert "description" in data["agents"][role]
                assert "tools_count" in data["agents"][role]
                assert "capabilities" in data["agents"][role]
    
    def test_get_agent_tools(self, client, mock_user, auth_headers):
        """Test getting tools for a specific agent."""
        with patch('app.core.auth.get_current_user', return_value=mock_user):
            agent_role = "data_extraction"
            response = client.get(f"/api/v1/ai-agents/{agent_role}/tools", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert data["agent_role"] == agent_role
            assert "tools" in data
            assert "total_count" in data
            assert isinstance(data["tools"], list)
            assert data["total_count"] >= 0
            
            # Check tool structure
            if data["tools"]:
                tool = data["tools"][0]
                assert "name" in tool
                assert "description" in tool
                assert "category" in tool
    
    def test_get_agent_tools_invalid_role(self, client, mock_user, auth_headers):
        """Test getting tools for invalid agent role."""
        with patch('app.core.auth.get_current_user', return_value=mock_user):
            response = client.get("/api/v1/ai-agents/invalid_role/tools", headers=auth_headers)
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "Invalid agent role" in response.json()["detail"]
    
    def test_execute_agent(self, client, mock_user, auth_headers):
        """Test executing an agent."""
        with patch('app.core.auth.get_current_user', return_value=mock_user):
            agent_role = "data_extraction"
            request_data = {
                "agent_role": agent_role,
                "task_description": "Extract data from test document",
                "input_data": {"document_id": "test_doc_123"},
                "workflow_id": "test_workflow_456"
            }
            
            response = client.post(
                f"/api/v1/ai-agents/{agent_role}/execute",
                json=request_data,
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert "execution_id" in data
            assert data["agent_role"] == agent_role
            assert data["status"] == "queued"
            assert "created_at" in data
            assert data["workflow_id"] == request_data["workflow_id"]
    
    def test_execute_agent_invalid_role(self, client, mock_user, auth_headers):
        """Test executing agent with invalid role."""
        with patch('app.core.auth.get_current_user', return_value=mock_user):
            request_data = {
                "agent_role": "invalid_role",
                "task_description": "Test task",
                "input_data": {}
            }
            
            response = client.post(
                "/api/v1/ai-agents/invalid_role/execute",
                json=request_data,
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_get_execution_status(self, client, mock_user, auth_headers):
        """Test getting execution status."""
        with patch('app.core.auth.get_current_user', return_value=mock_user):
            # First create an execution
            agent_role = "data_extraction"
            request_data = {
                "agent_role": agent_role,
                "task_description": "Test task",
                "input_data": {}
            }
            
            create_response = client.post(
                f"/api/v1/ai-agents/{agent_role}/execute",
                json=request_data,
                headers=auth_headers
            )
            
            execution_id = create_response.json()["execution_id"]
            
            # Then get the status
            response = client.get(
                f"/api/v1/ai-agents/executions/{execution_id}/status",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert data["execution_id"] == execution_id
            assert "status" in data
            assert "progress" in data
            assert "updated_at" in data
    
    def test_get_execution_status_not_found(self, client, mock_user, auth_headers):
        """Test getting status for non-existent execution."""
        with patch('app.core.auth.get_current_user', return_value=mock_user):
            response = client.get(
                "/api/v1/ai-agents/executions/nonexistent_id/status",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_create_workflow(self, client, mock_user, auth_headers):
        """Test creating a workflow."""
        with patch('app.core.auth.get_current_user', return_value=mock_user):
            request_data = {
                "workflow_type": "contract_processing",
                "description": "Complete contract processing workflow",
                "agents": ["data_extraction", "contract_generator", "compliance_checker"],
                "input_data": {"document_id": "test_doc_123"}
            }
            
            response = client.post(
                "/api/v1/ai-agents/workflows",
                json=request_data,
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert "workflow_id" in data
            assert data["status"] == "created"
            assert data["agents"] == request_data["agents"]
            assert "created_at" in data
            assert data["progress"] == 0.0
    
    def test_create_workflow_invalid_agent(self, client, mock_user, auth_headers):
        """Test creating workflow with invalid agent role."""
        with patch('app.core.auth.get_current_user', return_value=mock_user):
            request_data = {
                "workflow_type": "test_workflow",
                "description": "Test workflow",
                "agents": ["invalid_agent"],
                "input_data": {}
            }
            
            response = client.post(
                "/api/v1/ai-agents/workflows",
                json=request_data,
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_get_workflow_status(self, client, mock_user, auth_headers):
        """Test getting workflow status."""
        with patch('app.core.auth.get_current_user', return_value=mock_user):
            # First create a workflow
            request_data = {
                "workflow_type": "test_workflow",
                "description": "Test workflow",
                "agents": ["data_extraction"],
                "input_data": {}
            }
            
            create_response = client.post(
                "/api/v1/ai-agents/workflows",
                json=request_data,
                headers=auth_headers
            )
            
            workflow_id = create_response.json()["workflow_id"]
            
            # Then get the status
            response = client.get(
                f"/api/v1/ai-agents/workflows/{workflow_id}",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert data["workflow_id"] == workflow_id
            assert data["status"] == "created"
            assert data["agents"] == request_data["agents"]
    
    def test_get_workflow_status_not_found(self, client, mock_user, auth_headers):
        """Test getting status for non-existent workflow."""
        with patch('app.core.auth.get_current_user', return_value=mock_user):
            response = client.get(
                "/api/v1/ai-agents/workflows/nonexistent_id",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_unauthorized_access(self, client):
        """Test unauthorized access to endpoints."""
        # Test without authentication headers
        response = client.get("/api/v1/ai-agents/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        
        response = client.get("/api/v1/ai-agents/data_extraction/tools")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        
        response = client.post("/api/v1/ai-agents/data_extraction/execute", json={})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestAIAgentsAuthentication:
    """Test cases for AI agents authentication and authorization."""
    
    def test_user_role_mapping(self):
        """Test user role mapping."""
        # Test admin user
        admin_user = Mock(spec=User)
        admin_user.role = "admin"
        assert get_user_role(admin_user) == UserRole.ADMIN
        
        # Test basic user
        basic_user = Mock(spec=User)
        basic_user.role = "basic_user"
        assert get_user_role(basic_user) == UserRole.BASIC_USER
        
        # Test user without role
        no_role_user = Mock(spec=User)
        assert get_user_role(no_role_user) == UserRole.BASIC_USER
    
    def test_permission_checking(self):
        """Test permission checking functionality."""
        from app.core.ai_agent_auth import has_permission, get_user_permissions
        
        # Test admin permissions
        admin_user = Mock(spec=User)
        admin_user.role = "admin"
        admin_permissions = get_user_permissions(admin_user)
        
        assert AgentPermission.ADMIN_AGENTS in admin_permissions
        assert AgentPermission.EXECUTE_DATA_EXTRACTION in admin_permissions
        assert has_permission(admin_user, AgentPermission.ADMIN_AGENTS)
        
        # Test basic user permissions
        basic_user = Mock(spec=User)
        basic_user.role = "basic_user"
        basic_permissions = get_user_permissions(basic_user)
        
        assert AgentPermission.ADMIN_AGENTS not in basic_permissions
        assert AgentPermission.EXECUTE_DATA_EXTRACTION in basic_permissions
        assert not has_permission(basic_user, AgentPermission.ADMIN_AGENTS)
    
    def test_rate_limiting(self):
        """Test rate limiting functionality."""
        from app.core.ai_agent_auth import RateLimiter
        
        rate_limiter = RateLimiter()
        
        # Test basic user rate limit
        basic_user = Mock(spec=User)
        basic_user.id = "test_user_123"
        basic_user.role = "basic_user"
        
        # Should allow requests within limit
        for i in range(10):
            assert rate_limiter.check_rate_limit(basic_user) == True
        
        # Check remaining requests
        remaining = rate_limiter.get_remaining_requests(basic_user)
        assert remaining == 90  # 100 - 10 = 90


class TestAIAgentsWorkflows:
    """Test cases for multi-agent workflows."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_user(self):
        """Create mock user for testing."""
        user = Mock(spec=User)
        user.id = "test_user_123"
        user.email = "test@example.com"
        user.role = "agent_manager"
        return user
    
    @pytest.fixture
    def auth_headers(self):
        """Create authentication headers."""
        return {"Authorization": "Bearer test_token"}
    
    def test_complete_workflow_execution(self, client, mock_user, auth_headers):
        """Test complete workflow execution with multiple agents."""
        with patch('app.core.auth.get_current_user', return_value=mock_user):
            # Create workflow
            workflow_data = {
                "workflow_type": "contract_processing",
                "description": "Complete contract processing",
                "agents": ["data_extraction", "contract_generator", "compliance_checker"],
                "input_data": {"document_id": "test_doc_123"}
            }
            
            workflow_response = client.post(
                "/api/v1/ai-agents/workflows",
                json=workflow_data,
                headers=auth_headers
            )
            
            assert workflow_response.status_code == status.HTTP_200_OK
            workflow_id = workflow_response.json()["workflow_id"]
            
            # Execute agents in the workflow
            execution_ids = []
            for agent_role in workflow_data["agents"]:
                execution_data = {
                    "agent_role": agent_role,
                    "task_description": f"Execute {agent_role} for workflow",
                    "input_data": workflow_data["input_data"],
                    "workflow_id": workflow_id
                }
                
                execution_response = client.post(
                    f"/api/v1/ai-agents/{agent_role}/execute",
                    json=execution_data,
                    headers=auth_headers
                )
                
                assert execution_response.status_code == status.HTTP_200_OK
                execution_ids.append(execution_response.json()["execution_id"])
            
            # Check workflow status
            workflow_status_response = client.get(
                f"/api/v1/ai-agents/workflows/{workflow_id}",
                headers=auth_headers
            )
            
            assert workflow_status_response.status_code == status.HTTP_200_OK
            workflow_status = workflow_status_response.json()
            
            assert workflow_status["workflow_id"] == workflow_id
            assert workflow_status["agents"] == workflow_data["agents"]
            
            # Check individual execution statuses
            for execution_id in execution_ids:
                status_response = client.get(
                    f"/api/v1/ai-agents/executions/{execution_id}/status",
                    headers=auth_headers
                )
                
                assert status_response.status_code == status.HTTP_200_OK
                execution_status = status_response.json()
                assert execution_status["execution_id"] == execution_id


class TestAIAgentsWebSocket:
    """Test cases for WebSocket functionality."""
    
    @pytest.mark.asyncio
    async def test_websocket_connection(self):
        """Test WebSocket connection and basic messaging."""
        # This would require a running WebSocket server
        # For now, we'll test the connection manager directly
        from app.api.v1.ai_agents_ws import ConnectionManager
        
        manager = ConnectionManager()
        
        # Test connection tracking
        connection_id = "test_connection_123"
        user_id = "test_user_123"
        
        # Simulate connection (without actual WebSocket)
        manager.user_connections[user_id] = {connection_id}
        manager.active_connections[connection_id] = Mock()
        
        # Test subscription
        execution_id = "test_execution_123"
        manager.subscribe_to_execution(connection_id, execution_id)
        
        assert execution_id in manager.execution_subscribers
        assert connection_id in manager.execution_subscribers[execution_id]
        
        # Test stats
        stats = manager.get_stats()
        assert stats["total_connections"] == 1
        assert stats["users_connected"] == 1
        assert stats["execution_subscriptions"] == 1
        
        # Test disconnect
        manager.disconnect(connection_id, user_id)
        
        assert connection_id not in manager.active_connections
        assert user_id not in manager.user_connections
        assert execution_id not in manager.execution_subscribers
    
    @pytest.mark.asyncio
    async def test_progress_notifications(self):
        """Test progress notification functionality."""
        from app.api.v1.ai_agents_ws import notify_execution_progress, notify_workflow_progress
        
        # Test execution progress notification
        execution_id = "test_execution_123"
        progress = 50.0
        status = "running"
        details = {"step": "processing", "items_processed": 10}
        
        # This would normally send to WebSocket subscribers
        # For testing, we just ensure it doesn't raise exceptions
        await notify_execution_progress(execution_id, progress, status, details)
        
        # Test workflow progress notification
        workflow_id = "test_workflow_123"
        await notify_workflow_progress(workflow_id, progress, status, details)
