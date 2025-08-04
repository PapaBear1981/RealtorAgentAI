"""
Agent Performance Metrics Service.

This service handles tracking and analysis of AI agent performance metrics
including execution times, success rates, error rates, and resource usage.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlmodel import Session, select, func, and_, or_, desc
from sqlalchemy.exc import SQLAlchemyError

from ...core.database import get_session_context
from ...models.analytics import (
    AgentExecution, AgentPerformanceMetric, AgentExecutionPublic,
    AgentPerformanceMetricPublic, AgentPerformanceDashboard,
    AgentType, ExecutionStatus, MetricType
)
from ...models.user import User

logger = logging.getLogger(__name__)


class AgentMetricsServiceError(Exception):
    """Exception raised during agent metrics service operations."""
    pass


class AgentMetricsService:
    """
    Service for tracking and analyzing AI agent performance metrics.

    Provides functionality to:
    - Track agent executions
    - Calculate performance metrics
    - Generate performance reports
    - Monitor agent health
    """

    def __init__(self):
        self.logger = logger

    async def start_agent_execution(
        self,
        agent_type: AgentType,
        user_id: Optional[int] = None,
        deal_id: Optional[int] = None,
        contract_id: Optional[int] = None,
        input_data: Optional[Dict[str, Any]] = None,
        agent_version: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Start tracking a new agent execution.

        Args:
            agent_type: Type of agent being executed
            user_id: ID of user initiating the execution
            deal_id: ID of deal being processed
            contract_id: ID of contract being processed
            input_data: Input data for the agent
            agent_version: Version of the agent
            additional_data: Additional metadata

        Returns:
            execution_id: Unique identifier for the execution

        Raises:
            AgentMetricsServiceError: If execution tracking fails
        """
        try:
            async with get_session_context() as session:
                execution = AgentExecution(
                    agent_type=agent_type,
                    agent_version=agent_version,
                    status=ExecutionStatus.STARTED,
                    user_id=user_id,
                    deal_id=deal_id,
                    contract_id=contract_id,
                    input_data=input_data,
                    additional_data=additional_data
                )

                session.add(execution)
                await session.commit()
                await session.refresh(execution)

                self.logger.info(
                    f"Started tracking agent execution",
                    execution_id=execution.execution_id,
                    agent_type=agent_type.value,
                    user_id=user_id
                )

                return execution.execution_id

        except SQLAlchemyError as e:
            self.logger.error(f"Database error starting agent execution: {e}")
            raise AgentMetricsServiceError(f"Failed to start execution tracking: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error starting agent execution: {e}")
            raise AgentMetricsServiceError(f"Unexpected error: {str(e)}")

    async def update_agent_execution(
        self,
        execution_id: str,
        status: Optional[ExecutionStatus] = None,
        output_data: Optional[Dict[str, Any]] = None,
        success: Optional[bool] = None,
        error_message: Optional[str] = None,
        error_code: Optional[str] = None,
        cpu_usage_percent: Optional[float] = None,
        memory_usage_mb: Optional[float] = None,
        tokens_consumed: Optional[int] = None,
        api_calls_made: Optional[int] = None,
        estimated_cost: Optional[float] = None
    ) -> bool:
        """
        Update an existing agent execution with progress or completion data.

        Args:
            execution_id: Unique identifier for the execution
            status: Current execution status
            output_data: Output data from the agent
            success: Whether the execution was successful
            error_message: Error message if execution failed
            error_code: Error code if execution failed
            cpu_usage_percent: CPU usage percentage
            memory_usage_mb: Memory usage in MB
            tokens_consumed: Number of tokens consumed
            api_calls_made: Number of API calls made
            estimated_cost: Estimated cost of execution

        Returns:
            bool: True if update was successful

        Raises:
            AgentMetricsServiceError: If update fails
        """
        try:
            async with get_session_context() as session:
                # Find the execution
                stmt = select(AgentExecution).where(
                    AgentExecution.execution_id == execution_id
                )
                result = await session.exec(stmt)
                execution = result.first()

                if not execution:
                    raise AgentMetricsServiceError(f"Execution not found: {execution_id}")

                # Update fields
                if status is not None:
                    execution.status = status

                    # Set completion time if status indicates completion
                    if status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED,
                                ExecutionStatus.TIMEOUT, ExecutionStatus.CANCELLED]:
                        execution.completed_at = datetime.utcnow()

                        # Calculate duration
                        if execution.started_at:
                            duration = execution.completed_at - execution.started_at
                            execution.duration_ms = int(duration.total_seconds() * 1000)

                if output_data is not None:
                    execution.output_data = output_data
                if success is not None:
                    execution.success = success
                if error_message is not None:
                    execution.error_message = error_message
                if error_code is not None:
                    execution.error_code = error_code
                if cpu_usage_percent is not None:
                    execution.cpu_usage_percent = cpu_usage_percent
                if memory_usage_mb is not None:
                    execution.memory_usage_mb = memory_usage_mb
                if tokens_consumed is not None:
                    execution.tokens_consumed = tokens_consumed
                if api_calls_made is not None:
                    execution.api_calls_made = api_calls_made
                if estimated_cost is not None:
                    execution.estimated_cost = estimated_cost

                await session.commit()

                self.logger.info(
                    f"Updated agent execution",
                    execution_id=execution_id,
                    status=status.value if status else None,
                    success=success
                )

                return True

        except SQLAlchemyError as e:
            self.logger.error(f"Database error updating agent execution: {e}")
            raise AgentMetricsServiceError(f"Failed to update execution: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error updating agent execution: {e}")
            raise AgentMetricsServiceError(f"Unexpected error: {str(e)}")

    async def complete_agent_execution(
        self,
        execution_id: str,
        success: bool,
        output_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        error_code: Optional[str] = None,
        tokens_consumed: Optional[int] = None,
        estimated_cost: Optional[float] = None
    ) -> bool:
        """
        Mark an agent execution as completed.

        Args:
            execution_id: Unique identifier for the execution
            success: Whether the execution was successful
            output_data: Output data from the agent
            error_message: Error message if execution failed
            error_code: Error code if execution failed
            tokens_consumed: Number of tokens consumed
            estimated_cost: Estimated cost of execution

        Returns:
            bool: True if completion was successful
        """
        status = ExecutionStatus.COMPLETED if success else ExecutionStatus.FAILED

        return await self.update_agent_execution(
            execution_id=execution_id,
            status=status,
            success=success,
            output_data=output_data,
            error_message=error_message,
            error_code=error_code,
            tokens_consumed=tokens_consumed,
            estimated_cost=estimated_cost
        )

    async def get_agent_executions(
        self,
        agent_type: Optional[AgentType] = None,
        user_id: Optional[int] = None,
        status: Optional[ExecutionStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AgentExecutionPublic]:
        """
        Get agent executions with filtering options.

        Args:
            agent_type: Filter by agent type
            user_id: Filter by user ID
            status: Filter by execution status
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of agent executions
        """
        try:
            async with get_session_context() as session:
                stmt = select(AgentExecution)

                # Apply filters
                conditions = []
                if agent_type:
                    conditions.append(AgentExecution.agent_type == agent_type)
                if user_id:
                    conditions.append(AgentExecution.user_id == user_id)
                if status:
                    conditions.append(AgentExecution.status == status)
                if start_date:
                    conditions.append(AgentExecution.started_at >= start_date)
                if end_date:
                    conditions.append(AgentExecution.started_at <= end_date)

                if conditions:
                    stmt = stmt.where(and_(*conditions))

                stmt = stmt.order_by(desc(AgentExecution.started_at))
                stmt = stmt.offset(offset).limit(limit)

                result = await session.exec(stmt)
                executions = result.all()

                return [
                    AgentExecutionPublic(
                        id=execution.id,
                        execution_id=execution.execution_id,
                        agent_type=execution.agent_type,
                        status=execution.status,
                        started_at=execution.started_at,
                        completed_at=execution.completed_at,
                        duration_ms=execution.duration_ms,
                        success=execution.success,
                        error_message=execution.error_message,
                        tokens_consumed=execution.tokens_consumed,
                        estimated_cost=execution.estimated_cost,
                        created_at=execution.created_at
                    )
                    for execution in executions
                ]

        except SQLAlchemyError as e:
            self.logger.error(f"Database error getting agent executions: {e}")
            raise AgentMetricsServiceError(f"Failed to get executions: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error getting agent executions: {e}")
            raise AgentMetricsServiceError(f"Unexpected error: {str(e)}")

    async def calculate_performance_metrics(
        self,
        agent_type: Optional[AgentType] = None,
        period_hours: int = 24,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Calculate performance metrics for agents.

        Args:
            agent_type: Filter by agent type
            period_hours: Time period in hours
            end_time: End time for calculation (defaults to now)

        Returns:
            Dictionary containing performance metrics
        """
        try:
            if end_time is None:
                end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=period_hours)

            async with get_session_context() as session:
                # Base query
                stmt = select(AgentExecution).where(
                    and_(
                        AgentExecution.started_at >= start_time,
                        AgentExecution.started_at <= end_time
                    )
                )

                if agent_type:
                    stmt = stmt.where(AgentExecution.agent_type == agent_type)

                result = await session.exec(stmt)
                executions = result.all()

                if not executions:
                    return {
                        "total_executions": 0,
                        "successful_executions": 0,
                        "failed_executions": 0,
                        "success_rate": 0.0,
                        "error_rate": 0.0,
                        "average_duration_ms": 0.0,
                        "total_cost": 0.0,
                        "average_cost": 0.0
                    }

                # Calculate metrics
                total_executions = len(executions)
                successful_executions = sum(1 for e in executions if e.success)
                failed_executions = total_executions - successful_executions

                success_rate = (successful_executions / total_executions) * 100
                error_rate = (failed_executions / total_executions) * 100

                # Duration metrics (only for completed executions)
                completed_executions = [e for e in executions if e.duration_ms is not None]
                average_duration_ms = 0.0
                if completed_executions:
                    average_duration_ms = sum(e.duration_ms for e in completed_executions) / len(completed_executions)

                # Cost metrics
                executions_with_cost = [e for e in executions if e.estimated_cost is not None]
                total_cost = sum(e.estimated_cost for e in executions_with_cost)
                average_cost = total_cost / len(executions_with_cost) if executions_with_cost else 0.0

                return {
                    "total_executions": total_executions,
                    "successful_executions": successful_executions,
                    "failed_executions": failed_executions,
                    "success_rate": success_rate,
                    "error_rate": error_rate,
                    "average_duration_ms": average_duration_ms,
                    "total_cost": total_cost,
                    "average_cost": average_cost,
                    "period_start": start_time,
                    "period_end": end_time
                }

        except SQLAlchemyError as e:
            self.logger.error(f"Database error calculating performance metrics: {e}")
            raise AgentMetricsServiceError(f"Failed to calculate metrics: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error calculating performance metrics: {e}")
            raise AgentMetricsServiceError(f"Unexpected error: {str(e)}")


# Service instance
agent_metrics_service = AgentMetricsService()
