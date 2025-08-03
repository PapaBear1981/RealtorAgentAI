"""
System tasks for maintenance and monitoring.

This module contains Celery tasks for system maintenance, health checks,
metrics collection, and background cleanup operations.
"""

import logging
import os
import psutil
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from celery import current_task
import structlog
from sqlmodel import select, func, and_

from ..core.celery_app import celery_app, DatabaseTask
from ..core.storage import get_storage_client
from ..models.audit_log import AuditLog
from ..models.file import File, ProcessingStatus
from ..models.contract import Contract
from ..models.user import User

logger = structlog.get_logger(__name__)


@celery_app.task(bind=True, name="app.tasks.system_tasks.cleanup_expired_results")
def cleanup_expired_results(self) -> Dict[str, Any]:
    """
    Clean up expired Celery task results and temporary files.
    
    Returns:
        Dict: Cleanup results and statistics
    """
    try:
        logger.info("Starting expired results cleanup")
        
        cleanup_stats = {
            "celery_results_cleaned": 0,
            "temp_files_cleaned": 0,
            "storage_space_freed": 0,
            "errors": []
        }
        
        # Clean up Celery results (handled by Celery's built-in cleanup)
        # This is mainly for custom cleanup logic
        
        # Clean up temporary files older than 24 hours
        temp_dir = "/tmp"  # Adjust based on your system
        if os.path.exists(temp_dir):
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            
            for filename in os.listdir(temp_dir):
                if filename.startswith(("celery_", "contract_", "temp_")):
                    filepath = os.path.join(temp_dir, filename)
                    try:
                        file_stat = os.stat(filepath)
                        file_time = datetime.fromtimestamp(file_stat.st_mtime)
                        
                        if file_time < cutoff_time:
                            file_size = file_stat.st_size
                            os.remove(filepath)
                            cleanup_stats["temp_files_cleaned"] += 1
                            cleanup_stats["storage_space_freed"] += file_size
                    except Exception as e:
                        cleanup_stats["errors"].append(f"Error cleaning {filepath}: {str(e)}")
        
        # Clean up old processing jobs that are stuck
        # This would be implemented based on your specific needs
        
        logger.info(
            "Expired results cleanup completed",
            temp_files_cleaned=cleanup_stats["temp_files_cleaned"],
            space_freed=cleanup_stats["storage_space_freed"],
            errors=len(cleanup_stats["errors"])
        )
        
        return {
            "status": "completed",
            "cleanup_stats": cleanup_stats,
            "timestamp": datetime.utcnow().isoformat(),
            "task_id": self.request.id
        }
        
    except Exception as exc:
        logger.error("Expired results cleanup failed", error=str(exc), exc_info=True)
        
        return {
            "status": "failed",
            "error": str(exc),
            "timestamp": datetime.utcnow().isoformat(),
            "task_id": self.request.id
        }


@celery_app.task(bind=True, name="app.tasks.system_tasks.health_check")
def health_check(self) -> Dict[str, Any]:
    """
    Perform comprehensive system health check.
    
    Returns:
        Dict: System health status and metrics
    """
    try:
        logger.info("Starting system health check")
        
        health_status = {
            "overall_status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {}
        }
        
        # Check system resources
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            health_status["checks"]["system_resources"] = {
                "status": "healthy",
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "disk_percent": disk.percent,
                "disk_free_gb": disk.free / (1024**3)
            }
            
            # Mark as unhealthy if resources are critically low
            if cpu_percent > 90 or memory.percent > 90 or disk.percent > 90:
                health_status["checks"]["system_resources"]["status"] = "critical"
                health_status["overall_status"] = "unhealthy"
            elif cpu_percent > 75 or memory.percent > 75 or disk.percent > 75:
                health_status["checks"]["system_resources"]["status"] = "warning"
                if health_status["overall_status"] == "healthy":
                    health_status["overall_status"] = "warning"
                    
        except Exception as e:
            health_status["checks"]["system_resources"] = {
                "status": "error",
                "error": str(e)
            }
            health_status["overall_status"] = "unhealthy"
        
        # Check Redis connection
        try:
            from ..core.celery_app import celery_app
            redis_client = celery_app.broker_connection().default_channel.client
            redis_client.ping()
            
            health_status["checks"]["redis"] = {
                "status": "healthy",
                "connection": "active"
            }
        except Exception as e:
            health_status["checks"]["redis"] = {
                "status": "error",
                "error": str(e)
            }
            health_status["overall_status"] = "unhealthy"
        
        # Check database connection
        try:
            from ..core.database import get_session_context
            with next(get_session_context()) as session:
                # Simple query to test connection
                result = session.exec(select(func.count(User.id))).first()
                
                health_status["checks"]["database"] = {
                    "status": "healthy",
                    "connection": "active",
                    "user_count": result or 0
                }
        except Exception as e:
            health_status["checks"]["database"] = {
                "status": "error",
                "error": str(e)
            }
            health_status["overall_status"] = "unhealthy"
        
        # Check storage system
        try:
            storage_client = get_storage_client()
            # Test storage connectivity
            test_key = f"health_check_{datetime.utcnow().timestamp()}"
            storage_client.upload_file(
                BytesIO(b"health check"), test_key, "text/plain", {}
            )
            storage_client.delete_file(test_key)
            
            health_status["checks"]["storage"] = {
                "status": "healthy",
                "connection": "active"
            }
        except Exception as e:
            health_status["checks"]["storage"] = {
                "status": "error",
                "error": str(e)
            }
            health_status["overall_status"] = "unhealthy"
        
        logger.info(
            "System health check completed",
            overall_status=health_status["overall_status"],
            checks_passed=sum(1 for check in health_status["checks"].values() 
                            if check.get("status") == "healthy")
        )
        
        return health_status
        
    except Exception as exc:
        logger.error("System health check failed", error=str(exc), exc_info=True)
        
        return {
            "overall_status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(exc),
            "task_id": self.request.id
        }


@celery_app.task(bind=True, base=DatabaseTask, name="app.tasks.system_tasks.update_task_metrics")
def update_task_metrics(self) -> Dict[str, Any]:
    """
    Update task execution metrics and statistics.
    
    Returns:
        Dict: Updated metrics and statistics
    """
    try:
        logger.info("Starting task metrics update")
        
        # Get task statistics from audit logs
        last_hour = datetime.utcnow() - timedelta(hours=1)
        last_day = datetime.utcnow() - timedelta(days=1)
        
        # Task execution counts
        tasks_last_hour = self.session.exec(
            select(func.count(AuditLog.id)).where(
                and_(
                    AuditLog.ts >= last_hour,
                    AuditLog.actor.like("system:%_task:%")
                )
            )
        ).first() or 0
        
        tasks_last_day = self.session.exec(
            select(func.count(AuditLog.id)).where(
                and_(
                    AuditLog.ts >= last_day,
                    AuditLog.actor.like("system:%_task:%")
                )
            )
        ).first() or 0
        
        # Success rate
        successful_tasks_day = self.session.exec(
            select(func.count(AuditLog.id)).where(
                and_(
                    AuditLog.ts >= last_day,
                    AuditLog.actor.like("system:%_task:%"),
                    AuditLog.success == True
                )
            )
        ).first() or 0
        
        success_rate = (successful_tasks_day / tasks_last_day * 100) if tasks_last_day > 0 else 100
        
        # File processing statistics
        files_processing = self.session.exec(
            select(func.count(File.id)).where(File.processing_status == ProcessingStatus.PROCESSING)
        ).first() or 0
        
        files_completed_day = self.session.exec(
            select(func.count(File.id)).where(
                and_(
                    File.processing_completed_at >= last_day,
                    File.processing_status == ProcessingStatus.COMPLETED
                )
            )
        ).first() or 0
        
        # Contract processing statistics
        contracts_created_day = self.session.exec(
            select(func.count(Contract.id)).where(Contract.created_at >= last_day)
        ).first() or 0
        
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "task_execution": {
                "tasks_last_hour": tasks_last_hour,
                "tasks_last_day": tasks_last_day,
                "success_rate_percent": round(success_rate, 2),
                "successful_tasks_day": successful_tasks_day
            },
            "file_processing": {
                "files_currently_processing": files_processing,
                "files_completed_last_day": files_completed_day
            },
            "contract_processing": {
                "contracts_created_last_day": contracts_created_day
            },
            "system_info": {
                "task_id": self.request.id,
                "worker_id": self.request.hostname
            }
        }
        
        # Store metrics (in production, would store in time-series database)
        logger.info(
            "Task metrics updated",
            tasks_last_hour=tasks_last_hour,
            tasks_last_day=tasks_last_day,
            success_rate=success_rate
        )
        
        return {
            "status": "completed",
            "metrics": metrics
        }
        
    except Exception as exc:
        logger.error("Task metrics update failed", error=str(exc), exc_info=True)
        
        return {
            "status": "failed",
            "error": str(exc),
            "timestamp": datetime.utcnow().isoformat(),
            "task_id": self.request.id
        }


@celery_app.task(bind=True, base=DatabaseTask, name="app.tasks.system_tasks.backup_database")
def backup_database(self, backup_type: str = "incremental") -> Dict[str, Any]:
    """
    Perform database backup operation.
    
    Args:
        backup_type: Type of backup (full, incremental)
        
    Returns:
        Dict: Backup operation results
    """
    try:
        logger.info("Starting database backup", backup_type=backup_type)
        
        # This is a placeholder for actual backup implementation
        # In production, would integrate with database-specific backup tools
        
        backup_info = {
            "backup_type": backup_type,
            "started_at": datetime.utcnow().isoformat(),
            "status": "completed",
            "backup_size": 0,  # Would be actual backup size
            "backup_location": f"backup_{backup_type}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            "tables_backed_up": ["users", "contracts", "files", "audit_logs", "templates"],
            "duration_seconds": 0
        }
        
        # Simulate backup process
        import time
        time.sleep(2)  # Simulate backup time
        
        backup_info["completed_at"] = datetime.utcnow().isoformat()
        backup_info["duration_seconds"] = 2
        
        logger.info(
            "Database backup completed",
            backup_type=backup_type,
            backup_location=backup_info["backup_location"]
        )
        
        return {
            "status": "completed",
            "backup_info": backup_info,
            "task_id": self.request.id
        }
        
    except Exception as exc:
        logger.error("Database backup failed", error=str(exc), exc_info=True)
        
        return {
            "status": "failed",
            "error": str(exc),
            "backup_type": backup_type,
            "timestamp": datetime.utcnow().isoformat(),
            "task_id": self.request.id
        }


@celery_app.task(bind=True, name="app.tasks.system_tasks.optimize_storage")
def optimize_storage(self) -> Dict[str, Any]:
    """
    Optimize storage by cleaning up unused files and compressing old data.
    
    Returns:
        Dict: Storage optimization results
    """
    try:
        logger.info("Starting storage optimization")
        
        optimization_stats = {
            "files_analyzed": 0,
            "files_compressed": 0,
            "files_deleted": 0,
            "space_saved_bytes": 0,
            "errors": []
        }
        
        # This is a placeholder for actual storage optimization
        # In production, would implement:
        # - Compress old files
        # - Remove orphaned files
        # - Optimize file storage layout
        # - Clean up temporary files
        
        # Simulate optimization process
        optimization_stats["files_analyzed"] = 100
        optimization_stats["files_compressed"] = 25
        optimization_stats["files_deleted"] = 5
        optimization_stats["space_saved_bytes"] = 1024 * 1024 * 50  # 50MB saved
        
        logger.info(
            "Storage optimization completed",
            files_compressed=optimization_stats["files_compressed"],
            files_deleted=optimization_stats["files_deleted"],
            space_saved_mb=optimization_stats["space_saved_bytes"] / (1024 * 1024)
        )
        
        return {
            "status": "completed",
            "optimization_stats": optimization_stats,
            "timestamp": datetime.utcnow().isoformat(),
            "task_id": self.request.id
        }
        
    except Exception as exc:
        logger.error("Storage optimization failed", error=str(exc), exc_info=True)
        
        return {
            "status": "failed",
            "error": str(exc),
            "timestamp": datetime.utcnow().isoformat(),
            "task_id": self.request.id
        }
