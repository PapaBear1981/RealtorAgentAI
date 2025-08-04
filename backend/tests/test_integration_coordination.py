"""
Integration Tests for Multi-Agent Coordination.

This module tests the interaction between different agents, the CrewAI orchestrator,
shared memory system, and overall multi-agent coordination.
"""

import asyncio
import pytest
import json
import uuid
from typing import Dict, Any, List
from datetime import datetime, timedelta

import structlog

from app.services.agent_orchestrator import (
    AgentOrchestrator, AgentRole, WorkflowRequest, WorkflowStatus
)
from app.services.agent_memory import (
    AgentMemoryManager, MemoryType, MemoryScope
)
from app.core.config import get_settings

logger = structlog.get_logger(__name__)


class TestMultiAgentCoordination:
    """Test multi-agent coordination and collaboration."""

    @pytest.fixture
    def settings(self):
        """Get test settings."""
        settings = get_settings()
        if not settings.OPENROUTER_API_KEY:
            pytest.skip("OPENROUTER_API_KEY not configured for testing")
        return settings

    @pytest.fixture
    async def orchestrator(self, settings):
        """Create orchestrator for testing."""
        orchestrator = AgentOrchestrator()
        await orchestrator.initialize()
        return orchestrator

    @pytest.fixture
    async def memory_manager(self):
        """Create memory manager for testing."""
        memory_manager = AgentMemoryManager()
        await memory_manager.initialize()
        return memory_manager

    @pytest.fixture
    def sample_property_data(self):
        """Sample property data for testing."""
        return {
            "address": "123 Test Street, Test City, TC 12345",
            "price": 450000,
            "bedrooms": 3,
            "bathrooms": 2,
            "square_feet": 1800,
            "year_built": 2010,
            "property_type": "single_family",
            "seller": "John Seller",
            "buyer": "Jane Buyer"
        }

    @pytest.mark.asyncio
    async def test_sequential_agent_workflow(self, orchestrator, sample_property_data):
        """Test sequential workflow between multiple agents."""
        session_id = str(uuid.uuid4())

        # Step 1: Data Extraction Agent processes raw document
        raw_document = f"""
        Property Information:
        Address: {sample_property_data['address']}
        Listed Price: ${sample_property_data['price']:,}
        Bedrooms: {sample_property_data['bedrooms']}
        Bathrooms: {sample_property_data['bathrooms']}
        Square Footage: {sample_property_data['square_feet']} sq ft
        Year Built: {sample_property_data['year_built']}
        Seller: {sample_property_data['seller']}
        Buyer: {sample_property_data['buyer']}
        """

        extraction_request = WorkflowRequest(
            workflow_id=f"extract-{session_id}",
            primary_agent=AgentRole.DATA_EXTRACTION,
            task_description="Extract structured data from property document",
            context={
                "document_content": raw_document,
                "session_id": session_id
            },
            model_preference="qwen/qwen3-235b-a22b-thinking-2507"
        )

        extraction_result = await orchestrator.execute_workflow(extraction_request)
        assert extraction_result.status == WorkflowStatus.COMPLETED

        # Step 2: Contract Generator uses extracted data
        contract_request = WorkflowRequest(
            workflow_id=f"contract-{session_id}",
            primary_agent=AgentRole.CONTRACT_GENERATOR,
            task_description="Generate purchase agreement using extracted data",
            context={
                "extracted_data": extraction_result.results.get("extracted_data", {}),
                "contract_type": "purchase_agreement",
                "session_id": session_id,
                "previous_workflow": extraction_result.workflow_id
            },
            model_preference="qwen/qwen3-235b-a22b-thinking-2507"
        )

        contract_result = await orchestrator.execute_workflow(contract_request)
        assert contract_result.status == WorkflowStatus.COMPLETED

        # Step 3: Compliance Checker reviews generated contract
        compliance_request = WorkflowRequest(
            workflow_id=f"compliance-{session_id}",
            primary_agent=AgentRole.COMPLIANCE_CHECKER,
            task_description="Review contract for compliance issues",
            context={
                "contract_content": contract_result.results.get("generated_contract", ""),
                "session_id": session_id,
                "previous_workflows": [extraction_result.workflow_id, contract_result.workflow_id]
            },
            model_preference="qwen/qwen3-235b-a22b-thinking-2507"
        )

        compliance_result = await orchestrator.execute_workflow(compliance_request)
        assert compliance_result.status == WorkflowStatus.COMPLETED

        # Verify workflow chain
        assert all(result.cost > 0 for result in [extraction_result, contract_result, compliance_result])
        assert all(result.execution_time > 0 for result in [extraction_result, contract_result, compliance_result])

    @pytest.mark.asyncio
    async def test_parallel_agent_execution(self, orchestrator, sample_property_data):
        """Test parallel execution of multiple agents."""
        session_id = str(uuid.uuid4())
        
        # Create multiple workflows that can run in parallel
        workflows = [
            WorkflowRequest(
                workflow_id=f"summary-{session_id}",
                primary_agent=AgentRole.SUMMARY,
                task_description="Summarize property information",
                context={
                    "content_to_summarize": json.dumps(sample_property_data),
                    "summary_type": "property_overview"
                },
                model_preference="qwen/qwen3-235b-a22b-thinking-2507"
            ),
            WorkflowRequest(
                workflow_id=f"help-{session_id}",
                primary_agent=AgentRole.HELP,
                task_description="Provide guidance on property purchase",
                context={
                    "user_question": "What should I know about this property?",
                    "property_data": sample_property_data
                },
                model_preference="qwen/qwen3-235b-a22b-thinking-2507"
            ),
            WorkflowRequest(
                workflow_id=f"signature-{session_id}",
                primary_agent=AgentRole.SIGNATURE_TRACKER,
                task_description="Set up signature tracking for property transaction",
                context={
                    "document_type": "purchase_agreement",
                    "parties": [sample_property_data["seller"], sample_property_data["buyer"]]
                },
                model_preference="qwen/qwen3-235b-a22b-thinking-2507"
            )
        ]

        # Execute workflows in parallel
        start_time = datetime.utcnow()
        tasks = [orchestrator.execute_workflow(workflow) for workflow in workflows]
        results = await asyncio.gather(*tasks)
        end_time = datetime.utcnow()

        # Verify all completed successfully
        for result in results:
            assert result.status == WorkflowStatus.COMPLETED
            assert result.cost > 0

        # Parallel execution should be faster than sequential
        total_time = (end_time - start_time).total_seconds()
        individual_times = sum(result.execution_time for result in results)
        
        # Should show some parallelization benefit
        efficiency = individual_times / total_time
        assert efficiency > 1.5  # Should be at least 50% more efficient

    @pytest.mark.asyncio
    async def test_shared_memory_coordination(self, orchestrator, memory_manager):
        """Test coordination through shared memory system."""
        session_id = str(uuid.uuid4())
        
        # Agent 1: Store information in shared memory
        help_request = WorkflowRequest(
            workflow_id=f"help-store-{session_id}",
            primary_agent=AgentRole.HELP,
            task_description="Help user understand property disclosures and store context",
            context={
                "user_question": "What are the most important things in a property disclosure?",
                "session_id": session_id,
                "store_context": True
            },
            model_preference="qwen/qwen3-235b-a22b-thinking-2507"
        )

        help_result = await orchestrator.execute_workflow(help_request)
        assert help_result.status == WorkflowStatus.COMPLETED

        # Store the interaction in shared memory
        await memory_manager.store_interaction(
            agent_id="help_agent",
            interaction_data={
                "workflow_id": help_result.workflow_id,
                "user_question": "What are the most important things in a property disclosure?",
                "response": help_result.results.get("response", ""),
                "session_id": session_id,
                "context_type": "property_disclosure_guidance"
            },
            memory_type=MemoryType.CONVERSATION,
            scope=MemoryScope.SESSION
        )

        # Agent 2: Retrieve and use shared context
        compliance_request = WorkflowRequest(
            workflow_id=f"compliance-context-{session_id}",
            primary_agent=AgentRole.COMPLIANCE_CHECKER,
            task_description="Check compliance with context from previous help session",
            context={
                "contract_content": "Sample contract with property disclosure requirements...",
                "session_id": session_id,
                "use_shared_context": True
            },
            model_preference="qwen/qwen3-235b-a22b-thinking-2507"
        )

        # Retrieve shared context before execution
        shared_context = await memory_manager.get_session_context(session_id)
        compliance_request.context["shared_context"] = shared_context

        compliance_result = await orchestrator.execute_workflow(compliance_request)
        assert compliance_result.status == WorkflowStatus.COMPLETED

        # Verify context was used
        assert shared_context is not None
        assert len(shared_context) > 0

    @pytest.mark.asyncio
    async def test_agent_delegation_workflow(self, orchestrator):
        """Test agent delegation and collaboration."""
        session_id = str(uuid.uuid4())

        # Primary agent that delegates to others
        complex_request = WorkflowRequest(
            workflow_id=f"complex-{session_id}",
            primary_agent=AgentRole.HELP,
            task_description="Handle complex property transaction requiring multiple agent types",
            context={
                "user_request": "I need help with a complete property transaction including data extraction, contract generation, and compliance checking",
                "property_document": "Sample property document content...",
                "enable_delegation": True,
                "session_id": session_id
            },
            model_preference="qwen/qwen3-235b-a22b-thinking-2507"
        )

        result = await orchestrator.execute_workflow(complex_request)
        assert result.status == WorkflowStatus.COMPLETED

        # Should have multiple agent interactions if delegation occurred
        assert len(result.agent_interactions) >= 1
        assert result.cost > 0

    @pytest.mark.asyncio
    async def test_error_propagation_between_agents(self, orchestrator):
        """Test error handling and propagation in multi-agent workflows."""
        session_id = str(uuid.uuid4())

        # Create a workflow that will likely encounter issues
        problematic_request = WorkflowRequest(
            workflow_id=f"error-test-{session_id}",
            primary_agent=AgentRole.DATA_EXTRACTION,
            task_description="Extract data from invalid document",
            context={
                "document_content": "",  # Empty document
                "extraction_fields": ["invalid_field"],
                "session_id": session_id
            },
            model_preference="qwen/qwen3-235b-a22b-thinking-2507"
        )

        result = await orchestrator.execute_workflow(problematic_request)

        # Should handle gracefully
        assert result is not None
        # May complete with warnings or fail gracefully
        assert result.status in [WorkflowStatus.COMPLETED, WorkflowStatus.COMPLETED_WITH_WARNINGS, WorkflowStatus.FAILED]

        if result.errors:
            assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_workflow_state_management(self, orchestrator, memory_manager):
        """Test workflow state management across agent interactions."""
        session_id = str(uuid.uuid4())

        # Create a multi-step workflow with state tracking
        workflow_steps = [
            {
                "agent": AgentRole.DATA_EXTRACTION,
                "task": "Extract property data",
                "context": {"document_content": "Property: 123 Main St, Price: $300,000"}
            },
            {
                "agent": AgentRole.CONTRACT_GENERATOR,
                "task": "Generate contract draft",
                "context": {"use_previous_data": True}
            },
            {
                "agent": AgentRole.COMPLIANCE_CHECKER,
                "task": "Review contract compliance",
                "context": {"use_previous_contract": True}
            }
        ]

        workflow_results = []
        previous_result = None

        for i, step in enumerate(workflow_steps):
            # Build context with previous results
            context = step["context"].copy()
            context["session_id"] = session_id
            context["step_number"] = i + 1
            
            if previous_result:
                context["previous_workflow_id"] = previous_result.workflow_id
                context["previous_results"] = previous_result.results

            request = WorkflowRequest(
                workflow_id=f"step-{i+1}-{session_id}",
                primary_agent=step["agent"],
                task_description=step["task"],
                context=context,
                model_preference="qwen/qwen3-235b-a22b-thinking-2507"
            )

            result = await orchestrator.execute_workflow(request)
            assert result.status == WorkflowStatus.COMPLETED

            # Store workflow state
            await memory_manager.store_workflow_state(
                workflow_id=result.workflow_id,
                state_data={
                    "step": i + 1,
                    "agent": step["agent"].value,
                    "results": result.results,
                    "session_id": session_id
                }
            )

            workflow_results.append(result)
            previous_result = result

        # Verify workflow chain integrity
        assert len(workflow_results) == len(workflow_steps)
        
        # Each step should build on the previous
        for i in range(1, len(workflow_results)):
            current_context = workflow_results[i].metadata.get("context", {})
            assert "previous_workflow_id" in current_context

    @pytest.mark.asyncio
    async def test_concurrent_session_isolation(self, orchestrator, memory_manager):
        """Test that concurrent sessions don't interfere with each other."""
        session_1 = str(uuid.uuid4())
        session_2 = str(uuid.uuid4())

        # Create workflows for different sessions
        workflow_1 = WorkflowRequest(
            workflow_id=f"session1-{session_1}",
            primary_agent=AgentRole.HELP,
            task_description="Help with session 1 property question",
            context={
                "user_question": "Session 1: What is a home inspection?",
                "session_id": session_1
            },
            model_preference="qwen/qwen3-235b-a22b-thinking-2507"
        )

        workflow_2 = WorkflowRequest(
            workflow_id=f"session2-{session_2}",
            primary_agent=AgentRole.HELP,
            task_description="Help with session 2 property question",
            context={
                "user_question": "Session 2: What is property insurance?",
                "session_id": session_2
            },
            model_preference="qwen/qwen3-235b-a22b-thinking-2507"
        )

        # Execute concurrently
        results = await asyncio.gather(
            orchestrator.execute_workflow(workflow_1),
            orchestrator.execute_workflow(workflow_2)
        )

        result_1, result_2 = results

        # Both should complete successfully
        assert result_1.status == WorkflowStatus.COMPLETED
        assert result_2.status == WorkflowStatus.COMPLETED

        # Responses should be different and session-specific
        response_1 = result_1.results.get("response", "").lower()
        response_2 = result_2.results.get("response", "").lower()

        assert "inspection" in response_1 or "session 1" in response_1
        assert "insurance" in response_2 or "session 2" in response_2

        # Store session contexts separately
        await memory_manager.store_interaction(
            agent_id="help_agent",
            interaction_data={"session_id": session_1, "response": response_1},
            memory_type=MemoryType.CONVERSATION,
            scope=MemoryScope.SESSION
        )

        await memory_manager.store_interaction(
            agent_id="help_agent", 
            interaction_data={"session_id": session_2, "response": response_2},
            memory_type=MemoryType.CONVERSATION,
            scope=MemoryScope.SESSION
        )

        # Verify session isolation
        context_1 = await memory_manager.get_session_context(session_1)
        context_2 = await memory_manager.get_session_context(session_2)

        assert context_1 != context_2  # Should be different
