"""
AI Agents API Endpoints.

This module provides RESTful API endpoints for AI agent operations,
including agent execution, workflow management, and status tracking.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field
import structlog

from ...core.auth import get_current_user
from ...models.user import User
from ...services.agent_orchestrator import get_agent_orchestrator, AgentRole
from ...services.agent_memory import get_memory_manager
from ...services.agent_tools import get_tools_for_agent
from ...core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

router = APIRouter(prefix="/ai-agents", tags=["AI Agents"])
security = HTTPBearer()


# Request/Response Models
class AgentExecutionRequest(BaseModel):
    """Request model for agent execution."""
    agent_role: str = Field(..., description="Agent role (data_extraction, contract_generator, etc.)")
    task_description: str = Field(..., description="Description of the task to perform")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="Input data for the agent")
    workflow_id: Optional[str] = Field(None, description="Workflow ID for tracking")
    options: Dict[str, Any] = Field(default_factory=dict, description="Additional options")


class AgentExecutionResponse(BaseModel):
    """Response model for agent execution."""
    execution_id: str = Field(..., description="Unique execution ID")
    agent_role: str = Field(..., description="Agent role")
    status: str = Field(..., description="Execution status")
    created_at: datetime = Field(..., description="Creation timestamp")
    workflow_id: Optional[str] = Field(None, description="Workflow ID")


class AgentStatusResponse(BaseModel):
    """Response model for agent status."""
    execution_id: str = Field(..., description="Execution ID")
    status: str = Field(..., description="Current status")
    progress: float = Field(..., description="Progress percentage (0-100)")
    result: Optional[Dict[str, Any]] = Field(None, description="Execution result if completed")
    error: Optional[str] = Field(None, description="Error message if failed")
    updated_at: datetime = Field(..., description="Last update timestamp")


class WorkflowRequest(BaseModel):
    """Request model for workflow creation."""
    workflow_type: str = Field(..., description="Type of workflow")
    description: str = Field(..., description="Workflow description")
    agents: List[str] = Field(..., description="List of agent roles to include")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="Initial workflow data")


class WorkflowResponse(BaseModel):
    """Response model for workflow operations."""
    workflow_id: str = Field(..., description="Workflow ID")
    status: str = Field(..., description="Workflow status")
    agents: List[str] = Field(..., description="Included agents")
    created_at: datetime = Field(..., description="Creation timestamp")
    progress: float = Field(..., description="Overall progress")


class ToolListResponse(BaseModel):
    """Response model for tool listing."""
    agent_role: str = Field(..., description="Agent role")
    tools: List[Dict[str, Any]] = Field(..., description="Available tools")
    total_count: int = Field(..., description="Total number of tools")


# In-memory storage for execution tracking (in production, use Redis or database)
_execution_storage = {}
_workflow_storage = {}


@router.get("/", summary="Get AI Agents Overview")
async def get_agents_overview(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get overview of available AI agents and their capabilities."""
    try:
        orchestrator = get_agent_orchestrator()
        
        agents_info = {}
        for role in AgentRole:
            tools = get_tools_for_agent(role.value)
            agents_info[role.value] = {
                "role": role.value,
                "description": _get_agent_description(role),
                "tools_count": len(tools),
                "capabilities": _get_agent_capabilities(role)
            }
        
        return {
            "agents": agents_info,
            "total_agents": len(AgentRole),
            "system_status": "operational",
            "user_id": current_user.id
        }
        
    except Exception as e:
        logger.error(f"Failed to get agents overview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agents overview"
        )


@router.get("/{agent_role}/tools", response_model=ToolListResponse)
async def get_agent_tools(
    agent_role: str,
    current_user: User = Depends(get_current_user)
) -> ToolListResponse:
    """Get available tools for a specific agent role."""
    try:
        # Validate agent role
        if agent_role not in [role.value for role in AgentRole]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid agent role: {agent_role}"
            )
        
        tools = get_tools_for_agent(agent_role)
        tools_info = []
        
        for tool in tools:
            tools_info.append({
                "name": tool.name,
                "description": tool.description,
                "category": tool.category.value if hasattr(tool.category, 'value') else str(tool.category)
            })
        
        return ToolListResponse(
            agent_role=agent_role,
            tools=tools_info,
            total_count=len(tools_info)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent tools: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agent tools"
        )


@router.post("/{agent_role}/execute", response_model=AgentExecutionResponse)
async def execute_agent(
    agent_role: str,
    request: AgentExecutionRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
) -> AgentExecutionResponse:
    """Execute an AI agent with the specified task."""
    try:
        # Validate agent role
        if agent_role not in [role.value for role in AgentRole]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid agent role: {agent_role}"
            )
        
        # Generate execution ID
        execution_id = str(uuid.uuid4())
        
        # Create execution record
        execution_record = {
            "execution_id": execution_id,
            "agent_role": agent_role,
            "task_description": request.task_description,
            "input_data": request.input_data,
            "workflow_id": request.workflow_id,
            "user_id": current_user.id,
            "status": "queued",
            "progress": 0.0,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "result": None,
            "error": None
        }
        
        _execution_storage[execution_id] = execution_record
        
        # Start background execution
        background_tasks.add_task(
            _execute_agent_background,
            execution_id,
            agent_role,
            request.task_description,
            request.input_data,
            current_user.id,
            request.workflow_id
        )
        
        return AgentExecutionResponse(
            execution_id=execution_id,
            agent_role=agent_role,
            status="queued",
            created_at=execution_record["created_at"],
            workflow_id=request.workflow_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute agent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute agent"
        )


@router.get("/executions/{execution_id}/status", response_model=AgentStatusResponse)
async def get_execution_status(
    execution_id: str,
    current_user: User = Depends(get_current_user)
) -> AgentStatusResponse:
    """Get the status of an agent execution."""
    try:
        if execution_id not in _execution_storage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Execution not found"
            )
        
        execution = _execution_storage[execution_id]
        
        # Check if user has access to this execution
        if execution["user_id"] != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this execution"
            )
        
        return AgentStatusResponse(
            execution_id=execution_id,
            status=execution["status"],
            progress=execution["progress"],
            result=execution["result"],
            error=execution["error"],
            updated_at=execution["updated_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get execution status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve execution status"
        )


@router.post("/workflows", response_model=WorkflowResponse)
async def create_workflow(
    request: WorkflowRequest,
    current_user: User = Depends(get_current_user)
) -> WorkflowResponse:
    """Create a new multi-agent workflow."""
    try:
        # Validate agent roles
        for agent_role in request.agents:
            if agent_role not in [role.value for role in AgentRole]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid agent role: {agent_role}"
                )
        
        # Generate workflow ID
        workflow_id = str(uuid.uuid4())
        
        # Create workflow record
        workflow_record = {
            "workflow_id": workflow_id,
            "workflow_type": request.workflow_type,
            "description": request.description,
            "agents": request.agents,
            "input_data": request.input_data,
            "user_id": current_user.id,
            "status": "created",
            "progress": 0.0,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "executions": [],
            "result": None
        }
        
        _workflow_storage[workflow_id] = workflow_record
        
        # Store workflow state in memory manager
        memory_manager = get_memory_manager()
        await memory_manager.set_workflow_state(workflow_id, {
            "workflow_type": request.workflow_type,
            "agents": request.agents,
            "status": "created",
            "progress": 0.0,
            "input_data": request.input_data
        })
        
        return WorkflowResponse(
            workflow_id=workflow_id,
            status="created",
            agents=request.agents,
            created_at=workflow_record["created_at"],
            progress=0.0
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create workflow"
        )


@router.get("/workflows/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow_status(
    workflow_id: str,
    current_user: User = Depends(get_current_user)
) -> WorkflowResponse:
    """Get the status of a workflow."""
    try:
        if workflow_id not in _workflow_storage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )
        
        workflow = _workflow_storage[workflow_id]
        
        # Check if user has access to this workflow
        if workflow["user_id"] != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this workflow"
            )
        
        return WorkflowResponse(
            workflow_id=workflow_id,
            status=workflow["status"],
            agents=workflow["agents"],
            created_at=workflow["created_at"],
            progress=workflow["progress"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve workflow status"
        )


# Helper functions
def _get_agent_description(role: AgentRole) -> str:
    """Get description for an agent role."""
    descriptions = {
        AgentRole.DATA_EXTRACTION: "Extracts and processes data from documents with entity recognition and confidence scoring",
        AgentRole.CONTRACT_GENERATOR: "Generates contracts using templates with intelligent variable filling and formatting",
        AgentRole.COMPLIANCE_CHECKER: "Validates contracts against legal requirements and industry regulations",
        AgentRole.SIGNATURE_TRACKER: "Tracks e-signature workflows and coordinates multi-party signing processes",
        AgentRole.SUMMARY_AGENT: "Creates summaries, reports, and analyzes document changes",
        AgentRole.HELP_AGENT: "Provides contextual assistance, workflow guidance, and answers questions"
    }
    return descriptions.get(role, "AI agent for specialized real estate tasks")


def _get_agent_capabilities(role: AgentRole) -> List[str]:
    """Get capabilities list for an agent role."""
    capabilities = {
        AgentRole.DATA_EXTRACTION: [
            "Document parsing and text extraction",
            "Entity recognition and classification",
            "Data confidence scoring",
            "Multi-format document support"
        ],
        AgentRole.CONTRACT_GENERATOR: [
            "Template-based contract generation",
            "Intelligent variable mapping",
            "DOCX and PDF output formats",
            "Custom clause generation"
        ],
        AgentRole.COMPLIANCE_CHECKER: [
            "Legal requirement validation",
            "Jurisdiction-specific compliance",
            "Risk assessment and scoring",
            "Compliance reporting"
        ],
        AgentRole.SIGNATURE_TRACKER: [
            "E-signature workflow monitoring",
            "Multi-party coordination",
            "Status tracking and notifications",
            "Audit trail generation"
        ],
        AgentRole.SUMMARY_AGENT: [
            "Document summarization",
            "Change analysis and diff generation",
            "Executive reporting",
            "Key point extraction"
        ],
        AgentRole.HELP_AGENT: [
            "Contextual Q&A assistance",
            "Workflow guidance",
            "Legal clause explanation",
            "Process recommendations"
        ]
    }
    return capabilities.get(role, ["General AI assistance"])


async def _execute_agent_background(
    execution_id: str,
    agent_role: str,
    task_description: str,
    input_data: Dict[str, Any],
    user_id: str,
    workflow_id: Optional[str] = None
):
    """Background task for agent execution."""
    try:
        # Update status to running
        _execution_storage[execution_id]["status"] = "running"
        _execution_storage[execution_id]["progress"] = 10.0
        _execution_storage[execution_id]["updated_at"] = datetime.utcnow()
        
        # Get orchestrator and create agent
        orchestrator = get_agent_orchestrator()
        agent_role_enum = AgentRole(agent_role)
        agent = orchestrator.create_agent(agent_role_enum)
        
        # Update progress
        _execution_storage[execution_id]["progress"] = 30.0
        _execution_storage[execution_id]["updated_at"] = datetime.utcnow()
        
        # Execute the task (simplified for now)
        # In a full implementation, this would use the agent's tools and capabilities
        result = {
            "agent_role": agent_role,
            "task_description": task_description,
            "input_data": input_data,
            "execution_time": "2.5s",
            "tools_used": len(get_tools_for_agent(agent_role)),
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Update progress
        _execution_storage[execution_id]["progress"] = 90.0
        _execution_storage[execution_id]["updated_at"] = datetime.utcnow()
        
        # Simulate some processing time
        await asyncio.sleep(1)
        
        # Complete execution
        _execution_storage[execution_id]["status"] = "completed"
        _execution_storage[execution_id]["progress"] = 100.0
        _execution_storage[execution_id]["result"] = result
        _execution_storage[execution_id]["updated_at"] = datetime.utcnow()
        
        # Update workflow if applicable
        if workflow_id and workflow_id in _workflow_storage:
            workflow = _workflow_storage[workflow_id]
            workflow["executions"].append(execution_id)
            workflow["updated_at"] = datetime.utcnow()
            
            # Update workflow progress
            total_agents = len(workflow["agents"])
            completed_executions = len(workflow["executions"])
            workflow["progress"] = (completed_executions / total_agents) * 100
            
            if completed_executions >= total_agents:
                workflow["status"] = "completed"
        
        logger.info(f"Agent execution completed: {execution_id}")
        
    except Exception as e:
        logger.error(f"Agent execution failed: {execution_id}, error: {e}")
        _execution_storage[execution_id]["status"] = "failed"
        _execution_storage[execution_id]["error"] = str(e)
        _execution_storage[execution_id]["updated_at"] = datetime.utcnow()
