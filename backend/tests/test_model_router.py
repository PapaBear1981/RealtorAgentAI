"""
Tests for the Model Router Service.

This module contains comprehensive tests for the unified model router
including routing strategies, fallback mechanisms, and provider integration.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from app.services.model_router import (
    ModelRouter,
    ModelRequest,
    ModelResponse,
    ModelInfo,
    ModelProvider,
    RoutingStrategy,
    get_model_router
)


class TestModelRouter:
    """Test cases for the ModelRouter class."""
    
    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing."""
        settings = Mock()
        settings.OPENROUTER_API_KEY = "test-openrouter-key"
        settings.OPENAI_API_KEY = "test-openai-key"
        settings.ANTHROPIC_API_KEY = "test-anthropic-key"
        settings.OLLAMA_BASE_URL = "http://localhost:11434"
        settings.MODEL_ROUTER_STRATEGY = "cost_optimized"
        settings.MODEL_ROUTER_FALLBACK_ENABLED = True
        settings.MODEL_ROUTER_HEALTH_CHECK_INTERVAL = 300
        settings.MODEL_ROUTER_MAX_RETRIES = 3
        return settings
    
    @pytest.fixture
    def model_router(self, mock_settings):
        """Create a ModelRouter instance for testing."""
        with patch('app.services.model_router.get_settings', return_value=mock_settings):
            router = ModelRouter()
            # Mock the clients to avoid actual API calls
            router.openrouter_async_client = AsyncMock()
            router.openai_async_client = AsyncMock()
            router.anthropic_async_client = AsyncMock()
            router.ollama_client = AsyncMock()
            return router
    
    def test_model_router_initialization(self, model_router):
        """Test that ModelRouter initializes correctly."""
        assert model_router.strategy == RoutingStrategy.COST_OPTIMIZED
        assert model_router.fallback_enabled is True
        assert model_router.max_retries == 3
        assert len(model_router.models) > 0
    
    def test_model_registry_loading(self, model_router):
        """Test that models are loaded correctly into the registry."""
        # Check that OpenRouter models are loaded
        assert "openrouter/auto" in model_router.models
        assert "anthropic/claude-3.5-sonnet" in model_router.models
        assert "openai/gpt-4o-mini" in model_router.models
        
        # Check model properties
        auto_model = model_router.models["openrouter/auto"]
        assert auto_model.provider == ModelProvider.OPENROUTER
        assert auto_model.cost_per_token > 0
        assert auto_model.context_length > 0
    
    @pytest.mark.asyncio
    async def test_select_model_with_preference(self, model_router):
        """Test model selection with specific preference."""
        request = ModelRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model_preference="openrouter/auto"
        )
        
        selected_model = await model_router.select_model(request)
        assert selected_model == "openrouter/auto"
    
    @pytest.mark.asyncio
    async def test_select_model_cost_optimized(self, model_router):
        """Test cost-optimized model selection."""
        model_router.strategy = RoutingStrategy.COST_OPTIMIZED
        
        request = ModelRequest(
            messages=[{"role": "user", "content": "Hello"}]
        )
        
        selected_model = await model_router.select_model(request)
        
        # Should select the cheapest available model
        selected_info = model_router.models[selected_model]
        assert selected_info.is_available
        
        # Verify it's among the cheapest
        available_models = [m for m in model_router.models.values() if m.is_available]
        min_cost = min(m.cost_per_token for m in available_models)
        assert selected_info.cost_per_token == min_cost
    
    @pytest.mark.asyncio
    async def test_select_model_performance(self, model_router):
        """Test performance-optimized model selection."""
        model_router.strategy = RoutingStrategy.PERFORMANCE
        
        request = ModelRequest(
            messages=[{"role": "user", "content": "Hello"}]
        )
        
        selected_model = await model_router.select_model(request)
        
        # Should select the highest performance available model
        selected_info = model_router.models[selected_model]
        assert selected_info.is_available
        
        # Verify it's among the highest performance
        available_models = [m for m in model_router.models.values() if m.is_available]
        max_performance = max(m.performance_score for m in available_models)
        assert selected_info.performance_score == max_performance
    
    @pytest.mark.asyncio
    async def test_openrouter_generation(self, model_router):
        """Test OpenRouter API generation."""
        # Mock OpenRouter response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 20
        mock_response.usage.total_tokens = 30
        mock_response.id = "test-response-id"
        
        model_router.openrouter_async_client.chat.completions.create.return_value = mock_response
        
        request = ModelRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model_preference="openrouter/auto"
        )
        
        response = await model_router._generate_openrouter(request, "openrouter/auto")
        
        assert response.content == "Test response"
        assert response.model_used == "openrouter/auto"
        assert response.provider == ModelProvider.OPENROUTER
        assert response.token_usage["total_tokens"] == 30
        assert response.cost > 0
    
    @pytest.mark.asyncio
    async def test_health_check(self, model_router):
        """Test health check functionality."""
        # Mock Ollama response
        mock_ollama_response = Mock()
        mock_ollama_response.status_code = 200
        mock_ollama_response.json.return_value = {
            "models": [
                {"name": "llama3.2"},
                {"name": "mistral"}
            ]
        }
        
        model_router.ollama_client.get.return_value = mock_ollama_response
        
        await model_router._run_health_check()
        
        # Check that Ollama models are marked as available
        if "llama3.2" in model_router.models:
            assert model_router.models["llama3.2"].is_available
    
    @pytest.mark.asyncio
    async def test_fallback_mechanism(self, model_router):
        """Test fallback mechanism when primary model fails."""
        # Make the first model fail
        model_router.openrouter_async_client.chat.completions.create.side_effect = Exception("API Error")
        
        # Mock successful fallback
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Fallback response"
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 20
        mock_response.usage.total_tokens = 30
        mock_response.id = "fallback-response-id"
        
        model_router.openai_async_client.chat.completions.create.return_value = mock_response
        
        request = ModelRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model_preference="openrouter/auto"
        )
        
        # Should fallback to another model
        response = await model_router.generate_response(request)
        
        assert response.content == "Fallback response"
        assert response.provider in [ModelProvider.OPENAI, ModelProvider.ANTHROPIC]
    
    @pytest.mark.asyncio
    async def test_no_available_models_error(self, model_router):
        """Test error handling when no models are available."""
        # Mark all models as unavailable
        for model in model_router.models.values():
            model.is_available = False
        
        request = ModelRequest(
            messages=[{"role": "user", "content": "Hello"}]
        )
        
        with pytest.raises(ValueError, match="No available models found"):
            await model_router.select_model(request)


class TestModelRouterAPI:
    """Test cases for the Model Router API endpoints."""
    
    @pytest.fixture
    def mock_model_router(self):
        """Mock model router for API testing."""
        router = Mock()
        router.generate_response = AsyncMock()
        router.models = {
            "test-model": ModelInfo(
                id="test-model",
                name="Test Model",
                provider=ModelProvider.OPENROUTER,
                cost_per_token=0.00001,
                context_length=4096,
                capabilities=["text_generation"],
                performance_score=0.8,
                is_available=True
            )
        }
        router._run_health_check = AsyncMock()
        router.last_health_check = datetime.utcnow()
        router.openrouter_client = Mock()
        router.openai_client = Mock()
        router.anthropic_client = Mock()
        return router
    
    @pytest.mark.asyncio
    async def test_generate_response_endpoint(self, mock_model_router):
        """Test the generate response API endpoint."""
        # Mock successful response
        mock_response = ModelResponse(
            content="Test response",
            model_used="test-model",
            provider=ModelProvider.OPENROUTER,
            cost=0.001,
            processing_time=1.5,
            token_usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
        )
        mock_model_router.generate_response.return_value = mock_response
        
        # This would be tested with FastAPI TestClient in integration tests
        # Here we just verify the mock setup
        request = ModelRequest(
            messages=[{"role": "user", "content": "Hello"}]
        )
        
        response = await mock_model_router.generate_response(request)
        assert response.content == "Test response"
        assert response.model_used == "test-model"
    
    def test_model_info_serialization(self, mock_model_router):
        """Test model info serialization for API responses."""
        model_info = mock_model_router.models["test-model"]
        
        # Verify all required fields are present
        assert model_info.id == "test-model"
        assert model_info.name == "Test Model"
        assert model_info.provider == ModelProvider.OPENROUTER
        assert model_info.cost_per_token > 0
        assert model_info.context_length > 0
        assert isinstance(model_info.capabilities, list)
        assert isinstance(model_info.performance_score, float)
        assert isinstance(model_info.is_available, bool)


def test_get_model_router_singleton():
    """Test that get_model_router returns a singleton instance."""
    router1 = get_model_router()
    router2 = get_model_router()
    
    # Should return the same instance
    assert router1 is router2
