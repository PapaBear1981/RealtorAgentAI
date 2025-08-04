"""
API endpoints for the AI Agent Orchestrator.

This module provides REST API endpoints for managing agent workflows,
executing tasks, and monitoring agent system status.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from pydantic import BaseModel, Field
import structlog

from ..core.dependencies import get_current_active_user
from ..models.user import User
from ..services.agent_orchestrator import (
    get_agent_orchestrator,
    AgentRole,
    TaskPriority,
    WorkflowTask,
    WorkflowStatus
)
from ..services.agent_celery_tasks import (
    execute_agent_workflow,
    data_extraction_task,
    contract_generation_task,
    compliance_check_task,
    signature_tracking_task,
    document_summary_task,
    complete_contract_workflow
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/ai-agents/orchestrator", tags=["AI Agent Orchestrator"])


# Request/Response Models
class TaskRequest(BaseModel):
    """Request model for creating a task."""
    id: str = Field(..., description="Unique task identifier")
    description: str = Field(..., description="Task description")
    expected_output: str = Field(..., description="Expected output description")
    agent_role: AgentRole = Field(..., description="Agent role to execute the task")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="Task priority")
    context: Dict[str, Any] = Field(default_factory=dict, description="Task context data")
    dependencies: List[str] = Field(default_factory=list, description="Task dependencies")


class WorkflowRequest(BaseModel):
    """Request model for creating a workflow."""
    tasks: List[TaskRequest] = Field(..., description="List of tasks to execute")
    workflow_id: Optional[str] = Field(None, description="Optional workflow ID")
    process_type: str = Field(default="sequential", description="Process type (sequential, hierarchical)")


class WorkflowResponse(BaseModel):
    """Response model for workflow operations."""
    workflow_id: str = Field(..., description="Workflow identifier")
    status: str = Field(..., description="Workflow status")
    message: str = Field(..., description="Status message")
    task_count: Optional[int] = Field(None, description="Number of tasks")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")


class WorkflowStatusResponse(BaseModel):
    """Response model for workflow status."""
    workflow_id: str = Field(..., description="Workflow identifier")
    status: str = Field(..., description="Current status")
    active: bool = Field(..., description="Whether workflow is active")
    execution_time: Optional[float] = Field(None, description="Execution time in seconds")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    errors: List[str] = Field(default_factory=list, description="Error messages")


class AgentStatusResponse(BaseModel):
    """Response model for agent system status."""
    total_agents: int = Field(..., description="Total number of agents")
    active_workflows: int = Field(..., description="Number of active workflows")
    completed_workflows: int = Field(..., description="Number of completed workflows")
    memory_stats: Dict[str, Any] = Field(..., description="Memory usage statistics")
    model_router_status: Dict[str, Any] = Field(..., description="Model router status")


# Document Processing Endpoints
class DocumentExtractionRequest(BaseModel):
    """Request model for document data extraction."""
    document_id: str = Field(..., description="Document ID to process")


class ContractGenerationRequest(BaseModel):
    """Request model for contract generation."""
    template_id: str = Field(..., description="Contract template ID")
    extracted_data: Dict[str, Any] = Field(..., description="Extracted data for generation")


class ComplianceCheckRequest(BaseModel):
    """Request model for compliance checking."""
    contract_id: str = Field(..., description="Contract ID to check")
    jurisdiction: str = Field(default="default", description="Jurisdiction for compliance rules")


class SignatureTrackingRequest(BaseModel):
    """Request model for signature tracking."""
    contract_id: str = Field(..., description="Contract ID for signature")
    signers: List[Dict[str, Any]] = Field(..., description="List of signer information")


class DocumentSummaryRequest(BaseModel):
    """Request model for document summarization."""
    document_id: str = Field(..., description="Document ID to summarize")
    summary_type: str = Field(default="comprehensive", description="Type of summary")


class CompleteWorkflowRequest(BaseModel):
    """Request model for complete contract workflow."""
    document_id: str = Field(..., description="Source document ID")
    template_id: str = Field(..., description="Contract template ID")
    signers: List[Dict[str, Any]] = Field(..., description="List of signer information")


@router.post("/workflows", response_model=WorkflowResponse)
async def create_workflow(
    request: WorkflowRequest,
    current_user: User = Depends(get_current_active_user)
) -> WorkflowResponse:
    """
    Create and execute a multi-agent workflow.
    
    This endpoint creates a workflow with multiple tasks that will be executed
    by different specialized agents in the specified order.
    """
    try:
        orchestrator = get_agent_orchestrator()
        
        # Convert request tasks to WorkflowTask objects
        tasks = []
        for task_req in request.tasks:
            task = WorkflowTask(
                id=task_req.id,
                description=task_req.description,
                expected_output=task_req.expected_output,
                agent_role=task_req.agent_role,
                priority=task_req.priority,
                context=task_req.context,
                dependencies=task_req.dependencies
            )
            tasks.append(task)
        
        # Create workflow
        workflow_id = await orchestrator.create_workflow(
            tasks=tasks,
            workflow_id=request.workflow_id,
            user_id=str(current_user.id)
        )
        
        logger.info(
            "Workflow created via API",
            workflow_id=workflow_id,
            user_id=current_user.id,
            task_count=len(tasks)
        )
        
        return WorkflowResponse(
            workflow_id=workflow_id,
            status=WorkflowStatus.PENDING.value,
            message="Workflow created successfully",
            task_count=len(tasks),
            created_at=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Failed to create workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create workflow: {str(e)}"
        )


@router.post("/workflows/{workflow_id}/execute", response_model=WorkflowResponse)
async def execute_workflow(
    workflow_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user)
) -> WorkflowResponse:
    """
    Execute a created workflow in the background.
    
    This endpoint starts the execution of a previously created workflow
    using Celery for background processing.
    """
    try:
        orchestrator = get_agent_orchestrator()
        
        # Check if workflow exists
        status_info = await orchestrator.get_workflow_status(workflow_id)
        if status_info["status"] == "not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {workflow_id} not found"
            )
        
        # Execute workflow in background
        background_tasks.add_task(
            orchestrator.execute_workflow,
            workflow_id
        )
        
        logger.info(
            "Workflow execution started",
            workflow_id=workflow_id,
            user_id=current_user.id
        )
        
        return WorkflowResponse(
            workflow_id=workflow_id,
            status=WorkflowStatus.RUNNING.value,
            message="Workflow execution started",
            created_at=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute workflow: {str(e)}"
        )


@router.get("/workflows/{workflow_id}/status", response_model=WorkflowStatusResponse)
async def get_workflow_status(
    workflow_id: str,
    current_user: User = Depends(get_current_active_user)
) -> WorkflowStatusResponse:
    """Get the current status of a workflow."""
    try:
        orchestrator = get_agent_orchestrator()
        status_info = await orchestrator.get_workflow_status(workflow_id)
        
        if status_info["status"] == "not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {workflow_id} not found"
            )
        
        return WorkflowStatusResponse(
            workflow_id=workflow_id,
            status=status_info["status"],
            active=status_info["active"],
            execution_time=status_info.get("execution_time"),
            completed_at=datetime.fromisoformat(status_info["completed_at"]) if status_info.get("completed_at") else None,
            errors=status_info.get("errors", [])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get workflow status: {str(e)}"
        )


@router.delete("/workflows/{workflow_id}")
async def cancel_workflow(
    workflow_id: str,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Cancel an active workflow."""
    try:
        orchestrator = get_agent_orchestrator()
        cancelled = await orchestrator.cancel_workflow(workflow_id)
        
        if not cancelled:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Active workflow {workflow_id} not found"
            )
        
        logger.info(
            "Workflow cancelled via API",
            workflow_id=workflow_id,
            user_id=current_user.id
        )
        
        return {
            "workflow_id": workflow_id,
            "status": "cancelled",
            "message": "Workflow cancelled successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel workflow: {str(e)}"
        )


@router.get("/status", response_model=AgentStatusResponse)
async def get_agent_system_status(
    current_user: User = Depends(get_current_active_user)
) -> AgentStatusResponse:
    """Get the current status of the agent system."""
    try:
        orchestrator = get_agent_orchestrator()
        memory_stats = await orchestrator.memory_manager.get_memory_stats()
        
        # Get model router status
        model_router_status = {
            "available": True,
            "models_count": len(orchestrator.model_router.models),
            "strategy": orchestrator.model_router.strategy.value
        }
        
        return AgentStatusResponse(
            total_agents=len(orchestrator.agents),
            active_workflows=len(orchestrator.active_workflows),
            completed_workflows=len(orchestrator.workflow_results),
            memory_stats=memory_stats,
            model_router_status=model_router_status
        )
        
    except Exception as e:
        logger.error(f"Failed to get agent system status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent system status: {str(e)}"
        )


# Specialized Agent Task Endpoints
@router.post("/tasks/extract-data")
async def extract_document_data(
    request: DocumentExtractionRequest,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Extract data from a document using the Data Extraction Agent."""
    try:
        task_result = data_extraction_task.delay(
            document_id=request.document_id,
            user_id=str(current_user.id)
        )
        
        return {
            "task_id": task_result.id,
            "document_id": request.document_id,
            "status": "processing",
            "message": "Data extraction task started"
        }
        
    except Exception as e:
        logger.error(f"Failed to start data extraction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start data extraction: {str(e)}"
        )


@router.post("/tasks/generate-contract")
async def generate_contract(
    request: ContractGenerationRequest,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Generate a contract using the Contract Generator Agent."""
    try:
        task_result = contract_generation_task.delay(
            template_id=request.template_id,
            extracted_data=request.extracted_data,
            user_id=str(current_user.id)
        )
        
        return {
            "task_id": task_result.id,
            "template_id": request.template_id,
            "status": "processing",
            "message": "Contract generation task started"
        }
        
    except Exception as e:
        logger.error(f"Failed to start contract generation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start contract generation: {str(e)}"
        )


@router.post("/workflows/complete-contract")
async def execute_complete_contract_workflow(
    request: CompleteWorkflowRequest,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Execute a complete contract processing workflow."""
    try:
        task_result = complete_contract_workflow.delay(
            document_id=request.document_id,
            template_id=request.template_id,
            signers=request.signers,
            user_id=str(current_user.id)
        )
        
        return {
            "task_id": task_result.id,
            "document_id": request.document_id,
            "template_id": request.template_id,
            "status": "processing",
            "message": "Complete contract workflow started"
        }
        
    except Exception as e:
        logger.error(f"Failed to start complete contract workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start complete contract workflow: {str(e)}"
        )
