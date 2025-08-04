"""
LLM Integration Tests for AI Agents with OpenRouter API.

This module tests the integration between AI agents and the OpenRouter API,
specifically validating the qwen/qwen3-235b-a22b-thinking-2507 model integration.
"""

import asyncio
import pytest
import json
import time
from typing import Dict, Any, List
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

import structlog
from httpx import AsyncClient

from app.services.model_router import ModelRouter, ModelRequest, ModelResponse, ModelProvider
from app.services.agent_orchestrator import AgentOrchestrator, AgentRole, WorkflowRequest
from app.core.config import get_settings
from app.services.agent_memory import AgentMemoryManager

logger = structlog.get_logger(__name__)


class TestLLMIntegration:
    """Test suite for LLM integration with OpenRouter API."""

    @pytest.fixture
    def settings(self):
        """Get test settings."""
        settings = get_settings()
        # Ensure we have the required API key for testing
        if not settings.OPENROUTER_API_KEY:
            pytest.skip("OPENROUTER_API_KEY not configured for testing")
        return settings

    @pytest.fixture
    async def model_router(self, settings):
        """Create model router instance for testing."""
        router = ModelRouter()
        await router.initialize()
        return router

    @pytest.fixture
    async def agent_orchestrator(self, settings):
        """Create agent orchestrator for testing."""
        orchestrator = AgentOrchestrator()
        await orchestrator.initialize()
        return orchestrator

    @pytest.fixture
    def sample_messages(self):
        """Sample messages for testing."""
        return [
            {"role": "system", "content": "You are a helpful real estate assistant."},
            {"role": "user", "content": "Analyze this property disclosure document for potential issues."}
        ]

    @pytest.mark.asyncio
    async def test_openrouter_api_connection(self, model_router, sample_messages):
        """Test basic connection to OpenRouter API."""
        request = ModelRequest(
            messages=sample_messages,
            model_preference="qwen/qwen3-235b-a22b-thinking-2507",
            max_tokens=100,
            temperature=0.1
        )

        response = await model_router.generate_response(request)
        
        assert response is not None
        assert isinstance(response, ModelResponse)
        assert response.content is not None
        assert len(response.content) > 0
        assert response.model_used == "qwen/qwen3-235b-a22b-thinking-2507"
        assert response.provider == ModelProvider.OPENROUTER
        assert response.cost > 0
        assert response.processing_time > 0

    @pytest.mark.asyncio
    async def test_qwen_model_specific_features(self, model_router):
        """Test Qwen model's thinking and reasoning capabilities."""
        thinking_prompt = [
            {"role": "system", "content": "You are an expert real estate analyst. Think through problems step by step."},
            {"role": "user", "content": """
            Analyze this contract clause and think through potential legal issues:
            
            'The buyer agrees to purchase the property AS-IS with no warranties or guarantees 
            from the seller regarding the condition of the property, including but not limited 
            to structural, mechanical, electrical, or environmental conditions.'
            
            Please think through this step by step and identify potential risks.
            """}
        ]

        request = ModelRequest(
            messages=thinking_prompt,
            model_preference="qwen/qwen3-235b-a22b-thinking-2507",
            max_tokens=500,
            temperature=0.2
        )

        response = await model_router.generate_response(request)
        
        assert response is not None
        assert len(response.content) > 100  # Should be a detailed analysis
        
        # Check for thinking/reasoning indicators
        content_lower = response.content.lower()
        thinking_indicators = ["step", "first", "second", "consider", "however", "therefore", "analysis"]
        assert any(indicator in content_lower for indicator in thinking_indicators)

    @pytest.mark.asyncio
    async def test_all_agent_types_llm_integration(self, agent_orchestrator):
        """Test LLM integration for all agent types."""
        agent_roles = [
            AgentRole.DATA_EXTRACTION,
            AgentRole.CONTRACT_GENERATOR,
            AgentRole.COMPLIANCE_CHECKER,
            AgentRole.SIGNATURE_TRACKER,
            AgentRole.SUMMARY,
            AgentRole.HELP
        ]

        for role in agent_roles:
            # Create agent with Qwen model
            agent = await agent_orchestrator.create_agent(
                role=role,
                model_preference="qwen/qwen3-235b-a22b-thinking-2507"
            )
            
            assert agent is not None
            assert agent.role == role.value
            assert hasattr(agent, 'llm')
            
            # Test simple interaction
            test_task = f"Test task for {role.value}: Provide a brief response about real estate."
            
            # This would normally be done through CrewAI, but we'll test the LLM directly
            llm_response = await agent.llm.generate(
                messages=[{"role": "user", "content": test_task}]
            )
            
            assert llm_response is not None
            assert len(llm_response) > 10  # Should have meaningful content

    @pytest.mark.asyncio
    async def test_model_fallback_mechanism(self, model_router):
        """Test fallback when preferred model is unavailable."""
        # Test with invalid model first, should fallback
        request = ModelRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model_preference="invalid/model",
            max_tokens=50
        )

        response = await model_router.generate_response(request)
        
        assert response is not None
        # Should have fallen back to a different model
        assert response.model_used != "invalid/model"

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, model_router):
        """Test handling multiple concurrent requests."""
        requests = []
        for i in range(5):
            request = ModelRequest(
                messages=[{"role": "user", "content": f"Test message {i}"}],
                model_preference="qwen/qwen3-235b-a22b-thinking-2507",
                max_tokens=50
            )
            requests.append(model_router.generate_response(request))

        responses = await asyncio.gather(*requests)
        
        assert len(responses) == 5
        for response in responses:
            assert response is not None
            assert response.content is not None

    @pytest.mark.asyncio
    async def test_error_handling_invalid_api_key(self):
        """Test error handling with invalid API key."""
        # Create router with invalid API key
        with patch('app.core.config.get_settings') as mock_settings:
            mock_settings.return_value.OPENROUTER_API_KEY = "invalid_key"
            
            router = ModelRouter()
            await router.initialize()
            
            request = ModelRequest(
                messages=[{"role": "user", "content": "Test"}],
                model_preference="qwen/qwen3-235b-a22b-thinking-2507"
            )
            
            with pytest.raises(Exception):
                await router.generate_response(request)

    @pytest.mark.asyncio
    async def test_timeout_handling(self, model_router):
        """Test timeout handling for long requests."""
        # Create a request that might take longer
        long_request = ModelRequest(
            messages=[{
                "role": "user", 
                "content": "Write a very detailed 2000-word analysis of real estate market trends."
            }],
            model_preference="qwen/qwen3-235b-a22b-thinking-2507",
            max_tokens=2000
        )

        start_time = time.time()
        response = await model_router.generate_response(long_request)
        end_time = time.time()
        
        assert response is not None
        # Should complete within reasonable time (adjust as needed)
        assert end_time - start_time < 60  # 60 seconds max

    @pytest.mark.asyncio
    async def test_token_usage_tracking(self, model_router, sample_messages):
        """Test that token usage is properly tracked."""
        request = ModelRequest(
            messages=sample_messages,
            model_preference="qwen/qwen3-235b-a22b-thinking-2507",
            max_tokens=200
        )

        response = await model_router.generate_response(request)
        
        assert response.token_usage is not None
        assert "prompt_tokens" in response.token_usage
        assert "completion_tokens" in response.token_usage
        assert "total_tokens" in response.token_usage
        assert response.token_usage["total_tokens"] > 0

    @pytest.mark.asyncio
    async def test_cost_calculation(self, model_router, sample_messages):
        """Test that costs are properly calculated."""
        request = ModelRequest(
            messages=sample_messages,
            model_preference="qwen/qwen3-235b-a22b-thinking-2507",
            max_tokens=100
        )

        response = await model_router.generate_response(request)
        
        assert response.cost > 0
        # Cost should be reasonable for the token count
        expected_cost = response.token_usage["total_tokens"] * 0.00002  # Model cost per token
        assert abs(response.cost - expected_cost) < expected_cost * 0.5  # Within 50% tolerance


class TestAgentSpecificIntegration:
    """Test LLM integration for specific agent types."""

    @pytest.fixture
    async def data_extraction_agent(self):
        """Create data extraction agent for testing."""
        orchestrator = AgentOrchestrator()
        await orchestrator.initialize()
        return await orchestrator.create_agent(
            role=AgentRole.DATA_EXTRACTION,
            model_preference="qwen/qwen3-235b-a22b-thinking-2507"
        )

    @pytest.mark.asyncio
    async def test_data_extraction_agent_llm(self, data_extraction_agent):
        """Test data extraction agent with real LLM."""
        extraction_prompt = """
        Extract key information from this property document:
        
        Property Address: 123 Main St, Anytown, ST 12345
        Purchase Price: $350,000
        Buyer: John Smith
        Seller: Jane Doe
        Closing Date: March 15, 2024
        """

        response = await data_extraction_agent.llm.generate(
            messages=[{
                "role": "user", 
                "content": extraction_prompt
            }]
        )

        assert response is not None
        content_lower = response.lower()
        
        # Should extract key information
        assert "123 main st" in content_lower or "main st" in content_lower
        assert "350,000" in response or "350000" in response
        assert "john smith" in content_lower
        assert "jane doe" in content_lower
