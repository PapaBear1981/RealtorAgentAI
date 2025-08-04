"""
Integration Tests for Agent System.

This module contains comprehensive integration tests for the complete agent system
including database access, file operations, template processing, and agent collaboration.
"""

import pytest
import asyncio
import tempfile
import os
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from app.services.agent_tools import (
    ContractDatabaseTool,
    TemplateDatabaseTool,
    FileDatabaseTool,
    FileReadTool,
    FileWriteTool,
    FileProcessingTool,
    TemplateAnalysisTool,
    TemplateRenderingTool,
    CacheTool,
    PerformanceMonitorTool,
    get_tools_for_agent,
    tool_registry
)
from app.services.agent_tools.database_access import DatabaseQueryInput
from app.services.agent_tools.file_operations import FileReadInput, FileWriteInput, FileProcessingInput
from app.services.agent_tools.template_processing import TemplateAnalysisInput, TemplateRenderingInput
from app.services.agent_tools.performance_optimization import CacheInput, PerformanceMonitorInput
from app.services.agent_memory import get_memory_manager
from app.services.agent_orchestrator import get_agent_orchestrator, AgentRole


class TestDatabaseAccessIntegration:
    """Integration tests for database access tools."""
    
    @pytest.fixture
    def contract_db_tool(self):
        """Create ContractDatabaseTool instance for testing."""
        return ContractDatabaseTool()
    
    @pytest.fixture
    def template_db_tool(self):
        """Create TemplateDatabaseTool instance for testing."""
        return TemplateDatabaseTool()
    
    @pytest.mark.asyncio
    async def test_contract_database_operations(self, contract_db_tool):
        """Test contract database operations."""
        # Test query operation
        query_input = DatabaseQueryInput(
            model_type="contract",
            query_params={"operation": "query"},
            filters={"status": "draft"},
            user_id="test_user"
        )
        
        with patch('app.services.agent_tools.database_access.get_db') as mock_db:
            mock_session = Mock()
            mock_db.return_value.__next__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.order_by.return_value.count.return_value = 5
            mock_session.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
            
            result = await contract_db_tool.safe_execute(query_input)
            
            assert result.success is True
            assert "contracts" in result.data
            assert "total_count" in result.data
    
    @pytest.mark.asyncio
    async def test_template_database_search(self, template_db_tool):
        """Test template database search functionality."""
        search_input = DatabaseQueryInput(
            model_type="template",
            query_params={"operation": "search", "search_term": "real estate"},
            user_id="test_user"
        )
        
        with patch('app.services.agent_tools.database_access.get_db') as mock_db:
            mock_session = Mock()
            mock_db.return_value.__next__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.limit.return_value.all.return_value = []
            
            result = await template_db_tool.safe_execute(search_input)
            
            assert result.success is True
            assert "templates" in result.data
            assert "search_term" in result.data


class TestFileOperationsIntegration:
    """Integration tests for file operations tools."""
    
    @pytest.fixture
    def file_read_tool(self):
        """Create FileReadTool instance for testing."""
        return FileReadTool()
    
    @pytest.fixture
    def file_write_tool(self):
        """Create FileWriteTool instance for testing."""
        return FileWriteTool()
    
    @pytest.fixture
    def file_processing_tool(self):
        """Create FileProcessingTool instance for testing."""
        return FileProcessingTool()
    
    @pytest.fixture
    def temp_file(self):
        """Create temporary file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("This is a test file for agent integration testing.\nIt contains multiple lines.\nAnd some test content.")
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_file_read_write_cycle(self, file_read_tool, file_write_tool, temp_file):
        """Test complete file read/write cycle."""
        # Read the temporary file
        read_input = FileReadInput(
            file_path=temp_file,
            read_mode="text",
            user_id="test_user"
        )
        
        read_result = await file_read_tool.safe_execute(read_input)
        assert read_result.success is True
        assert "content" in read_result.data
        
        original_content = read_result.data["content"]
        
        # Write modified content to new file
        new_content = original_content + "\nAdded by integration test."
        new_file_path = temp_file + ".new"
        
        write_input = FileWriteInput(
            file_path=new_file_path,
            content=new_content,
            write_mode="text",
            user_id="test_user"
        )
        
        write_result = await file_write_tool.safe_execute(write_input)
        assert write_result.success is True
        
        # Read back the new file to verify
        read_new_input = FileReadInput(
            file_path=new_file_path,
            read_mode="text",
            user_id="test_user"
        )
        
        read_new_result = await file_read_tool.safe_execute(read_new_input)
        assert read_new_result.success is True
        assert read_new_result.data["content"] == new_content
        
        # Cleanup
        if os.path.exists(new_file_path):
            os.unlink(new_file_path)
    
    @pytest.mark.asyncio
    async def test_file_processing_analysis(self, file_processing_tool, temp_file):
        """Test file processing and analysis."""
        processing_input = FileProcessingInput(
            file_path=temp_file,
            operation="analyze",
            user_id="test_user"
        )
        
        result = await file_processing_tool.safe_execute(processing_input)
        
        assert result.success is True
        assert "file_path" in result.data
        assert "file_size" in result.data
        assert "content_analysis" in result.data
        assert "checksum" in result.data


class TestTemplateProcessingIntegration:
    """Integration tests for template processing tools."""
    
    @pytest.fixture
    def template_analysis_tool(self):
        """Create TemplateAnalysisTool instance for testing."""
        return TemplateAnalysisTool()
    
    @pytest.fixture
    def template_rendering_tool(self):
        """Create TemplateRenderingTool instance for testing."""
        return TemplateRenderingTool()
    
    @pytest.fixture
    def sample_template(self):
        """Sample template for testing."""
        return """
        REAL ESTATE PURCHASE AGREEMENT
        
        This agreement is between {{buyer_name}} (Buyer) and {{seller_name}} (Seller)
        for the purchase of the property located at {{property_address}}.
        
        Purchase Price: {{purchase_price}}
        {% if down_payment %}
        Down Payment: {{down_payment}}
        {% endif %}
        
        {% for contingency in contingencies %}
        - {{contingency}}
        {% endfor %}
        """
    
    @pytest.mark.asyncio
    async def test_template_analysis_and_rendering(self, template_analysis_tool, template_rendering_tool, sample_template):
        """Test complete template analysis and rendering workflow."""
        # Analyze template
        analysis_input = TemplateAnalysisInput(
            template_content=sample_template,
            analysis_type="comprehensive",
            user_id="test_user"
        )
        
        analysis_result = await template_analysis_tool.safe_execute(analysis_input)
        
        assert analysis_result.success is True
        assert "variables" in analysis_result.data
        assert "structure" in analysis_result.data
        assert "complexity" in analysis_result.data
        
        # Extract variables from analysis
        variables = analysis_result.data["variables"]["variables"]
        assert "buyer_name" in variables
        assert "seller_name" in variables
        assert "property_address" in variables
        assert "purchase_price" in variables
        
        # Render template with variables
        template_variables = {
            "buyer_name": "John Doe",
            "seller_name": "Jane Smith",
            "property_address": "123 Main Street, Anytown, ST 12345",
            "purchase_price": "$250,000",
            "down_payment": "$50,000",
            "contingencies": ["Financing contingency", "Inspection contingency"]
        }
        
        rendering_input = TemplateRenderingInput(
            template_content=sample_template,
            variables=template_variables,
            user_id="test_user"
        )
        
        rendering_result = await template_rendering_tool.safe_execute(rendering_input)
        
        assert rendering_result.success is True
        assert "rendered_content" in rendering_result.data
        assert "validation_result" in rendering_result.data
        
        rendered_content = rendering_result.data["rendered_content"]
        assert "John Doe" in rendered_content
        assert "Jane Smith" in rendered_content
        assert "$250,000" in rendered_content
        assert "Financing contingency" in rendered_content


class TestPerformanceOptimizationIntegration:
    """Integration tests for performance optimization tools."""
    
    @pytest.fixture
    def cache_tool(self):
        """Create CacheTool instance for testing."""
        return CacheTool()
    
    @pytest.fixture
    def performance_monitor_tool(self):
        """Create PerformanceMonitorTool instance for testing."""
        return PerformanceMonitorTool()
    
    @pytest.mark.asyncio
    async def test_cache_operations(self, cache_tool):
        """Test cache operations."""
        # Set cache value
        set_input = CacheInput(
            operation="set",
            key="test_key",
            value={"data": "test_value", "timestamp": datetime.utcnow().isoformat()},
            ttl=300,
            user_id="test_user"
        )
        
        set_result = await cache_tool.safe_execute(set_input)
        assert set_result.success is True
        assert set_result.data["success"] is True
        
        # Get cache value
        get_input = CacheInput(
            operation="get",
            key="test_key",
            user_id="test_user"
        )
        
        get_result = await cache_tool.safe_execute(get_input)
        assert get_result.success is True
        assert get_result.data["found"] is True
        assert get_result.data["value"]["data"] == "test_value"
        
        # Get cache stats
        stats_input = CacheInput(
            operation="stats",
            key="",
            user_id="test_user"
        )
        
        stats_result = await cache_tool.safe_execute(stats_input)
        assert stats_result.success is True
        assert "stats" in stats_result.data
        assert stats_result.data["stats"]["cache_size"] > 0
    
    @pytest.mark.asyncio
    async def test_performance_monitoring(self, performance_monitor_tool):
        """Test performance monitoring."""
        # Start timer
        start_input = PerformanceMonitorInput(
            operation="start",
            metric_name="test_operation",
            metadata={"test": "data"},
            user_id="test_user"
        )
        
        start_result = await performance_monitor_tool.safe_execute(start_input)
        assert start_result.success is True
        timer_id = start_result.data["timer_id"]
        
        # Simulate some work
        await asyncio.sleep(0.1)
        
        # Stop timer
        stop_input = PerformanceMonitorInput(
            operation="stop",
            metric_name="test_operation",
            metadata={"timer_id": timer_id},
            user_id="test_user"
        )
        
        stop_result = await performance_monitor_tool.safe_execute(stop_input)
        assert stop_result.success is True
        assert stop_result.data["duration"] > 0
        
        # Get performance report
        report_input = PerformanceMonitorInput(
            operation="report",
            metric_name="test_operation",
            user_id="test_user"
        )
        
        report_result = await performance_monitor_tool.safe_execute(report_input)
        assert report_result.success is True
        assert "metrics" in report_result.data
        assert report_result.data["metrics"]["count"] > 0


class TestAgentCollaborationIntegration:
    """Integration tests for agent collaboration features."""
    
    @pytest.mark.asyncio
    async def test_agent_memory_collaboration(self):
        """Test agent memory collaboration features."""
        memory_manager = get_memory_manager()
        
        # Test workflow state sharing
        workflow_id = "test_workflow_123"
        workflow_state = {
            "current_step": "data_extraction",
            "progress": 0.3,
            "extracted_data": {"parties": ["John Doe", "Jane Smith"]}
        }
        
        success = await memory_manager.set_workflow_state(workflow_id, workflow_state)
        assert success is True
        
        retrieved_state = await memory_manager.get_workflow_state(workflow_id)
        assert retrieved_state is not None
        assert retrieved_state["current_step"] == "data_extraction"
        assert retrieved_state["progress"] == 0.3
        
        # Test agent data sharing
        agent_id = "data_extraction_agent"
        data_key = "extracted_entities"
        shared_data = {
            "entities": ["buyer", "seller", "property"],
            "confidence": 0.95
        }
        
        success = await memory_manager.share_agent_data(agent_id, data_key, shared_data)
        assert success is True
        
        retrieved_data = await memory_manager.get_agent_data(agent_id, data_key)
        assert retrieved_data is not None
        assert retrieved_data["confidence"] == 0.95
        
        # Test performance metrics
        success = await memory_manager.record_performance_metric("extraction_time", 2.5, {"entities": 3})
        assert success is True
        
        metrics = await memory_manager.get_performance_metrics("extraction_time")
        assert len(metrics) > 0
        assert metrics[0]["value"] == 2.5
        
        # Test collaboration summary
        summary = await memory_manager.get_collaboration_summary(workflow_id)
        assert "workflow_states" in summary
        assert "active_agents" in summary
        assert summary["workflow_specific"]["workflow_id"] == workflow_id


class TestEndToEndWorkflow:
    """End-to-end integration tests for complete agent workflows."""
    
    @pytest.mark.asyncio
    async def test_complete_contract_processing_workflow(self):
        """Test complete contract processing workflow using multiple agents and tools."""
        # This test simulates a complete workflow from document upload to contract generation
        
        # Step 1: File processing (simulating document upload)
        file_processor = FileProcessingTool()
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("Purchase Agreement between John Doe and Jane Smith for property at 123 Main St. Price: $250,000")
            temp_file = f.name
        
        try:
            # Extract text from document
            extract_input = FileProcessingInput(
                file_path=temp_file,
                operation="extract_text",
                user_id="test_user"
            )
            
            extract_result = await file_processor.safe_execute(extract_input)
            assert extract_result.success is True
            
            extracted_text = extract_result.data["extracted_text"]
            
            # Step 2: Template analysis and rendering
            template_analyzer = TemplateAnalysisTool()
            template_renderer = TemplateRenderingTool()
            
            # Analyze a contract template
            template_content = """
            PURCHASE AGREEMENT
            
            Buyer: {{buyer_name}}
            Seller: {{seller_name}}
            Property: {{property_address}}
            Price: {{purchase_price}}
            """
            
            analysis_input = TemplateAnalysisInput(
                template_content=template_content,
                user_id="test_user"
            )
            
            analysis_result = await template_analyzer.safe_execute(analysis_input)
            assert analysis_result.success is True
            
            # Render template with extracted data
            variables = {
                "buyer_name": "John Doe",
                "seller_name": "Jane Smith", 
                "property_address": "123 Main St",
                "purchase_price": "$250,000"
            }
            
            render_input = TemplateRenderingInput(
                template_content=template_content,
                variables=variables,
                user_id="test_user"
            )
            
            render_result = await template_renderer.safe_execute(render_input)
            assert render_result.success is True
            
            rendered_content = render_result.data["rendered_content"]
            assert "John Doe" in rendered_content
            assert "$250,000" in rendered_content
            
            # Step 3: Performance monitoring
            cache_tool = CacheTool()
            
            # Cache the rendered contract
            cache_input = CacheInput(
                operation="set",
                key="contract_123",
                value={"content": rendered_content, "status": "generated"},
                ttl=3600,
                user_id="test_user"
            )
            
            cache_result = await cache_tool.safe_execute(cache_input)
            assert cache_result.success is True
            
            # Verify workflow completed successfully
            assert extract_result.success
            assert analysis_result.success
            assert render_result.success
            assert cache_result.success
            
        finally:
            # Cleanup
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    @pytest.mark.asyncio
    async def test_tool_registry_integration(self):
        """Test tool registry integration with agent roles."""
        # Test that tools are properly assigned to agent roles
        data_extraction_tools = get_tools_for_agent("data_extraction")
        assert len(data_extraction_tools) >= 3
        
        contract_generator_tools = get_tools_for_agent("contract_generator")
        assert len(contract_generator_tools) >= 3
        
        # Test that new tools are included
        all_tools = tool_registry.list_tools()
        tool_names = [tool["name"] for tool in all_tools]
        
        # Check for new database access tools
        assert "contract_db_access" in tool_names
        assert "template_db_access" in tool_names
        assert "file_db_access" in tool_names
        
        # Check for new file operation tools
        assert "file_reader" in tool_names
        assert "file_writer" in tool_names
        assert "file_processor" in tool_names
        
        # Check for new template processing tools
        assert "template_analyzer" in tool_names
        assert "template_renderer" in tool_names
