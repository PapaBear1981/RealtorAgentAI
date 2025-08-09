"""
Performance Optimization and Monitoring API Endpoints.

This module provides API endpoints for performance monitoring, load balancing,
caching, database optimization, scaling management, and real-time alerting.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
import structlog

from ...core.dependencies import get_current_user
from ...core.ai_agent_auth import verify_admin_access
from ...models.user import User
from ...services.performance.load_balancer import get_load_balancer
from ...services.performance.cache_manager import get_cache_manager
from ...services.performance.database_optimizer import get_database_optimizer
from ...services.performance.scaling_manager import get_scaling_manager
from ...services.performance.memory_manager import get_memory_manager
from ...services.performance.monitoring_system import get_monitoring_system

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/performance", tags=["Performance Optimization"])


# Request/Response Models
class CacheInvalidationRequest(BaseModel):
    """Request model for cache invalidation."""
    pattern: str = Field(..., description="Cache invalidation pattern")
    levels: List[str] = Field(default=["L1_MEMORY"], description="Cache levels to invalidate")


class ScalingPolicyRequest(BaseModel):
    """Request model for scaling policy updates."""
    service_name: str = Field(..., description="Service name")
    min_instances: int = Field(1, description="Minimum instances")
    max_instances: int = Field(10, description="Maximum instances")
    target_cpu_utilization: float = Field(70.0, description="Target CPU utilization")
    scale_up_threshold: float = Field(80.0, description="Scale up threshold")
    scale_down_threshold: float = Field(30.0, description="Scale down threshold")
    enabled: bool = Field(True, description="Enable scaling policy")


class AlertRuleRequest(BaseModel):
    """Request model for alert rule configuration."""
    name: str = Field(..., description="Alert rule name")
    metric_name: str = Field(..., description="Metric name to monitor")
    condition: str = Field(..., description="Alert condition (gt, lt, eq, ne)")
    threshold: float = Field(..., description="Alert threshold value")
    severity: str = Field(..., description="Alert severity (info, warning, error, critical)")
    enabled: bool = Field(True, description="Enable alert rule")


# Load Balancing Endpoints

@router.get("/load-balancer/overview")
async def get_load_balancer_overview(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get load balancer system overview."""
    try:
        load_balancer = get_load_balancer()
        overview = load_balancer.get_system_overview()

        return {
            "status": "success",
            "data": overview,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get load balancer overview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve load balancer overview"
        )


@router.get("/load-balancer/pools/{pool_id}/statistics")
async def get_pool_statistics(
    pool_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get detailed statistics for a specific resource pool."""
    try:
        load_balancer = get_load_balancer()
        stats = load_balancer.get_pool_statistics(pool_id)

        if not stats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pool {pool_id} not found"
            )

        return {
            "status": "success",
            "data": stats,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get pool statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve pool statistics"
        )


# Caching Endpoints

@router.get("/cache/statistics")
async def get_cache_statistics(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get comprehensive cache performance statistics."""
    try:
        cache_manager = get_cache_manager()
        stats = cache_manager.get_performance_stats()

        return {
            "status": "success",
            "data": stats,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get cache statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cache statistics"
        )


@router.post("/cache/invalidate")
async def invalidate_cache(
    request: CacheInvalidationRequest,
    current_user: User = Depends(verify_admin_access)
) -> Dict[str, Any]:
    """Invalidate cache entries matching pattern."""
    try:
        cache_manager = get_cache_manager()
        invalidated_count = await cache_manager.invalidate_by_pattern(request.pattern)

        return {
            "status": "success",
            "message": f"Invalidated {invalidated_count} cache entries",
            "pattern": request.pattern,
            "invalidated_count": invalidated_count,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to invalidate cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to invalidate cache"
        )


@router.post("/cache/warm")
async def warm_cache(
    keys: List[str] = None,
    current_user: User = Depends(verify_admin_access)
) -> Dict[str, Any]:
    """Warm cache with frequently accessed data."""
    try:
        cache_manager = get_cache_manager()
        warmed_count = await cache_manager.warm_cache(keys)

        return {
            "status": "success",
            "message": f"Warmed cache with {warmed_count} entries",
            "warmed_count": warmed_count,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to warm cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to warm cache"
        )


# Database Optimization Endpoints

@router.get("/database/statistics")
async def get_database_statistics(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get database performance statistics."""
    try:
        db_optimizer = get_database_optimizer()
        stats = db_optimizer.get_performance_stats()

        return {
            "status": "success",
            "data": stats,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get database statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve database statistics"
        )


@router.get("/database/slow-queries")
async def get_slow_queries(
    threshold_seconds: float = Query(1.0, description="Threshold in seconds"),
    limit: int = Query(10, description="Maximum number of queries to return"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get slow database queries."""
    try:
        db_optimizer = get_database_optimizer()
        slow_queries = await db_optimizer.get_slow_queries(threshold_seconds, limit)

        return {
            "status": "success",
            "data": {
                "slow_queries": slow_queries,
                "threshold_seconds": threshold_seconds,
                "total_found": len(slow_queries)
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get slow queries: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve slow queries"
        )


@router.get("/database/optimization-recommendations")
async def get_optimization_recommendations(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get database optimization recommendations."""
    try:
        db_optimizer = get_database_optimizer()
        recommendations = db_optimizer.get_optimization_recommendations()

        return {
            "status": "success",
            "data": {
                "recommendations": recommendations,
                "total_recommendations": len(recommendations)
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get optimization recommendations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve optimization recommendations"
        )


# Scaling Management Endpoints

@router.get("/scaling/overview")
async def get_scaling_overview(
    service_name: Optional[str] = Query(None, description="Specific service name"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get scaling system overview."""
    try:
        scaling_manager = get_scaling_manager()
        overview = scaling_manager.get_service_overview(service_name)

        return {
            "status": "success",
            "data": overview,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get scaling overview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve scaling overview"
        )


@router.get("/scaling/history")
async def get_scaling_history(
    service_name: Optional[str] = Query(None, description="Specific service name"),
    limit: int = Query(50, description="Maximum number of events to return"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get scaling event history."""
    try:
        scaling_manager = get_scaling_manager()
        history = scaling_manager.get_scaling_history(service_name, limit)

        return {
            "status": "success",
            "data": {
                "scaling_events": history,
                "total_events": len(history)
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get scaling history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve scaling history"
        )


# Memory Management Endpoints

@router.get("/memory/statistics")
async def get_memory_statistics(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get comprehensive memory statistics."""
    try:
        memory_manager = get_memory_manager()
        stats = memory_manager.get_memory_stats()

        return {
            "status": "success",
            "data": stats,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get memory statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve memory statistics"
        )


@router.get("/memory/leaks")
async def get_memory_leaks(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get detected memory leaks."""
    try:
        memory_manager = get_memory_manager()
        leaks = memory_manager.get_memory_leaks()

        return {
            "status": "success",
            "data": {
                "memory_leaks": leaks,
                "total_leaks": len(leaks)
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get memory leaks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve memory leaks"
        )


@router.get("/memory/alerts")
async def get_memory_alerts(
    hours: int = Query(24, description="Hours to look back"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get recent memory alerts."""
    try:
        memory_manager = get_memory_manager()
        alerts = memory_manager.get_recent_alerts(hours)

        return {
            "status": "success",
            "data": {
                "memory_alerts": alerts,
                "total_alerts": len(alerts),
                "hours_back": hours
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get memory alerts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve memory alerts"
        )


# Monitoring and Alerting Endpoints

@router.get("/monitoring/dashboard")
async def get_monitoring_dashboard(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get comprehensive monitoring dashboard data."""
    try:
        monitoring_system = get_monitoring_system()
        dashboard_data = monitoring_system.get_dashboard_data()

        return {
            "status": "success",
            "data": dashboard_data,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get monitoring dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve monitoring dashboard"
        )


@router.get("/monitoring/metrics/{metric_name}/history")
async def get_metric_history(
    metric_name: str,
    hours: int = Query(24, description="Hours of history to retrieve"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get metric history for specified time period."""
    try:
        monitoring_system = get_monitoring_system()
        history = monitoring_system.get_metric_history(metric_name, hours)

        return {
            "status": "success",
            "data": {
                "metric_name": metric_name,
                "history": history,
                "data_points": len(history),
                "hours_back": hours
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get metric history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve metric history"
        )


# System Health Endpoint

@router.get("/health/comprehensive")
async def get_comprehensive_health_check(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get comprehensive system health check."""
    try:
        # Collect health data from all performance components
        load_balancer = get_load_balancer()
        cache_manager = get_cache_manager()
        db_optimizer = get_database_optimizer()
        scaling_manager = get_scaling_manager()
        memory_manager = get_memory_manager()
        monitoring_system = get_monitoring_system()

        health_data = {
            "load_balancer": {
                "status": "healthy",
                "total_agents": load_balancer.get_system_overview().get("total_agents", 0),
                "total_pools": load_balancer.get_system_overview().get("total_pools", 0)
            },
            "cache": {
                "status": "healthy",
                "hit_rate": cache_manager.get_performance_stats().get("multi_level_cache", {}).get("hit_rate", 0)
            },
            "database": {
                "status": "healthy",
                "total_queries": db_optimizer.get_performance_stats().get("query_performance", {}).get("total_queries", 0),
                "error_rate": db_optimizer.get_performance_stats().get("query_performance", {}).get("error_rate", 0)
            },
            "scaling": {
                "status": "healthy",
                "services_monitored": len(scaling_manager.get_service_overview())
            },
            "memory": {
                "status": "healthy",
                "usage_percent": memory_manager.get_memory_stats().get("current_memory", {}).get("usage_percent", 0),
                "leaks_detected": len(memory_manager.get_memory_leaks())
            },
            "monitoring": {
                "status": "healthy",
                "metrics_collected": len(monitoring_system.get_dashboard_data().get("metrics", {})),
                "active_alerts": monitoring_system.get_dashboard_data().get("alerts", {}).get("active", {}).get("total", 0)
            }
        }

        # Determine overall health status
        overall_status = "healthy"

        # Check for critical conditions
        if health_data["memory"]["usage_percent"] > 90:
            overall_status = "warning"
        if health_data["database"]["error_rate"] > 10:
            overall_status = "critical"
        if health_data["monitoring"]["active_alerts"] > 5:
            overall_status = "warning"

        return {
            "status": "success",
            "data": {
                "overall_status": overall_status,
                "components": health_data,
                "timestamp": datetime.utcnow().isoformat()
            }
        }

    except Exception as e:
        logger.error(f"Failed to get comprehensive health check: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system health"
        )
