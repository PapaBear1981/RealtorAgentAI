"""
Model Router API endpoints.

Provides REST API access to the unified model router service
for AI inference requests with intelligent routing and fallback.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
import structlog

from ..core.dependencies import get_current_active_user
from ..models.user import User
from ..services.model_router import (
    get_model_router,
    ModelRequest,
    ModelResponse,
    ModelRouter,
    ModelInfo,
    ModelProvider,
    RoutingStrategy
)

logger = structlog.get_logger(__name__)
router = APIRouter()


class ModelRequestAPI(BaseModel):
    """API model for model inference requests."""
    messages: List[Dict[str, str]] = Field(..., description="Chat messages")
    model_preference: Optional[str] = Field(None, description="Preferred model ID")
    max_tokens: int = Field(2000, description="Maximum tokens to generate")
    temperature: float = Field(0.1, description="Temperature for generation")
    stream: bool = Field(False, description="Enable streaming response")
    tools: Optional[List[Dict[str, Any]]] = Field(None, description="Available tools")
    system_prompt: Optional[str] = Field(None, description="System prompt")


class ModelResponseAPI(BaseModel):
    """API model for model inference responses."""
    content: str = Field(..., description="Generated content")
    model_used: str = Field(..., description="Model that generated the response")
    provider: str = Field(..., description="Provider used")
    cost: float = Field(..., description="Cost of the request")
    processing_time: float = Field(..., description="Processing time in seconds")
    token_usage: Dict[str, int] = Field(..., description="Token usage statistics")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ModelInfoAPI(BaseModel):
    """API model for model information."""
    id: str = Field(..., description="Model ID")
    name: str = Field(..., description="Model name")
    provider: str = Field(..., description="Provider")
    cost_per_token: float = Field(..., description="Cost per token")
    context_length: int = Field(..., description="Context length")
    capabilities: List[str] = Field(..., description="Model capabilities")
    performance_score: float = Field(..., description="Performance score")
    is_available: bool = Field(..., description="Availability status")


class HealthCheckResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Health status")
    available_models: int = Field(..., description="Number of available models")
    providers: Dict[str, bool] = Field(..., description="Provider availability")
    last_check: str = Field(..., description="Last health check time")


@router.post("/generate", response_model=ModelResponseAPI)
async def generate_response(
    request: ModelRequestAPI,
    current_user: User = Depends(get_current_active_user),
    model_router: ModelRouter = Depends(get_model_router)
) -> ModelResponseAPI:
    """
    Generate AI response using the model router.

    This endpoint provides unified access to multiple AI providers with
    intelligent routing, fallback mechanisms, and cost optimization.
    """
    try:
        # Convert API request to internal format
        internal_request = ModelRequest(
            messages=request.messages,
            model_preference=request.model_preference,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            stream=request.stream,
            tools=request.tools,
            system_prompt=request.system_prompt
        )

        # Generate response
        response = await model_router.generate_response(internal_request)

        # Log usage for monitoring
        logger.info(
            "Model router request completed",
            user_id=current_user.id,
            model_used=response.model_used,
            provider=response.provider.value,
            cost=response.cost,
            processing_time=response.processing_time,
            token_usage=response.token_usage
        )

        # Convert to API response
        return ModelResponseAPI(
            content=response.content,
            model_used=response.model_used,
            provider=response.provider.value,
            cost=response.cost,
            processing_time=response.processing_time,
            token_usage=response.token_usage,
            metadata=response.metadata
        )

    except Exception as e:
        logger.error(f"Model router request failed: {e}", user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model generation failed: {str(e)}"
        )


@router.get("/models", response_model=List[ModelInfoAPI])
async def list_available_models(
    current_user: User = Depends(get_current_active_user),
    model_router: ModelRouter = Depends(get_model_router)
) -> List[ModelInfoAPI]:
    """
    List all available models across all providers.

    Returns information about models including availability, cost,
    capabilities, and performance metrics.
    """
    try:
        models = []
        for model_info in model_router.models.values():
            models.append(ModelInfoAPI(
                id=model_info.id,
                name=model_info.name,
                provider=model_info.provider.value,
                cost_per_token=model_info.cost_per_token,
                context_length=model_info.context_length,
                capabilities=model_info.capabilities,
                performance_score=model_info.performance_score,
                is_available=model_info.is_available
            ))

        # Sort by availability and performance
        models.sort(key=lambda m: (not m.is_available, -m.performance_score))

        logger.info(f"Listed {len(models)} models", user_id=current_user.id)
        return models

    except Exception as e:
        logger.error(f"Failed to list models: {e}", user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list models: {str(e)}"
        )


@router.get("/health", response_model=HealthCheckResponse)
async def health_check(
    current_user: User = Depends(get_current_active_user),
    model_router: ModelRouter = Depends(get_model_router)
) -> HealthCheckResponse:
    """
    Check health status of all model providers.

    Runs health checks and returns availability status for all providers
    and models.
    """
    try:
        # Force health check
        await model_router._run_health_check()

        # Count available models
        available_models = sum(1 for model in model_router.models.values() if model.is_available)

        # Check provider availability
        providers = {
            "openrouter": model_router.openrouter_client is not None,
            "openai": model_router.openai_client is not None,
            "anthropic": model_router.anthropic_client is not None,
            "ollama": any(
                model.is_available and model.provider == ModelProvider.OLLAMA
                for model in model_router.models.values()
            )
        }

        status_text = "healthy" if available_models > 0 else "degraded"

        logger.info(
            f"Health check completed: {status_text}",
            available_models=available_models,
            providers=providers,
            user_id=current_user.id
        )

        return HealthCheckResponse(
            status=status_text,
            available_models=available_models,
            providers=providers,
            last_check=model_router.last_health_check.isoformat()
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}", user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}"
        )


@router.post("/strategy")
async def update_routing_strategy(
    strategy: str,
    current_user: User = Depends(get_current_active_user),
    model_router: ModelRouter = Depends(get_model_router)
) -> Dict[str, str]:
    """
    Update the model routing strategy.

    Available strategies:
    - cost_optimized: Select cheapest available model
    - performance: Select highest performance model
    - balanced: Balance cost and performance
    """
    try:
        # Validate strategy
        if strategy not in ["cost_optimized", "performance", "balanced"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid strategy. Must be: cost_optimized, performance, or balanced"
            )

        # Update strategy
        model_router.strategy = RoutingStrategy(strategy)

        logger.info(f"Updated routing strategy to {strategy}", user_id=current_user.id)

        return {"status": "success", "strategy": strategy}

    except Exception as e:
        logger.error(f"Failed to update strategy: {e}", user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update strategy: {str(e)}"
        )
