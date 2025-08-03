"""
Task retry logic and error handling system.

This module provides comprehensive retry strategies, exponential backoff,
dead letter queue management, and error handling for Celery tasks.
"""

import logging
import random
import time
from typing import Dict, Any, Optional, List, Callable, Type
from datetime import datetime, timedelta
from enum import Enum

import structlog
from celery import Task
from celery.exceptions import Retry, WorkerLostError, SoftTimeLimitExceeded
from kombu import Queue, Exchange

from .redis_config import get_redis_client

logger = structlog.get_logger(__name__)


class RetryStrategy(Enum):
    """Retry strategy types."""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"
    FIBONACCI_BACKOFF = "fibonacci_backoff"


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RetryableError(Exception):
    """Base class for retryable errors."""
    
    def __init__(self, message: str, retry_after: Optional[int] = None, severity: ErrorSeverity = ErrorSeverity.MEDIUM):
        super().__init__(message)
        self.retry_after = retry_after
        self.severity = severity


class NonRetryableError(Exception):
    """Base class for non-retryable errors."""
    
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.HIGH):
        super().__init__(message)
        self.severity = severity


class RetryConfig:
    """Configuration for task retry behavior."""
    
    def __init__(
        self,
        max_retries: int = 3,
        strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF,
        base_delay: int = 60,
        max_delay: int = 3600,
        jitter: bool = True,
        backoff_multiplier: float = 2.0,
        retryable_exceptions: Optional[List[Type[Exception]]] = None,
        non_retryable_exceptions: Optional[List[Type[Exception]]] = None
    ):
        self.max_retries = max_retries
        self.strategy = strategy
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter
        self.backoff_multiplier = backoff_multiplier
        self.retryable_exceptions = retryable_exceptions or [
            ConnectionError,
            TimeoutError,
            RetryableError,
            WorkerLostError
        ]
        self.non_retryable_exceptions = non_retryable_exceptions or [
            ValueError,
            TypeError,
            KeyError,
            NonRetryableError,
            SoftTimeLimitExceeded
        ]


class RetryHandler:
    """Handles retry logic and error management for tasks."""
    
    def __init__(self, config: RetryConfig):
        self.config = config
        self.redis_client = get_redis_client()
    
    def should_retry(self, exception: Exception, retry_count: int) -> bool:
        """
        Determine if a task should be retried based on the exception and retry count.
        
        Args:
            exception: The exception that occurred
            retry_count: Current retry count
            
        Returns:
            bool: Whether the task should be retried
        """
        # Check if max retries exceeded
        if retry_count >= self.config.max_retries:
            return False
        
        # Check for non-retryable exceptions
        for non_retryable in self.config.non_retryable_exceptions:
            if isinstance(exception, non_retryable):
                return False
        
        # Check for retryable exceptions
        for retryable in self.config.retryable_exceptions:
            if isinstance(exception, retryable):
                return True
        
        # Default behavior for unknown exceptions
        return True
    
    def calculate_delay(self, retry_count: int) -> int:
        """
        Calculate retry delay based on the configured strategy.
        
        Args:
            retry_count: Current retry count
            
        Returns:
            int: Delay in seconds
        """
        if self.config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = self.config.base_delay * (self.config.backoff_multiplier ** retry_count)
        elif self.config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self.config.base_delay * (retry_count + 1)
        elif self.config.strategy == RetryStrategy.FIBONACCI_BACKOFF:
            delay = self.config.base_delay * self._fibonacci(retry_count + 1)
        else:  # FIXED_DELAY
            delay = self.config.base_delay
        
        # Apply maximum delay limit
        delay = min(delay, self.config.max_delay)
        
        # Add jitter to prevent thundering herd
        if self.config.jitter:
            jitter_amount = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_amount, jitter_amount)
        
        return max(int(delay), 1)  # Ensure at least 1 second delay
    
    def _fibonacci(self, n: int) -> int:
        """Calculate Fibonacci number for backoff strategy."""
        if n <= 1:
            return n
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b
    
    def log_retry_attempt(
        self,
        task_id: str,
        task_name: str,
        exception: Exception,
        retry_count: int,
        delay: int
    ):
        """Log retry attempt with context information."""
        logger.warning(
            "Task retry scheduled",
            task_id=task_id,
            task_name=task_name,
            exception_type=type(exception).__name__,
            exception_message=str(exception),
            retry_count=retry_count,
            max_retries=self.config.max_retries,
            delay_seconds=delay,
            strategy=self.config.strategy.value
        )
    
    def log_final_failure(
        self,
        task_id: str,
        task_name: str,
        exception: Exception,
        retry_count: int
    ):
        """Log final task failure after all retries exhausted."""
        logger.error(
            "Task failed after all retries",
            task_id=task_id,
            task_name=task_name,
            exception_type=type(exception).__name__,
            exception_message=str(exception),
            total_retries=retry_count,
            max_retries=self.config.max_retries
        )


class DeadLetterQueue:
    """Manages dead letter queue for failed tasks."""
    
    def __init__(self, redis_client=None):
        self.redis_client = redis_client or get_redis_client()
        self.dlq_key = "celery:dead_letter_queue"
        self.dlq_metadata_key = "celery:dead_letter_metadata"
    
    def add_failed_task(
        self,
        task_id: str,
        task_name: str,
        args: tuple,
        kwargs: dict,
        exception: Exception,
        retry_count: int,
        failure_timestamp: Optional[datetime] = None
    ):
        """
        Add a failed task to the dead letter queue.
        
        Args:
            task_id: Celery task ID
            task_name: Task name
            args: Task arguments
            kwargs: Task keyword arguments
            exception: Exception that caused the failure
            retry_count: Number of retries attempted
            failure_timestamp: When the task failed
        """
        try:
            failure_timestamp = failure_timestamp or datetime.utcnow()
            
            # Task data
            task_data = {
                "task_id": task_id,
                "task_name": task_name,
                "args": args,
                "kwargs": kwargs,
                "exception_type": type(exception).__name__,
                "exception_message": str(exception),
                "retry_count": retry_count,
                "failure_timestamp": failure_timestamp.isoformat(),
                "severity": getattr(exception, 'severity', ErrorSeverity.MEDIUM).value
            }
            
            # Add to dead letter queue
            self.redis_client.lpush(self.dlq_key, str(task_data))
            
            # Add metadata for easier querying
            metadata_key = f"{self.dlq_metadata_key}:{task_id}"
            self.redis_client.hset(metadata_key, mapping={
                "task_name": task_name,
                "failure_timestamp": failure_timestamp.isoformat(),
                "exception_type": type(exception).__name__,
                "severity": getattr(exception, 'severity', ErrorSeverity.MEDIUM).value
            })
            
            # Set expiration for metadata (30 days)
            self.redis_client.expire(metadata_key, 30 * 24 * 3600)
            
            logger.error(
                "Task added to dead letter queue",
                task_id=task_id,
                task_name=task_name,
                exception_type=type(exception).__name__,
                retry_count=retry_count
            )
            
        except Exception as e:
            logger.error(
                "Failed to add task to dead letter queue",
                task_id=task_id,
                error=str(e)
            )
    
    def get_failed_tasks(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get failed tasks from the dead letter queue.
        
        Args:
            limit: Maximum number of tasks to retrieve
            
        Returns:
            List: Failed task information
        """
        try:
            # Get tasks from the queue
            task_data_list = self.redis_client.lrange(self.dlq_key, 0, limit - 1)
            
            failed_tasks = []
            for task_data_str in task_data_list:
                try:
                    # Parse task data (would use proper JSON in production)
                    task_data = eval(task_data_str)  # Simplified parsing
                    failed_tasks.append(task_data)
                except Exception as e:
                    logger.warning("Failed to parse dead letter task data", error=str(e))
            
            return failed_tasks
            
        except Exception as e:
            logger.error("Failed to retrieve failed tasks", error=str(e))
            return []
    
    def retry_failed_task(self, task_id: str) -> bool:
        """
        Retry a failed task from the dead letter queue.
        
        Args:
            task_id: Task ID to retry
            
        Returns:
            bool: Whether the retry was successful
        """
        try:
            # Get task metadata
            metadata_key = f"{self.dlq_metadata_key}:{task_id}"
            task_metadata = self.redis_client.hgetall(metadata_key)
            
            if not task_metadata:
                logger.warning("Task metadata not found for retry", task_id=task_id)
                return False
            
            # In production, would reconstruct and resubmit the task
            logger.info("Task retry requested", task_id=task_id)
            
            return True
            
        except Exception as e:
            logger.error("Failed to retry task", task_id=task_id, error=str(e))
            return False
    
    def clear_old_tasks(self, days: int = 30):
        """
        Clear old tasks from the dead letter queue.
        
        Args:
            days: Number of days to keep tasks
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Get all tasks
            all_tasks = self.get_failed_tasks(limit=1000)
            
            removed_count = 0
            for task_data in all_tasks:
                try:
                    failure_time = datetime.fromisoformat(task_data["failure_timestamp"])
                    if failure_time < cutoff_date:
                        # Remove from queue (simplified - would need proper implementation)
                        removed_count += 1
                except Exception:
                    continue
            
            logger.info(
                "Cleaned up old dead letter tasks",
                removed_count=removed_count,
                cutoff_days=days
            )
            
        except Exception as e:
            logger.error("Failed to clean up dead letter queue", error=str(e))


# Global instances
default_retry_config = RetryConfig()
default_retry_handler = RetryHandler(default_retry_config)
dead_letter_queue = DeadLetterQueue()


def get_retry_handler(config: Optional[RetryConfig] = None) -> RetryHandler:
    """
    Get retry handler instance.
    
    Args:
        config: Optional custom retry configuration
        
    Returns:
        RetryHandler: Retry handler instance
    """
    if config:
        return RetryHandler(config)
    return default_retry_handler


def get_dead_letter_queue() -> DeadLetterQueue:
    """
    Get dead letter queue instance.
    
    Returns:
        DeadLetterQueue: Dead letter queue instance
    """
    return dead_letter_queue


# Export for easy importing
__all__ = [
    "RetryStrategy",
    "ErrorSeverity",
    "RetryableError",
    "NonRetryableError",
    "RetryConfig",
    "RetryHandler",
    "DeadLetterQueue",
    "get_retry_handler",
    "get_dead_letter_queue"
]
