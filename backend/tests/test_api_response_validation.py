"""
API Response Validation Tests.

This module tests that responses from the OpenRouter API are properly
parsed, validated, and integrated into the agent workflow system.
"""

import asyncio
import pytest
import json
from typing import Dict, Any, List
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

import structlog
from pydantic import ValidationError

from app.services.model_router import (
    ModelRouter, ModelRequest, ModelResponse, ModelProvider
)
from app.core.config import get_settings

logger = structlog.get_logger(__name__)


class TestAPIResponseValidation:
    """Test API response parsing and validation."""

    @pytest.fixture
    def settings(self):
        """Get test settings."""
        settings = get_settings()
        if not settings.OPENROUTER_API_KEY:
            pytest.skip("OPENROUTER_API_KEY not configured for testing")
        return settings

    @pytest.fixture
    async def model_router(self, settings):
        """Create model router for testing."""
        router = ModelRouter()
        await router.initialize()
        return router

    @pytest.fixture
    def valid_openrouter_response(self):
        """Sample valid OpenRouter API response."""
        return {
            "id": "chatcmpl-test123",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "qwen/qwen3-235b-a22b-thinking-2507",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "This is a test response from the Qwen model."
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 25,
                "completion_tokens": 12,
                "total_tokens": 37
            }
        }

    @pytest.fixture
    def invalid_openrouter_response(self):
        """Sample invalid OpenRouter API response."""
        return {
            "error": {
                "message": "Invalid API key",
                "type": "authentication_error",
                "code": "invalid_api_key"
            }
        }

    @pytest.mark.asyncio
    async def test_valid_response_parsing(self, model_router):
        """Test parsing of valid OpenRouter API responses."""
        request = ModelRequest(
            messages=[{"role": "user", "content": "Hello, test message"}],
            model_preference="qwen/qwen3-235b-a22b-thinking-2507",
            max_tokens=50
        )

        response = await model_router.generate_response(request)

        # Validate response structure
        assert isinstance(response, ModelResponse)
        assert response.content is not None
        assert isinstance(response.content, str)
        assert len(response.content) > 0
        
        # Validate model information
        assert response.model_used == "qwen/qwen3-235b-a22b-thinking-2507"
        assert response.provider == ModelProvider.OPENROUTER
        
        # Validate metrics
        assert isinstance(response.cost, (int, float))
        assert response.cost >= 0
        assert isinstance(response.processing_time, (int, float))
        assert response.processing_time > 0
        
        # Validate token usage
        assert isinstance(response.token_usage, dict)
        assert "prompt_tokens" in response.token_usage
        assert "completion_tokens" in response.token_usage
        assert "total_tokens" in response.token_usage
        assert all(isinstance(v, int) and v >= 0 for v in response.token_usage.values())

    @pytest.mark.asyncio
    async def test_response_content_validation(self, model_router):
        """Test validation of response content quality."""
        request = ModelRequest(
            messages=[{
                "role": "user", 
                "content": "Explain the importance of property inspections in real estate."
            }],
            model_preference="qwen/qwen3-235b-a22b-thinking-2507",
            max_tokens=200
        )

        response = await model_router.generate_response(request)

        # Content quality checks
        assert response.content is not None
        assert len(response.content.strip()) > 20  # Meaningful content
        assert not response.content.startswith("Error:")  # No error in content
        
        # Check for relevant content
        content_lower = response.content.lower()
        relevant_terms = ["property", "inspection", "real estate", "important", "buyer", "seller"]
        assert any(term in content_lower for term in relevant_terms)

    @pytest.mark.asyncio
    async def test_token_usage_accuracy(self, model_router):
        """Test accuracy of token usage reporting."""
        short_request = ModelRequest(
            messages=[{"role": "user", "content": "Hi"}],
            model_preference="qwen/qwen3-235b-a22b-thinking-2507",
            max_tokens=10
        )

        long_request = ModelRequest(
            messages=[{
                "role": "user", 
                "content": "Please provide a detailed analysis of real estate market trends, including factors affecting property values, buyer behavior, and economic indicators that influence the housing market."
            }],
            model_preference="qwen/qwen3-235b-a22b-thinking-2507",
            max_tokens=300
        )

        short_response = await model_router.generate_response(short_request)
        long_response = await model_router.generate_response(long_request)

        # Short request should use fewer tokens
        assert short_response.token_usage["prompt_tokens"] < long_response.token_usage["prompt_tokens"]
        
        # Total tokens should be sum of prompt and completion
        for response in [short_response, long_response]:
            expected_total = response.token_usage["prompt_tokens"] + response.token_usage["completion_tokens"]
            assert response.token_usage["total_tokens"] == expected_total

    @pytest.mark.asyncio
    async def test_cost_calculation_accuracy(self, model_router):
        """Test accuracy of cost calculations."""
        request = ModelRequest(
            messages=[{"role": "user", "content": "Calculate property tax for a $500,000 home."}],
            model_preference="qwen/qwen3-235b-a22b-thinking-2507",
            max_tokens=100
        )

        response = await model_router.generate_response(request)

        # Cost should be positive
        assert response.cost > 0
        
        # Cost should be reasonable for token usage
        # Qwen model cost is approximately $0.00002 per token
        expected_cost = response.token_usage["total_tokens"] * 0.00002
        
        # Allow for some variance in pricing
        assert abs(response.cost - expected_cost) < expected_cost * 0.5

    @pytest.mark.asyncio
    async def test_error_response_handling(self, model_router):
        """Test handling of error responses from API."""
        # Test with invalid model
        with patch.object(model_router, '_call_openrouter') as mock_call:
            mock_call.return_value = {
                "error": {
                    "message": "Model not found",
                    "type": "invalid_request_error",
                    "code": "model_not_found"
                }
            }

            request = ModelRequest(
                messages=[{"role": "user", "content": "Test"}],
                model_preference="invalid/model"
            )

            with pytest.raises(Exception) as exc_info:
                await model_router.generate_response(request)
            
            assert "Model not found" in str(exc_info.value) or "error" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_malformed_response_handling(self, model_router):
        """Test handling of malformed API responses."""
        with patch.object(model_router, '_call_openrouter') as mock_call:
            # Test with missing required fields
            mock_call.return_value = {
                "id": "test",
                "choices": []  # Empty choices
            }

            request = ModelRequest(
                messages=[{"role": "user", "content": "Test"}],
                model_preference="qwen/qwen3-235b-a22b-thinking-2507"
            )

            with pytest.raises(Exception):
                await model_router.generate_response(request)

    @pytest.mark.asyncio
    async def test_response_metadata_validation(self, model_router):
        """Test validation of response metadata."""
        request = ModelRequest(
            messages=[{"role": "user", "content": "Test metadata"}],
            model_preference="qwen/qwen3-235b-a22b-thinking-2507",
            max_tokens=50
        )

        response = await model_router.generate_response(request)

        # Check metadata structure
        assert isinstance(response.metadata, dict)
        
        # Should contain timing information
        assert "request_timestamp" in response.metadata or response.processing_time > 0
        
        # Should contain model information
        assert response.model_used is not None
        assert response.provider is not None

    @pytest.mark.asyncio
    async def test_streaming_response_validation(self, model_router):
        """Test validation of streaming responses."""
        request = ModelRequest(
            messages=[{"role": "user", "content": "Tell me about real estate"}],
            model_preference="qwen/qwen3-235b-a22b-thinking-2507",
            max_tokens=100,
            stream=True
        )

        # Note: This test depends on streaming implementation
        try:
            response = await model_router.generate_response(request)
            
            # Even with streaming, final response should be complete
            assert response.content is not None
            assert len(response.content) > 0
            assert response.token_usage is not None
            
        except NotImplementedError:
            # Streaming might not be implemented yet
            pytest.skip("Streaming not implemented")

    @pytest.mark.asyncio
    async def test_concurrent_response_validation(self, model_router):
        """Test validation of concurrent API responses."""
        requests = []
        for i in range(3):
            request = ModelRequest(
                messages=[{"role": "user", "content": f"Test concurrent request {i}"}],
                model_preference="qwen/qwen3-235b-a22b-thinking-2507",
                max_tokens=50
            )
            requests.append(model_router.generate_response(request))

        responses = await asyncio.gather(*requests)

        # All responses should be valid
        for i, response in enumerate(responses):
            assert isinstance(response, ModelResponse)
            assert response.content is not None
            assert f"request {i}" in response.content or len(response.content) > 0
            assert response.cost > 0
            assert response.processing_time > 0

    @pytest.mark.asyncio
    async def test_response_encoding_validation(self, model_router):
        """Test handling of different text encodings in responses."""
        # Test with unicode content
        request = ModelRequest(
            messages=[{
                "role": "user", 
                "content": "Explain property rights in français (French) and español (Spanish)"
            }],
            model_preference="qwen/qwen3-235b-a22b-thinking-2507",
            max_tokens=150
        )

        response = await model_router.generate_response(request)

        # Should handle unicode properly
        assert response.content is not None
        assert isinstance(response.content, str)
        
        # Should be valid UTF-8
        try:
            response.content.encode('utf-8')
        except UnicodeEncodeError:
            pytest.fail("Response contains invalid UTF-8 characters")

    @pytest.mark.asyncio
    async def test_large_response_validation(self, model_router):
        """Test validation of large API responses."""
        request = ModelRequest(
            messages=[{
                "role": "user", 
                "content": "Write a comprehensive guide to real estate investing, including market analysis, financing options, and risk management strategies."
            }],
            model_preference="qwen/qwen3-235b-a22b-thinking-2507",
            max_tokens=1500
        )

        response = await model_router.generate_response(request)

        # Should handle large responses
        assert response.content is not None
        assert len(response.content) > 500  # Should be substantial
        assert response.token_usage["completion_tokens"] > 100
        assert response.cost > 0.001  # Should reflect larger usage
