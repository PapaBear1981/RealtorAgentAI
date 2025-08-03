"""
Task management API endpoints.

This module provides REST API endpoints for task submission, monitoring,
and management of background processing operations.
"""

from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from pydantic import BaseModel, Field
from sqlmodel import Session

from ..core.database import get_session
from ..core.dependencies import get_current_active_user, require_admin
from ..services.task_service import get_task_service, TaskPriority
from ..core.task_retry import get_dead_letter_queue
from ..models.user import User

router = APIRouter()
task_service = get_task_service()
dlq = get_dead_letter_queue()


# Request/Response Models

class TaskSubmissionRequest(BaseModel):
    """Request model for task submission."""
    priority: str = Field(default="NORMAL", description="Task priority level")
    options: Optional[Dict[str, Any]] = Field(default=None, description="Task-specific options")


class FileProcessingRequest(TaskSubmissionRequest):
    """Request model for file processing tasks."""
    file_id: int = Field(description="Database file record ID")
    force_ocr: bool = Field(default=False, description="Force OCR processing")
    enhance_quality: bool = Field(default=True, description="Apply text quality enhancement")


class ContractAnalysisRequest(TaskSubmissionRequest):
    """Request model for contract analysis tasks."""
    contract_id: int = Field(description="Database contract record ID")
    analysis_type: str = Field(default="comprehensive", description="Type of analysis")
    model_preference: str = Field(default="gpt-4", description="Preferred AI model")


class DocumentExportRequest(TaskSubmissionRequest):
    """Request model for document export tasks."""
    contract_id: int = Field(description="Database contract record ID")
    export_format: str = Field(default="pdf", description="Export format (pdf, docx)")
    template_options: Optional[Dict[str, Any]] = Field(default=None, description="Template options")
    include_metadata: bool = Field(default=True, description="Include contract metadata")


class TaskResponse(BaseModel):
    """Response model for task operations."""
    status: str
    task_id: Optional[str] = None
    message: Optional[str] = None
    estimated_completion: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class TaskStatusResponse(BaseModel):
    """Response model for task status."""
    task_id: str
    status: str
    result: Optional[Any] = None
    error: Optional[str] = None
    progress: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


# File Processing Endpoints

@router.post("/files/process", response_model=TaskResponse, tags=["file-processing"])
async def submit_file_processing(
    request: FileProcessingRequest,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Submit file for complete processing pipeline.
    
    Initiates file processing including validation, OCR, and metadata extraction.
    """
    try:
        # Validate priority
        try:
            priority = TaskPriority[request.priority.upper()]
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid priority: {request.priority}"
            )
        
        # Get file record to validate existence
        from ..models.file import File
        file_record = session.get(File, request.file_id)
        if not file_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {request.file_id}"
            )
        
        # Submit processing task
        result = task_service.submit_file_processing(
            file_id=request.file_id,
            user_id=current_user.id,
            storage_key=file_record.storage_key,
            original_filename=file_record.original_filename,
            file_size=file_record.file_size,
            mime_type=file_record.mime_type,
            priority=priority
        )
        
        return TaskResponse(
            status=result["status"],
            task_id=result.get("workflow_id"),
            estimated_completion=result.get("estimated_completion"),
            metadata=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit file processing: {str(e)}"
        )


@router.post("/files/{file_id}/ocr", response_model=TaskResponse, tags=["file-processing"])
async def submit_ocr_processing(
    file_id: int,
    request: TaskSubmissionRequest,
    force_ocr: bool = Query(default=False, description="Force OCR processing"),
    enhance_quality: bool = Query(default=True, description="Apply text enhancement"),
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Submit file for OCR processing.
    
    Extracts text from PDF documents and images using OCR technology.
    """
    try:
        # Validate priority
        try:
            priority = TaskPriority[request.priority.upper()]
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid priority: {request.priority}"
            )
        
        # Validate file exists
        from ..models.file import File
        file_record = session.get(File, file_id)
        if not file_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {file_id}"
            )
        
        # Submit OCR task
        result = task_service.submit_ocr_processing(
            file_id=file_id,
            user_id=current_user.id,
            force_ocr=force_ocr,
            enhance_quality=enhance_quality,
            priority=priority
        )
        
        return TaskResponse(
            status=result["status"],
            task_id=result["task_id"],
            estimated_completion=result.get("estimated_completion"),
            metadata=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit OCR processing: {str(e)}"
        )


# Contract Analysis Endpoints

@router.post("/contracts/analyze", response_model=TaskResponse, tags=["contract-analysis"])
async def submit_contract_analysis(
    request: ContractAnalysisRequest,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Submit contract for AI-powered analysis.
    
    Analyzes contract content using AI models to extract insights,
    identify risks, and provide recommendations.
    """
    try:
        # Validate priority
        try:
            priority = TaskPriority[request.priority.upper()]
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid priority: {request.priority}"
            )
        
        # Validate contract exists
        from ..models.contract import Contract
        contract = session.get(Contract, request.contract_id)
        if not contract:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Contract not found: {request.contract_id}"
            )
        
        # Submit analysis task
        result = task_service.submit_contract_analysis(
            contract_id=request.contract_id,
            user_id=current_user.id,
            analysis_type=request.analysis_type,
            model_preference=request.model_preference,
            priority=priority
        )
        
        return TaskResponse(
            status=result["status"],
            task_id=result["task_id"],
            estimated_completion=result.get("estimated_completion"),
            metadata=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit contract analysis: {str(e)}"
        )


# Document Export Endpoints

@router.post("/contracts/export", response_model=TaskResponse, tags=["document-export"])
async def submit_document_export(
    request: DocumentExportRequest,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Submit contract for document export.
    
    Generates PDF or DOCX documents from contract content with
    customizable formatting and metadata inclusion.
    """
    try:
        # Validate priority
        try:
            priority = TaskPriority[request.priority.upper()]
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid priority: {request.priority}"
            )
        
        # Validate export format
        if request.export_format.lower() not in ["pdf", "docx"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported export format: {request.export_format}"
            )
        
        # Validate contract exists
        from ..models.contract import Contract
        contract = session.get(Contract, request.contract_id)
        if not contract:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Contract not found: {request.contract_id}"
            )
        
        # Submit export task
        result = task_service.submit_document_export(
            contract_id=request.contract_id,
            user_id=current_user.id,
            export_format=request.export_format,
            template_options=request.template_options,
            include_metadata=request.include_metadata,
            priority=priority
        )
        
        return TaskResponse(
            status=result["status"],
            task_id=result["task_id"],
            estimated_completion=result.get("estimated_completion"),
            metadata=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit document export: {str(e)}"
        )


# Task Monitoring Endpoints

@router.get("/tasks/{task_id}/status", response_model=TaskStatusResponse, tags=["task-monitoring"])
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get status of a specific task.
    
    Returns current status, progress, and results for the specified task.
    """
    try:
        status_info = task_service.get_task_status(task_id)
        
        return TaskStatusResponse(
            task_id=task_id,
            status=status_info["status"],
            result=status_info.get("result"),
            error=status_info.get("traceback"),
            metadata=status_info
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task status: {str(e)}"
        )


@router.get("/tasks/queues/status", tags=["task-monitoring"])
async def get_queue_status(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get status of all task queues.
    
    Returns information about active, scheduled, and reserved tasks
    across all processing queues.
    """
    try:
        return task_service.get_queue_status()
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get queue status: {str(e)}"
        )


@router.delete("/tasks/{task_id}", response_model=TaskResponse, tags=["task-management"])
async def cancel_task(
    task_id: str,
    terminate: bool = Query(default=False, description="Forcefully terminate task"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Cancel a running task.
    
    Cancels or terminates the specified task. Use terminate=true for
    forceful termination of stuck tasks.
    """
    try:
        result = task_service.cancel_task(task_id, terminate)
        
        return TaskResponse(
            status=result["status"],
            task_id=task_id,
            message=f"Task {'terminated' if terminate else 'cancelled'} successfully",
            metadata=result
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel task: {str(e)}"
        )


# Admin Endpoints

@router.get("/admin/workers/stats", tags=["admin"])
async def get_worker_stats(
    current_user: User = Depends(require_admin)
):
    """
    Get worker statistics and health information.
    
    Admin-only endpoint that returns detailed worker statistics,
    registered tasks, and health status.
    """
    try:
        return task_service.get_worker_stats()
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get worker stats: {str(e)}"
        )


@router.get("/admin/dead-letter-queue", tags=["admin"])
async def get_failed_tasks(
    limit: int = Query(default=100, le=1000, description="Maximum number of tasks to retrieve"),
    current_user: User = Depends(require_admin)
):
    """
    Get failed tasks from dead letter queue.
    
    Admin-only endpoint that returns tasks that have failed
    after exhausting all retry attempts.
    """
    try:
        failed_tasks = dlq.get_failed_tasks(limit)
        
        return {
            "failed_tasks": failed_tasks,
            "total_count": len(failed_tasks),
            "limit": limit
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get failed tasks: {str(e)}"
        )


@router.post("/admin/dead-letter-queue/{task_id}/retry", response_model=TaskResponse, tags=["admin"])
async def retry_failed_task(
    task_id: str,
    current_user: User = Depends(require_admin)
):
    """
    Retry a failed task from dead letter queue.
    
    Admin-only endpoint that attempts to retry a task that
    previously failed and was moved to the dead letter queue.
    """
    try:
        success = dlq.retry_failed_task(task_id)
        
        if success:
            return TaskResponse(
                status="retry_submitted",
                task_id=task_id,
                message="Task retry submitted successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Failed task not found: {task_id}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retry task: {str(e)}"
        )
