"""
Advanced Workflow Orchestrator for Multi-Agent Collaboration.

This module provides sophisticated workflow orchestration capabilities
for coordinating multiple AI agents in complex real estate workflows.
"""

import asyncio
import uuid
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import structlog

from .agent_orchestrator import AgentRole, get_agent_orchestrator
from .agent_memory import get_memory_manager
from .agent_tools import get_tools_for_agent

logger = structlog.get_logger(__name__)


class WorkflowStatus(Enum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskStatus(Enum):
    """Individual task status within a workflow."""
    WAITING = "waiting"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class WorkflowTask:
    """Individual task within a workflow."""
    task_id: str
    agent_role: AgentRole
    task_type: str
    description: str
    input_data: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)
    priority: TaskPriority = TaskPriority.NORMAL
    timeout: Optional[int] = None
    retry_count: int = 0
    max_retries: int = 3
    status: TaskStatus = TaskStatus.WAITING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    assigned_agent_id: Optional[str] = None


@dataclass
class WorkflowDefinition:
    """Complete workflow definition."""
    workflow_id: str
    name: str
    description: str
    tasks: List[WorkflowTask]
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = ""


@dataclass
class WorkflowExecution:
    """Runtime workflow execution state."""
    execution_id: str
    workflow_definition: WorkflowDefinition
    status: WorkflowStatus = WorkflowStatus.PENDING
    progress: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    context: Dict[str, Any] = field(default_factory=dict)
    agent_assignments: Dict[str, str] = field(default_factory=dict)  # task_id -> agent_id
    execution_log: List[Dict[str, Any]] = field(default_factory=list)


class AdvancedWorkflowOrchestrator:
    """Advanced orchestrator for multi-agent workflows."""
    
    def __init__(self):
        self.active_workflows: Dict[str, WorkflowExecution] = {}
        self.workflow_definitions: Dict[str, WorkflowDefinition] = {}
        self.agent_pool: Dict[str, Dict[str, Any]] = {}  # agent_id -> agent_info
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.running = False
        self.worker_tasks: List[asyncio.Task] = []
        self.load_balancer = LoadBalancer()
        self.performance_monitor = WorkflowPerformanceMonitor()
        
        # Initialize predefined workflow templates
        self._initialize_workflow_templates()
    
    async def start(self):
        """Start the workflow orchestrator."""
        if self.running:
            return
        
        self.running = True
        
        # Start worker tasks for parallel execution
        for i in range(3):  # 3 concurrent workers
            task = asyncio.create_task(self._worker(f"worker-{i}"))
            self.worker_tasks.append(task)
        
        # Start monitoring task
        monitor_task = asyncio.create_task(self._monitor_workflows())
        self.worker_tasks.append(monitor_task)
        
        logger.info("Advanced Workflow Orchestrator started")
    
    async def stop(self):
        """Stop the workflow orchestrator."""
        self.running = False
        
        # Cancel all worker tasks
        for task in self.worker_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.worker_tasks, return_exceptions=True)
        self.worker_tasks.clear()
        
        logger.info("Advanced Workflow Orchestrator stopped")
    
    def register_workflow_template(self, template: WorkflowDefinition):
        """Register a workflow template."""
        self.workflow_definitions[template.workflow_id] = template
        logger.info(f"Registered workflow template: {template.name}")
    
    async def create_workflow_execution(
        self,
        template_id: str,
        input_data: Dict[str, Any],
        user_id: str,
        execution_id: Optional[str] = None
    ) -> WorkflowExecution:
        """Create a new workflow execution from a template."""
        if template_id not in self.workflow_definitions:
            raise ValueError(f"Workflow template not found: {template_id}")
        
        template = self.workflow_definitions[template_id]
        execution_id = execution_id or str(uuid.uuid4())
        
        # Create execution with deep copy of template
        execution = WorkflowExecution(
            execution_id=execution_id,
            workflow_definition=template,
            context={"input_data": input_data, "user_id": user_id}
        )
        
        # Initialize task states
        for task in execution.workflow_definition.tasks:
            task.status = TaskStatus.WAITING
            task.result = None
            task.error = None
            task.started_at = None
            task.completed_at = None
        
        self.active_workflows[execution_id] = execution
        
        # Store in memory manager
        memory_manager = get_memory_manager()
        await memory_manager.set_workflow_state(execution_id, {
            "status": execution.status.value,
            "progress": execution.progress,
            "context": execution.context,
            "created_at": datetime.utcnow().isoformat()
        })
        
        logger.info(f"Created workflow execution: {execution_id} from template: {template.name}")
        return execution
    
    async def start_workflow_execution(self, execution_id: str) -> bool:
        """Start executing a workflow."""
        if execution_id not in self.active_workflows:
            return False
        
        execution = self.active_workflows[execution_id]
        execution.status = WorkflowStatus.RUNNING
        execution.started_at = datetime.utcnow()
        
        # Queue ready tasks
        await self._queue_ready_tasks(execution)
        
        logger.info(f"Started workflow execution: {execution_id}")
        return True
    
    async def pause_workflow_execution(self, execution_id: str) -> bool:
        """Pause a running workflow."""
        if execution_id not in self.active_workflows:
            return False
        
        execution = self.active_workflows[execution_id]
        if execution.status == WorkflowStatus.RUNNING:
            execution.status = WorkflowStatus.PAUSED
            logger.info(f"Paused workflow execution: {execution_id}")
            return True
        
        return False
    
    async def resume_workflow_execution(self, execution_id: str) -> bool:
        """Resume a paused workflow."""
        if execution_id not in self.active_workflows:
            return False
        
        execution = self.active_workflows[execution_id]
        if execution.status == WorkflowStatus.PAUSED:
            execution.status = WorkflowStatus.RUNNING
            await self._queue_ready_tasks(execution)
            logger.info(f"Resumed workflow execution: {execution_id}")
            return True
        
        return False
    
    async def cancel_workflow_execution(self, execution_id: str) -> bool:
        """Cancel a workflow execution."""
        if execution_id not in self.active_workflows:
            return False
        
        execution = self.active_workflows[execution_id]
        execution.status = WorkflowStatus.CANCELLED
        execution.completed_at = datetime.utcnow()
        
        logger.info(f"Cancelled workflow execution: {execution_id}")
        return True
    
    async def get_workflow_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow execution status."""
        if execution_id not in self.active_workflows:
            return None
        
        execution = self.active_workflows[execution_id]
        
        # Calculate progress
        total_tasks = len(execution.workflow_definition.tasks)
        completed_tasks = sum(1 for task in execution.workflow_definition.tasks 
                            if task.status == TaskStatus.COMPLETED)
        execution.progress = (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 0
        
        return {
            "execution_id": execution_id,
            "status": execution.status.value,
            "progress": execution.progress,
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "running_tasks": sum(1 for task in execution.workflow_definition.tasks 
                               if task.status == TaskStatus.RUNNING),
            "failed_tasks": sum(1 for task in execution.workflow_definition.tasks 
                              if task.status == TaskStatus.FAILED)
        }
    
    async def _queue_ready_tasks(self, execution: WorkflowExecution):
        """Queue tasks that are ready to execute."""
        for task in execution.workflow_definition.tasks:
            if task.status == TaskStatus.WAITING and self._are_dependencies_met(task, execution):
                task.status = TaskStatus.READY
                await self.task_queue.put((execution.execution_id, task.task_id))
    
    def _are_dependencies_met(self, task: WorkflowTask, execution: WorkflowExecution) -> bool:
        """Check if all task dependencies are completed."""
        for dep_id in task.dependencies:
            dep_task = next((t for t in execution.workflow_definition.tasks if t.task_id == dep_id), None)
            if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                return False
        return True
    
    async def _worker(self, worker_id: str):
        """Worker coroutine for executing tasks."""
        logger.info(f"Workflow worker {worker_id} started")
        
        while self.running:
            try:
                # Get next task from queue
                execution_id, task_id = await asyncio.wait_for(
                    self.task_queue.get(), timeout=1.0
                )
                
                if execution_id not in self.active_workflows:
                    continue
                
                execution = self.active_workflows[execution_id]
                if execution.status != WorkflowStatus.RUNNING:
                    continue
                
                task = next((t for t in execution.workflow_definition.tasks if t.task_id == task_id), None)
                if not task or task.status != TaskStatus.READY:
                    continue
                
                # Execute the task
                await self._execute_task(execution, task, worker_id)
                
                # Queue any newly ready tasks
                await self._queue_ready_tasks(execution)
                
                # Check if workflow is complete
                await self._check_workflow_completion(execution)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
    
    async def _execute_task(self, execution: WorkflowExecution, task: WorkflowTask, worker_id: str):
        """Execute a single task."""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        
        # Assign agent using load balancer
        agent_id = await self.load_balancer.assign_agent(task.agent_role, task.priority)
        task.assigned_agent_id = agent_id
        execution.agent_assignments[task.task_id] = agent_id
        
        logger.info(f"Worker {worker_id} executing task {task.task_id} with agent {agent_id}")
        
        try:
            # Get agent orchestrator
            orchestrator = get_agent_orchestrator()
            agent = orchestrator.create_agent(task.agent_role)
            
            # Prepare task context
            task_context = {
                **execution.context,
                "task_id": task.task_id,
                "workflow_id": execution.execution_id,
                "input_data": task.input_data
            }
            
            # Execute task (simplified - in real implementation would use agent tools)
            result = await self._simulate_task_execution(task, task_context)
            
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            
            # Update execution context with task result
            execution.context[f"task_{task.task_id}_result"] = result
            
            # Log execution
            execution.execution_log.append({
                "timestamp": datetime.utcnow().isoformat(),
                "event": "task_completed",
                "task_id": task.task_id,
                "agent_id": agent_id,
                "worker_id": worker_id,
                "duration": (task.completed_at - task.started_at).total_seconds()
            })
            
            logger.info(f"Task {task.task_id} completed successfully")
            
        except Exception as e:
            task.error = str(e)
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.utcnow()
            
            # Log error
            execution.execution_log.append({
                "timestamp": datetime.utcnow().isoformat(),
                "event": "task_failed",
                "task_id": task.task_id,
                "agent_id": agent_id,
                "worker_id": worker_id,
                "error": str(e)
            })
            
            logger.error(f"Task {task.task_id} failed: {e}")
            
            # Check if we should retry
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.READY
                await self.task_queue.put((execution.execution_id, task.task_id))
                logger.info(f"Retrying task {task.task_id} (attempt {task.retry_count})")
        
        finally:
            # Release agent
            await self.load_balancer.release_agent(agent_id)
    
    async def _simulate_task_execution(self, task: WorkflowTask, context: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate task execution (placeholder for actual agent execution)."""
        # Simulate processing time
        await asyncio.sleep(0.5)
        
        return {
            "task_type": task.task_type,
            "agent_role": task.agent_role.value,
            "processed_at": datetime.utcnow().isoformat(),
            "context_keys": list(context.keys()),
            "status": "success"
        }
    
    async def _check_workflow_completion(self, execution: WorkflowExecution):
        """Check if workflow execution is complete."""
        all_tasks_done = all(
            task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.SKIPPED]
            for task in execution.workflow_definition.tasks
        )
        
        if all_tasks_done:
            failed_tasks = [task for task in execution.workflow_definition.tasks 
                          if task.status == TaskStatus.FAILED]
            
            if failed_tasks:
                execution.status = WorkflowStatus.FAILED
            else:
                execution.status = WorkflowStatus.COMPLETED
            
            execution.completed_at = datetime.utcnow()
            
            # Update memory manager
            memory_manager = get_memory_manager()
            await memory_manager.set_workflow_state(execution.execution_id, {
                "status": execution.status.value,
                "progress": 100.0,
                "completed_at": execution.completed_at.isoformat(),
                "failed_tasks": len(failed_tasks)
            })
            
            logger.info(f"Workflow {execution.execution_id} completed with status: {execution.status.value}")
    
    async def _monitor_workflows(self):
        """Monitor workflow executions for timeouts and health."""
        while self.running:
            try:
                current_time = datetime.utcnow()
                
                for execution in self.active_workflows.values():
                    if execution.status == WorkflowStatus.RUNNING:
                        # Check for task timeouts
                        for task in execution.workflow_definition.tasks:
                            if (task.status == TaskStatus.RUNNING and 
                                task.timeout and 
                                task.started_at and
                                (current_time - task.started_at).total_seconds() > task.timeout):
                                
                                task.status = TaskStatus.FAILED
                                task.error = "Task timeout"
                                task.completed_at = current_time
                                
                                logger.warning(f"Task {task.task_id} timed out")
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Workflow monitor error: {e}")
                await asyncio.sleep(30)
    
    def _initialize_workflow_templates(self):
        """Initialize predefined workflow templates."""
        # Contract Processing Workflow
        contract_workflow = WorkflowDefinition(
            workflow_id="contract_processing",
            name="Complete Contract Processing",
            description="End-to-end contract processing workflow",
            tasks=[
                WorkflowTask(
                    task_id="extract_data",
                    agent_role=AgentRole.DATA_EXTRACTION,
                    task_type="document_analysis",
                    description="Extract data from contract document",
                    input_data={},
                    priority=TaskPriority.HIGH
                ),
                WorkflowTask(
                    task_id="generate_contract",
                    agent_role=AgentRole.CONTRACT_GENERATOR,
                    task_type="contract_generation",
                    description="Generate contract from extracted data",
                    input_data={},
                    dependencies=["extract_data"],
                    priority=TaskPriority.HIGH
                ),
                WorkflowTask(
                    task_id="compliance_check",
                    agent_role=AgentRole.COMPLIANCE_CHECKER,
                    task_type="compliance_validation",
                    description="Validate contract compliance",
                    input_data={},
                    dependencies=["generate_contract"],
                    priority=TaskPriority.CRITICAL
                ),
                WorkflowTask(
                    task_id="prepare_signatures",
                    agent_role=AgentRole.SIGNATURE_TRACKER,
                    task_type="signature_preparation",
                    description="Prepare contract for signatures",
                    input_data={},
                    dependencies=["compliance_check"],
                    priority=TaskPriority.NORMAL
                ),
                WorkflowTask(
                    task_id="generate_summary",
                    agent_role=AgentRole.SUMMARY_AGENT,
                    task_type="document_summary",
                    description="Generate contract summary",
                    input_data={},
                    dependencies=["compliance_check"],
                    priority=TaskPriority.LOW
                )
            ]
        )
        
        self.register_workflow_template(contract_workflow)


class LoadBalancer:
    """Load balancer for agent assignment."""
    
    def __init__(self):
        self.agent_workload: Dict[str, int] = {}
        self.agent_capabilities: Dict[str, List[AgentRole]] = {}
    
    async def assign_agent(self, required_role: AgentRole, priority: TaskPriority) -> str:
        """Assign an agent for a task."""
        # Simplified assignment - in production would consider actual agent availability
        agent_id = f"agent_{required_role.value}_{uuid.uuid4().hex[:8]}"
        self.agent_workload[agent_id] = self.agent_workload.get(agent_id, 0) + 1
        return agent_id
    
    async def release_agent(self, agent_id: str):
        """Release an agent after task completion."""
        if agent_id in self.agent_workload:
            self.agent_workload[agent_id] = max(0, self.agent_workload[agent_id] - 1)


class WorkflowPerformanceMonitor:
    """Monitor workflow performance and optimization."""
    
    def __init__(self):
        self.metrics: Dict[str, Any] = {}
    
    def record_workflow_completion(self, execution: WorkflowExecution):
        """Record workflow completion metrics."""
        if execution.started_at and execution.completed_at:
            duration = (execution.completed_at - execution.started_at).total_seconds()
            workflow_type = execution.workflow_definition.workflow_id
            
            if workflow_type not in self.metrics:
                self.metrics[workflow_type] = {
                    "total_executions": 0,
                    "total_duration": 0,
                    "success_count": 0,
                    "failure_count": 0
                }
            
            self.metrics[workflow_type]["total_executions"] += 1
            self.metrics[workflow_type]["total_duration"] += duration
            
            if execution.status == WorkflowStatus.COMPLETED:
                self.metrics[workflow_type]["success_count"] += 1
            else:
                self.metrics[workflow_type]["failure_count"] += 1


# Global orchestrator instance
_advanced_orchestrator = None


async def get_advanced_orchestrator() -> AdvancedWorkflowOrchestrator:
    """Get the global advanced workflow orchestrator instance."""
    global _advanced_orchestrator
    
    if _advanced_orchestrator is None:
        _advanced_orchestrator = AdvancedWorkflowOrchestrator()
        await _advanced_orchestrator.start()
    
    return _advanced_orchestrator
