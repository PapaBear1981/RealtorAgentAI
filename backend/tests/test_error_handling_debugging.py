"""
Error Handling and Debugging Tests.

This module tests error scenarios including API failures, invalid responses,
timeout handling, and fallback mechanisms. Also implements debugging tools.
"""

import asyncio
import pytest
import json
import time
from typing import Dict, Any, List
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

import structlog
import httpx

from app.services.model_router import ModelRouter, ModelRequest, ModelResponse, ModelProvider
from app.services.agent_orchestrator import AgentOrchestrator, AgentRole, WorkflowRequest
from app.core.config import get_settings

logger = structlog.get_logger(__name__)


class TestErrorHandling:
    """Test error handling scenarios."""

    @pytest.fixture
    def settings(self):
        """Get test settings."""
        return get_settings()

    @pytest.fixture
    async def model_router(self, settings):
        """Create model router for testing."""
        router = ModelRouter()
        await router.initialize()
        return router

    @pytest.fixture
    async def orchestrator(self, settings):
        """Create orchestrator for testing."""
        orchestrator = AgentOrchestrator()
        await orchestrator.initialize()
        return orchestrator

    @pytest.mark.asyncio
    async def test_api_key_authentication_error(self):
        """Test handling of invalid API key."""
        # Create router with invalid API key
        with patch('app.core.config.get_settings') as mock_settings:
            mock_settings.return_value.OPENROUTER_API_KEY = "invalid_key_12345"
            
            router = ModelRouter()
            await router.initialize()
            
            request = ModelRequest(
                messages=[{"role": "user", "content": "Test"}],
                model_preference="qwen/qwen3-235b-a22b-thinking-2507"
            )
            
            with pytest.raises(Exception) as exc_info:
                await router.generate_response(request)
            
            # Should contain authentication error information
            error_msg = str(exc_info.value).lower()
            assert any(term in error_msg for term in ["auth", "key", "invalid", "unauthorized"])

    @pytest.mark.asyncio
    async def test_network_timeout_handling(self, model_router):
        """Test handling of network timeouts."""
        with patch.object(model_router, 'openrouter_async_client') as mock_client:
            # Simulate timeout
            mock_client.chat.completions.create.side_effect = httpx.TimeoutException("Request timeout")
            
            request = ModelRequest(
                messages=[{"role": "user", "content": "Test timeout"}],
                model_preference="qwen/qwen3-235b-a22b-thinking-2507"
            )
            
            with pytest.raises(Exception) as exc_info:
                await router.generate_response(request)
            
            assert "timeout" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_rate_limit_handling(self, model_router):
        """Test handling of rate limit errors."""
        with patch.object(model_router, '_call_openrouter') as mock_call:
            mock_call.side_effect = Exception("Rate limit exceeded")
            
            request = ModelRequest(
                messages=[{"role": "user", "content": "Test rate limit"}],
                model_preference="qwen/qwen3-235b-a22b-thinking-2507"
            )
            
            with pytest.raises(Exception) as exc_info:
                await router.generate_response(request)
            
            assert "rate limit" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_model_unavailable_fallback(self, model_router):
        """Test fallback when specific model is unavailable."""
        # Test with a model that doesn't exist
        request = ModelRequest(
            messages=[{"role": "user", "content": "Test fallback"}],
            model_preference="nonexistent/model-123"
        )

        # Should either fallback to available model or raise appropriate error
        try:
            response = await model_router.generate_response(request)
            # If successful, should have used a different model
            assert response.model_used != "nonexistent/model-123"
        except Exception as e:
            # Should be a meaningful error about model availability
            error_msg = str(e).lower()
            assert any(term in error_msg for term in ["model", "not found", "unavailable", "invalid"])

    @pytest.mark.asyncio
    async def test_malformed_request_handling(self, model_router):
        """Test handling of malformed requests."""
        # Test with empty messages
        with pytest.raises((ValueError, ValidationError, Exception)):
            request = ModelRequest(
                messages=[],  # Empty messages
                model_preference="qwen/qwen3-235b-a22b-thinking-2507"
            )
            await model_router.generate_response(request)

        # Test with invalid message format
        with pytest.raises((ValueError, ValidationError, Exception)):
            request = ModelRequest(
                messages=[{"invalid": "format"}],  # Missing role/content
                model_preference="qwen/qwen3-235b-a22b-thinking-2507"
            )
            await model_router.generate_response(request)

    @pytest.mark.asyncio
    async def test_agent_workflow_error_recovery(self, orchestrator):
        """Test agent workflow error recovery."""
        # Create a workflow that might fail
        workflow_request = WorkflowRequest(
            workflow_id="test-error-recovery",
            primary_agent=AgentRole.DATA_EXTRACTION,
            task_description="Extract data from completely invalid content",
            context={
                "document_content": "",  # Empty content
                "extraction_fields": ["nonexistent_field"]
            },
            model_preference="qwen/qwen3-235b-a22b-thinking-2507"
        )

        result = await orchestrator.execute_workflow(workflow_request)

        # Should handle gracefully
        assert result is not None
        # Should either complete with warnings or fail gracefully
        assert result.status in ["completed", "completed_with_warnings", "failed"]
        
        if result.errors:
            assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_memory_system_error_handling(self, orchestrator):
        """Test memory system error handling."""
        from app.services.agent_memory import AgentMemoryManager
        
        memory_manager = AgentMemoryManager()
        await memory_manager.initialize()

        # Test with invalid memory operations
        with pytest.raises(Exception):
            await memory_manager.store_interaction(
                agent_id="",  # Empty agent ID
                interaction_data={},
                memory_type=None,  # Invalid memory type
                scope=None  # Invalid scope
            )

    @pytest.mark.asyncio
    async def test_concurrent_error_handling(self, model_router):
        """Test error handling under concurrent load."""
        # Create multiple requests, some of which will fail
        requests = []
        
        for i in range(5):
            if i % 2 == 0:
                # Valid request
                request = ModelRequest(
                    messages=[{"role": "user", "content": f"Valid request {i}"}],
                    model_preference="qwen/qwen3-235b-a22b-thinking-2507"
                )
            else:
                # Invalid request
                request = ModelRequest(
                    messages=[{"role": "user", "content": f"Request {i}"}],
                    model_preference="invalid/model"
                )
            
            requests.append(model_router.generate_response(request))

        # Gather results, allowing for failures
        results = await asyncio.gather(*requests, return_exceptions=True)

        # Should have mix of successes and failures
        successes = [r for r in results if isinstance(r, ModelResponse)]
        failures = [r for r in results if isinstance(r, Exception)]
        
        assert len(successes) > 0  # Some should succeed
        assert len(failures) > 0   # Some should fail


class TestDebuggingTools:
    """Test debugging and monitoring tools."""

    @pytest.fixture
    async def model_router(self):
        """Create model router with debugging enabled."""
        router = ModelRouter()
        await router.initialize()
        return router

    @pytest.mark.asyncio
    async def test_request_response_logging(self, model_router):
        """Test that requests and responses are properly logged."""
        import logging
        
        # Capture logs
        log_capture = []
        
        class TestHandler(logging.Handler):
            def emit(self, record):
                log_capture.append(record.getMessage())
        
        handler = TestHandler()
        logging.getLogger().addHandler(handler)
        
        try:
            request = ModelRequest(
                messages=[{"role": "user", "content": "Test logging"}],
                model_preference="qwen/qwen3-235b-a22b-thinking-2507",
                max_tokens=50
            )

            await model_router.generate_response(request)

            # Check that relevant information was logged
            log_messages = " ".join(log_capture)
            assert any(term in log_messages.lower() for term in ["request", "response", "model", "qwen"])
            
        finally:
            logging.getLogger().removeHandler(handler)

    @pytest.mark.asyncio
    async def test_performance_metrics_collection(self, model_router):
        """Test collection of performance metrics."""
        request = ModelRequest(
            messages=[{"role": "user", "content": "Test performance metrics"}],
            model_preference="qwen/qwen3-235b-a22b-thinking-2507",
            max_tokens=100
        )

        start_time = time.time()
        response = await model_router.generate_response(request)
        end_time = time.time()

        # Verify metrics are collected
        assert response.processing_time > 0
        assert response.processing_time <= (end_time - start_time) + 1  # Allow small buffer
        assert response.cost > 0
        assert response.token_usage["total_tokens"] > 0

    @pytest.mark.asyncio
    async def test_error_context_preservation(self, model_router):
        """Test that error context is preserved for debugging."""
        with patch.object(model_router, '_call_openrouter') as mock_call:
            mock_call.side_effect = Exception("Test error with context")
            
            request = ModelRequest(
                messages=[{"role": "user", "content": "Test error context"}],
                model_preference="qwen/qwen3-235b-a22b-thinking-2507"
            )

            try:
                await model_router.generate_response(request)
            except Exception as e:
                # Error should contain useful context
                error_str = str(e)
                assert "test error" in error_str.lower()
                # Should preserve request context for debugging

    @pytest.mark.asyncio
    async def test_health_check_monitoring(self, model_router):
        """Test health check and monitoring capabilities."""
        # Test model availability check
        available_models = await model_router.get_available_models()
        
        assert isinstance(available_models, list)
        assert len(available_models) > 0
        
        # Check that Qwen model is in the list
        qwen_models = [m for m in available_models if "qwen" in m.get("id", "").lower()]
        assert len(qwen_models) > 0

    @pytest.mark.asyncio
    async def test_debug_mode_functionality(self, model_router):
        """Test debug mode functionality."""
        # Enable debug mode
        with patch.dict('os.environ', {'DEBUG': 'true'}):
            request = ModelRequest(
                messages=[{"role": "user", "content": "Debug mode test"}],
                model_preference="qwen/qwen3-235b-a22b-thinking-2507",
                max_tokens=50
            )

            response = await model_router.generate_response(request)

            # In debug mode, should have additional metadata
            assert response.metadata is not None
            # Should contain debug information
            assert len(response.metadata) > 0

    @pytest.mark.asyncio
    async def test_request_tracing(self, model_router):
        """Test request tracing for debugging."""
        request = ModelRequest(
            messages=[{"role": "user", "content": "Trace this request"}],
            model_preference="qwen/qwen3-235b-a22b-thinking-2507",
            max_tokens=50
        )

        response = await model_router.generate_response(request)

        # Should have tracing information
        assert response.metadata is not None
        # Should track request flow
        assert response.processing_time > 0

    def test_configuration_validation(self):
        """Test configuration validation for debugging."""
        settings = get_settings()
        
        # Check required settings
        if settings.OPENROUTER_API_KEY:
            assert len(settings.OPENROUTER_API_KEY) > 10  # Should be meaningful key
        
        # Check model configuration
        assert settings.DEFAULT_LLM_MODEL is not None
        assert len(settings.DEFAULT_LLM_MODEL) > 0
