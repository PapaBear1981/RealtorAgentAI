"""
Tests for task API endpoints.

This module contains integration tests for the task management API,
including task submission, monitoring, and administrative operations.
"""

import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.main import app
from app.models.user import User
from app.models.file import File, FileStatus, ProcessingStatus
from app.models.contract import Contract, ContractStatus
from tests.conftest import create_test_user, create_test_file, create_test_contract


class TestTaskAPI:
    """Test cases for task API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self, session: Session):
        """Create authentication headers for test user."""
        user = create_test_user(session, email="test@example.com")
        
        # Mock JWT token creation
        with patch('app.core.security.create_access_token') as mock_create_token:
            mock_create_token.return_value = "test-jwt-token"
            
            return {"Authorization": "Bearer test-jwt-token"}
    
    @pytest.fixture
    def admin_headers(self, session: Session):
        """Create authentication headers for admin user."""
        user = create_test_user(session, email="admin@example.com", is_admin=True)
        
        with patch('app.core.security.create_access_token') as mock_create_token:
            mock_create_token.return_value = "admin-jwt-token"
            
            return {"Authorization": "Bearer admin-jwt-token"}
    
    def test_submit_file_processing(self, client, session: Session, auth_headers):
        """Test file processing task submission."""
        # Create test file
        file_record = create_test_file(session, user_id=1)
        
        with patch('app.services.task_service.get_task_service') as mock_service:
            mock_task_service = Mock()
            mock_task_service.submit_file_processing.return_value = {
                "status": "submitted",
                "workflow_id": "test-workflow-id",
                "file_id": file_record.id,
                "priority": "NORMAL",
                "estimated_completion": "2023-01-01T01:00:00"
            }
            mock_service.return_value = mock_task_service
            
            response = client.post(
                "/api/tasks/files/process",
                json={
                    "file_id": file_record.id,
                    "priority": "NORMAL",
                    "force_ocr": False,
                    "enhance_quality": True
                },
                headers=auth_headers
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "submitted"
        assert data["task_id"] == "test-workflow-id"
        assert "estimated_completion" in data
    
    def test_submit_file_processing_invalid_priority(self, client, session: Session, auth_headers):
        """Test file processing with invalid priority."""
        file_record = create_test_file(session, user_id=1)
        
        response = client.post(
            "/api/tasks/files/process",
            json={
                "file_id": file_record.id,
                "priority": "INVALID",
                "force_ocr": False,
                "enhance_quality": True
            },
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "Invalid priority" in response.json()["detail"]
    
    def test_submit_file_processing_file_not_found(self, client, auth_headers):
        """Test file processing with non-existent file."""
        response = client.post(
            "/api/tasks/files/process",
            json={
                "file_id": 999,
                "priority": "NORMAL",
                "force_ocr": False,
                "enhance_quality": True
            },
            headers=auth_headers
        )
        
        assert response.status_code == 404
        assert "File not found" in response.json()["detail"]
    
    def test_submit_ocr_processing(self, client, session: Session, auth_headers):
        """Test OCR processing task submission."""
        file_record = create_test_file(session, user_id=1)
        
        with patch('app.services.task_service.get_task_service') as mock_service:
            mock_task_service = Mock()
            mock_task_service.submit_ocr_processing.return_value = {
                "status": "submitted",
                "task_id": "ocr-task-id",
                "file_id": file_record.id,
                "priority": "HIGH",
                "estimated_completion": "2023-01-01T01:00:00"
            }
            mock_service.return_value = mock_task_service
            
            response = client.post(
                f"/api/tasks/files/{file_record.id}/ocr",
                json={"priority": "HIGH"},
                params={"force_ocr": True, "enhance_quality": True},
                headers=auth_headers
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "submitted"
        assert data["task_id"] == "ocr-task-id"
    
    def test_submit_contract_analysis(self, client, session: Session, auth_headers):
        """Test contract analysis task submission."""
        contract = create_test_contract(session, user_id=1)
        
        with patch('app.services.task_service.get_task_service') as mock_service:
            mock_task_service = Mock()
            mock_task_service.submit_contract_analysis.return_value = {
                "status": "submitted",
                "task_id": "analysis-task-id",
                "contract_id": contract.id,
                "analysis_type": "legal",
                "priority": "HIGH",
                "estimated_completion": "2023-01-01T01:00:00"
            }
            mock_service.return_value = mock_task_service
            
            response = client.post(
                "/api/tasks/contracts/analyze",
                json={
                    "contract_id": contract.id,
                    "priority": "HIGH",
                    "analysis_type": "legal",
                    "model_preference": "gpt-4"
                },
                headers=auth_headers
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "submitted"
        assert data["task_id"] == "analysis-task-id"
    
    def test_submit_document_export_pdf(self, client, session: Session, auth_headers):
        """Test PDF document export task submission."""
        contract = create_test_contract(session, user_id=1)
        
        with patch('app.services.task_service.get_task_service') as mock_service:
            mock_task_service = Mock()
            mock_task_service.submit_document_export.return_value = {
                "status": "submitted",
                "task_id": "export-task-id",
                "contract_id": contract.id,
                "export_format": "pdf",
                "priority": "NORMAL",
                "estimated_completion": "2023-01-01T01:00:00"
            }
            mock_service.return_value = mock_task_service
            
            response = client.post(
                "/api/tasks/contracts/export",
                json={
                    "contract_id": contract.id,
                    "priority": "NORMAL",
                    "export_format": "pdf",
                    "template_options": {"page_size": "A4"},
                    "include_metadata": True
                },
                headers=auth_headers
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "submitted"
        assert data["task_id"] == "export-task-id"
    
    def test_submit_document_export_invalid_format(self, client, session: Session, auth_headers):
        """Test document export with invalid format."""
        contract = create_test_contract(session, user_id=1)
        
        response = client.post(
            "/api/tasks/contracts/export",
            json={
                "contract_id": contract.id,
                "priority": "NORMAL",
                "export_format": "invalid",
                "include_metadata": True
            },
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "Unsupported export format" in response.json()["detail"]
    
    def test_get_task_status(self, client, auth_headers):
        """Test getting task status."""
        with patch('app.services.task_service.get_task_service') as mock_service:
            mock_task_service = Mock()
            mock_task_service.get_task_status.return_value = {
                "task_id": "test-task-id",
                "status": "SUCCESS",
                "result": {"output": "completed"},
                "traceback": None,
                "date_done": "2023-01-01T01:00:00",
                "task_name": "test_task",
                "args": [1, 2, 3],
                "kwargs": {"key": "value"}
            }
            mock_service.return_value = mock_task_service
            
            response = client.get(
                "/api/tasks/test-task-id/status",
                headers=auth_headers
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "test-task-id"
        assert data["status"] == "SUCCESS"
        assert data["result"] == {"output": "completed"}
    
    def test_get_queue_status(self, client, auth_headers):
        """Test getting queue status."""
        with patch('app.services.task_service.get_task_service') as mock_service:
            mock_task_service = Mock()
            mock_task_service.get_queue_status.return_value = {
                "timestamp": "2023-01-01T01:00:00",
                "active_tasks": {"worker1": [{"id": "task1"}]},
                "scheduled_tasks": {"worker1": []},
                "reserved_tasks": {"worker1": []},
                "queue_lengths": {"ingest": 5, "ocr": 2, "llm": 1, "export": 3, "system": 0},
                "total_active": 1,
                "total_scheduled": 0,
                "total_reserved": 0
            }
            mock_service.return_value = mock_task_service
            
            response = client.get(
                "/api/tasks/queues/status",
                headers=auth_headers
            )
        
        assert response.status_code == 200
        data = response.json()
        assert "timestamp" in data
        assert data["total_active"] == 1
        assert data["queue_lengths"]["ingest"] == 5
    
    def test_cancel_task(self, client, auth_headers):
        """Test cancelling a task."""
        with patch('app.services.task_service.get_task_service') as mock_service:
            mock_task_service = Mock()
            mock_task_service.cancel_task.return_value = {
                "status": "cancelled",
                "task_id": "test-task-id",
                "terminated": False,
                "timestamp": "2023-01-01T01:00:00"
            }
            mock_service.return_value = mock_task_service
            
            response = client.delete(
                "/api/tasks/test-task-id",
                params={"terminate": False},
                headers=auth_headers
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"
        assert data["task_id"] == "test-task-id"
        assert "successfully" in data["message"]
    
    def test_get_worker_stats_admin_required(self, client, auth_headers):
        """Test worker stats endpoint requires admin access."""
        response = client.get(
            "/api/tasks/admin/workers/stats",
            headers=auth_headers
        )
        
        # Should return 403 for non-admin user
        assert response.status_code == 403
    
    def test_get_worker_stats_admin(self, client, admin_headers):
        """Test getting worker stats as admin."""
        with patch('app.services.task_service.get_task_service') as mock_service:
            mock_task_service = Mock()
            mock_task_service.get_worker_stats.return_value = {
                "timestamp": "2023-01-01T01:00:00",
                "worker_stats": {"worker1": {"pool": {"max-concurrency": 4}}},
                "registered_tasks": {"worker1": ["task1", "task2"]},
                "worker_ping": {"worker1": "pong"},
                "total_workers": 1
            }
            mock_service.return_value = mock_task_service
            
            response = client.get(
                "/api/tasks/admin/workers/stats",
                headers=admin_headers
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_workers"] == 1
        assert "worker_stats" in data
    
    def test_get_failed_tasks_admin(self, client, admin_headers):
        """Test getting failed tasks as admin."""
        with patch('app.core.task_retry.get_dead_letter_queue') as mock_dlq:
            mock_dlq_instance = Mock()
            mock_dlq_instance.get_failed_tasks.return_value = [
                {
                    "task_id": "failed-task-1",
                    "task_name": "test_task",
                    "exception_type": "ValueError",
                    "retry_count": 3
                }
            ]
            mock_dlq.return_value = mock_dlq_instance
            
            response = client.get(
                "/api/tasks/admin/dead-letter-queue",
                params={"limit": 50},
                headers=admin_headers
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert data["limit"] == 50
        assert len(data["failed_tasks"]) == 1
        assert data["failed_tasks"][0]["task_id"] == "failed-task-1"
    
    def test_retry_failed_task_admin(self, client, admin_headers):
        """Test retrying failed task as admin."""
        with patch('app.core.task_retry.get_dead_letter_queue') as mock_dlq:
            mock_dlq_instance = Mock()
            mock_dlq_instance.retry_failed_task.return_value = True
            mock_dlq.return_value = mock_dlq_instance
            
            response = client.post(
                "/api/tasks/admin/dead-letter-queue/failed-task-id/retry",
                headers=admin_headers
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "retry_submitted"
        assert data["task_id"] == "failed-task-id"
        assert "successfully" in data["message"]
    
    def test_retry_failed_task_not_found(self, client, admin_headers):
        """Test retrying non-existent failed task."""
        with patch('app.core.task_retry.get_dead_letter_queue') as mock_dlq:
            mock_dlq_instance = Mock()
            mock_dlq_instance.retry_failed_task.return_value = False
            mock_dlq.return_value = mock_dlq_instance
            
            response = client.post(
                "/api/tasks/admin/dead-letter-queue/non-existent-task/retry",
                headers=admin_headers
            )
        
        assert response.status_code == 404
        assert "Failed task not found" in response.json()["detail"]
    
    def test_unauthorized_access(self, client):
        """Test API endpoints without authentication."""
        # Test file processing endpoint
        response = client.post(
            "/api/tasks/files/process",
            json={"file_id": 1, "priority": "NORMAL"}
        )
        assert response.status_code == 401
        
        # Test task status endpoint
        response = client.get("/api/tasks/test-task-id/status")
        assert response.status_code == 401
        
        # Test admin endpoint
        response = client.get("/api/tasks/admin/workers/stats")
        assert response.status_code == 401
