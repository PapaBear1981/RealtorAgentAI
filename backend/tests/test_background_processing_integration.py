"""
Integration tests for background processing system.

This module contains comprehensive integration tests for the complete
background processing pipeline including task execution, monitoring,
and error handling.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from app.core.celery_app import get_celery_app
from app.core.redis_config import get_redis_manager
from app.core.task_retry import get_retry_handler, get_dead_letter_queue
from app.core.performance_monitor import get_performance_monitor
from app.services.task_service import get_task_service, TaskPriority
from tests.conftest import create_test_user, create_test_file, create_test_contract


class TestBackgroundProcessingIntegration:
    """Integration tests for background processing system."""
    
    @pytest.fixture
    def celery_app(self):
        """Get Celery application for testing."""
        return get_celery_app()
    
    @pytest.fixture
    def redis_manager(self):
        """Get Redis manager for testing."""
        with patch('app.core.redis_config.redis.Redis'):
            return get_redis_manager()
    
    @pytest.fixture
    def task_service(self):
        """Get task service for testing."""
        return get_task_service()
    
    @pytest.fixture
    def performance_monitor(self, celery_app):
        """Get performance monitor for testing."""
        return get_performance_monitor(celery_app)
    
    def test_redis_connection_health(self, redis_manager):
        """Test Redis connection health check."""
        with patch.object(redis_manager, '_redis_client') as mock_client:
            mock_client.ping.return_value = True
            mock_client.set.return_value = True
            mock_client.get.return_value = "test_value"
            mock_client.delete.return_value = 1
            
            health_status = redis_manager.health_check()
            
            assert health_status["status"] == "healthy"
            assert health_status["connection_active"] is True
            assert health_status["test_operation_success"] is True
    
    def test_celery_task_routing(self, celery_app):
        """Test Celery task routing configuration."""
        # Test that task routes are properly configured
        routes = celery_app.conf.task_routes
        
        assert "app.tasks.ingest_tasks.*" in routes
        assert "app.tasks.ocr_tasks.*" in routes
        assert "app.tasks.llm_tasks.*" in routes
        assert "app.tasks.export_tasks.*" in routes
        assert "app.tasks.system_tasks.*" in routes
        
        # Verify queue assignments
        assert routes["app.tasks.ingest_tasks.*"]["queue"] == "ingest"
        assert routes["app.tasks.ocr_tasks.*"]["queue"] == "ocr"
        assert routes["app.tasks.llm_tasks.*"]["queue"] == "llm"
        assert routes["app.tasks.export_tasks.*"]["queue"] == "export"
        assert routes["app.tasks.system_tasks.*"]["queue"] == "system"
    
    def test_task_priority_handling(self, task_service):
        """Test task priority handling across different queues."""
        with patch('app.tasks.ingest_tasks.process_file_upload') as mock_task:
            mock_result = Mock()
            mock_result.id = "high-priority-task"
            mock_task.apply_async.return_value = mock_result
            
            # Submit high priority task
            result = task_service.submit_file_processing(
                file_id=1,
                user_id=1,
                storage_key="test/file.pdf",
                original_filename="test.pdf",
                file_size=1024,
                mime_type="application/pdf",
                priority=TaskPriority.HIGH
            )
            
            # Verify priority was set correctly
            assert result["priority"] == "HIGH"
            
            # Check that apply_async was called with correct priority
            call_args = mock_task.apply_async.call_args
            assert "priority" in call_args[1] or any(
                hasattr(arg, 'priority') for arg in call_args[0] if hasattr(arg, 'priority')
            )
    
    def test_retry_mechanism_integration(self):
        """Test retry mechanism integration with tasks."""
        retry_handler = get_retry_handler()
        
        # Test retryable exception
        connection_error = ConnectionError("Network timeout")
        assert retry_handler.should_retry(connection_error, 0) is True
        assert retry_handler.should_retry(connection_error, 2) is True
        assert retry_handler.should_retry(connection_error, 3) is False  # Max retries exceeded
        
        # Test non-retryable exception
        value_error = ValueError("Invalid input")
        assert retry_handler.should_retry(value_error, 0) is False
        
        # Test delay calculation
        delay_0 = retry_handler.calculate_delay(0)
        delay_1 = retry_handler.calculate_delay(1)
        delay_2 = retry_handler.calculate_delay(2)
        
        assert delay_1 > delay_0  # Exponential backoff
        assert delay_2 > delay_1
    
    def test_dead_letter_queue_integration(self):
        """Test dead letter queue integration."""
        dlq = get_dead_letter_queue()
        
        with patch.object(dlq, 'redis_client') as mock_redis:
            # Test adding failed task
            exception = ValueError("Task failed")
            dlq.add_failed_task(
                task_id="failed-task-123",
                task_name="test_task",
                args=(1, 2, 3),
                kwargs={"key": "value"},
                exception=exception,
                retry_count=3
            )
            
            # Verify Redis operations were called
            mock_redis.lpush.assert_called_once()
            mock_redis.hset.assert_called_once()
            mock_redis.expire.assert_called_once()
    
    def test_performance_monitoring_integration(self, performance_monitor):
        """Test performance monitoring integration."""
        with patch('psutil.cpu_percent', return_value=45.0), \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk, \
             patch.object(performance_monitor, 'redis_client') as mock_redis:
            
            # Mock system metrics
            mock_memory.return_value.percent = 60.0
            mock_disk.return_value.percent = 30.0
            
            # Mock Redis queue lengths
            mock_redis.llen.return_value = 5
            
            # Mock Celery inspect
            with patch.object(performance_monitor.celery_app.control, 'inspect') as mock_inspect:
                mock_inspect.return_value.active.return_value = {"worker1": [{"id": "task1"}]}
                
                # Collect metrics
                metrics = performance_monitor.collect_metrics()
                
                assert metrics.cpu_percent == 45.0
                assert metrics.memory_percent == 60.0
                assert metrics.disk_percent == 30.0
                assert metrics.active_tasks == 1
                assert all(length == 5 for length in metrics.queue_lengths.values())
    
    def test_scaling_decision_logic(self, performance_monitor):
        """Test auto-scaling decision logic."""
        from app.core.performance_monitor import PerformanceMetrics
        
        # Create metrics that should trigger scale-up
        high_load_metrics = PerformanceMetrics(
            timestamp=datetime.utcnow(),
            cpu_percent=85.0,  # Above threshold
            memory_percent=70.0,
            disk_percent=40.0,
            queue_lengths={"ingest": 15, "ocr": 8, "llm": 12, "export": 5, "system": 2},  # High queue lengths
            active_tasks=25,
            worker_count=3,
            avg_task_duration=45.0,
            error_rate=2.0,
            throughput=8.0
        )
        
        scaling_decisions = performance_monitor.analyze_scaling_needs(high_load_metrics)
        
        # Should have scaling decisions for queues with high load
        scale_up_decisions = [d for d in scaling_decisions if d.action.value == "scale_up"]
        assert len(scale_up_decisions) > 0
        
        # Check that decisions have proper reasoning
        for decision in scale_up_decisions:
            assert decision.reason
            assert decision.confidence > 0
            assert decision.target_workers > decision.current_workers
    
    def test_task_workflow_integration(self, task_service, session):
        """Test complete task workflow integration."""
        # Create test data
        user = create_test_user(session)
        file_record = create_test_file(session, user_id=user.id)
        
        with patch('app.tasks.ingest_tasks.process_file_upload') as mock_ingest, \
             patch('app.tasks.ocr_tasks.process_document_ocr') as mock_ocr:
            
            # Mock task results
            mock_ingest_result = Mock()
            mock_ingest_result.id = "ingest-task-id"
            mock_ingest_result.parent = Mock()
            mock_ingest_result.parent.id = "parent-task-id"
            
            mock_ocr_result = Mock()
            mock_ocr_result.id = "ocr-task-id"
            
            # Mock chain workflow
            with patch('app.services.task_service.chain') as mock_chain:
                mock_workflow = Mock()
                mock_workflow.apply_async.return_value = mock_ingest_result
                mock_chain.return_value = mock_workflow
                
                # Submit file processing workflow
                result = task_service.submit_file_processing(
                    file_id=file_record.id,
                    user_id=user.id,
                    storage_key=file_record.storage_key,
                    original_filename=file_record.original_filename,
                    file_size=file_record.file_size,
                    mime_type=file_record.mime_type,
                    priority=TaskPriority.NORMAL
                )
                
                # Verify workflow was created and submitted
                assert result["status"] == "submitted"
                assert result["workflow_id"] == "ingest-task-id"
                assert "tasks" in result
                
                # Verify chain was called with correct tasks
                mock_chain.assert_called_once()
    
    def test_error_handling_integration(self, task_service):
        """Test error handling integration across the system."""
        with patch('app.tasks.llm_tasks.analyze_contract_content') as mock_task:
            # Simulate task failure
            mock_task.apply_async.side_effect = Exception("Task submission failed")
            
            # Attempt to submit task
            with pytest.raises(Exception, match="Task submission failed"):
                task_service.submit_contract_analysis(
                    contract_id=1,
                    user_id=1,
                    analysis_type="comprehensive",
                    model_preference="gpt-4",
                    priority=TaskPriority.HIGH
                )
    
    def test_monitoring_api_integration(self, task_service):
        """Test monitoring API integration."""
        with patch.object(task_service.celery_app.control, 'inspect') as mock_inspect:
            # Mock inspect responses
            mock_inspect.return_value.active.return_value = {"worker1": [{"id": "active-task"}]}
            mock_inspect.return_value.scheduled.return_value = {"worker1": [{"id": "scheduled-task"}]}
            mock_inspect.return_value.reserved.return_value = {"worker1": []}
            
            with patch('app.services.task_service.get_redis_client') as mock_redis:
                mock_redis_client = Mock()
                mock_redis_client.llen.return_value = 3
                mock_redis.return_value = mock_redis_client
                
                # Get queue status
                queue_status = task_service.get_queue_status()
                
                assert "timestamp" in queue_status
                assert queue_status["total_active"] == 1
                assert queue_status["total_scheduled"] == 1
                assert queue_status["total_reserved"] == 0
                assert all(length == 3 for length in queue_status["queue_lengths"].values())
    
    def test_task_cancellation_integration(self, task_service):
        """Test task cancellation integration."""
        with patch.object(task_service.celery_app.control, 'revoke') as mock_revoke:
            # Cancel task
            result = task_service.cancel_task("test-task-id", terminate=False)
            
            assert result["status"] == "cancelled"
            assert result["task_id"] == "test-task-id"
            assert result["terminated"] is False
            
            # Verify revoke was called
            mock_revoke.assert_called_once_with("test-task-id", terminate=False)
    
    def test_worker_stats_integration(self, task_service):
        """Test worker statistics integration."""
        with patch.object(task_service.celery_app.control, 'inspect') as mock_inspect:
            mock_inspect.return_value.stats.return_value = {
                "worker1": {"pool": {"max-concurrency": 4, "processes": [1, 2, 3, 4]}}
            }
            mock_inspect.return_value.registered.return_value = {
                "worker1": ["app.tasks.ingest_tasks.process_file_upload"]
            }
            mock_inspect.return_value.ping.return_value = {"worker1": "pong"}
            
            # Get worker stats
            stats = task_service.get_worker_stats()
            
            assert "timestamp" in stats
            assert stats["total_workers"] == 1
            assert "worker1" in stats["worker_stats"]
            assert "worker1" in stats["registered_tasks"]
            assert stats["worker_ping"]["worker1"] == "pong"


class TestPerformanceAndScaling:
    """Performance and scaling integration tests."""
    
    @pytest.fixture
    def performance_monitor(self):
        """Create performance monitor for testing."""
        with patch('app.core.performance_monitor.get_redis_client'), \
             patch('app.core.performance_monitor.psutil'):
            celery_app = Mock()
            return get_performance_monitor(celery_app)
    
    def test_performance_summary_generation(self, performance_monitor):
        """Test performance summary generation."""
        # Add some mock metrics to history
        from app.core.performance_monitor import PerformanceMetrics
        
        mock_metrics = PerformanceMetrics(
            timestamp=datetime.utcnow(),
            cpu_percent=65.0,
            memory_percent=55.0,
            disk_percent=35.0,
            queue_lengths={"ingest": 5, "ocr": 3, "llm": 2, "export": 4, "system": 1},
            active_tasks=8,
            worker_count=4,
            avg_task_duration=30.0,
            error_rate=1.5,
            throughput=12.0
        )
        
        performance_monitor.metrics_history = [mock_metrics]
        
        summary = performance_monitor.get_performance_summary()
        
        assert "timestamp" in summary
        assert "current_metrics" in summary
        assert "averages" in summary
        assert "queue_lengths" in summary
        assert "performance_status" in summary
        assert "recommendations" in summary
        
        # Check performance status
        assert summary["performance_status"] in ["healthy", "warning", "critical"]
        
        # Check that recommendations are provided
        assert isinstance(summary["recommendations"], list)
        assert len(summary["recommendations"]) > 0
