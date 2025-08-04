"""
Performance Tests for AI Agents.

This module tests agent response times, concurrent request handling,
and resource usage under various load conditions.
"""

import asyncio
import pytest
import time
import psutil
import statistics
from typing import List, Dict, Any
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

import structlog

from app.services.model_router import ModelRouter, ModelRequest, ModelResponse
from app.services.agent_orchestrator import AgentOrchestrator, AgentRole, WorkflowRequest
from app.core.config import get_settings

logger = structlog.get_logger(__name__)


class TestPerformance:
    """Test performance characteristics of AI agents."""

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
    async def orchestrator(self, settings):
        """Create orchestrator for testing."""
        orchestrator = AgentOrchestrator()
        await orchestrator.initialize()
        return orchestrator

    @pytest.mark.asyncio
    async def test_single_request_response_time(self, model_router):
        """Test response time for single requests."""
        request = ModelRequest(
            messages=[{"role": "user", "content": "What is a property disclosure?"}],
            model_preference="qwen/qwen3-235b-a22b-thinking-2507",
            max_tokens=100
        )

        start_time = time.time()
        response = await model_router.generate_response(request)
        end_time = time.time()

        response_time = end_time - start_time

        # Performance assertions
        assert response_time < 30.0  # Should respond within 30 seconds
        assert response.processing_time > 0
        assert response.processing_time <= response_time + 1  # Allow small buffer

        logger.info(f"Single request response time: {response_time:.2f}s")

    @pytest.mark.asyncio
    async def test_concurrent_request_handling(self, model_router):
        """Test handling of concurrent requests."""
        num_concurrent = 5
        requests = []

        for i in range(num_concurrent):
            request = ModelRequest(
                messages=[{"role": "user", "content": f"Concurrent test {i}: Explain property taxes."}],
                model_preference="qwen/qwen3-235b-a22b-thinking-2507",
                max_tokens=100
            )
            requests.append(request)

        start_time = time.time()
        
        # Execute all requests concurrently
        tasks = [model_router.generate_response(req) for req in requests]
        responses = await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_time = end_time - start_time

        # Validate all responses
        assert len(responses) == num_concurrent
        for response in responses:
            assert response is not None
            assert response.content is not None

        # Performance assertions
        assert total_time < 60.0  # All should complete within 60 seconds
        
        # Concurrent execution should be faster than sequential
        avg_individual_time = sum(r.processing_time for r in responses) / len(responses)
        efficiency = avg_individual_time / total_time
        assert efficiency > 0.5  # Should show some concurrency benefit

        logger.info(f"Concurrent requests ({num_concurrent}): {total_time:.2f}s total, efficiency: {efficiency:.2f}")

    @pytest.mark.asyncio
    async def test_load_testing(self, model_router):
        """Test system under sustained load."""
        num_requests = 10
        batch_size = 3
        
        all_response_times = []
        all_costs = []

        for batch in range(0, num_requests, batch_size):
            batch_requests = []
            
            for i in range(batch, min(batch + batch_size, num_requests)):
                request = ModelRequest(
                    messages=[{"role": "user", "content": f"Load test {i}: Summarize a real estate contract."}],
                    model_preference="qwen/qwen3-235b-a22b-thinking-2507",
                    max_tokens=150
                )
                batch_requests.append(request)

            batch_start = time.time()
            tasks = [model_router.generate_response(req) for req in batch_requests]
            responses = await asyncio.gather(*tasks)
            batch_end = time.time()

            batch_time = batch_end - batch_start
            all_response_times.extend([r.processing_time for r in responses])
            all_costs.extend([r.cost for r in responses])

            logger.info(f"Batch {batch//batch_size + 1}: {batch_time:.2f}s for {len(batch_requests)} requests")

            # Brief pause between batches
            await asyncio.sleep(1)

        # Analyze performance metrics
        avg_response_time = statistics.mean(all_response_times)
        max_response_time = max(all_response_times)
        min_response_time = min(all_response_times)
        
        total_cost = sum(all_costs)

        # Performance assertions
        assert avg_response_time < 20.0  # Average should be reasonable
        assert max_response_time < 45.0  # No request should take too long
        assert total_cost > 0  # Should track costs

        logger.info(f"Load test results - Avg: {avg_response_time:.2f}s, Max: {max_response_time:.2f}s, Min: {min_response_time:.2f}s, Total cost: ${total_cost:.4f}")

    @pytest.mark.asyncio
    async def test_memory_usage_monitoring(self, model_router):
        """Test memory usage during operations."""
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Perform multiple requests
        for i in range(5):
            request = ModelRequest(
                messages=[{"role": "user", "content": f"Memory test {i}: Analyze property investment strategies."}],
                model_preference="qwen/qwen3-235b-a22b-thinking-2507",
                max_tokens=200
            )
            
            await model_router.generate_response(request)
            
            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = current_memory - initial_memory
            
            # Memory shouldn't grow excessively
            assert memory_increase < 500  # Less than 500MB increase
            
            logger.info(f"Memory after request {i}: {current_memory:.1f}MB (+{memory_increase:.1f}MB)")

    @pytest.mark.asyncio
    async def test_agent_workflow_performance(self, orchestrator):
        """Test performance of complete agent workflows."""
        workflow_times = []

        for i in range(3):  # Test multiple workflows
            workflow_request = WorkflowRequest(
                workflow_id=f"perf-test-{i}",
                primary_agent=AgentRole.SUMMARY,
                task_description=f"Performance test {i}: Summarize real estate market conditions",
                context={
                    "content_to_summarize": f"Test content {i}: The real estate market shows various trends including price fluctuations, inventory levels, and buyer behavior patterns.",
                    "summary_type": "brief"
                },
                model_preference="qwen/qwen3-235b-a22b-thinking-2507"
            )

            start_time = time.time()
            result = await orchestrator.execute_workflow(workflow_request)
            end_time = time.time()

            workflow_time = end_time - start_time
            workflow_times.append(workflow_time)

            assert result.status == "completed"
            assert workflow_time < 45.0  # Should complete within 45 seconds

            logger.info(f"Workflow {i} completed in {workflow_time:.2f}s")

        # Analyze workflow performance
        avg_workflow_time = statistics.mean(workflow_times)
        assert avg_workflow_time < 30.0  # Average should be reasonable

    @pytest.mark.asyncio
    async def test_token_efficiency(self, model_router):
        """Test token usage efficiency."""
        # Test with different request sizes
        test_cases = [
            ("Short", "What is escrow?", 50),
            ("Medium", "Explain the home buying process including financing options.", 150),
            ("Long", "Provide a comprehensive analysis of real estate investment strategies, market trends, and risk factors.", 300)
        ]

        for case_name, content, max_tokens in test_cases:
            request = ModelRequest(
                messages=[{"role": "user", "content": content}],
                model_preference="qwen/qwen3-235b-a22b-thinking-2507",
                max_tokens=max_tokens
            )

            response = await model_router.generate_response(request)

            # Token efficiency checks
            token_usage = response.token_usage
            efficiency = len(response.content) / token_usage["completion_tokens"] if token_usage["completion_tokens"] > 0 else 0

            assert efficiency > 2.0  # Should generate reasonable content per token
            assert token_usage["completion_tokens"] <= max_tokens  # Should respect limits

            logger.info(f"{case_name} request - Tokens: {token_usage['completion_tokens']}, Efficiency: {efficiency:.2f} chars/token")

    @pytest.mark.asyncio
    async def test_cost_efficiency(self, model_router):
        """Test cost efficiency of operations."""
        total_cost = 0
        total_tokens = 0
        total_content_length = 0

        for i in range(5):
            request = ModelRequest(
                messages=[{"role": "user", "content": f"Cost test {i}: Explain property valuation methods."}],
                model_preference="qwen/qwen3-235b-a22b-thinking-2507",
                max_tokens=100
            )

            response = await model_router.generate_response(request)

            total_cost += response.cost
            total_tokens += response.token_usage["total_tokens"]
            total_content_length += len(response.content)

        # Cost efficiency metrics
        cost_per_token = total_cost / total_tokens if total_tokens > 0 else 0
        cost_per_char = total_cost / total_content_length if total_content_length > 0 else 0

        # Should be within reasonable cost ranges
        assert cost_per_token < 0.0001  # Less than $0.0001 per token
        assert total_cost < 0.1  # Total cost should be reasonable

        logger.info(f"Cost efficiency - Per token: ${cost_per_token:.6f}, Per char: ${cost_per_char:.6f}, Total: ${total_cost:.4f}")

    @pytest.mark.asyncio
    async def test_error_rate_under_load(self, model_router):
        """Test error rates under load conditions."""
        num_requests = 15
        successful_requests = 0
        failed_requests = 0

        tasks = []
        for i in range(num_requests):
            request = ModelRequest(
                messages=[{"role": "user", "content": f"Error rate test {i}: Describe property insurance."}],
                model_preference="qwen/qwen3-235b-a22b-thinking-2507",
                max_tokens=100
            )
            tasks.append(model_router.generate_response(request))

        # Execute all requests and handle exceptions
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                failed_requests += 1
                logger.warning(f"Request failed: {result}")
            else:
                successful_requests += 1

        success_rate = successful_requests / num_requests
        error_rate = failed_requests / num_requests

        # Performance assertions
        assert success_rate > 0.8  # At least 80% success rate
        assert error_rate < 0.2   # Less than 20% error rate

        logger.info(f"Error rate test - Success: {success_rate:.2%}, Errors: {error_rate:.2%}")

    @pytest.mark.asyncio
    async def test_response_quality_consistency(self, model_router):
        """Test consistency of response quality under load."""
        responses = []
        
        # Same question multiple times
        base_question = "What are the key factors to consider when buying a house?"
        
        for i in range(5):
            request = ModelRequest(
                messages=[{"role": "user", "content": base_question}],
                model_preference="qwen/qwen3-235b-a22b-thinking-2507",
                max_tokens=200
            )
            
            response = await model_router.generate_response(request)
            responses.append(response)

        # Analyze response consistency
        response_lengths = [len(r.content) for r in responses]
        avg_length = statistics.mean(response_lengths)
        length_variance = statistics.variance(response_lengths) if len(response_lengths) > 1 else 0

        # Responses should be reasonably consistent
        assert all(length > 50 for length in response_lengths)  # All should be substantial
        assert length_variance < (avg_length * 0.5) ** 2  # Variance shouldn't be too high

        logger.info(f"Response consistency - Avg length: {avg_length:.1f}, Variance: {length_variance:.1f}")

    @pytest.mark.asyncio
    async def test_scalability_limits(self, model_router):
        """Test system behavior at scalability limits."""
        # Gradually increase load to find limits
        max_concurrent = 10
        
        for concurrent_level in [2, 5, 8, max_concurrent]:
            tasks = []
            
            for i in range(concurrent_level):
                request = ModelRequest(
                    messages=[{"role": "user", "content": f"Scalability test level {concurrent_level}, request {i}"}],
                    model_preference="qwen/qwen3-235b-a22b-thinking-2507",
                    max_tokens=100
                )
                tasks.append(model_router.generate_response(request))

            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()

            successful = sum(1 for r in results if not isinstance(r, Exception))
            total_time = end_time - start_time
            
            success_rate = successful / concurrent_level
            throughput = successful / total_time

            logger.info(f"Concurrent level {concurrent_level}: {success_rate:.2%} success, {throughput:.2f} req/s")

            # Should maintain reasonable performance
            assert success_rate > 0.7  # At least 70% success rate
            assert total_time < 60.0   # Should complete within reasonable time
