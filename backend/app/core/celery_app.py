"""
Celery application configuration for background task processing.

This module configures Celery with Redis broker, task routing, retry logic,
and monitoring capabilities for the RealtorAgentAI platform.
"""

import logging
from typing import Dict, Any, Optional
from celery import Celery, Task
from celery.signals import task_prerun, task_postrun, task_failure, task_retry
from kombu import Queue, Exchange
import structlog

from .config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class DatabaseTask(Task):
    """
    Custom Celery task base class with database session management.
    
    Provides automatic database session handling and cleanup for tasks
    that need database access.
    """
    
    _session = None
    
    def __call__(self, *args, **kwargs):
        """Execute task with database session management."""
        try:
            return super().__call__(*args, **kwargs)
        finally:
            if self._session:
                self._session.close()
                self._session = None
    
    @property
    def session(self):
        """Get database session for the task."""
        if self._session is None:
            from .database import get_session_context
            self._session = next(get_session_context())
        return self._session


# Create Celery application
celery_app = Celery(
    "realtor_agent_ai",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.ingest_tasks",
        "app.tasks.ocr_tasks", 
        "app.tasks.llm_tasks",
        "app.tasks.export_tasks",
        "app.tasks.system_tasks"
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task routing configuration
    task_routes={
        # Ingest queue - file upload and validation tasks
        "app.tasks.ingest_tasks.*": {"queue": "ingest"},
        
        # OCR queue - document text extraction tasks
        "app.tasks.ocr_tasks.*": {"queue": "ocr"},
        
        # LLM queue - AI model interaction tasks
        "app.tasks.llm_tasks.*": {"queue": "llm"},
        
        # Export queue - document generation and delivery tasks
        "app.tasks.export_tasks.*": {"queue": "export"},
        
        # System queue - maintenance and monitoring tasks
        "app.tasks.system_tasks.*": {"queue": "system"},
    },
    
    # Queue definitions with priority support
    task_queues=(
        # High priority ingest queue for critical file processing
        Queue("ingest", Exchange("ingest"), routing_key="ingest", 
              queue_arguments={"x-max-priority": 10}),
        
        # OCR queue with medium priority
        Queue("ocr", Exchange("ocr"), routing_key="ocr",
              queue_arguments={"x-max-priority": 5}),
        
        # LLM queue with high priority for AI interactions
        Queue("llm", Exchange("llm"), routing_key="llm",
              queue_arguments={"x-max-priority": 8}),
        
        # Export queue with medium priority
        Queue("export", Exchange("export"), routing_key="export",
              queue_arguments={"x-max-priority": 6}),
        
        # System queue with low priority for maintenance tasks
        Queue("system", Exchange("system"), routing_key="system",
              queue_arguments={"x-max-priority": 3}),
        
        # Dead letter queue for failed tasks
        Queue("dead_letter", Exchange("dead_letter"), routing_key="dead_letter"),
    ),
    
    # Task execution settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task result settings
    result_expires=3600,  # Results expire after 1 hour
    result_persistent=True,
    
    # Worker settings
    worker_prefetch_multiplier=1,  # Disable prefetching for better load balancing
    worker_max_tasks_per_child=1000,  # Restart workers after 1000 tasks
    worker_disable_rate_limits=False,
    
    # Task retry settings
    task_acks_late=True,  # Acknowledge tasks after completion
    task_reject_on_worker_lost=True,  # Reject tasks if worker is lost
    task_default_retry_delay=60,  # Default retry delay in seconds
    task_max_retries=3,  # Default maximum retries
    
    # Monitoring and logging
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # Security settings
    worker_hijack_root_logger=False,
    worker_log_color=False,
    
    # Beat scheduler settings (for periodic tasks)
    beat_schedule={
        "cleanup-expired-results": {
            "task": "app.tasks.system_tasks.cleanup_expired_results",
            "schedule": 3600.0,  # Run every hour
        },
        "health-check": {
            "task": "app.tasks.system_tasks.health_check",
            "schedule": 300.0,  # Run every 5 minutes
        },
        "update-task-metrics": {
            "task": "app.tasks.system_tasks.update_task_metrics",
            "schedule": 60.0,  # Run every minute
        },
    },
    beat_schedule_filename="celerybeat-schedule",
)

# Configure retry policy with exponential backoff
celery_app.conf.task_annotations = {
    "*": {
        "rate_limit": "100/m",  # Global rate limit
        "retry_kwargs": {
            "max_retries": 3,
            "countdown": 60,  # Initial delay
        },
        "retry_backoff": True,  # Enable exponential backoff
        "retry_backoff_max": 600,  # Maximum backoff delay (10 minutes)
        "retry_jitter": True,  # Add random jitter to backoff
    },
    
    # Specific task configurations
    "app.tasks.llm_tasks.*": {
        "rate_limit": "10/m",  # Lower rate limit for LLM tasks
        "retry_kwargs": {"max_retries": 5},
        "soft_time_limit": 300,  # 5 minute soft limit
        "time_limit": 600,  # 10 minute hard limit
    },
    
    "app.tasks.ocr_tasks.*": {
        "rate_limit": "20/m",
        "soft_time_limit": 180,  # 3 minute soft limit
        "time_limit": 300,  # 5 minute hard limit
    },
    
    "app.tasks.export_tasks.*": {
        "rate_limit": "30/m",
        "soft_time_limit": 120,  # 2 minute soft limit
        "time_limit": 240,  # 4 minute hard limit
    },
}


# Task event handlers for monitoring and logging
@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """Log task start."""
    logger.info(
        "Task started",
        task_id=task_id,
        task_name=task.name if task else sender,
        args=args,
        kwargs=kwargs
    )


@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, 
                        retval=None, state=None, **kwds):
    """Log task completion."""
    logger.info(
        "Task completed",
        task_id=task_id,
        task_name=task.name if task else sender,
        state=state,
        result_type=type(retval).__name__ if retval else None
    )


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwds):
    """Log task failure."""
    logger.error(
        "Task failed",
        task_id=task_id,
        task_name=sender.name if sender else "unknown",
        exception=str(exception),
        traceback=traceback
    )


@task_retry.connect
def task_retry_handler(sender=None, task_id=None, reason=None, einfo=None, **kwds):
    """Log task retry."""
    logger.warning(
        "Task retry",
        task_id=task_id,
        task_name=sender.name if sender else "unknown",
        reason=str(reason),
        retry_count=sender.request.retries if sender else 0
    )


def get_celery_app() -> Celery:
    """
    Get configured Celery application instance.
    
    Returns:
        Celery: Configured Celery application
    """
    return celery_app


# Export for easy importing
__all__ = [
    "celery_app",
    "get_celery_app", 
    "DatabaseTask"
]
