"""
Task service for managing background processing operations.

This service provides high-level interfaces for submitting and monitoring
background tasks across different queues and processing types.
"""

import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from enum import Enum

import structlog
from celery import group, chain, chord
from celery.result import AsyncResult, GroupResult

from ..core.celery_app import get_celery_app
from ..tasks.ingest_tasks import process_file_upload, validate_document, extract_metadata, virus_scan_file
from ..tasks.ocr_tasks import extract_text_from_pdf, extract_text_from_image, process_document_ocr
from ..tasks.llm_tasks import analyze_contract_content, generate_contract_summary, extract_contract_entities
from ..tasks.export_tasks import generate_pdf_document, generate_docx_document, prepare_document_delivery
from ..tasks.system_tasks import health_check, update_task_metrics, cleanup_expired_results

logger = structlog.get_logger(__name__)


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = 1
    NORMAL = 5
    HIGH = 8
    CRITICAL = 10


class TaskStatus(Enum):
    """Task status enumeration."""
    PENDING = "PENDING"
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RETRY = "RETRY"
    REVOKED = "REVOKED"


class TaskService:
    """
    Service for managing background tasks and queues.
    
    Provides high-level interfaces for task submission, monitoring,
    and management across different processing queues.
    """
    
    def __init__(self):
        self.celery_app = get_celery_app()
    
    # File Processing Tasks
    
    def submit_file_processing(
        self,
        file_id: int,
        user_id: int,
        storage_key: str,
        original_filename: str,
        file_size: int,
        mime_type: str,
        priority: TaskPriority = TaskPriority.NORMAL
    ) -> Dict[str, Any]:
        """
        Submit file for complete processing pipeline.
        
        Args:
            file_id: Database file record ID
            user_id: User who uploaded the file
            storage_key: Storage location key
            original_filename: Original filename
            file_size: File size in bytes
            mime_type: MIME type of the file
            priority: Task priority level
            
        Returns:
            Dict: Task submission results with task IDs
        """
        try:
            logger.info(
                "Submitting file for processing",
                file_id=file_id,
                user_id=user_id,
                filename=original_filename,
                priority=priority.name
            )
            
            # Create processing workflow
            workflow = chain(
                # Step 1: Initial file processing
                process_file_upload.s(
                    file_id, user_id, storage_key, original_filename, file_size, mime_type
                ).set(priority=priority.value),
                
                # Step 2: OCR processing (if applicable)
                process_document_ocr.s(file_id, user_id, False, True).set(priority=priority.value)
            )
            
            # Execute workflow
            result = workflow.apply_async()
            
            return {
                "status": "submitted",
                "workflow_id": result.id,
                "file_id": file_id,
                "priority": priority.name,
                "estimated_completion": (datetime.utcnow() + timedelta(minutes=10)).isoformat(),
                "tasks": {
                    "file_processing": result.parent.id if result.parent else None,
                    "ocr_processing": result.id
                }
            }
            
        except Exception as exc:
            logger.error("Failed to submit file processing", file_id=file_id, error=str(exc))
            raise
    
    def submit_ocr_processing(
        self,
        file_id: int,
        user_id: int,
        force_ocr: bool = False,
        enhance_quality: bool = True,
        priority: TaskPriority = TaskPriority.NORMAL
    ) -> Dict[str, Any]:
        """
        Submit file for OCR processing.
        
        Args:
            file_id: Database file record ID
            user_id: User requesting processing
            force_ocr: Force OCR even if text is extractable
            enhance_quality: Apply text quality enhancement
            priority: Task priority level
            
        Returns:
            Dict: Task submission results
        """
        try:
            logger.info(
                "Submitting OCR processing",
                file_id=file_id,
                user_id=user_id,
                force_ocr=force_ocr,
                priority=priority.name
            )
            
            result = process_document_ocr.apply_async(
                args=[file_id, user_id, force_ocr, enhance_quality],
                priority=priority.value
            )
            
            return {
                "status": "submitted",
                "task_id": result.id,
                "file_id": file_id,
                "priority": priority.name,
                "estimated_completion": (datetime.utcnow() + timedelta(minutes=5)).isoformat()
            }
            
        except Exception as exc:
            logger.error("Failed to submit OCR processing", file_id=file_id, error=str(exc))
            raise
    
    # Contract Analysis Tasks
    
    def submit_contract_analysis(
        self,
        contract_id: int,
        user_id: int,
        analysis_type: str = "comprehensive",
        model_preference: str = "gpt-4",
        priority: TaskPriority = TaskPriority.HIGH
    ) -> Dict[str, Any]:
        """
        Submit contract for AI analysis.
        
        Args:
            contract_id: Database contract record ID
            user_id: User requesting analysis
            analysis_type: Type of analysis to perform
            model_preference: Preferred AI model
            priority: Task priority level
            
        Returns:
            Dict: Task submission results
        """
        try:
            logger.info(
                "Submitting contract analysis",
                contract_id=contract_id,
                user_id=user_id,
                analysis_type=analysis_type,
                priority=priority.name
            )
            
            result = analyze_contract_content.apply_async(
                args=[contract_id, user_id, analysis_type, model_preference],
                priority=priority.value
            )
            
            return {
                "status": "submitted",
                "task_id": result.id,
                "contract_id": contract_id,
                "analysis_type": analysis_type,
                "priority": priority.name,
                "estimated_completion": (datetime.utcnow() + timedelta(minutes=3)).isoformat()
            }
            
        except Exception as exc:
            logger.error("Failed to submit contract analysis", contract_id=contract_id, error=str(exc))
            raise
    
    def submit_contract_summary(
        self,
        contract_text: str,
        summary_type: str = "executive",
        max_length: int = 500,
        priority: TaskPriority = TaskPriority.NORMAL
    ) -> Dict[str, Any]:
        """
        Submit contract for summary generation.
        
        Args:
            contract_text: Contract content to summarize
            summary_type: Type of summary to generate
            max_length: Maximum summary length
            priority: Task priority level
            
        Returns:
            Dict: Task submission results
        """
        try:
            logger.info(
                "Submitting contract summary",
                text_length=len(contract_text),
                summary_type=summary_type,
                priority=priority.name
            )
            
            result = generate_contract_summary.apply_async(
                args=[contract_text, summary_type, max_length],
                priority=priority.value
            )
            
            return {
                "status": "submitted",
                "task_id": result.id,
                "summary_type": summary_type,
                "priority": priority.name,
                "estimated_completion": (datetime.utcnow() + timedelta(minutes=2)).isoformat()
            }
            
        except Exception as exc:
            logger.error("Failed to submit contract summary", error=str(exc))
            raise
    
    # Document Export Tasks
    
    def submit_document_export(
        self,
        contract_id: int,
        user_id: int,
        export_format: str = "pdf",
        template_options: Optional[Dict[str, Any]] = None,
        include_metadata: bool = True,
        priority: TaskPriority = TaskPriority.NORMAL
    ) -> Dict[str, Any]:
        """
        Submit contract for document export.
        
        Args:
            contract_id: Database contract record ID
            user_id: User requesting export
            export_format: Export format (pdf, docx)
            template_options: Formatting options
            include_metadata: Include contract metadata
            priority: Task priority level
            
        Returns:
            Dict: Task submission results
        """
        try:
            logger.info(
                "Submitting document export",
                contract_id=contract_id,
                user_id=user_id,
                export_format=export_format,
                priority=priority.name
            )
            
            # Select appropriate export task
            if export_format.lower() == "pdf":
                task = generate_pdf_document
            elif export_format.lower() == "docx":
                task = generate_docx_document
            else:
                raise ValueError(f"Unsupported export format: {export_format}")
            
            result = task.apply_async(
                args=[contract_id, user_id, template_options, include_metadata],
                priority=priority.value
            )
            
            return {
                "status": "submitted",
                "task_id": result.id,
                "contract_id": contract_id,
                "export_format": export_format,
                "priority": priority.name,
                "estimated_completion": (datetime.utcnow() + timedelta(minutes=2)).isoformat()
            }
            
        except Exception as exc:
            logger.error("Failed to submit document export", contract_id=contract_id, error=str(exc))
            raise
    
    # Task Monitoring and Management
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get status of a specific task.
        
        Args:
            task_id: Celery task ID
            
        Returns:
            Dict: Task status information
        """
        try:
            result = AsyncResult(task_id, app=self.celery_app)
            
            status_info = {
                "task_id": task_id,
                "status": result.status,
                "result": result.result if result.ready() else None,
                "traceback": result.traceback if result.failed() else None,
                "date_done": result.date_done.isoformat() if result.date_done else None,
                "task_name": result.name,
                "args": result.args,
                "kwargs": result.kwargs
            }
            
            # Add progress information if available
            if hasattr(result, 'info') and result.info:
                if isinstance(result.info, dict):
                    status_info.update(result.info)
            
            return status_info
            
        except Exception as exc:
            logger.error("Failed to get task status", task_id=task_id, error=str(exc))
            return {
                "task_id": task_id,
                "status": "ERROR",
                "error": str(exc)
            }
    
    def get_queue_status(self) -> Dict[str, Any]:
        """
        Get status of all task queues.
        
        Returns:
            Dict: Queue status information
        """
        try:
            inspect = self.celery_app.control.inspect()
            
            # Get active tasks
            active_tasks = inspect.active()
            
            # Get scheduled tasks
            scheduled_tasks = inspect.scheduled()
            
            # Get reserved tasks
            reserved_tasks = inspect.reserved()
            
            # Get queue lengths (requires Redis inspection)
            from ..core.redis_config import get_redis_client
            redis_client = get_redis_client()
            
            queue_lengths = {}
            for queue_name in ['ingest', 'ocr', 'llm', 'export', 'system']:
                try:
                    length = redis_client.llen(queue_name)
                    queue_lengths[queue_name] = length
                except Exception:
                    queue_lengths[queue_name] = 0
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "active_tasks": active_tasks,
                "scheduled_tasks": scheduled_tasks,
                "reserved_tasks": reserved_tasks,
                "queue_lengths": queue_lengths,
                "total_active": sum(len(tasks) for tasks in (active_tasks or {}).values()),
                "total_scheduled": sum(len(tasks) for tasks in (scheduled_tasks or {}).values()),
                "total_reserved": sum(len(tasks) for tasks in (reserved_tasks or {}).values())
            }
            
        except Exception as exc:
            logger.error("Failed to get queue status", error=str(exc))
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(exc)
            }
    
    def cancel_task(self, task_id: str, terminate: bool = False) -> Dict[str, Any]:
        """
        Cancel a running task.
        
        Args:
            task_id: Celery task ID
            terminate: Whether to terminate the task forcefully
            
        Returns:
            Dict: Cancellation results
        """
        try:
            logger.info("Cancelling task", task_id=task_id, terminate=terminate)
            
            if terminate:
                self.celery_app.control.terminate(task_id)
            else:
                self.celery_app.control.revoke(task_id, terminate=False)
            
            return {
                "status": "cancelled",
                "task_id": task_id,
                "terminated": terminate,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as exc:
            logger.error("Failed to cancel task", task_id=task_id, error=str(exc))
            return {
                "status": "error",
                "task_id": task_id,
                "error": str(exc),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def get_worker_stats(self) -> Dict[str, Any]:
        """
        Get worker statistics and health information.
        
        Returns:
            Dict: Worker statistics
        """
        try:
            inspect = self.celery_app.control.inspect()
            
            # Get worker stats
            stats = inspect.stats()
            
            # Get registered tasks
            registered = inspect.registered()
            
            # Get worker ping
            ping = inspect.ping()
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "worker_stats": stats,
                "registered_tasks": registered,
                "worker_ping": ping,
                "total_workers": len(ping or {})
            }
            
        except Exception as exc:
            logger.error("Failed to get worker stats", error=str(exc))
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(exc)
            }


# Global task service instance
_task_service = None


def get_task_service() -> TaskService:
    """
    Get global task service instance.
    
    Returns:
        TaskService: Task service instance
    """
    global _task_service
    
    if _task_service is None:
        _task_service = TaskService()
    
    return _task_service
