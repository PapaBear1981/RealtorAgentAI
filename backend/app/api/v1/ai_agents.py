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

from ...core.dependencies import get_current_user
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


class ContractFillRequest(BaseModel):
    """Request model for contract filling."""
    contract_type: str = Field(..., description="Type of contract to fill")
    source_data: Dict[str, Any] = Field(default_factory=dict, description="Source data for filling")
    deal_name: Optional[str] = Field(None, description="Name of the deal")
    template_id: Optional[str] = Field(None, description="Template ID to use")


class DocumentExtractRequest(BaseModel):
    """Request model for document extraction."""
    extracted_data: Dict[str, Any] = Field(default_factory=dict, description="Previously extracted data")
    target_fields: List[str] = Field(default_factory=list, description="Target fields to extract")
    source_files: List[str] = Field(default_factory=list, description="Source file IDs")


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


class ContractFillResponse(BaseModel):
    """Response model for contract fill requests."""
    success: bool = Field(..., description="Whether the operation was successful")
    execution_id: str = Field(..., description="Unique execution ID")
    ai_response: Optional[str] = Field(None, description="AI-generated contract content")
    extracted_variables: Optional[Dict[str, Any]] = Field(None, description="Extracted contract variables")
    confidence: Optional[float] = Field(None, description="Overall confidence score")
    execution_time: Optional[float] = Field(None, description="Execution time in seconds")
    error: Optional[str] = Field(None, description="Error message if failed")


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


@router.post("/contract-fill", response_model=ContractFillResponse)
async def fill_contract(
    request: ContractFillRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
) -> ContractFillResponse:
    """Fill a contract using AI agent with extracted data."""
    try:
        # Generate execution ID
        execution_id = str(uuid.uuid4())

        # Prepare task description for contract generation
        task_description = f"""
        Fill a {request.contract_type} contract using the provided source data.

        Contract Type: {request.contract_type}
        Deal Name: {request.deal_name or 'Unnamed Deal'}

        Source Data Available:
        {', '.join(request.source_data.keys()) if request.source_data else 'No source data provided'}

        Please extract relevant information from the source data and generate appropriate
        contract variables and content. Focus on:
        1. Party information (buyers, sellers, agents)
        2. Property details (address, description, features)
        3. Financial terms (price, down payment, financing)
        4. Important dates (closing, contingencies)
        5. Legal terms and conditions

        Provide structured output with extracted variables and confidence scores.
        """

        # Create execution record
        execution_record = {
            "execution_id": execution_id,
            "agent_role": "contract_generator",
            "task_description": task_description,
            "input_data": {
                "contract_type": request.contract_type,
                "source_data": request.source_data,
                "deal_name": request.deal_name,
                "template_id": request.template_id
            },
            "workflow_id": None,
            "user_id": current_user.id,
            "status": "queued",
            "progress": 0.0,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "result": None,
            "error": None
        }

        _execution_storage[execution_id] = execution_record

        # Execute agent synchronously and wait for completion
        await _execute_agent_background(
            execution_id,
            "contract_generator",
            task_description,
            execution_record["input_data"],
            current_user.id,
            None
        )

        # Get the execution result
        logger.info(f"Looking for execution_id: {execution_id}")
        logger.info(f"Available execution IDs: {list(_execution_storage.keys())}")

        if execution_id in _execution_storage:
            result = _execution_storage[execution_id]
            logger.info(f"Found execution result for {execution_id}")

            if result["status"] == "completed" and result.get("result"):
                ai_response = result["result"].get("ai_response", "")
                execution_time_raw = result["result"].get("execution_time", 0)

                logger.info(f"Retrieved execution result: {result}")
                logger.info(f"AI response from storage: {ai_response[:200]}..." if ai_response else "AI response is empty")
                logger.info(f"AI response length: {len(ai_response) if ai_response else 0}")

                # Parse execution time (remove 's' suffix if present)
                if isinstance(execution_time_raw, str) and execution_time_raw.endswith('s'):
                    execution_time = float(execution_time_raw[:-1])
                else:
                    execution_time = float(execution_time_raw) if execution_time_raw else 0.0

                # Parse AI response to extract variables (simplified)
                extracted_variables = {
                    "contract_type": request.contract_type,
                    "deal_name": request.deal_name,
                    "ai_generated_content": ai_response
                }

                response = ContractFillResponse(
                    success=True,
                    execution_id=execution_id,
                    ai_response=ai_response,
                    extracted_variables=extracted_variables,
                    confidence=0.85,  # Default confidence
                    execution_time=execution_time
                )

                logger.info(f"Returning ContractFillResponse with ai_response length: {len(response.ai_response) if response.ai_response else 0}")
                return response
            else:
                error_msg = result.get("error", "Unknown error occurred")
                return ContractFillResponse(
                    success=False,
                    execution_id=execution_id,
                    error=error_msg
                )
        else:
            return ContractFillResponse(
                success=False,
                execution_id=execution_id,
                error="Execution record not found"
            )

    except Exception as e:
        logger.error(f"Failed to queue contract fill task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to queue contract filling task"
        )


@router.post("/document-extract", response_model=AgentExecutionResponse)
async def extract_from_documents(
    request: DocumentExtractRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
) -> AgentExecutionResponse:
    """Extract and enhance data from documents using AI agent."""
    try:
        # Generate execution ID
        execution_id = str(uuid.uuid4())

        # Prepare task description for data extraction
        task_description = f"""
        Extract and enhance data from the provided documents and existing extracted data.

        Target Fields: {', '.join(request.target_fields) if request.target_fields else 'All relevant fields'}
        Source Files: {len(request.source_files)} files

        Existing Extracted Data:
        {', '.join(request.extracted_data.keys()) if request.extracted_data else 'No existing data'}

        Please analyze the documents and extracted data to:
        1. Identify and extract key entities (parties, properties, financial terms, dates)
        2. Enhance the existing extracted data with additional insights
        3. Validate and improve data quality
        4. Provide confidence scores for extracted information
        5. Structure the data for contract generation

        Focus on real estate contract elements including:
        - Party information (buyers, sellers, agents, attorneys)
        - Property details (address, description, legal description)
        - Financial terms (purchase price, earnest money, financing)
        - Important dates (closing, contingencies, inspections)
        - Legal terms and conditions
        """

        # Create execution record
        execution_record = {
            "execution_id": execution_id,
            "agent_role": "data_extraction",
            "task_description": task_description,
            "input_data": {
                "extracted_data": request.extracted_data,
                "target_fields": request.target_fields,
                "source_files": request.source_files
            },
            "workflow_id": None,
            "user_id": current_user.id,
            "status": "queued",
            "progress": 0.0,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "result": None,
            "error": None
        }

        _execution_storage[execution_id] = execution_record

        # Start background execution with data extraction agent
        background_tasks.add_task(
            _execute_agent_background,
            execution_id,
            "data_extraction",
            task_description,
            execution_record["input_data"],
            current_user.id,
            None
        )

        return AgentExecutionResponse(
            execution_id=execution_id,
            status="queued",
            agent_role="data_extraction",
            created_at=datetime.utcnow(),
            workflow_id=None
        )

    except Exception as e:
        logger.error(f"Failed to queue document extraction task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to queue document extraction task"
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
    start_time = datetime.utcnow()

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

        # Create a single task for the agent to execute
        from ...services.agent_orchestrator import WorkflowTask, TaskPriority

        task = WorkflowTask(
            id=f"task_{execution_id}",
            description=task_description,
            expected_output="Detailed analysis and results based on the task description and input data",
            agent_role=agent_role_enum,
            priority=TaskPriority.HIGH,
            context=input_data,
            dependencies=[],
            created_at=datetime.utcnow()
        )

        # Update progress
        _execution_storage[execution_id]["progress"] = 50.0
        _execution_storage[execution_id]["updated_at"] = datetime.utcnow()

        # Execute the task using CrewAI
        from crewai import Task as CrewTask, Crew, Process

        # Create CrewAI task
        crew_task = CrewTask(
            description=task_description,
            expected_output="Detailed analysis and results based on the task description and input data",
            agent=agent
        )

        # Create crew with single agent and task
        crew = Crew(
            agents=[agent],
            tasks=[crew_task],
            process=Process.sequential,
            verbose=True
        )

        # Update progress
        _execution_storage[execution_id]["progress"] = 70.0
        _execution_storage[execution_id]["updated_at"] = datetime.utcnow()

        # Execute the crew (this will make real AI calls)
        logger.info(f"Executing agent {agent_role} for task: {task_description}")
        crew_result = crew.kickoff()

        # Update progress
        _execution_storage[execution_id]["progress"] = 90.0
        _execution_storage[execution_id]["updated_at"] = datetime.utcnow()

        # Calculate execution time
        execution_time = (datetime.utcnow() - start_time).total_seconds()

        # Extract AI response from CrewAI result
        ai_response = ""
        logger.info(f"CrewAI result type: {type(crew_result)}")
        logger.info(f"CrewAI result attributes: {dir(crew_result)}")

        if hasattr(crew_result, 'raw'):
            ai_response = crew_result.raw
            logger.info(f"Using crew_result.raw: {len(ai_response)} chars")
        elif hasattr(crew_result, 'output'):
            ai_response = crew_result.output
            logger.info(f"Using crew_result.output: {len(ai_response)} chars")
        else:
            ai_response = str(crew_result)
            logger.info(f"Using str(crew_result): {len(ai_response)} chars")

        # Format the result
        result = {
            "agent_role": agent_role,
            "task_description": task_description,
            "input_data": input_data,
            "ai_response": ai_response,
            "execution_time": f"{execution_time:.2f}s",
            "tools_used": len(get_tools_for_agent(agent_role)),
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat(),
            "execution_id": execution_id
        }

        # Complete execution
        _execution_storage[execution_id]["status"] = "completed"
        _execution_storage[execution_id]["progress"] = 100.0
        _execution_storage[execution_id]["result"] = result
        _execution_storage[execution_id]["updated_at"] = datetime.utcnow()

        logger.info(f"Stored execution result for {execution_id}: ai_response length = {len(ai_response)}")
        logger.info(f"Execution storage keys: {list(_execution_storage.keys())}")
        logger.info(f"Stored result keys: {list(result.keys())}")

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

        logger.info(f"Agent execution completed: {execution_id}, execution_time: {execution_time:.2f}s")

    except Exception as e:
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        logger.error(f"Agent execution failed: {execution_id}, error: {e}, execution_time: {execution_time:.2f}s")
        _execution_storage[execution_id]["status"] = "failed"
        _execution_storage[execution_id]["error"] = str(e)
        _execution_storage[execution_id]["updated_at"] = datetime.utcnow()
        _execution_storage[execution_id]["execution_time"] = f"{execution_time:.2f}s"
