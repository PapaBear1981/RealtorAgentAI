"""
Celery tasks for AI Agent System integration.

This module provides Celery task integration for the agent orchestrator,
enabling background processing and workflow management.
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

import structlog
from celery import Task
from celery.exceptions import Retry

from ..core.celery_app import celery_app
from ..services.agent_orchestrator import (
    get_agent_orchestrator, 
    WorkflowTask, 
    AgentRole, 
    TaskPriority,
    WorkflowStatus
)

logger = structlog.get_logger(__name__)


class AgentTask(Task):
    """Base class for agent-related Celery tasks."""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        logger.error(
            "Agent task failed",
            task_id=task_id,
            exception=str(exc),
            args=args,
            kwargs=kwargs
        )
    
    def on_success(self, retval, task_id, args, kwargs):
        """Handle task success."""
        logger.info(
            "Agent task completed",
            task_id=task_id,
            result_type=type(retval).__name__
        )


@celery_app.task(base=AgentTask, bind=True, max_retries=3)
def execute_agent_workflow(self, 
                          tasks_data: List[Dict[str, Any]], 
                          workflow_id: Optional[str] = None,
                          user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Execute a multi-agent workflow as a Celery task.
    
    Args:
        tasks_data: List of task dictionaries
        workflow_id: Optional workflow ID
        user_id: Optional user ID
        
    Returns:
        Workflow execution results
    """
    try:
        # Convert task data to WorkflowTask objects
        tasks = []
        for task_data in tasks_data:
            task = WorkflowTask(
                id=task_data["id"],
                description=task_data["description"],
                expected_output=task_data["expected_output"],
                agent_role=AgentRole(task_data["agent_role"]),
                priority=TaskPriority(task_data.get("priority", "medium")),
                context=task_data.get("context", {}),
                dependencies=task_data.get("dependencies", [])
            )
            tasks.append(task)
        
        # Get orchestrator and execute workflow
        orchestrator = get_agent_orchestrator()
        
        # Run async workflow in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Create workflow
            workflow_id = loop.run_until_complete(
                orchestrator.create_workflow(
                    tasks=tasks,
                    workflow_id=workflow_id,
                    user_id=user_id
                )
            )
            
            # Execute workflow
            result = loop.run_until_complete(
                orchestrator.execute_workflow(workflow_id)
            )
            
            return {
                "workflow_id": workflow_id,
                "status": result.status.value,
                "results": result.results,
                "execution_time": result.execution_time,
                "cost": result.cost,
                "completed_at": result.completed_at.isoformat() if result.completed_at else None,
                "errors": result.errors
            }
            
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"Workflow execution failed: {exc}")
        
        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            raise self.retry(
                countdown=60 * (2 ** self.request.retries),
                exc=exc
            )
        
        # Final failure
        return {
            "workflow_id": workflow_id,
            "status": WorkflowStatus.FAILED.value,
            "results": {},
            "execution_time": 0.0,
            "cost": 0.0,
            "completed_at": datetime.utcnow().isoformat(),
            "errors": [str(exc)]
        }


@celery_app.task(base=AgentTask, bind=True)
def execute_single_agent_task(self,
                             task_data: Dict[str, Any],
                             agent_role: str,
                             user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Execute a single agent task.
    
    Args:
        task_data: Task data dictionary
        agent_role: Agent role string
        user_id: Optional user ID
        
    Returns:
        Task execution results
    """
    try:
        # Create single task workflow
        task = WorkflowTask(
            id=task_data["id"],
            description=task_data["description"],
            expected_output=task_data["expected_output"],
            agent_role=AgentRole(agent_role),
            priority=TaskPriority(task_data.get("priority", "medium")),
            context=task_data.get("context", {})
        )
        
        # Execute as single-task workflow
        return execute_agent_workflow(self, [task.dict()], user_id=user_id)
        
    except Exception as exc:
        logger.error(f"Single agent task failed: {exc}")
        return {
            "task_id": task_data.get("id"),
            "status": WorkflowStatus.FAILED.value,
            "results": {},
            "error": str(exc)
        }


@celery_app.task(base=AgentTask)
def data_extraction_task(document_id: str, 
                        user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Extract data from a document using the Data Extraction Agent.
    
    Args:
        document_id: ID of the document to process
        user_id: Optional user ID
        
    Returns:
        Extraction results
    """
    task_data = {
        "id": f"extract_{document_id}",
        "description": f"Extract structured data from document {document_id}",
        "expected_output": "Structured JSON with extracted entities, confidence scores, and metadata",
        "context": {
            "document_id": document_id,
            "extraction_type": "comprehensive"
        }
    }
    
    return execute_single_agent_task.delay(
        task_data=task_data,
        agent_role=AgentRole.DATA_EXTRACTION.value,
        user_id=user_id
    ).get()


@celery_app.task(base=AgentTask)
def contract_generation_task(template_id: str,
                           extracted_data: Dict[str, Any],
                           user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate a contract using the Contract Generator Agent.
    
    Args:
        template_id: ID of the contract template
        extracted_data: Extracted data for contract generation
        user_id: Optional user ID
        
    Returns:
        Contract generation results
    """
    task_data = {
        "id": f"generate_{template_id}",
        "description": f"Generate contract using template {template_id}",
        "expected_output": "Complete contract document with filled templates and validation results",
        "context": {
            "template_id": template_id,
            "extracted_data": extracted_data,
            "generation_type": "full_contract"
        }
    }
    
    return execute_single_agent_task.delay(
        task_data=task_data,
        agent_role=AgentRole.CONTRACT_GENERATOR.value,
        user_id=user_id
    ).get()


@celery_app.task(base=AgentTask)
def compliance_check_task(contract_id: str,
                         jurisdiction: str = "default",
                         user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Check contract compliance using the Compliance Checker Agent.
    
    Args:
        contract_id: ID of the contract to check
        jurisdiction: Jurisdiction for compliance rules
        user_id: Optional user ID
        
    Returns:
        Compliance check results
    """
    task_data = {
        "id": f"compliance_{contract_id}",
        "description": f"Check compliance for contract {contract_id}",
        "expected_output": "Compliance report with violations, warnings, and recommendations",
        "context": {
            "contract_id": contract_id,
            "jurisdiction": jurisdiction,
            "check_type": "full_compliance"
        }
    }
    
    return execute_single_agent_task.delay(
        task_data=task_data,
        agent_role=AgentRole.COMPLIANCE_CHECKER.value,
        user_id=user_id
    ).get()


@celery_app.task(base=AgentTask)
def signature_tracking_task(contract_id: str,
                          signers: List[Dict[str, Any]],
                          user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Track signature workflow using the Signature Tracker Agent.
    
    Args:
        contract_id: ID of the contract for signature
        signers: List of signer information
        user_id: Optional user ID
        
    Returns:
        Signature tracking results
    """
    task_data = {
        "id": f"signature_{contract_id}",
        "description": f"Track signature workflow for contract {contract_id}",
        "expected_output": "Signature status report with tracking information and next steps",
        "context": {
            "contract_id": contract_id,
            "signers": signers,
            "tracking_type": "full_workflow"
        }
    }
    
    return execute_single_agent_task.delay(
        task_data=task_data,
        agent_role=AgentRole.SIGNATURE_TRACKER.value,
        user_id=user_id
    ).get()


@celery_app.task(base=AgentTask)
def document_summary_task(document_id: str,
                         summary_type: str = "comprehensive",
                         user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate document summary using the Summary Agent.
    
    Args:
        document_id: ID of the document to summarize
        summary_type: Type of summary (comprehensive, executive, changes)
        user_id: Optional user ID
        
    Returns:
        Summary results
    """
    task_data = {
        "id": f"summary_{document_id}",
        "description": f"Generate {summary_type} summary for document {document_id}",
        "expected_output": "Structured summary with key points, highlights, and actionable items",
        "context": {
            "document_id": document_id,
            "summary_type": summary_type
        }
    }
    
    return execute_single_agent_task.delay(
        task_data=task_data,
        agent_role=AgentRole.SUMMARY_AGENT.value,
        user_id=user_id
    ).get()


@celery_app.task(base=AgentTask)
def complete_contract_workflow(document_id: str,
                              template_id: str,
                              signers: List[Dict[str, Any]],
                              user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Execute a complete contract processing workflow.
    
    This task orchestrates multiple agents to:
    1. Extract data from the document
    2. Generate contract using template
    3. Check compliance
    4. Initialize signature workflow
    5. Generate summary
    
    Args:
        document_id: ID of the source document
        template_id: ID of the contract template
        signers: List of signer information
        user_id: Optional user ID
        
    Returns:
        Complete workflow results
    """
    workflow_tasks = [
        {
            "id": f"extract_{document_id}",
            "description": f"Extract data from document {document_id}",
            "expected_output": "Structured data extraction results",
            "agent_role": AgentRole.DATA_EXTRACTION.value,
            "context": {"document_id": document_id}
        },
        {
            "id": f"generate_{template_id}",
            "description": f"Generate contract using template {template_id}",
            "expected_output": "Generated contract document",
            "agent_role": AgentRole.CONTRACT_GENERATOR.value,
            "context": {"template_id": template_id},
            "dependencies": [f"extract_{document_id}"]
        },
        {
            "id": f"compliance_check",
            "description": "Check contract compliance",
            "expected_output": "Compliance validation report",
            "agent_role": AgentRole.COMPLIANCE_CHECKER.value,
            "context": {"check_type": "full"},
            "dependencies": [f"generate_{template_id}"]
        },
        {
            "id": f"signature_setup",
            "description": "Initialize signature workflow",
            "expected_output": "Signature workflow setup results",
            "agent_role": AgentRole.SIGNATURE_TRACKER.value,
            "context": {"signers": signers},
            "dependencies": [f"compliance_check"]
        },
        {
            "id": f"summary_generation",
            "description": "Generate workflow summary",
            "expected_output": "Complete workflow summary",
            "agent_role": AgentRole.SUMMARY_AGENT.value,
            "context": {"summary_type": "workflow"},
            "dependencies": [f"signature_setup"]
        }
    ]
    
    return execute_agent_workflow.delay(
        tasks_data=workflow_tasks,
        user_id=user_id
    ).get()
