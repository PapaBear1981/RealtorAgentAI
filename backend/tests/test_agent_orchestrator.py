"""
Tests for the Agent Orchestrator Service.

This module contains comprehensive tests for the CrewAI-based agent orchestrator
including workflow management, agent creation, and memory system integration.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from app.services.agent_orchestrator import (
    AgentOrchestrator,
    AgentRole,
    TaskPriority,
    WorkflowTask,
    WorkflowStatus,
    ModelRouterLLM,
    get_agent_orchestrator
)
from app.services.agent_memory import MemoryType, MemoryScope


class TestModelRouterLLM:
    """Test cases for the ModelRouterLLM class."""
    
    @pytest.fixture
    def mock_model_router(self):
        """Mock model router for testing."""
        router = Mock()
        router.generate_response = AsyncMock()
        return router
    
    @pytest.fixture
    def model_router_llm(self, mock_model_router):
        """Create ModelRouterLLM instance for testing."""
        with patch('app.services.agent_orchestrator.get_model_router', return_value=mock_model_router):
            return ModelRouterLLM(model_preference="test-model")
    
    def test_model_router_llm_initialization(self, model_router_llm):
        """Test that ModelRouterLLM initializes correctly."""
        assert model_router_llm.model_preference == "test-model"
        assert model_router_llm.model_router is not None
    
    def test_model_router_llm_call(self, model_router_llm, mock_model_router):
        """Test synchronous call to model router."""
        # Mock response
        mock_response = Mock()
        mock_response.content = "Test response"
        mock_response.model_used = "test-model"
        mock_response.provider.value = "openrouter"
        mock_response.cost = 0.001
        mock_response.processing_time = 1.5
        
        mock_model_router.generate_response.return_value = mock_response
        
        messages = [{"role": "user", "content": "Hello"}]
        result = model_router_llm.call(messages)
        
        assert result == "Test response"
        mock_model_router.generate_response.assert_called_once()


class TestAgentOrchestrator:
    """Test cases for the AgentOrchestrator class."""
    
    @pytest.fixture
    def mock_model_router(self):
        """Mock model router for testing."""
        router = Mock()
        router.models = {"test-model": Mock()}
        router.strategy.value = "cost_optimized"
        return router
    
    @pytest.fixture
    def mock_memory_manager(self):
        """Mock memory manager for testing."""
        manager = Mock()
        manager.store_memory = AsyncMock()
        manager.retrieve_memory = AsyncMock()
        manager.search_memories = AsyncMock()
        manager.get_memory_stats = AsyncMock(return_value={"total_entries": 0})
        return manager
    
    @pytest.fixture
    def orchestrator(self, mock_model_router, mock_memory_manager):
        """Create AgentOrchestrator instance for testing."""
        with patch('app.services.agent_orchestrator.get_model_router', return_value=mock_model_router), \
             patch('app.services.agent_orchestrator.AgentMemoryManager', return_value=mock_memory_manager):
            return AgentOrchestrator()
    
    def test_orchestrator_initialization(self, orchestrator):
        """Test that AgentOrchestrator initializes correctly."""
        assert len(orchestrator.agent_configs) == 6
        assert AgentRole.DATA_EXTRACTION in orchestrator.agent_configs
        assert AgentRole.CONTRACT_GENERATOR in orchestrator.agent_configs
        assert AgentRole.COMPLIANCE_CHECKER in orchestrator.agent_configs
        assert AgentRole.SIGNATURE_TRACKER in orchestrator.agent_configs
        assert AgentRole.SUMMARY_AGENT in orchestrator.agent_configs
        assert AgentRole.HELP_AGENT in orchestrator.agent_configs
    
    def test_agent_config_properties(self, orchestrator):
        """Test that agent configurations have correct properties."""
        data_extraction_config = orchestrator.agent_configs[AgentRole.DATA_EXTRACTION]
        
        assert data_extraction_config.role == AgentRole.DATA_EXTRACTION
        assert "extract" in data_extraction_config.goal.lower()
        assert "data extraction specialist" in data_extraction_config.backstory.lower()
        assert data_extraction_config.allow_delegation is False
        
        contract_generator_config = orchestrator.agent_configs[AgentRole.CONTRACT_GENERATOR]
        assert contract_generator_config.allow_delegation is True
    
    @patch('app.services.agent_orchestrator.Agent')
    def test_create_agent(self, mock_agent_class, orchestrator):
        """Test agent creation."""
        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent
        
        agent = orchestrator.create_agent(AgentRole.DATA_EXTRACTION, "test-model")
        
        assert agent == mock_agent
        assert AgentRole.DATA_EXTRACTION in orchestrator.agents
        mock_agent_class.assert_called_once()
    
    def test_get_agent(self, orchestrator):
        """Test getting an existing agent."""
        # Initially no agents
        agent = orchestrator.get_agent(AgentRole.DATA_EXTRACTION)
        assert agent is None
        
        # Add mock agent
        mock_agent = Mock()
        orchestrator.agents[AgentRole.DATA_EXTRACTION] = mock_agent
        
        agent = orchestrator.get_agent(AgentRole.DATA_EXTRACTION)
        assert agent == mock_agent
    
    @patch('app.services.agent_orchestrator.Agent')
    def test_get_or_create_agent(self, mock_agent_class, orchestrator):
        """Test getting or creating an agent."""
        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent
        
        # First call should create agent
        agent1 = orchestrator.get_or_create_agent(AgentRole.DATA_EXTRACTION)
        assert agent1 == mock_agent
        
        # Second call should return existing agent
        agent2 = orchestrator.get_or_create_agent(AgentRole.DATA_EXTRACTION)
        assert agent2 == mock_agent
        assert agent1 is agent2
        
        # Should only create once
        mock_agent_class.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_workflow(self, orchestrator, mock_memory_manager):
        """Test workflow creation."""
        tasks = [
            WorkflowTask(
                id="task1",
                description="Test task 1",
                expected_output="Output 1",
                agent_role=AgentRole.DATA_EXTRACTION
            ),
            WorkflowTask(
                id="task2",
                description="Test task 2",
                expected_output="Output 2",
                agent_role=AgentRole.CONTRACT_GENERATOR
            )
        ]
        
        with patch('app.services.agent_orchestrator.Crew') as mock_crew_class, \
             patch.object(orchestrator, 'get_or_create_agent') as mock_get_agent:
            
            mock_agent = Mock()
            mock_get_agent.return_value = mock_agent
            mock_crew = Mock()
            mock_crew_class.return_value = mock_crew
            
            workflow_id = await orchestrator.create_workflow(tasks, user_id="test-user")
            
            assert workflow_id is not None
            assert workflow_id in orchestrator.active_workflows
            
            # Verify memory storage calls
            assert mock_memory_manager.store_memory.call_count >= 3  # Workflow + 2 tasks
    
    @pytest.mark.asyncio
    async def test_execute_workflow(self, orchestrator, mock_memory_manager):
        """Test workflow execution."""
        workflow_id = "test-workflow"
        
        # Mock crew
        mock_crew = Mock()
        mock_crew.kickoff.return_value = "Workflow completed successfully"
        orchestrator.active_workflows[workflow_id] = mock_crew
        
        result = await orchestrator.execute_workflow(workflow_id)
        
        assert result.workflow_id == workflow_id
        assert result.status == WorkflowStatus.COMPLETED
        assert "Workflow completed successfully" in result.results["output"]
        assert result.execution_time > 0
        assert workflow_id not in orchestrator.active_workflows
        assert workflow_id in orchestrator.workflow_results
    
    @pytest.mark.asyncio
    async def test_execute_workflow_failure(self, orchestrator):
        """Test workflow execution failure handling."""
        workflow_id = "test-workflow"
        
        # Mock crew that raises exception
        mock_crew = Mock()
        mock_crew.kickoff.side_effect = Exception("Test error")
        orchestrator.active_workflows[workflow_id] = mock_crew
        
        with pytest.raises(Exception, match="Test error"):
            await orchestrator.execute_workflow(workflow_id)
        
        # Verify cleanup
        assert workflow_id not in orchestrator.active_workflows
        assert workflow_id in orchestrator.workflow_results
        
        result = orchestrator.workflow_results[workflow_id]
        assert result.status == WorkflowStatus.FAILED
        assert "Test error" in result.errors
    
    @pytest.mark.asyncio
    async def test_get_workflow_status(self, orchestrator):
        """Test getting workflow status."""
        workflow_id = "test-workflow"
        
        # Test not found
        status = await orchestrator.get_workflow_status(workflow_id)
        assert status["status"] == "not_found"
        assert status["active"] is False
        
        # Test active workflow
        mock_crew = Mock()
        orchestrator.active_workflows[workflow_id] = mock_crew
        
        status = await orchestrator.get_workflow_status(workflow_id)
        assert status["status"] == WorkflowStatus.RUNNING.value
        assert status["active"] is True
        
        # Test completed workflow
        del orchestrator.active_workflows[workflow_id]
        mock_result = Mock()
        mock_result.status = WorkflowStatus.COMPLETED
        mock_result.execution_time = 10.5
        mock_result.completed_at = datetime.utcnow()
        mock_result.errors = []
        orchestrator.workflow_results[workflow_id] = mock_result
        
        status = await orchestrator.get_workflow_status(workflow_id)
        assert status["status"] == WorkflowStatus.COMPLETED.value
        assert status["active"] is False
        assert status["execution_time"] == 10.5
    
    @pytest.mark.asyncio
    async def test_cancel_workflow(self, orchestrator, mock_memory_manager):
        """Test workflow cancellation."""
        workflow_id = "test-workflow"
        
        # Test cancelling non-existent workflow
        cancelled = await orchestrator.cancel_workflow(workflow_id)
        assert cancelled is False
        
        # Test cancelling active workflow
        mock_crew = Mock()
        orchestrator.active_workflows[workflow_id] = mock_crew
        
        cancelled = await orchestrator.cancel_workflow(workflow_id)
        assert cancelled is True
        assert workflow_id not in orchestrator.active_workflows
        
        # Verify memory storage for cancellation
        mock_memory_manager.store_memory.assert_called()


class TestWorkflowTask:
    """Test cases for WorkflowTask dataclass."""
    
    def test_workflow_task_creation(self):
        """Test WorkflowTask creation with defaults."""
        task = WorkflowTask(
            id="test-task",
            description="Test description",
            expected_output="Test output",
            agent_role=AgentRole.DATA_EXTRACTION
        )
        
        assert task.id == "test-task"
        assert task.description == "Test description"
        assert task.expected_output == "Test output"
        assert task.agent_role == AgentRole.DATA_EXTRACTION
        assert task.priority == TaskPriority.MEDIUM
        assert task.context == {}
        assert task.dependencies == []
        assert task.status == WorkflowStatus.PENDING
        assert isinstance(task.created_at, datetime)
    
    def test_workflow_task_with_custom_values(self):
        """Test WorkflowTask creation with custom values."""
        context = {"key": "value"}
        dependencies = ["task1", "task2"]
        
        task = WorkflowTask(
            id="test-task",
            description="Test description",
            expected_output="Test output",
            agent_role=AgentRole.CONTRACT_GENERATOR,
            priority=TaskPriority.HIGH,
            context=context,
            dependencies=dependencies
        )
        
        assert task.priority == TaskPriority.HIGH
        assert task.context == context
        assert task.dependencies == dependencies


class TestAgentRoles:
    """Test cases for AgentRole enum."""
    
    def test_agent_role_values(self):
        """Test that all agent roles have correct values."""
        assert AgentRole.DATA_EXTRACTION.value == "data_extraction"
        assert AgentRole.CONTRACT_GENERATOR.value == "contract_generator"
        assert AgentRole.COMPLIANCE_CHECKER.value == "compliance_checker"
        assert AgentRole.SIGNATURE_TRACKER.value == "signature_tracker"
        assert AgentRole.SUMMARY_AGENT.value == "summary_agent"
        assert AgentRole.HELP_AGENT.value == "help_agent"
    
    def test_agent_role_count(self):
        """Test that we have the expected number of agent roles."""
        roles = list(AgentRole)
        assert len(roles) == 6


def test_get_agent_orchestrator_singleton():
    """Test that get_agent_orchestrator returns a singleton instance."""
    orchestrator1 = get_agent_orchestrator()
    orchestrator2 = get_agent_orchestrator()
    
    # Should return the same instance
    assert orchestrator1 is orchestrator2


class TestIntegration:
    """Integration tests for the agent orchestrator system."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self):
        """Test a complete end-to-end workflow execution."""
        with patch('app.services.agent_orchestrator.get_model_router') as mock_router, \
             patch('app.services.agent_orchestrator.AgentMemoryManager') as mock_memory, \
             patch('app.services.agent_orchestrator.Agent') as mock_agent_class, \
             patch('app.services.agent_orchestrator.Crew') as mock_crew_class:
            
            # Setup mocks
            mock_router.return_value = Mock(models={}, strategy=Mock(value="cost_optimized"))
            mock_memory.return_value = Mock(
                store_memory=AsyncMock(),
                get_memory_stats=AsyncMock(return_value={})
            )
            mock_agent_class.return_value = Mock()
            mock_crew = Mock()
            mock_crew.kickoff.return_value = "Success"
            mock_crew_class.return_value = mock_crew
            
            # Create orchestrator
            orchestrator = AgentOrchestrator()
            
            # Create and execute workflow
            tasks = [
                WorkflowTask(
                    id="extract",
                    description="Extract data",
                    expected_output="Extracted data",
                    agent_role=AgentRole.DATA_EXTRACTION
                )
            ]
            
            workflow_id = await orchestrator.create_workflow(tasks)
            result = await orchestrator.execute_workflow(workflow_id)
            
            assert result.status == WorkflowStatus.COMPLETED
            assert "Success" in result.results["output"]
