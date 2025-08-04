"""
Tests for Agent Tools.

This module contains comprehensive tests for all agent tools including
data extraction, contract generation, compliance checking, and more.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from app.services.agent_tools import (
    DocumentParsingTool,
    EntityRecognitionTool,
    ConfidenceScoringTool,
    TemplateFillTool,
    ClauseGenerationTool,
    ComplianceValidationTool,
    SignatureTrackingTool,
    DocumentSummarizationTool,
    ContextualQATool,
    ToolCategory,
    ToolResult,
    get_tools_for_agent,
    tool_registry
)
from app.services.agent_tools.base import ToolInput


class TestDocumentParsingTool:
    """Test cases for DocumentParsingTool."""
    
    @pytest.fixture
    def document_parsing_tool(self):
        """Create DocumentParsingTool instance for testing."""
        return DocumentParsingTool()
    
    def test_tool_properties(self, document_parsing_tool):
        """Test tool properties."""
        assert document_parsing_tool.name == "document_parser"
        assert document_parsing_tool.category == ToolCategory.DOCUMENT_PROCESSING
        assert "parse documents" in document_parsing_tool.description.lower()
    
    @pytest.mark.asyncio
    async def test_document_parsing_execution(self, document_parsing_tool):
        """Test document parsing execution."""
        from app.services.agent_tools.data_extraction import DocumentParsingInput
        
        input_data = DocumentParsingInput(
            document_id="test_doc_123",
            document_type="pdf",
            user_id="test_user"
        )
        
        result = await document_parsing_tool.safe_execute(input_data)
        
        assert isinstance(result, ToolResult)
        assert result.success is True
        assert result.tool_name == "document_parser"
        assert "document_id" in result.data
        assert "text_content" in result.data


class TestEntityRecognitionTool:
    """Test cases for EntityRecognitionTool."""
    
    @pytest.fixture
    def entity_recognition_tool(self):
        """Create EntityRecognitionTool instance for testing."""
        return EntityRecognitionTool()
    
    @pytest.mark.asyncio
    async def test_entity_recognition_execution(self, entity_recognition_tool):
        """Test entity recognition execution."""
        from app.services.agent_tools.data_extraction import EntityRecognitionInput
        
        input_data = EntityRecognitionInput(
            text_content="This is a purchase agreement between John Doe (buyer) and Jane Smith (seller) for $250,000.",
            document_type="contract",
            user_id="test_user"
        )
        
        result = await entity_recognition_tool.safe_execute(input_data)
        
        assert result.success is True
        assert "entities" in result.data
        assert "entity_count" in result.data
        assert isinstance(result.data["entities"], dict)


class TestTemplateFillTool:
    """Test cases for TemplateFillTool."""
    
    @pytest.fixture
    def template_fill_tool(self):
        """Create TemplateFillTool instance for testing."""
        return TemplateFillTool()
    
    @pytest.mark.asyncio
    async def test_template_filling_execution(self, template_fill_tool):
        """Test template filling execution."""
        from app.services.agent_tools.contract_generation import TemplateFillInput
        
        extracted_data = {
            "parties": [
                {"name": "John Doe", "role": "buyer"},
                {"name": "Jane Smith", "role": "seller"}
            ],
            "financial_terms": [
                {"value": "$250,000", "type": "purchase_price"}
            ],
            "addresses": [
                {"value": "123 Main St, Anytown, ST 12345"}
            ]
        }
        
        input_data = TemplateFillInput(
            template_id="residential_purchase_template",
            extracted_data=extracted_data,
            user_id="test_user"
        )
        
        result = await template_fill_tool.safe_execute(input_data)
        
        assert result.success is True
        assert "filled_template" in result.data
        assert "variable_mapping" in result.data
        assert "fill_percentage" in result.data


class TestComplianceValidationTool:
    """Test cases for ComplianceValidationTool."""
    
    @pytest.fixture
    def compliance_tool(self):
        """Create ComplianceValidationTool instance for testing."""
        return ComplianceValidationTool()
    
    @pytest.mark.asyncio
    async def test_compliance_validation_execution(self, compliance_tool):
        """Test compliance validation execution."""
        from app.services.agent_tools.compliance_checking import ComplianceCheckInput
        
        contract_content = """
        REAL ESTATE PURCHASE AGREEMENT
        
        This agreement is between John Doe (Buyer) and Jane Smith (Seller)
        for the purchase of property located at 123 Main St.
        
        Purchase Price: $250,000
        
        Buyer and Seller signatures required below.
        """
        
        input_data = ComplianceCheckInput(
            contract_content=contract_content,
            contract_type="residential_purchase",
            jurisdiction="default",
            user_id="test_user"
        )
        
        result = await compliance_tool.safe_execute(input_data)
        
        assert result.success is True
        assert "compliance_score" in result.data
        assert "validation_results" in result.data
        assert "recommendations" in result.data


class TestSignatureTrackingTool:
    """Test cases for SignatureTrackingTool."""
    
    @pytest.fixture
    def signature_tool(self):
        """Create SignatureTrackingTool instance for testing."""
        return SignatureTrackingTool()
    
    @pytest.mark.asyncio
    async def test_signature_tracking_execution(self, signature_tool):
        """Test signature tracking execution."""
        from app.services.agent_tools.signature_tracking import SignatureTrackingInput
        
        signers = [
            {"id": "signer1", "name": "John Doe", "email": "john@example.com", "role": "buyer"},
            {"id": "signer2", "name": "Jane Smith", "email": "jane@example.com", "role": "seller"}
        ]
        
        input_data = SignatureTrackingInput(
            contract_id="contract_123",
            signers=signers,
            user_id="test_user"
        )
        
        result = await signature_tool.safe_execute(input_data)
        
        assert result.success is True
        assert "current_status" in result.data
        assert "workflow_progress" in result.data
        assert "next_actions" in result.data


class TestDocumentSummarizationTool:
    """Test cases for DocumentSummarizationTool."""
    
    @pytest.fixture
    def summarization_tool(self):
        """Create DocumentSummarizationTool instance for testing."""
        return DocumentSummarizationTool()
    
    @pytest.mark.asyncio
    async def test_document_summarization_execution(self, summarization_tool):
        """Test document summarization execution."""
        from app.services.agent_tools.summarization import DocumentSummarizationInput
        
        document_content = """
        REAL ESTATE PURCHASE AGREEMENT
        
        PARTIES: This agreement is between John Doe, a single individual (Buyer) 
        and Jane Smith, a married woman (Seller).
        
        PROPERTY: The property is located at 123 Main Street, Anytown, State 12345.
        The property is a single-family residence with 3 bedrooms and 2 bathrooms.
        
        PURCHASE PRICE: The total purchase price is Two Hundred Fifty Thousand 
        Dollars ($250,000).
        
        FINANCING: Buyer's obligation is contingent upon obtaining financing 
        in the amount of $200,000 at an interest rate not to exceed 6.5% per annum.
        
        CLOSING: Closing shall occur on or before December 31, 2024.
        """
        
        input_data = DocumentSummarizationInput(
            document_content=document_content,
            summary_type="comprehensive",
            user_id="test_user"
        )
        
        result = await summarization_tool.safe_execute(input_data)
        
        assert result.success is True
        assert "summary" in result.data
        assert "key_points" in result.data
        assert "action_items" in result.data
        assert "metrics" in result.data


class TestContextualQATool:
    """Test cases for ContextualQATool."""
    
    @pytest.fixture
    def qa_tool(self):
        """Create ContextualQATool instance for testing."""
        return ContextualQATool()
    
    @pytest.mark.asyncio
    async def test_contextual_qa_execution(self, qa_tool):
        """Test contextual Q&A execution."""
        from app.services.agent_tools.help_assistance import ContextualQAInput
        
        context_data = {
            "contract_id": "contract_123",
            "workflow_step": "compliance_check",
            "user_role": "buyer"
        }
        
        input_data = ContextualQAInput(
            question="What is a contingency clause?",
            context_data=context_data,
            user_id="test_user"
        )
        
        result = await qa_tool.safe_execute(input_data)
        
        assert result.success is True
        assert "answer" in result.data
        assert "question_analysis" in result.data
        assert "follow_up_suggestions" in result.data


class TestToolRegistry:
    """Test cases for the tool registry system."""
    
    def test_tool_registration(self):
        """Test that tools are properly registered."""
        tools = tool_registry.list_tools()
        assert len(tools) > 0
        
        # Check that we have tools from each category
        tool_names = [tool["name"] for tool in tools]
        
        # Data extraction tools
        assert "document_parser" in tool_names
        assert "entity_recognizer" in tool_names
        assert "confidence_scorer" in tool_names
        
        # Contract generation tools
        assert "template_filler" in tool_names
        assert "clause_generator" in tool_names
        assert "document_generator" in tool_names
        
        # Compliance tools
        assert "compliance_validator" in tool_names
        
        # Signature tracking tools
        assert "signature_tracker" in tool_names
        
        # Summarization tools
        assert "document_summarizer" in tool_names
        
        # Help tools
        assert "contextual_qa" in tool_names
    
    def test_get_tools_for_agent(self):
        """Test getting tools for specific agent roles."""
        # Data extraction agent tools
        data_tools = get_tools_for_agent("data_extraction")
        assert len(data_tools) == 3
        tool_names = [tool.name for tool in data_tools]
        assert "document_parser" in tool_names
        assert "entity_recognizer" in tool_names
        assert "confidence_scorer" in tool_names
        
        # Contract generator agent tools
        contract_tools = get_tools_for_agent("contract_generator")
        assert len(contract_tools) == 3
        tool_names = [tool.name for tool in contract_tools]
        assert "template_filler" in tool_names
        assert "clause_generator" in tool_names
        assert "document_generator" in tool_names
        
        # Help agent tools
        help_tools = get_tools_for_agent("help_agent")
        assert len(help_tools) == 3
        tool_names = [tool.name for tool in help_tools]
        assert "contextual_qa" in tool_names
        assert "workflow_guide" in tool_names
        assert "clause_explainer" in tool_names
    
    def test_get_tools_by_category(self):
        """Test getting tools by category."""
        from app.services.agent_tools import get_tools_by_category
        
        # Data extraction category
        data_tools = get_tools_by_category(ToolCategory.DATA_EXTRACTION)
        assert len(data_tools) >= 2  # At least entity recognizer and confidence scorer
        
        # Document processing category
        doc_tools = get_tools_by_category(ToolCategory.DOCUMENT_PROCESSING)
        assert len(doc_tools) >= 1  # At least document parser
        
        # Contract generation category
        contract_tools = get_tools_by_category(ToolCategory.CONTRACT_GENERATION)
        assert len(contract_tools) >= 3  # Template filler, clause generator, document generator


class TestToolIntegration:
    """Integration tests for tool system."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_data_extraction_workflow(self):
        """Test complete data extraction workflow."""
        # Step 1: Parse document
        doc_parser = DocumentParsingTool()
        from app.services.agent_tools.data_extraction import DocumentParsingInput
        
        parse_input = DocumentParsingInput(
            document_id="test_doc",
            document_type="pdf",
            user_id="test_user"
        )
        
        parse_result = await doc_parser.safe_execute(parse_input)
        assert parse_result.success
        
        # Step 2: Extract entities
        entity_tool = EntityRecognitionTool()
        from app.services.agent_tools.data_extraction import EntityRecognitionInput
        
        entity_input = EntityRecognitionInput(
            text_content=parse_result.data["text_content"],
            document_type="contract",
            user_id="test_user"
        )
        
        entity_result = await entity_tool.safe_execute(entity_input)
        assert entity_result.success
        
        # Step 3: Score confidence
        confidence_tool = ConfidenceScoringTool()
        from app.services.agent_tools.data_extraction import ConfidenceScoringInput
        
        confidence_input = ConfidenceScoringInput(
            extracted_entities=entity_result.data["entities"],
            validation_results=entity_result.data["validation_results"],
            user_id="test_user"
        )
        
        confidence_result = await confidence_tool.safe_execute(confidence_input)
        assert confidence_result.success
        assert "overall_confidence" in confidence_result.data
    
    @pytest.mark.asyncio
    async def test_contract_generation_workflow(self):
        """Test contract generation workflow."""
        # Step 1: Fill template
        template_tool = TemplateFillTool()
        from app.services.agent_tools.contract_generation import TemplateFillInput
        
        extracted_data = {
            "parties": [{"name": "John Doe", "role": "buyer"}],
            "financial_terms": [{"value": "$250,000"}]
        }
        
        fill_input = TemplateFillInput(
            template_id="test_template",
            extracted_data=extracted_data,
            user_id="test_user"
        )
        
        fill_result = await template_tool.safe_execute(fill_input)
        assert fill_result.success
        
        # Step 2: Generate document
        doc_gen_tool = DocumentGenerationTool()
        from app.services.agent_tools.contract_generation import DocumentGenerationInput
        
        doc_input = DocumentGenerationInput(
            filled_template=fill_result.data["filled_template"],
            output_format="docx",
            user_id="test_user"
        )
        
        doc_result = await doc_gen_tool.safe_execute(doc_input)
        assert doc_result.success
        assert "document_id" in doc_result.data
