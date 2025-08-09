"""
Analytics API endpoints for RealtorAgentAI.

This module provides REST API endpoints for analytics and reporting
including agent performance metrics, contract processing statistics,
cost analysis, user behavior analytics, and predictive analytics.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from ...core.dependencies import get_current_user
from ...models.user import User
from ...models.analytics import (
    AgentType, ExecutionStatus, MetricType, CostCategory, EventType, ReportType,
    AgentExecutionPublic, AgentPerformanceMetricPublic, ContractProcessingMetricPublic,
    CostTrackingPublic, UserBehaviorEventPublic, WorkflowPatternPublic,
    PredictiveModelPublic, AnalyticsReportPublic,
    AgentPerformanceDashboard, ContractProcessingDashboard, CostAnalysisDashboard,
    UserBehaviorDashboard, PredictiveAnalyticsDashboard, ExecutiveSummaryDashboard
)
from ...services.analytics.agent_metrics_service import agent_metrics_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["analytics"])


# Request/Response Models

class AgentExecutionStartRequest(BaseModel):
    """Request model for starting agent execution tracking."""
    agent_type: AgentType
    deal_id: Optional[int] = None
    contract_id: Optional[int] = None
    input_data: Optional[Dict[str, Any]] = None
    agent_version: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None


class AgentExecutionUpdateRequest(BaseModel):
    """Request model for updating agent execution."""
    status: Optional[ExecutionStatus] = None
    output_data: Optional[Dict[str, Any]] = None
    success: Optional[bool] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    cpu_usage_percent: Optional[float] = Field(None, ge=0, le=100)
    memory_usage_mb: Optional[float] = Field(None, ge=0)
    tokens_consumed: Optional[int] = Field(None, ge=0)
    api_calls_made: Optional[int] = Field(None, ge=0)
    estimated_cost: Optional[float] = Field(None, ge=0)


class AgentExecutionCompleteRequest(BaseModel):
    """Request model for completing agent execution."""
    success: bool
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    tokens_consumed: Optional[int] = Field(None, ge=0)
    estimated_cost: Optional[float] = Field(None, ge=0)


class PerformanceMetricsResponse(BaseModel):
    """Response model for performance metrics."""
    total_executions: int
    successful_executions: int
    failed_executions: int
    success_rate: float
    error_rate: float
    average_duration_ms: float
    total_cost: float
    average_cost: float
    period_start: datetime
    period_end: datetime


class AnalyticsFilterParams(BaseModel):
    """Common filter parameters for analytics queries."""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    user_id: Optional[int] = None
    deal_id: Optional[int] = None
    contract_id: Optional[int] = None


# Agent Performance Metrics Endpoints

@router.post("/agent-executions/start", response_model=Dict[str, str])
async def start_agent_execution(
    request: AgentExecutionStartRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """
    Start tracking a new agent execution.

    Args:
        request: Agent execution start request
        current_user: Current authenticated user

    Returns:
        Dictionary containing the execution_id

    Raises:
        HTTPException: If execution tracking fails
    """
    try:
        execution_id = await agent_metrics_service.start_agent_execution(
            agent_type=request.agent_type,
            user_id=current_user.id,
            deal_id=request.deal_id,
            contract_id=request.contract_id,
            input_data=request.input_data,
            agent_version=request.agent_version,
            additional_data=request.additional_data
        )

        return {"execution_id": execution_id}

    except Exception as e:
        logger.error(f"Failed to start agent execution: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start execution tracking: {str(e)}"
        )


@router.put("/agent-executions/{execution_id}")
async def update_agent_execution(
    execution_id: str,
    request: AgentExecutionUpdateRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, bool]:
    """
    Update an existing agent execution.

    Args:
        execution_id: Unique identifier for the execution
        request: Agent execution update request
        current_user: Current authenticated user

    Returns:
        Dictionary indicating success

    Raises:
        HTTPException: If update fails
    """
    try:
        success = await agent_metrics_service.update_agent_execution(
            execution_id=execution_id,
            status=request.status,
            output_data=request.output_data,
            success=request.success,
            error_message=request.error_message,
            error_code=request.error_code,
            cpu_usage_percent=request.cpu_usage_percent,
            memory_usage_mb=request.memory_usage_mb,
            tokens_consumed=request.tokens_consumed,
            api_calls_made=request.api_calls_made,
            estimated_cost=request.estimated_cost
        )

        return {"success": success}

    except Exception as e:
        logger.error(f"Failed to update agent execution: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update execution: {str(e)}"
        )


@router.post("/agent-executions/{execution_id}/complete")
async def complete_agent_execution(
    execution_id: str,
    request: AgentExecutionCompleteRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, bool]:
    """
    Mark an agent execution as completed.

    Args:
        execution_id: Unique identifier for the execution
        request: Agent execution completion request
        current_user: Current authenticated user

    Returns:
        Dictionary indicating success

    Raises:
        HTTPException: If completion fails
    """
    try:
        success = await agent_metrics_service.complete_agent_execution(
            execution_id=execution_id,
            success=request.success,
            output_data=request.output_data,
            error_message=request.error_message,
            error_code=request.error_code,
            tokens_consumed=request.tokens_consumed,
            estimated_cost=request.estimated_cost
        )

        return {"success": success}

    except Exception as e:
        logger.error(f"Failed to complete agent execution: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete execution: {str(e)}"
        )


@router.get("/agent-executions", response_model=List[AgentExecutionPublic])
async def get_agent_executions(
    agent_type: Optional[AgentType] = Query(None, description="Filter by agent type"),
    status: Optional[ExecutionStatus] = Query(None, description="Filter by execution status"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    current_user: User = Depends(get_current_user)
) -> List[AgentExecutionPublic]:
    """
    Get agent executions with filtering options.

    Args:
        agent_type: Filter by agent type
        status: Filter by execution status
        start_date: Filter by start date
        end_date: Filter by end date
        limit: Maximum number of results
        offset: Number of results to skip
        current_user: Current authenticated user

    Returns:
        List of agent executions

    Raises:
        HTTPException: If retrieval fails
    """
    try:
        # Non-admin users can only see their own executions
        user_id = None if current_user.role == "admin" else current_user.id

        executions = await agent_metrics_service.get_agent_executions(
            agent_type=agent_type,
            user_id=user_id,
            status=status,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )

        return executions

    except Exception as e:
        logger.error(f"Failed to get agent executions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get executions: {str(e)}"
        )


@router.get("/agent-performance/metrics", response_model=PerformanceMetricsResponse)
async def get_agent_performance_metrics(
    agent_type: Optional[AgentType] = Query(None, description="Filter by agent type"),
    period_hours: int = Query(24, ge=1, le=8760, description="Time period in hours"),
    end_time: Optional[datetime] = Query(None, description="End time for calculation"),
    current_user: User = Depends(get_current_user)
) -> PerformanceMetricsResponse:
    """
    Get agent performance metrics.

    Args:
        agent_type: Filter by agent type
        period_hours: Time period in hours
        end_time: End time for calculation
        current_user: Current authenticated user

    Returns:
        Performance metrics

    Raises:
        HTTPException: If calculation fails
    """
    try:
        metrics = await agent_metrics_service.calculate_performance_metrics(
            agent_type=agent_type,
            period_hours=period_hours,
            end_time=end_time
        )

        return PerformanceMetricsResponse(**metrics)

    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get metrics: {str(e)}"
        )


# Dashboard Endpoints

@router.get("/dashboard/overview", response_model=Dict[str, Any])
async def get_dashboard_overview(
    period_hours: int = Query(24, ge=1, le=8760, description="Time period in hours"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get dashboard overview metrics.

    Args:
        period_hours: Time period in hours
        current_user: Current authenticated user

    Returns:
        Dashboard overview data

    Raises:
        HTTPException: If dashboard generation fails
    """
    try:
        # For now, return mock data since the services aren't fully implemented
        # TODO: Replace with actual service calls when analytics services are ready

        dashboard_data = {
            "totalAgentExecutions": 0,
            "successRate": 0.0,
            "averageProcessingTime": 0.0,
            "totalCost": 0.0,
            "activeUsers": 1,  # Current user
            "contractsProcessed": 0,
            "dealsInProgress": 0,
            "pendingSignatures": 0,
            "complianceAlerts": 0,
            "recentUploads": 0,
            "generated_at": datetime.utcnow().isoformat()
        }

        return dashboard_data

    except Exception as e:
        logger.error(f"Failed to get dashboard overview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dashboard overview: {str(e)}"
        )


@router.get("/dashboard/agent-performance", response_model=Dict[str, Any])
async def get_agent_performance_dashboard(
    period_hours: int = Query(24, ge=1, le=8760, description="Time period in hours"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get agent performance dashboard data.

    Args:
        period_hours: Time period in hours
        current_user: Current authenticated user

    Returns:
        Dashboard data

    Raises:
        HTTPException: If dashboard generation fails
    """
    try:
        # Get overall metrics
        overall_metrics = await agent_metrics_service.calculate_performance_metrics(
            period_hours=period_hours
        )

        # Get metrics by agent type
        agent_metrics = {}
        for agent_type in AgentType:
            metrics = await agent_metrics_service.calculate_performance_metrics(
                agent_type=agent_type,
                period_hours=period_hours
            )
            agent_metrics[agent_type.value] = metrics

        # Get recent executions
        recent_executions = await agent_metrics_service.get_agent_executions(
            limit=10
        )

        dashboard_data = {
            "overall_metrics": overall_metrics,
            "agent_metrics": agent_metrics,
            "recent_executions": recent_executions,
            "generated_at": datetime.utcnow().isoformat()
        }

        return dashboard_data

    except Exception as e:
        logger.error(f"Failed to get agent performance dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dashboard: {str(e)}"
        )


# Health Check Endpoint

@router.get("/health")
async def analytics_health_check() -> Dict[str, str]:
    """
    Health check endpoint for analytics service.

    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "service": "analytics",
        "timestamp": datetime.utcnow().isoformat()
    }
