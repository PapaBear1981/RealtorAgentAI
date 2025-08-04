"""
Model Router Service for unified AI model access.

This service provides a unified interface for accessing multiple AI model providers
including OpenRouter, Ollama, OpenAI, and Anthropic with intelligent routing,
fallback mechanisms, and cost optimization.
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Union, AsyncGenerator
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import httpx
import structlog
from openai import OpenAI, AsyncOpenAI
from anthropic import Anthropic, AsyncAnthropic

from ..core.config import get_settings
from ..core.ai_agent_logging import get_ai_agent_logger, log_llm_interaction

logger = structlog.get_logger(__name__)
ai_logger = get_ai_agent_logger(__name__)
settings = get_settings()


class ModelProvider(Enum):
    """Available model providers."""
    OPENROUTER = "openrouter"
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class RoutingStrategy(Enum):
    """Model routing strategies."""
    COST_OPTIMIZED = "cost_optimized"
    PERFORMANCE = "performance"
    BALANCED = "balanced"


@dataclass
class ModelInfo:
    """Information about an available model."""
    id: str
    name: str
    provider: ModelProvider
    cost_per_token: float
    context_length: int
    capabilities: List[str] = field(default_factory=list)
    performance_score: float = 1.0
    is_available: bool = True
    last_health_check: Optional[datetime] = None


@dataclass
class ModelRequest:
    """Request for model inference."""
    messages: List[Dict[str, str]]
    model_preference: Optional[str] = None
    max_tokens: int = 2000
    temperature: float = 0.1
    stream: bool = False
    tools: Optional[List[Dict[str, Any]]] = None
    system_prompt: Optional[str] = None


@dataclass
class ModelResponse:
    """Response from model inference."""
    content: str
    model_used: str
    provider: ModelProvider
    cost: float
    processing_time: float
    token_usage: Dict[str, int]
    metadata: Dict[str, Any] = field(default_factory=dict)


class ModelRouter:
    """
    Unified model router for AI inference requests.

    Provides intelligent routing, fallback mechanisms, and cost optimization
    across multiple AI model providers.
    """

    def __init__(self):
        self.settings = get_settings()
        self.strategy = RoutingStrategy(self.settings.MODEL_ROUTER_STRATEGY)
        self.fallback_enabled = self.settings.MODEL_ROUTER_FALLBACK_ENABLED
        self.max_retries = self.settings.MODEL_ROUTER_MAX_RETRIES

        # Initialize clients
        self._init_clients()

        # Model registry
        self.models: Dict[str, ModelInfo] = {}
        self._load_model_registry()

        # Health monitoring
        self.last_health_check = datetime.utcnow()
        self.health_check_interval = timedelta(seconds=self.settings.MODEL_ROUTER_HEALTH_CHECK_INTERVAL)

    async def initialize(self):
        """Initialize the model router asynchronously."""
        # Perform any async initialization if needed
        await self.health_check()
        logger.info("Model router async initialization completed")

    def _init_clients(self):
        """Initialize AI provider clients."""
        # OpenRouter client (unified access)
        if self.settings.OPENROUTER_API_KEY:
            self.openrouter_client = OpenAI(
                api_key=self.settings.OPENROUTER_API_KEY,
                base_url="https://openrouter.ai/api/v1"
            )
            self.openrouter_async_client = AsyncOpenAI(
                api_key=self.settings.OPENROUTER_API_KEY,
                base_url="https://openrouter.ai/api/v1"
            )
        else:
            self.openrouter_client = None
            self.openrouter_async_client = None

        # Direct OpenAI client
        if self.settings.OPENAI_API_KEY:
            self.openai_client = OpenAI(api_key=self.settings.OPENAI_API_KEY)
            self.openai_async_client = AsyncOpenAI(api_key=self.settings.OPENAI_API_KEY)
        else:
            self.openai_client = None
            self.openai_async_client = None

        # Direct Anthropic client
        if self.settings.ANTHROPIC_API_KEY:
            self.anthropic_client = Anthropic(api_key=self.settings.ANTHROPIC_API_KEY)
            self.anthropic_async_client = AsyncAnthropic(api_key=self.settings.ANTHROPIC_API_KEY)
        else:
            self.anthropic_client = None
            self.anthropic_async_client = None

        # Ollama client (HTTP)
        self.ollama_base_url = self.settings.OLLAMA_BASE_URL
        self.ollama_client = httpx.AsyncClient(base_url=self.ollama_base_url, timeout=30.0)

    def _load_model_registry(self):
        """Load available models from all providers."""
        # OpenRouter models (access to 100+ models)
        if self.openrouter_client:
            self.models.update({
                "openrouter/auto": ModelInfo(
                    id="openrouter/auto",
                    name="Auto Router",
                    provider=ModelProvider.OPENROUTER,
                    cost_per_token=0.000015,  # Average cost
                    context_length=200000,
                    capabilities=["text_generation", "reasoning", "analysis"],
                    performance_score=0.9
                ),
                "anthropic/claude-3.5-sonnet": ModelInfo(
                    id="anthropic/claude-3.5-sonnet",
                    name="Claude 3.5 Sonnet",
                    provider=ModelProvider.OPENROUTER,
                    cost_per_token=0.000015,
                    context_length=200000,
                    capabilities=["text_generation", "reasoning", "analysis", "legal_review"],
                    performance_score=0.95
                ),
                "openai/gpt-4o": ModelInfo(
                    id="openai/gpt-4o",
                    name="GPT-4o",
                    provider=ModelProvider.OPENROUTER,
                    cost_per_token=0.00003,
                    context_length=128000,
                    capabilities=["text_generation", "reasoning", "analysis"],
                    performance_score=0.92
                ),
                "openai/gpt-4o-mini": ModelInfo(
                    id="openai/gpt-4o-mini",
                    name="GPT-4o Mini",
                    provider=ModelProvider.OPENROUTER,
                    cost_per_token=0.0000015,
                    context_length=128000,
                    capabilities=["text_generation", "analysis"],
                    performance_score=0.85
                ),
                "qwen/qwen3-235b-a22b-thinking-2507": ModelInfo(
                    id="qwen/qwen3-235b-a22b-thinking-2507",
                    name="Qwen3 235B A22B Thinking",
                    provider=ModelProvider.OPENROUTER,
                    cost_per_token=0.00002,  # Estimated cost for large model
                    context_length=32768,
                    capabilities=["text_generation", "reasoning", "analysis", "thinking", "complex_reasoning"],
                    performance_score=0.98  # High performance for thinking model
                )
            })

        # Direct provider models
        if self.openai_client:
            self.models.update({
                "gpt-4": ModelInfo(
                    id="gpt-4",
                    name="GPT-4",
                    provider=ModelProvider.OPENAI,
                    cost_per_token=0.00003,
                    context_length=8192,
                    capabilities=["text_generation", "reasoning", "analysis"],
                    performance_score=0.9
                ),
                "gpt-4o-mini": ModelInfo(
                    id="gpt-4o-mini",
                    name="GPT-4o Mini",
                    provider=ModelProvider.OPENAI,
                    cost_per_token=0.0000015,
                    context_length=128000,
                    capabilities=["text_generation", "analysis"],
                    performance_score=0.85
                )
            })

        if self.anthropic_client:
            self.models.update({
                "claude-3-sonnet-20240229": ModelInfo(
                    id="claude-3-sonnet-20240229",
                    name="Claude 3 Sonnet",
                    provider=ModelProvider.ANTHROPIC,
                    cost_per_token=0.000015,
                    context_length=200000,
                    capabilities=["text_generation", "reasoning", "analysis", "legal_review"],
                    performance_score=0.95
                )
            })

        # Ollama models (will be populated by health check)
        self.models.update({
            "llama3.2": ModelInfo(
                id="llama3.2",
                name="Llama 3.2",
                provider=ModelProvider.OLLAMA,
                cost_per_token=0.0,  # Local model, no cost
                context_length=8192,
                capabilities=["text_generation", "analysis"],
                performance_score=0.8,
                is_available=False  # Will be checked
            )
        })

        logger.info(f"Loaded {len(self.models)} models into registry")


    async def select_model(self, request: ModelRequest) -> str:
        """
        Select the best model for the request based on routing strategy.

        Args:
            request: The model request

        Returns:
            Selected model ID
        """
        # Check if specific model is requested and available
        if request.model_preference and request.model_preference in self.models:
            model = self.models[request.model_preference]
            if model.is_available:
                return request.model_preference

        # Filter available models
        available_models = [
            model for model in self.models.values()
            if model.is_available
        ]

        if not available_models:
            raise ValueError("No available models found")

        # Apply routing strategy
        if self.strategy == RoutingStrategy.COST_OPTIMIZED:
            # Select cheapest model that meets requirements
            selected = min(available_models, key=lambda m: m.cost_per_token)
        elif self.strategy == RoutingStrategy.PERFORMANCE:
            # Select highest performance model
            selected = max(available_models, key=lambda m: m.performance_score)
        else:  # BALANCED
            # Balance cost and performance
            selected = min(available_models, key=lambda m: m.cost_per_token / m.performance_score)

        logger.info(f"Selected model: {selected.id} (strategy: {self.strategy.value})")
        return selected.id

    @log_llm_interaction("model_router")
    async def generate_response(self, request: ModelRequest) -> ModelResponse:
        """
        Generate response using the selected model with fallback support.

        Args:
            request: The model request

        Returns:
            Model response
        """
        start_time = time.time()

        # Ensure health check is recent
        await self._ensure_health_check()

        # Select model
        selected_model_id = await self.select_model(request)

        # Attempt generation with retries and fallbacks
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                model_info = self.models[selected_model_id]

                # Route to appropriate provider
                if model_info.provider == ModelProvider.OPENROUTER:
                    response = await self._generate_openrouter(request, selected_model_id)
                elif model_info.provider == ModelProvider.OPENAI:
                    response = await self._generate_openai(request, selected_model_id)
                elif model_info.provider == ModelProvider.ANTHROPIC:
                    response = await self._generate_anthropic(request, selected_model_id)
                elif model_info.provider == ModelProvider.OLLAMA:
                    response = await self._generate_ollama(request, selected_model_id)
                else:
                    raise ValueError(f"Unsupported provider: {model_info.provider}")

                # Calculate processing time
                processing_time = time.time() - start_time
                response.processing_time = processing_time

                logger.info(f"Generated response using {selected_model_id} in {processing_time:.2f}s")
                return response

            except Exception as e:
                last_exception = e
                logger.warning(f"Attempt {attempt + 1} failed for model {selected_model_id}: {e}")

                # Mark model as temporarily unavailable
                self.models[selected_model_id].is_available = False

                # Try fallback if enabled
                if self.fallback_enabled and attempt < self.max_retries - 1:
                    try:
                        selected_model_id = await self.select_model(request)
                        logger.info(f"Falling back to model: {selected_model_id}")
                    except ValueError:
                        # No more available models
                        break

        # All attempts failed
        raise Exception(f"All model attempts failed. Last error: {last_exception}")

    async def _generate_openrouter(self, request: ModelRequest, model_id: str) -> ModelResponse:
        """Generate response using OpenRouter API."""
        if not self.openrouter_async_client:
            raise ValueError("OpenRouter client not initialized")

        # Prepare messages
        messages = request.messages.copy()
        if request.system_prompt:
            messages.insert(0, {"role": "system", "content": request.system_prompt})

        # Make request
        response = await self.openrouter_async_client.chat.completions.create(
            model=model_id,
            messages=messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            stream=request.stream,
            tools=request.tools
        )

        # Extract response data
        content = response.choices[0].message.content or ""
        token_usage = {
            "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
            "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            "total_tokens": response.usage.total_tokens if response.usage else 0
        }

        # Calculate cost
        model_info = self.models[model_id]
        cost = token_usage["total_tokens"] * model_info.cost_per_token

        return ModelResponse(
            content=content,
            model_used=model_id,
            provider=ModelProvider.OPENROUTER,
            cost=cost,
            processing_time=0.0,  # Will be set by caller
            token_usage=token_usage,
            metadata={"response_id": response.id}
        )

    async def _generate_openai(self, request: ModelRequest, model_id: str) -> ModelResponse:
        """Generate response using direct OpenAI API."""
        if not self.openai_async_client:
            raise ValueError("OpenAI client not initialized")

        # Prepare messages
        messages = request.messages.copy()
        if request.system_prompt:
            messages.insert(0, {"role": "system", "content": request.system_prompt})

        # Make request
        response = await self.openai_async_client.chat.completions.create(
            model=model_id,
            messages=messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            stream=request.stream,
            tools=request.tools
        )

        # Extract response data
        content = response.choices[0].message.content or ""
        token_usage = {
            "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
            "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            "total_tokens": response.usage.total_tokens if response.usage else 0
        }

        # Calculate cost
        model_info = self.models[model_id]
        cost = token_usage["total_tokens"] * model_info.cost_per_token

        return ModelResponse(
            content=content,
            model_used=model_id,
            provider=ModelProvider.OPENAI,
            cost=cost,
            processing_time=0.0,  # Will be set by caller
            token_usage=token_usage,
            metadata={"response_id": response.id}
        )

    async def _generate_anthropic(self, request: ModelRequest, model_id: str) -> ModelResponse:
        """Generate response using direct Anthropic API."""
        if not self.anthropic_async_client:
            raise ValueError("Anthropic client not initialized")

        # Prepare messages for Anthropic format
        messages = []
        system_prompt = request.system_prompt or ""

        for msg in request.messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                messages.append(msg)

        # Make request
        response = await self.anthropic_async_client.messages.create(
            model=model_id,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            system=system_prompt,
            messages=messages
        )

        # Extract response data
        content = ""
        if response.content:
            content = response.content[0].text if response.content[0].type == "text" else ""

        token_usage = {
            "prompt_tokens": response.usage.input_tokens,
            "completion_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.input_tokens + response.usage.output_tokens
        }

        # Calculate cost
        model_info = self.models[model_id]
        cost = token_usage["total_tokens"] * model_info.cost_per_token

        return ModelResponse(
            content=content,
            model_used=model_id,
            provider=ModelProvider.ANTHROPIC,
            cost=cost,
            processing_time=0.0,  # Will be set by caller
            token_usage=token_usage,
            metadata={"response_id": response.id}
        )

    async def _generate_ollama(self, request: ModelRequest, model_id: str) -> ModelResponse:
        """Generate response using Ollama local API."""
        # Prepare request payload
        messages = request.messages.copy()
        if request.system_prompt:
            messages.insert(0, {"role": "system", "content": request.system_prompt})

        payload = {
            "model": model_id,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens
            }
        }

        # Make request to Ollama
        response = await self.ollama_client.post("/api/chat", json=payload)
        response.raise_for_status()

        data = response.json()

        # Extract response data
        content = data.get("message", {}).get("content", "")

        # Ollama doesn't provide detailed token usage, estimate
        estimated_tokens = len(content.split()) * 1.3  # Rough estimation
        token_usage = {
            "prompt_tokens": int(estimated_tokens * 0.7),
            "completion_tokens": int(estimated_tokens * 0.3),
            "total_tokens": int(estimated_tokens)
        }

        return ModelResponse(
            content=content,
            model_used=model_id,
            provider=ModelProvider.OLLAMA,
            cost=0.0,  # Local model, no cost
            processing_time=0.0,  # Will be set by caller
            token_usage=token_usage,
            metadata={
                "eval_count": data.get("eval_count", 0),
                "eval_duration": data.get("eval_duration", 0)
            }
        )

    async def _ensure_health_check(self):
        """Ensure health check is recent, run if needed."""
        now = datetime.utcnow()
        if now - self.last_health_check > self.health_check_interval:
            await self._run_health_check()
            self.last_health_check = now

    async def _run_health_check(self):
        """Run health check on all providers."""
        logger.info("Running health check on all providers")

        # Check Ollama availability
        try:
            response = await self.ollama_client.get("/api/tags")
            if response.status_code == 200:
                data = response.json()
                available_models = [model["name"] for model in data.get("models", [])]

                # Update Ollama model availability
                for model_id, model_info in self.models.items():
                    if model_info.provider == ModelProvider.OLLAMA:
                        model_info.is_available = model_id in available_models

                logger.info(f"Ollama health check: {len(available_models)} models available")
            else:
                # Mark all Ollama models as unavailable
                for model_info in self.models.values():
                    if model_info.provider == ModelProvider.OLLAMA:
                        model_info.is_available = False

        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            # Mark all Ollama models as unavailable
            for model_info in self.models.values():
                if model_info.provider == ModelProvider.OLLAMA:
                    model_info.is_available = False

        # Other providers are assumed available if clients are initialized
        # (they handle their own error cases)
        for model_info in self.models.values():
            if model_info.provider in [ModelProvider.OPENROUTER, ModelProvider.OPENAI, ModelProvider.ANTHROPIC]:
                # Reset availability for cloud providers
                model_info.is_available = True

        logger.info("Health check completed")

    async def health_check(self):
        """Perform health check on all providers."""
        logger.info("Starting health check")
        # For now, just check if clients are initialized
        if self.openrouter_async_client:
            logger.info("OpenRouter client available")
        if self.openai_async_client:
            logger.info("OpenAI client available")
        if self.anthropic_async_client:
            logger.info("Anthropic client available")
        logger.info("Health check completed")

    async def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available models."""
        return [
            {
                "id": model_info.id,
                "name": model_info.name,
                "provider": model_info.provider.value,
                "cost_per_token": model_info.cost_per_token,
                "context_length": model_info.context_length,
                "capabilities": model_info.capabilities,
                "is_available": model_info.is_available
            }
            for model_info in self.models.values()
        ]


# Global model router instance
model_router = ModelRouter()


def get_model_router() -> ModelRouter:
    """Get the global model router instance."""
    return model_router
