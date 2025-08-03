"""
Tests for task service functionality.

This module contains comprehensive tests for the task service,
including task submission, monitoring, and management operations.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from app.services.task_service import TaskService, TaskPriority, TaskStatus
from app.core.task_retry import RetryConfig, RetryHandler, DeadLetterQueue


class TestTaskService:
    """Test cases for TaskService class."""
    
    @pytest.fixture
    def task_service(self):
        """Create TaskService instance for testing."""
        return TaskService()
    
    @pytest.fixture
    def mock_celery_app(self):
        """Mock Celery application."""
        with patch('app.services.task_service.get_celery_app') as mock:
            celery_app = Mock()
            mock.return_value = celery_app
            yield celery_app
    
    def test_submit_file_processing(self, task_service, mock_celery_app):
        """Test file processing task submission."""
        # Mock task result
        mock_result = Mock()
        mock_result.id = "test-task-id"
        mock_result.parent = Mock()
        mock_result.parent.id = "parent-task-id"
        
        with patch('app.tasks.ingest_tasks.process_file_upload') as mock_task:
            mock_task.s.return_value.set.return_value = Mock()
            
            with patch('app.tasks.ocr_tasks.process_document_ocr') as mock_ocr:
                mock_ocr.s.return_value.set.return_value = Mock()
                
                with patch('app.services.task_service.chain') as mock_chain:
                    mock_workflow = Mock()
                    mock_workflow.apply_async.return_value = mock_result
                    mock_chain.return_value = mock_workflow
                    
                    result = task_service.submit_file_processing(
                        file_id=1,
                        user_id=1,
                        storage_key="test/file.pdf",
                        original_filename="test.pdf",
                        file_size=1024,
                        mime_type="application/pdf",
                        priority=TaskPriority.HIGH
                    )
        
        assert result["status"] == "submitted"
        assert result["workflow_id"] == "test-task-id"
        assert result["file_id"] == 1
        assert result["priority"] == "HIGH"
        assert "estimated_completion" in result
        assert "tasks" in result
    
    def test_submit_ocr_processing(self, task_service):
        """Test OCR processing task submission."""
        with patch('app.tasks.ocr_tasks.process_document_ocr') as mock_task:
            mock_result = Mock()
            mock_result.id = "ocr-task-id"
            mock_task.apply_async.return_value = mock_result
            
            result = task_service.submit_ocr_processing(
                file_id=1,
                user_id=1,
                force_ocr=True,
                enhance_quality=True,
                priority=TaskPriority.NORMAL
            )
        
        assert result["status"] == "submitted"
        assert result["task_id"] == "ocr-task-id"
        assert result["file_id"] == 1
        assert result["priority"] == "NORMAL"
        
        # Verify task was called with correct arguments
        mock_task.apply_async.assert_called_once_with(
            args=[1, 1, True, True],
            priority=TaskPriority.NORMAL.value
        )
    
    def test_submit_contract_analysis(self, task_service):
        """Test contract analysis task submission."""
        with patch('app.tasks.llm_tasks.analyze_contract_content') as mock_task:
            mock_result = Mock()
            mock_result.id = "analysis-task-id"
            mock_task.apply_async.return_value = mock_result
            
            result = task_service.submit_contract_analysis(
                contract_id=1,
                user_id=1,
                analysis_type="legal",
                model_preference="gpt-4",
                priority=TaskPriority.HIGH
            )
        
        assert result["status"] == "submitted"
        assert result["task_id"] == "analysis-task-id"
        assert result["contract_id"] == 1
        assert result["analysis_type"] == "legal"
        assert result["priority"] == "HIGH"
    
    def test_submit_document_export(self, task_service):
        """Test document export task submission."""
        with patch('app.tasks.export_tasks.generate_pdf_document') as mock_task:
            mock_result = Mock()
            mock_result.id = "export-task-id"
            mock_task.apply_async.return_value = mock_result
            
            result = task_service.submit_document_export(
                contract_id=1,
                user_id=1,
                export_format="pdf",
                template_options={"page_size": "A4"},
                include_metadata=True,
                priority=TaskPriority.NORMAL
            )
        
        assert result["status"] == "submitted"
        assert result["task_id"] == "export-task-id"
        assert result["contract_id"] == 1
        assert result["export_format"] == "pdf"
    
    def test_submit_document_export_docx(self, task_service):
        """Test DOCX document export task submission."""
        with patch('app.tasks.export_tasks.generate_docx_document') as mock_task:
            mock_result = Mock()
            mock_result.id = "docx-export-task-id"
            mock_task.apply_async.return_value = mock_result
            
            result = task_service.submit_document_export(
                contract_id=1,
                user_id=1,
                export_format="docx",
                priority=TaskPriority.NORMAL
            )
        
        assert result["status"] == "submitted"
        assert result["task_id"] == "docx-export-task-id"
        assert result["export_format"] == "docx"
    
    def test_submit_document_export_invalid_format(self, task_service):
        """Test document export with invalid format."""
        with pytest.raises(ValueError, match="Unsupported export format"):
            task_service.submit_document_export(
                contract_id=1,
                user_id=1,
                export_format="invalid",
                priority=TaskPriority.NORMAL
            )
    
    def test_get_task_status(self, task_service, mock_celery_app):
        """Test getting task status."""
        with patch('app.services.task_service.AsyncResult') as mock_async_result:
            mock_result = Mock()
            mock_result.status = "SUCCESS"
            mock_result.result = {"output": "test result"}
            mock_result.ready.return_value = True
            mock_result.failed.return_value = False
            mock_result.traceback = None
            mock_result.date_done = datetime.utcnow()
            mock_result.name = "test_task"
            mock_result.args = [1, 2, 3]
            mock_result.kwargs = {"key": "value"}
            mock_result.info = {"progress": 100}
            
            mock_async_result.return_value = mock_result
            
            status_info = task_service.get_task_status("test-task-id")
        
        assert status_info["task_id"] == "test-task-id"
        assert status_info["status"] == "SUCCESS"
        assert status_info["result"] == {"output": "test result"}
        assert status_info["traceback"] is None
        assert status_info["task_name"] == "test_task"
        assert status_info["args"] == [1, 2, 3]
        assert status_info["kwargs"] == {"key": "value"}
        assert status_info["progress"] == 100
    
    def test_get_task_status_error(self, task_service, mock_celery_app):
        """Test getting task status with error."""
        with patch('app.services.task_service.AsyncResult') as mock_async_result:
            mock_async_result.side_effect = Exception("Connection error")
            
            status_info = task_service.get_task_status("test-task-id")
        
        assert status_info["task_id"] == "test-task-id"
        assert status_info["status"] == "ERROR"
        assert "Connection error" in status_info["error"]
    
    def test_get_queue_status(self, task_service, mock_celery_app):
        """Test getting queue status."""
        # Mock inspect methods
        mock_inspect = Mock()
        mock_inspect.active.return_value = {"worker1": [{"id": "task1"}]}
        mock_inspect.scheduled.return_value = {"worker1": [{"id": "task2"}]}
        mock_inspect.reserved.return_value = {"worker1": [{"id": "task3"}]}
        
        mock_celery_app.control.inspect.return_value = mock_inspect
        
        # Mock Redis client
        with patch('app.services.task_service.get_redis_client') as mock_redis:
            mock_redis_client = Mock()
            mock_redis_client.llen.return_value = 5
            mock_redis.return_value = mock_redis_client
            
            queue_status = task_service.get_queue_status()
        
        assert "timestamp" in queue_status
        assert queue_status["active_tasks"] == {"worker1": [{"id": "task1"}]}
        assert queue_status["scheduled_tasks"] == {"worker1": [{"id": "task2"}]}
        assert queue_status["reserved_tasks"] == {"worker1": [{"id": "task3"}]}
        assert queue_status["total_active"] == 1
        assert queue_status["total_scheduled"] == 1
        assert queue_status["total_reserved"] == 1
        assert all(length == 5 for length in queue_status["queue_lengths"].values())
    
    def test_cancel_task(self, task_service, mock_celery_app):
        """Test cancelling a task."""
        result = task_service.cancel_task("test-task-id", terminate=False)
        
        assert result["status"] == "cancelled"
        assert result["task_id"] == "test-task-id"
        assert result["terminated"] is False
        assert "timestamp" in result
        
        mock_celery_app.control.revoke.assert_called_once_with("test-task-id", terminate=False)
    
    def test_cancel_task_with_terminate(self, task_service, mock_celery_app):
        """Test terminating a task."""
        result = task_service.cancel_task("test-task-id", terminate=True)
        
        assert result["status"] == "cancelled"
        assert result["task_id"] == "test-task-id"
        assert result["terminated"] is True
        
        mock_celery_app.control.terminate.assert_called_once_with("test-task-id")
    
    def test_get_worker_stats(self, task_service, mock_celery_app):
        """Test getting worker statistics."""
        mock_inspect = Mock()
        mock_inspect.stats.return_value = {"worker1": {"pool": {"max-concurrency": 4}}}
        mock_inspect.registered.return_value = {"worker1": ["task1", "task2"]}
        mock_inspect.ping.return_value = {"worker1": "pong"}
        
        mock_celery_app.control.inspect.return_value = mock_inspect
        
        stats = task_service.get_worker_stats()
        
        assert "timestamp" in stats
        assert stats["worker_stats"] == {"worker1": {"pool": {"max-concurrency": 4}}}
        assert stats["registered_tasks"] == {"worker1": ["task1", "task2"]}
        assert stats["worker_ping"] == {"worker1": "pong"}
        assert stats["total_workers"] == 1


class TestRetryHandler:
    """Test cases for RetryHandler class."""
    
    @pytest.fixture
    def retry_config(self):
        """Create RetryConfig for testing."""
        return RetryConfig(
            max_retries=3,
            base_delay=60,
            max_delay=3600,
            jitter=False  # Disable jitter for predictable tests
        )
    
    @pytest.fixture
    def retry_handler(self, retry_config):
        """Create RetryHandler for testing."""
        with patch('app.core.task_retry.get_redis_client'):
            return RetryHandler(retry_config)
    
    def test_should_retry_retryable_exception(self, retry_handler):
        """Test retry decision for retryable exceptions."""
        assert retry_handler.should_retry(ConnectionError("Network error"), 0) is True
        assert retry_handler.should_retry(TimeoutError("Timeout"), 1) is True
    
    def test_should_retry_non_retryable_exception(self, retry_handler):
        """Test retry decision for non-retryable exceptions."""
        assert retry_handler.should_retry(ValueError("Invalid value"), 0) is False
        assert retry_handler.should_retry(TypeError("Type error"), 1) is False
    
    def test_should_retry_max_retries_exceeded(self, retry_handler):
        """Test retry decision when max retries exceeded."""
        assert retry_handler.should_retry(ConnectionError("Network error"), 3) is False
        assert retry_handler.should_retry(ConnectionError("Network error"), 5) is False
    
    def test_calculate_delay_exponential_backoff(self, retry_handler):
        """Test exponential backoff delay calculation."""
        assert retry_handler.calculate_delay(0) == 60  # base_delay * 2^0
        assert retry_handler.calculate_delay(1) == 120  # base_delay * 2^1
        assert retry_handler.calculate_delay(2) == 240  # base_delay * 2^2
    
    def test_calculate_delay_max_delay_limit(self, retry_handler):
        """Test delay calculation with max delay limit."""
        # Should be capped at max_delay (3600)
        delay = retry_handler.calculate_delay(10)
        assert delay == 3600
    
    def test_fibonacci_calculation(self, retry_handler):
        """Test Fibonacci number calculation."""
        assert retry_handler._fibonacci(0) == 0
        assert retry_handler._fibonacci(1) == 1
        assert retry_handler._fibonacci(2) == 1
        assert retry_handler._fibonacci(3) == 2
        assert retry_handler._fibonacci(4) == 3
        assert retry_handler._fibonacci(5) == 5


class TestDeadLetterQueue:
    """Test cases for DeadLetterQueue class."""
    
    @pytest.fixture
    def mock_redis_client(self):
        """Mock Redis client."""
        return Mock()
    
    @pytest.fixture
    def dlq(self, mock_redis_client):
        """Create DeadLetterQueue for testing."""
        return DeadLetterQueue(mock_redis_client)
    
    def test_add_failed_task(self, dlq, mock_redis_client):
        """Test adding failed task to dead letter queue."""
        exception = ValueError("Test error")
        
        dlq.add_failed_task(
            task_id="test-task-id",
            task_name="test_task",
            args=(1, 2, 3),
            kwargs={"key": "value"},
            exception=exception,
            retry_count=3
        )
        
        # Verify Redis operations
        mock_redis_client.lpush.assert_called_once()
        mock_redis_client.hset.assert_called_once()
        mock_redis_client.expire.assert_called_once()
    
    def test_get_failed_tasks(self, dlq, mock_redis_client):
        """Test retrieving failed tasks from dead letter queue."""
        # Mock Redis response
        mock_redis_client.lrange.return_value = [
            "{'task_id': 'task1', 'task_name': 'test_task1'}",
            "{'task_id': 'task2', 'task_name': 'test_task2'}"
        ]
        
        failed_tasks = dlq.get_failed_tasks(limit=10)
        
        assert len(failed_tasks) == 2
        assert failed_tasks[0]["task_id"] == "task1"
        assert failed_tasks[1]["task_id"] == "task2"
        
        mock_redis_client.lrange.assert_called_once_with(dlq.dlq_key, 0, 9)
    
    def test_retry_failed_task(self, dlq, mock_redis_client):
        """Test retrying failed task."""
        # Mock Redis response
        mock_redis_client.hgetall.return_value = {
            "task_name": "test_task",
            "failure_timestamp": "2023-01-01T00:00:00",
            "exception_type": "ValueError"
        }
        
        success = dlq.retry_failed_task("test-task-id")
        
        assert success is True
        mock_redis_client.hgetall.assert_called_once()
    
    def test_retry_failed_task_not_found(self, dlq, mock_redis_client):
        """Test retrying non-existent failed task."""
        # Mock Redis response - no metadata found
        mock_redis_client.hgetall.return_value = {}
        
        success = dlq.retry_failed_task("non-existent-task")
        
        assert success is False
