"""
Agent Orchestrator Service for CrewAI-based multi-agent system.

This service provides the core orchestration for specialized real estate agents
using the CrewAI framework with integration to our Model Router Service.
"""

import asyncio
import uuid
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field

import structlog
from crewai import Agent, Task, Crew, Process
from crewai.llm import LLM

from ..core.config import get_settings
from ..services.model_router import get_model_router, ModelRequest
from .agent_memory import AgentMemoryManager, MemoryType, MemoryScope
from .agent_tools import get_tools_for_agent, tool_registry

logger = structlog.get_logger(__name__)
settings = get_settings()


class AgentRole(Enum):
    """Available agent roles in the real estate system."""
    DATA_EXTRACTION = "data_extraction"
    CONTRACT_GENERATOR = "contract_generator"
    COMPLIANCE_CHECKER = "compliance_checker"
    SIGNATURE_TRACKER = "signature_tracker"
    SUMMARY_AGENT = "summary_agent"
    HELP_AGENT = "help_agent"


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class WorkflowStatus(Enum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentConfig:
    """Configuration for an individual agent."""
    role: AgentRole
    goal: str
    backstory: str
    tools: List[str] = field(default_factory=list)
    max_iter: int = 5
    memory: bool = True
    verbose: bool = True
    allow_delegation: bool = True


@dataclass
class WorkflowTask:
    """A task to be executed by agents."""
    id: str
    description: str
    expected_output: str
    agent_role: AgentRole
    priority: TaskPriority = TaskPriority.MEDIUM
    context: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    status: WorkflowStatus = WorkflowStatus.PENDING


@dataclass
class WorkflowResult:
    """Result of workflow execution."""
    workflow_id: str
    status: WorkflowStatus
    results: Dict[str, Any]
    execution_time: float
    cost: float
    agent_interactions: List[Dict[str, Any]]
    errors: List[str] = field(default_factory=list)
    completed_at: Optional[datetime] = None


class ModelRouterLLM(LLM):
    """
    Custom LLM wrapper that integrates CrewAI with our Model Router Service.

    This allows all agents to use the unified model routing with intelligent
    fallbacks and cost optimization.
    """

    def __init__(self, model_preference: Optional[str] = None):
        self.model_router = get_model_router()
        self.model_preference = model_preference or "openrouter/auto"
        super().__init__(model=self.model_preference)

    def call(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        Make a synchronous call to the model router.

        Args:
            messages: List of chat messages
            **kwargs: Additional parameters

        Returns:
            Generated response content
        """
        import concurrent.futures
        import threading

        def run_async_in_thread():
            """Run the async call in a separate thread with its own event loop."""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self._async_call(messages, **kwargs))
            finally:
                loop.close()

        # Run the async call in a separate thread to avoid event loop conflicts
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_async_in_thread)
            return future.result(timeout=60)  # 60 second timeout

    async def _async_call(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        Make an async call to the model router.

        Args:
            messages: List of chat messages
            **kwargs: Additional parameters

        Returns:
            Generated response content
        """
        try:
            # Create model request
            request = ModelRequest(
                messages=messages,
                model_preference=self.model_preference,
                max_tokens=kwargs.get('max_tokens', 2000),
                temperature=kwargs.get('temperature', 0.1),
                system_prompt=kwargs.get('system_prompt')
            )

            # Generate response using model router
            response = await self.model_router.generate_response(request)

            logger.info(
                "Agent LLM call completed",
                model_used=response.model_used,
                provider=response.provider.value,
                cost=response.cost,
                processing_time=response.processing_time
            )

            return response.content

        except Exception as e:
            logger.error(f"Agent LLM call failed: {e}")
            raise


class AgentOrchestrator:
    """
    Core orchestrator for managing CrewAI agents and workflows.

    Provides centralized management of agent lifecycle, task delegation,
    and workflow coordination with integration to existing backend systems.
    """

    def __init__(self):
        self.settings = get_settings()
        self.model_router = get_model_router()
        self.memory_manager = AgentMemoryManager()

        # Agent registry
        self.agents: Dict[AgentRole, Agent] = {}
        self.agent_configs: Dict[AgentRole, AgentConfig] = {}

        # Workflow tracking
        self.active_workflows: Dict[str, Crew] = {}
        self.workflow_results: Dict[str, WorkflowResult] = {}

        # Initialize default agent configurations
        self._init_agent_configs()

        logger.info("Agent Orchestrator initialized")

    def _init_agent_configs(self):
        """Initialize default configurations for all agent roles."""
        self.agent_configs = {
            AgentRole.DATA_EXTRACTION: AgentConfig(
                role=AgentRole.DATA_EXTRACTION,
                goal="Extract and normalize data from real estate documents with high accuracy and confidence scoring",
                backstory="""You are an expert data extraction specialist with deep knowledge of real estate documents,
                contracts, and legal terminology. You excel at parsing complex documents, identifying key entities,
                and providing structured output with confidence scores. Your expertise includes property details,
                financial terms, legal clauses, and party information extraction.""",
                tools=["document_parser", "entity_recognizer", "confidence_scorer"],
                allow_delegation=False
            ),

            AgentRole.CONTRACT_GENERATOR: AgentConfig(
                role=AgentRole.CONTRACT_GENERATOR,
                goal="Generate comprehensive real estate contracts using templates and extracted data with legal compliance",
                backstory="""You are a seasoned real estate contract specialist with extensive experience in
                contract generation, template management, and legal compliance. You understand the nuances of
                real estate law, can fill complex templates accurately, and ensure all generated contracts
                meet legal standards and industry best practices.""",
                tools=["template_engine", "contract_validator", "legal_checker"],
                allow_delegation=True
            ),

            AgentRole.COMPLIANCE_CHECKER: AgentConfig(
                role=AgentRole.COMPLIANCE_CHECKER,
                goal="Validate contracts and documents against legal requirements and industry regulations",
                backstory="""You are a meticulous compliance expert with deep knowledge of real estate regulations,
                legal requirements, and industry standards. You excel at identifying potential issues, validating
                contract terms, and ensuring all documents meet jurisdictional requirements and best practices.""",
                tools=["compliance_validator", "regulation_checker", "risk_assessor"],
                allow_delegation=False
            ),

            AgentRole.SIGNATURE_TRACKER: AgentConfig(
                role=AgentRole.SIGNATURE_TRACKER,
                goal="Monitor and coordinate e-signature workflows with multi-party tracking and notifications",
                backstory="""You are an efficient workflow coordinator specializing in e-signature processes and
                document execution. You excel at tracking signature status, coordinating multi-party workflows,
                managing notifications, and ensuring timely completion of signature processes.""",
                tools=["signature_monitor", "notification_sender", "workflow_tracker"],
                allow_delegation=True
            ),

            AgentRole.SUMMARY_AGENT: AgentConfig(
                role=AgentRole.SUMMARY_AGENT,
                goal="Create comprehensive summaries, diffs, and executive reports for contracts and documents",
                backstory="""You are a skilled analyst and communicator who excels at distilling complex information
                into clear, actionable summaries. You can identify key changes, highlight important terms, and
                create executive-level reports that help stakeholders understand document content and implications.""",
                tools=["summarizer", "diff_generator", "report_creator"],
                allow_delegation=False
            ),

            AgentRole.HELP_AGENT: AgentConfig(
                role=AgentRole.HELP_AGENT,
                goal="Provide contextual assistance, answer questions, and guide users through real estate workflows",
                backstory="""You are a knowledgeable real estate assistant with comprehensive understanding of
                the platform, workflows, and real estate processes. You excel at providing contextual help,
                answering questions, explaining complex concepts, and guiding users through various tasks
                with patience and clarity.""",
                tools=["knowledge_base", "workflow_guide", "context_analyzer"],
                allow_delegation=True
            )
        }

        logger.info(f"Initialized {len(self.agent_configs)} agent configurations")

    def create_agent(self, role: AgentRole, model_preference: Optional[str] = None) -> Agent:
        """
        Create a CrewAI agent with the specified role.

        Args:
            role: The agent role to create
            model_preference: Optional model preference for this agent

        Returns:
            Configured CrewAI Agent instance
        """
        if role not in self.agent_configs:
            raise ValueError(f"Unknown agent role: {role}")

        config = self.agent_configs[role]

        # Create custom LLM with model router integration
        llm = ModelRouterLLM(model_preference=model_preference)

        # For now, create agents without custom tools to avoid compatibility issues
        # Custom tools will be integrated in a future update
        agent_tools = []  # get_tools_for_agent(config.role.value)

        # Create the agent
        agent = Agent(
            role=config.role.value,
            goal=config.goal,
            backstory=config.backstory,
            llm=llm,
            max_iter=config.max_iter,
            memory=config.memory,
            verbose=config.verbose,
            allow_delegation=config.allow_delegation,
            tools=agent_tools
        )

        # Store in registry
        self.agents[role] = agent

        logger.info(
            "Agent created",
            role=role.value,
            model_preference=model_preference,
            allow_delegation=config.allow_delegation
        )

        return agent

    def get_agent(self, role: AgentRole) -> Optional[Agent]:
        """Get an existing agent by role."""
        return self.agents.get(role)

    def get_or_create_agent(self, role: AgentRole,
                           model_preference: Optional[str] = None) -> Agent:
        """Get an existing agent or create a new one."""
        agent = self.get_agent(role)
        if agent is None:
            agent = self.create_agent(role, model_preference)
        return agent

    async def create_workflow(self,
                             tasks: List[WorkflowTask],
                             workflow_id: Optional[str] = None,
                             process_type: Process = Process.sequential,
                             user_id: Optional[str] = None) -> str:
        """
        Create and execute a multi-agent workflow.

        Args:
            tasks: List of tasks to execute
            workflow_id: Optional workflow ID (generated if not provided)
            process_type: CrewAI process type (sequential, hierarchical)
            user_id: Optional user ID for context

        Returns:
            Workflow ID
        """
        if not workflow_id:
            workflow_id = str(uuid.uuid4())

        try:
            # Store workflow context in memory
            await self.memory_manager.store_memory(
                content={
                    "workflow_id": workflow_id,
                    "user_id": user_id,
                    "task_count": len(tasks),
                    "process_type": process_type.value,
                    "created_at": datetime.utcnow().isoformat()
                },
                memory_type=MemoryType.WORKFLOW,
                scope=MemoryScope.WORKFLOW,
                identifier=workflow_id,
                workflow_id=workflow_id,
                user_id=user_id,
                tags={"workflow_context"}
            )

            # Create agents for required roles
            agents = []
            crew_tasks = []

            for task in tasks:
                # Get or create agent for this task
                agent = self.get_or_create_agent(task.agent_role)
                agents.append(agent)

                # Create CrewAI task
                crew_task = Task(
                    description=task.description,
                    expected_output=task.expected_output,
                    agent=agent
                    # Note: context parameter removed as it's causing validation issues
                )
                crew_tasks.append(crew_task)

                # Store task context in memory
                await self.memory_manager.store_memory(
                    content={
                        "task_id": task.id,
                        "description": task.description,
                        "agent_role": task.agent_role.value,
                        "priority": task.priority.value,
                        "context": task.context
                    },
                    memory_type=MemoryType.WORKFLOW,
                    scope=MemoryScope.WORKFLOW,
                    identifier=f"{workflow_id}_{task.id}",
                    workflow_id=workflow_id,
                    user_id=user_id,
                    tags={"task_context", task.agent_role.value}
                )

            # Create crew
            crew = Crew(
                agents=list(set(agents)),  # Remove duplicates
                tasks=crew_tasks,
                process=process_type,
                verbose=True,
                memory=False  # Disable memory to avoid Chroma dependency
            )

            # Store active workflow
            self.active_workflows[workflow_id] = crew

            logger.info(
                "Workflow created",
                workflow_id=workflow_id,
                task_count=len(tasks),
                agent_count=len(set(agents)),
                process_type=process_type.value
            )

            return workflow_id

        except Exception as e:
            logger.error(f"Failed to create workflow {workflow_id}: {e}")
            raise

    async def execute_workflow(self, workflow_id: str) -> WorkflowResult:
        """
        Execute a workflow and return results.

        Args:
            workflow_id: The workflow ID to execute

        Returns:
            Workflow execution results
        """
        if workflow_id not in self.active_workflows:
            raise ValueError(f"Workflow {workflow_id} not found")

        crew = self.active_workflows[workflow_id]
        start_time = datetime.utcnow()

        try:
            logger.info(f"Starting workflow execution: {workflow_id}")

            # Execute the crew with proper error handling and monitoring
            try:
                result = crew.kickoff()

                # Extract meaningful results from crew execution
                if hasattr(result, 'raw'):
                    # CrewAI result object
                    output_content = result.raw
                elif isinstance(result, str):
                    # String result
                    output_content = result
                else:
                    # Other result types
                    output_content = str(result)

                execution_time = (datetime.utcnow() - start_time).total_seconds()

                # Calculate cost from model router usage (if available)
                total_cost = 0.0
                agent_interactions = []

                # Try to extract agent interaction data
                if hasattr(crew, 'agents'):
                    for agent in crew.agents:
                        if hasattr(agent, 'llm') and hasattr(agent.llm, 'model_router'):
                            # Add interaction data if available
                            agent_interactions.append({
                                "agent_role": agent.role,
                                "model_used": getattr(agent.llm, 'model_preference', 'unknown'),
                                "execution_time": execution_time / len(crew.agents)  # Estimate
                            })

                # Create workflow result
                workflow_result = WorkflowResult(
                    workflow_id=workflow_id,
                    status=WorkflowStatus.COMPLETED,
                    results={
                        "output": output_content,
                        "raw_result": str(result),
                        "agent_count": len(crew.agents) if hasattr(crew, 'agents') else 0,
                        "task_count": len(crew.tasks) if hasattr(crew, 'tasks') else 0
                    },
                    execution_time=execution_time,
                    cost=total_cost,
                    agent_interactions=agent_interactions,
                    completed_at=datetime.utcnow()
                )

            except Exception as crew_error:
                logger.error(f"Crew execution failed for workflow {workflow_id}: {crew_error}")
                execution_time = (datetime.utcnow() - start_time).total_seconds()

                # Create failed result with error details
                workflow_result = WorkflowResult(
                    workflow_id=workflow_id,
                    status=WorkflowStatus.FAILED,
                    results={"error_details": str(crew_error)},
                    execution_time=execution_time,
                    cost=0.0,
                    agent_interactions=[],
                    errors=[f"Crew execution failed: {str(crew_error)}"],
                    completed_at=datetime.utcnow()
                )

                # Store failed result and return it
                self.workflow_results[workflow_id] = workflow_result
                del self.active_workflows[workflow_id]
                return workflow_result

            # Store result
            self.workflow_results[workflow_id] = workflow_result

            # Store completion in memory
            await self.memory_manager.store_memory(
                content={
                    "workflow_id": workflow_id,
                    "status": WorkflowStatus.COMPLETED.value,
                    "execution_time": execution_time,
                    "completed_at": datetime.utcnow().isoformat(),
                    "result_summary": str(result)[:500]  # Truncated summary
                },
                memory_type=MemoryType.WORKFLOW,
                scope=MemoryScope.WORKFLOW,
                identifier=f"{workflow_id}_result",
                workflow_id=workflow_id,
                tags={"workflow_result", "completed"}
            )

            # Clean up active workflow
            del self.active_workflows[workflow_id]

            logger.info(
                "Workflow completed",
                workflow_id=workflow_id,
                execution_time=execution_time,
                status=WorkflowStatus.COMPLETED.value
            )

            return workflow_result

        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()

            # Create failed result
            workflow_result = WorkflowResult(
                workflow_id=workflow_id,
                status=WorkflowStatus.FAILED,
                results={},
                execution_time=execution_time,
                cost=0.0,
                agent_interactions=[],
                errors=[str(e)],
                completed_at=datetime.utcnow()
            )

            # Store failed result
            self.workflow_results[workflow_id] = workflow_result

            # Clean up active workflow
            if workflow_id in self.active_workflows:
                del self.active_workflows[workflow_id]

            logger.error(
                "Workflow failed",
                workflow_id=workflow_id,
                execution_time=execution_time,
                error=str(e)
            )

            raise

    async def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get the current status of a workflow."""
        if workflow_id in self.active_workflows:
            return {
                "workflow_id": workflow_id,
                "status": WorkflowStatus.RUNNING.value,
                "active": True
            }
        elif workflow_id in self.workflow_results:
            result = self.workflow_results[workflow_id]
            return {
                "workflow_id": workflow_id,
                "status": result.status.value,
                "active": False,
                "execution_time": result.execution_time,
                "completed_at": result.completed_at.isoformat() if result.completed_at else None,
                "errors": result.errors
            }
        else:
            return {
                "workflow_id": workflow_id,
                "status": "not_found",
                "active": False
            }

    async def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel an active workflow."""
        if workflow_id in self.active_workflows:
            del self.active_workflows[workflow_id]

            # Store cancellation in memory
            await self.memory_manager.store_memory(
                content={
                    "workflow_id": workflow_id,
                    "status": WorkflowStatus.CANCELLED.value,
                    "cancelled_at": datetime.utcnow().isoformat()
                },
                memory_type=MemoryType.WORKFLOW,
                scope=MemoryScope.WORKFLOW,
                identifier=f"{workflow_id}_cancelled",
                workflow_id=workflow_id,
                tags={"workflow_result", "cancelled"}
            )

            logger.info(f"Workflow cancelled: {workflow_id}")
            return True

        return False


# Global orchestrator instance
orchestrator = AgentOrchestrator()


def get_agent_orchestrator() -> AgentOrchestrator:
    """Get the global agent orchestrator instance."""
    return orchestrator
