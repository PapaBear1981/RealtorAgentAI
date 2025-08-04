"""
End-to-End Agent Workflow Tests.

This module tests complete agent execution pipelines from user request
through LLM processing to final response delivery.
"""

import asyncio
import pytest
import json
import uuid
from typing import Dict, Any, List
from datetime import datetime

import structlog

from app.services.agent_orchestrator import (
    AgentOrchestrator, AgentRole, WorkflowRequest, WorkflowStatus
)
from app.services.agent_memory import AgentMemoryManager, MemoryType, MemoryScope
from app.core.config import get_settings

logger = structlog.get_logger(__name__)


class TestEndToEndWorkflows:
    """Test complete agent workflows from start to finish."""

    @pytest.fixture
    def settings(self):
        """Get test settings."""
        settings = get_settings()
        if not settings.OPENROUTER_API_KEY:
            pytest.skip("OPENROUTER_API_KEY not configured for testing")
        return settings

    @pytest.fixture
    async def orchestrator(self, settings):
        """Create agent orchestrator for testing."""
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
    def sample_property_document(self):
        """Sample property document for testing."""
        return """
        PROPERTY DISCLOSURE STATEMENT
        
        Property Address: 456 Oak Avenue, Springfield, IL 62701
        Seller: Robert Johnson
        Buyer: Sarah Williams
        
        PROPERTY DETAILS:
        - Year Built: 1995
        - Square Footage: 2,400 sq ft
        - Bedrooms: 4
        - Bathrooms: 2.5
        - Garage: 2-car attached
        - Lot Size: 0.75 acres
        
        KNOWN ISSUES:
        - Minor roof leak in master bedroom (repaired 2023)
        - HVAC system serviced annually
        - Basement has minor water seepage during heavy rains
        - Kitchen appliances included (refrigerator, stove, dishwasher)
        
        RECENT IMPROVEMENTS:
        - New windows installed (2022)
        - Hardwood floors refinished (2023)
        - Exterior painted (2023)
        
        Purchase Price: $425,000
        Closing Date: April 30, 2024
        """

    @pytest.mark.asyncio
    async def test_data_extraction_workflow(self, orchestrator, sample_property_document):
        """Test complete data extraction workflow."""
        # Create workflow request
        workflow_request = WorkflowRequest(
            workflow_id=str(uuid.uuid4()),
            primary_agent=AgentRole.DATA_EXTRACTION,
            task_description="Extract all key information from the property disclosure document",
            context={
                "document_content": sample_property_document,
                "document_type": "property_disclosure",
                "extraction_fields": [
                    "property_address", "seller", "buyer", "purchase_price", 
                    "closing_date", "property_details", "known_issues"
                ]
            },
            model_preference="qwen/qwen3-235b-a22b-thinking-2507"
        )

        # Execute workflow
        result = await orchestrator.execute_workflow(workflow_request)

        # Validate results
        assert result is not None
        assert result.status == WorkflowStatus.COMPLETED
        assert result.workflow_id == workflow_request.workflow_id
        assert result.execution_time > 0
        assert result.cost > 0

        # Check extracted data
        extracted_data = result.results.get("extracted_data", {})
        assert "property_address" in extracted_data
        assert "456 Oak Avenue" in str(extracted_data.get("property_address", ""))
        assert "purchase_price" in extracted_data
        assert "425,000" in str(extracted_data.get("purchase_price", ""))

    @pytest.mark.asyncio
    async def test_contract_generation_workflow(self, orchestrator):
        """Test complete contract generation workflow."""
        contract_data = {
            "property_address": "789 Pine Street, Chicago, IL 60601",
            "seller_name": "Michael Brown",
            "buyer_name": "Lisa Davis",
            "purchase_price": 550000,
            "earnest_money": 10000,
            "closing_date": "2024-05-15",
            "financing_contingency": True,
            "inspection_period": 10
        }

        workflow_request = WorkflowRequest(
            workflow_id=str(uuid.uuid4()),
            primary_agent=AgentRole.CONTRACT_GENERATOR,
            task_description="Generate a purchase agreement contract",
            context={
                "contract_type": "purchase_agreement",
                "contract_data": contract_data,
                "template_preferences": ["standard", "residential"]
            },
            model_preference="qwen/qwen3-235b-a22b-thinking-2507"
        )

        result = await orchestrator.execute_workflow(workflow_request)

        assert result.status == WorkflowStatus.COMPLETED
        assert "generated_contract" in result.results
        
        contract_content = result.results["generated_contract"]
        assert "789 Pine Street" in contract_content
        assert "Michael Brown" in contract_content
        assert "Lisa Davis" in contract_content
        assert "$550,000" in contract_content or "550,000" in contract_content

    @pytest.mark.asyncio
    async def test_compliance_checking_workflow(self, orchestrator):
        """Test complete compliance checking workflow."""
        contract_content = """
        PURCHASE AGREEMENT
        
        This agreement is between John Seller and Jane Buyer for the purchase
        of property located at 321 Elm Street, Boston, MA 02101.
        
        Purchase Price: $750,000
        Earnest Money: $15,000
        
        CONTINGENCIES:
        - Financing contingency: 30 days
        - Inspection contingency: 14 days
        
        DISCLOSURES:
        - Lead paint disclosure: Not applicable (built 1985)
        - Property condition: Sold as-is
        """

        workflow_request = WorkflowRequest(
            workflow_id=str(uuid.uuid4()),
            primary_agent=AgentRole.COMPLIANCE_CHECKER,
            task_description="Check contract for legal compliance and required disclosures",
            context={
                "contract_content": contract_content,
                "jurisdiction": "Massachusetts",
                "property_type": "residential",
                "compliance_standards": ["state_law", "federal_law", "local_ordinances"]
            },
            model_preference="qwen/qwen3-235b-a22b-thinking-2507"
        )

        result = await orchestrator.execute_workflow(workflow_request)

        assert result.status == WorkflowStatus.COMPLETED
        assert "compliance_report" in result.results
        
        compliance_report = result.results["compliance_report"]
        assert "lead paint" in compliance_report.lower()
        assert len(compliance_report) > 100  # Should be detailed

    @pytest.mark.asyncio
    async def test_multi_agent_collaboration_workflow(self, orchestrator, sample_property_document):
        """Test workflow involving multiple agents working together."""
        # Step 1: Data extraction
        extraction_request = WorkflowRequest(
            workflow_id=str(uuid.uuid4()),
            primary_agent=AgentRole.DATA_EXTRACTION,
            task_description="Extract property information for contract generation",
            context={
                "document_content": sample_property_document,
                "extraction_purpose": "contract_generation"
            },
            model_preference="qwen/qwen3-235b-a22b-thinking-2507"
        )

        extraction_result = await orchestrator.execute_workflow(extraction_request)
        assert extraction_result.status == WorkflowStatus.COMPLETED

        # Step 2: Use extracted data for contract generation
        extracted_data = extraction_result.results.get("extracted_data", {})
        
        contract_request = WorkflowRequest(
            workflow_id=str(uuid.uuid4()),
            primary_agent=AgentRole.CONTRACT_GENERATOR,
            task_description="Generate contract using extracted property data",
            context={
                "contract_type": "purchase_agreement",
                "extracted_property_data": extracted_data,
                "previous_workflow_id": extraction_result.workflow_id
            },
            model_preference="qwen/qwen3-235b-a22b-thinking-2507"
        )

        contract_result = await orchestrator.execute_workflow(contract_request)
        assert contract_result.status == WorkflowStatus.COMPLETED

        # Step 3: Compliance check on generated contract
        generated_contract = contract_result.results.get("generated_contract", "")
        
        compliance_request = WorkflowRequest(
            workflow_id=str(uuid.uuid4()),
            primary_agent=AgentRole.COMPLIANCE_CHECKER,
            task_description="Verify compliance of generated contract",
            context={
                "contract_content": generated_contract,
                "previous_workflow_ids": [extraction_result.workflow_id, contract_result.workflow_id]
            },
            model_preference="qwen/qwen3-235b-a22b-thinking-2507"
        )

        compliance_result = await orchestrator.execute_workflow(compliance_request)
        assert compliance_result.status == WorkflowStatus.COMPLETED

        # Verify the chain of workflows
        assert len(compliance_result.agent_interactions) > 0
        assert compliance_result.cost > 0

    @pytest.mark.asyncio
    async def test_workflow_with_memory_persistence(self, orchestrator, memory_manager):
        """Test workflow with memory persistence across interactions."""
        session_id = str(uuid.uuid4())
        
        # First interaction - store context
        first_request = WorkflowRequest(
            workflow_id=str(uuid.uuid4()),
            primary_agent=AgentRole.HELP,
            task_description="Help user understand property disclosure requirements",
            context={
                "user_question": "What should I look for in a property disclosure?",
                "session_id": session_id,
                "user_context": "first_time_buyer"
            },
            model_preference="qwen/qwen3-235b-a22b-thinking-2507"
        )

        first_result = await orchestrator.execute_workflow(first_request)
        assert first_result.status == WorkflowStatus.COMPLETED

        # Store interaction in memory
        await memory_manager.store_interaction(
            agent_id="help_agent",
            interaction_data={
                "workflow_id": first_result.workflow_id,
                "user_question": "What should I look for in a property disclosure?",
                "response": first_result.results.get("response", ""),
                "session_id": session_id
            },
            memory_type=MemoryType.CONVERSATION,
            scope=MemoryScope.SESSION
        )

        # Second interaction - should reference previous context
        second_request = WorkflowRequest(
            workflow_id=str(uuid.uuid4()),
            primary_agent=AgentRole.HELP,
            task_description="Follow up on previous disclosure question",
            context={
                "user_question": "Can you give me specific examples of red flags?",
                "session_id": session_id,
                "previous_workflow_id": first_result.workflow_id
            },
            model_preference="qwen/qwen3-235b-a22b-thinking-2507"
        )

        second_result = await orchestrator.execute_workflow(second_request)
        assert second_result.status == WorkflowStatus.COMPLETED

        # Response should be contextually aware
        response = second_result.results.get("response", "")
        assert len(response) > 50  # Should be detailed
        # Should reference disclosure context from previous interaction
        assert "disclosure" in response.lower() or "property" in response.lower()

    @pytest.mark.asyncio
    async def test_workflow_error_recovery(self, orchestrator):
        """Test workflow error handling and recovery mechanisms."""
        # Create a request that might cause issues
        problematic_request = WorkflowRequest(
            workflow_id=str(uuid.uuid4()),
            primary_agent=AgentRole.DATA_EXTRACTION,
            task_description="Extract data from malformed document",
            context={
                "document_content": "This is not a valid property document...",
                "extraction_fields": ["nonexistent_field", "invalid_data"]
            },
            model_preference="qwen/qwen3-235b-a22b-thinking-2507"
        )

        result = await orchestrator.execute_workflow(problematic_request)

        # Should handle gracefully
        assert result is not None
        # May complete with warnings or partial results
        assert result.status in [WorkflowStatus.COMPLETED, WorkflowStatus.COMPLETED_WITH_WARNINGS]
        
        if result.errors:
            assert len(result.errors) > 0
            # Should have meaningful error messages
            assert any("document" in error.lower() for error in result.errors)

    @pytest.mark.asyncio
    async def test_workflow_performance_metrics(self, orchestrator):
        """Test that workflow performance metrics are properly tracked."""
        start_time = datetime.utcnow()
        
        workflow_request = WorkflowRequest(
            workflow_id=str(uuid.uuid4()),
            primary_agent=AgentRole.SUMMARY,
            task_description="Summarize a simple property transaction",
            context={
                "content_to_summarize": "Property at 123 Test St sold for $300,000 to buyer John Doe.",
                "summary_type": "brief"
            },
            model_preference="qwen/qwen3-235b-a22b-thinking-2507"
        )

        result = await orchestrator.execute_workflow(workflow_request)
        end_time = datetime.utcnow()

        assert result.status == WorkflowStatus.COMPLETED
        assert result.execution_time > 0
        assert result.execution_time < (end_time - start_time).total_seconds() + 1  # Allow small buffer
        assert result.cost > 0
        assert len(result.agent_interactions) > 0

        # Check interaction details
        interaction = result.agent_interactions[0]
        assert "model_used" in interaction
        assert "processing_time" in interaction
        assert interaction["model_used"] == "qwen/qwen3-235b-a22b-thinking-2507"
