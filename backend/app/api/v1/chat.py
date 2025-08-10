"""
Enhanced Chat API for AI Assistant Agent

This module provides intelligent conversation capabilities for the AI Assistant Agent,
including natural language processing, contextual responses, and task orchestration.
"""

from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from datetime import datetime
import structlog

from ...core.dependencies import get_current_active_user
from ...models.user import User
from ...services.conversation_service import (
    ConversationService,
    ConversationContext
)
from ...services.model_router import get_model_router
from ...services.file_service import FileService

logger = structlog.get_logger(__name__)
router = APIRouter()


class ChatMessage(BaseModel):
    """Chat message model."""
    role: str = Field(..., description="Message role (user, assistant, system)")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message timestamp")


class ChatRequest(BaseModel):
    """Request model for chat interactions."""
    message: str = Field(..., description="User message")
    context: Optional[Dict[str, Any]] = Field(None, description="Conversation context")
    conversation_history: List[ChatMessage] = Field(default_factory=list, description="Recent conversation history")
    current_page: str = Field("dashboard", description="Current page context")
    available_files: List[str] = Field(default_factory=list, description="Available files for processing")


class ChatResponse(BaseModel):
    """Response model for chat interactions."""
    content: str = Field(..., description="AI response content")
    intent: str = Field(..., description="Detected conversation intent")
    tone: str = Field(..., description="Response tone")
    suggested_actions: List[Dict[str, Any]] = Field(default_factory=list, description="Suggested actions")
    follow_up_questions: List[str] = Field(default_factory=list, description="Follow-up questions")
    requires_clarification: bool = Field(False, description="Whether clarification is needed")
    task_breakdown: List[Dict[str, Any]] = Field(default_factory=list, description="Task breakdown if applicable")
    confidence: float = Field(0.8, description="Response confidence score")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class TaskExecutionRequest(BaseModel):
    """Request model for task execution."""
    task_type: str = Field(..., description="Type of task to execute")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Task parameters")
    context: Optional[Dict[str, Any]] = Field(None, description="Execution context")


class TaskExecutionResponse(BaseModel):
    """Response model for task execution."""
    success: bool = Field(..., description="Whether task was successful")
    execution_id: str = Field(..., description="Unique execution ID")
    status: str = Field(..., description="Current execution status")
    progress: float = Field(0.0, description="Progress percentage (0-100)")
    result: Optional[Dict[str, Any]] = Field(None, description="Task result if completed")
    error: Optional[str] = Field(None, description="Error message if failed")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")


@router.post("/message", response_model=ChatResponse)
async def process_chat_message(
    request: ChatRequest,
    current_user: User = Depends(get_current_active_user)
) -> ChatResponse:
    """
    Process a chat message with enhanced conversational AI.

    This endpoint provides intelligent conversation capabilities including:
    - Natural language understanding
    - Contextual greetings with personalization
    - Intelligent task interpretation
    - Proactive follow-up questions
    - Multi-task orchestration
    """
    try:
        # Initialize conversation service
        model_router = get_model_router()
        conversation_service = ConversationService(model_router)

        # Available files (frontend should pass; otherwise empty for now)
        file_names = request.available_files or []

        # Build conversation context with the authenticated user
        context = ConversationContext(
            user=current_user,
            current_page=request.current_page,
            recent_messages=[
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat()
                }
                for msg in request.conversation_history[-10:]  # Last 10 messages
            ],
            available_files=file_names,
            conversation_history=[
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat()
                }
                for msg in request.conversation_history
            ]
        )

        # Process the message
        response = await conversation_service.process_message(request.message, context)

        # Convert to API response
        return ChatResponse(
            content=response.content,
            intent=response.intent.value,
            tone=response.tone.value,
            suggested_actions=response.suggested_actions,
            follow_up_questions=response.follow_up_questions,
            requires_clarification=response.requires_clarification,
            task_breakdown=response.task_breakdown,
            confidence=response.confidence
        )

    except Exception as e:
        logger.error(f"Chat message processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process chat message: {str(e)}"
        ) from e


@router.post("/execute-task", response_model=TaskExecutionResponse)
async def execute_task(
    request: TaskExecutionRequest,
    current_user: User = Depends(get_current_active_user)
) -> TaskExecutionResponse:
    """
    Execute a task identified from conversation.

    This endpoint handles task execution based on conversation analysis,
    providing orchestrated workflows and progress tracking.
    """
    try:
        # Import here to avoid circular imports
        from ...services.agent_orchestrator import get_agent_orchestrator
        from ...services.agent_tools import get_tools_for_agent

        orchestrator = get_agent_orchestrator()

        # Generate unique execution ID
        import uuid
        execution_id = str(uuid.uuid4())

        # Map task types to agent roles
        task_agent_mapping = {
            "contract_fill": "contract_generator",
            "document_extract": "data_extraction",
            "signature_send": "signature_tracker",
            "file_search": "help_assistance",
            "compliance_check": "compliance_checker",
            "summary_generate": "summary_agent"
        }

        agent_role = task_agent_mapping.get(request.task_type, "help_assistance")

        # Execute task asynchronously
        # Note: This would typically be handled by a background task queue
        # For now, we'll return a pending status and the frontend can poll for updates

        return TaskExecutionResponse(
            success=True,
            execution_id=execution_id,
            status="pending",
            progress=0.0,
            estimated_completion=datetime.utcnow()
        )

    except Exception as e:
        logger.error(f"Task execution failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute task: {str(e)}"
        )


@router.get("/task-status/{execution_id}", response_model=TaskExecutionResponse)
async def get_task_status(
    execution_id: str,
    current_user: User = Depends(get_current_active_user)
) -> TaskExecutionResponse:
    """
    Get the status of a task execution.

    This endpoint provides real-time status updates for ongoing tasks.
    """
    try:
        # This would typically query a task queue or database
        # For now, return a mock response
        return TaskExecutionResponse(
            success=True,
            execution_id=execution_id,
            status="completed",
            progress=100.0,
            result={"message": "Task completed successfully"}
        )

    except Exception as e:
        logger.error(f"Failed to get task status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task status: {str(e)}"
        )


@router.get("/conversation-context")
async def get_conversation_context(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Get current conversation context for the user.

    This endpoint provides context information that can be used
    to enhance conversation quality and personalization.
    """
    try:
        # Get user's available files
        file_service = FileService()
        try:
            # This would typically get user files from the database
            # For now, we'll return some mock file names
            file_names = ["johnson_property_disclosure.pdf", "johnson_financial_info.pdf", "property_inspection_report.pdf"]
        except Exception as e:
            logger.warning(f"Could not retrieve user files: {e}")
            file_names = []

        # Get user preferences (this would typically come from a user preferences service)
        user_preferences = {
            "communication_style": "professional",
            "preferred_contract_types": ["purchase_agreement", "listing_agreement"],
            "common_workflows": ["contract_fill", "document_extract"]
        }

        return {
            "user": {
                "id": current_user.id,
                "name": current_user.name,
                "email": current_user.email,
                "role": current_user.role
            },
            "available_files": file_names,
            "file_count": len(file_names),
            "preferences": user_preferences,
            "capabilities": [
                "contract_filling",
                "document_extraction",
                "signature_management",
                "compliance_checking",
                "workflow_orchestration"
            ]
        }

    except Exception as e:
        logger.error(f"Failed to get conversation context: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get conversation context: {str(e)}"
        )
