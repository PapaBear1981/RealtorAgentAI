"""
Performance monitoring and auto-scaling for background processing.

This module provides performance monitoring, resource management,
and auto-scaling capabilities for Celery workers and task queues.
"""

import logging
import psutil
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

import structlog
from celery import Celery

from .redis_config import get_redis_client
from .config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class ScalingAction(Enum):
    """Scaling action types."""
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    NO_ACTION = "no_action"


@dataclass
class PerformanceMetrics:
    """Performance metrics data structure."""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    queue_lengths: Dict[str, int]
    active_tasks: int
    worker_count: int
    avg_task_duration: float
    error_rate: float
    throughput: float  # tasks per minute


@dataclass
class ScalingDecision:
    """Scaling decision data structure."""
    action: ScalingAction
    queue_name: str
    current_workers: int
    target_workers: int
    reason: str
    confidence: float


class PerformanceMonitor:
    """
    Performance monitoring and auto-scaling system.
    
    Monitors system resources, task queue performance, and worker
    efficiency to make intelligent scaling decisions.
    """
    
    def __init__(self, celery_app: Celery):
        self.celery_app = celery_app
        self.redis_client = get_redis_client()
        
        # Configuration
        self.monitoring_interval = getattr(settings, 'MONITORING_INTERVAL', 60)  # seconds
        self.scaling_cooldown = getattr(settings, 'SCALING_COOLDOWN', 300)  # seconds
        self.max_workers_per_queue = getattr(settings, 'MAX_WORKERS_PER_QUEUE', 10)
        self.min_workers_per_queue = getattr(settings, 'MIN_WORKERS_PER_QUEUE', 1)
        
        # Scaling thresholds
        self.cpu_scale_up_threshold = 75.0
        self.cpu_scale_down_threshold = 25.0
        self.memory_scale_up_threshold = 80.0
        self.queue_length_scale_up_threshold = 10
        self.queue_length_scale_down_threshold = 2
        self.error_rate_threshold = 5.0  # percent
        
        # Metrics history
        self.metrics_history: List[PerformanceMetrics] = []
        self.max_history_size = 100
        
        # Last scaling actions
        self.last_scaling_actions: Dict[str, datetime] = {}
    
    def collect_metrics(self) -> PerformanceMetrics:
        """
        Collect current performance metrics.
        
        Returns:
            PerformanceMetrics: Current system metrics
        """
        try:
            # System resource metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Queue length metrics
            queue_lengths = {}
            for queue_name in ['ingest', 'ocr', 'llm', 'export', 'system']:
                try:
                    length = self.redis_client.llen(queue_name)
                    queue_lengths[queue_name] = length
                except Exception:
                    queue_lengths[queue_name] = 0
            
            # Worker and task metrics
            inspect = self.celery_app.control.inspect()
            active_tasks_data = inspect.active() or {}
            active_tasks = sum(len(tasks) for tasks in active_tasks_data.values())
            worker_count = len(active_tasks_data)
            
            # Calculate average task duration and throughput
            avg_task_duration, error_rate, throughput = self._calculate_task_metrics()
            
            metrics = PerformanceMetrics(
                timestamp=datetime.utcnow(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                disk_percent=disk.percent,
                queue_lengths=queue_lengths,
                active_tasks=active_tasks,
                worker_count=worker_count,
                avg_task_duration=avg_task_duration,
                error_rate=error_rate,
                throughput=throughput
            )
            
            # Add to history
            self.metrics_history.append(metrics)
            if len(self.metrics_history) > self.max_history_size:
                self.metrics_history.pop(0)
            
            logger.info(
                "Performance metrics collected",
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                active_tasks=active_tasks,
                worker_count=worker_count,
                total_queue_length=sum(queue_lengths.values())
            )
            
            return metrics
            
        except Exception as e:
            logger.error("Failed to collect performance metrics", error=str(e))
            raise
    
    def _calculate_task_metrics(self) -> tuple[float, float, float]:
        """
        Calculate task performance metrics from recent history.
        
        Returns:
            tuple: (avg_task_duration, error_rate, throughput)
        """
        if len(self.metrics_history) < 2:
            return 0.0, 0.0, 0.0
        
        # Simple calculations based on available data
        # In production, would use more sophisticated metrics from task results
        
        recent_metrics = self.metrics_history[-10:]  # Last 10 data points
        
        # Average task duration (placeholder calculation)
        avg_duration = 30.0  # Default 30 seconds
        
        # Error rate (placeholder calculation)
        error_rate = 2.0  # Default 2% error rate
        
        # Throughput calculation
        if len(recent_metrics) >= 2:
            time_diff = (recent_metrics[-1].timestamp - recent_metrics[0].timestamp).total_seconds()
            if time_diff > 0:
                # Estimate throughput based on queue changes
                throughput = 10.0  # Default 10 tasks per minute
            else:
                throughput = 0.0
        else:
            throughput = 0.0
        
        return avg_duration, error_rate, throughput
    
    def analyze_scaling_needs(self, metrics: PerformanceMetrics) -> List[ScalingDecision]:
        """
        Analyze current metrics and determine scaling needs.
        
        Args:
            metrics: Current performance metrics
            
        Returns:
            List[ScalingDecision]: Scaling decisions for each queue
        """
        decisions = []
        
        for queue_name, queue_length in metrics.queue_lengths.items():
            decision = self._analyze_queue_scaling(queue_name, queue_length, metrics)
            if decision.action != ScalingAction.NO_ACTION:
                decisions.append(decision)
        
        return decisions
    
    def _analyze_queue_scaling(
        self,
        queue_name: str,
        queue_length: int,
        metrics: PerformanceMetrics
    ) -> ScalingDecision:
        """
        Analyze scaling needs for a specific queue.
        
        Args:
            queue_name: Name of the queue
            queue_length: Current queue length
            metrics: Current performance metrics
            
        Returns:
            ScalingDecision: Scaling decision for the queue
        """
        # Check cooldown period
        last_action_time = self.last_scaling_actions.get(queue_name)
        if last_action_time:
            time_since_last_action = (datetime.utcnow() - last_action_time).total_seconds()
            if time_since_last_action < self.scaling_cooldown:
                return ScalingDecision(
                    action=ScalingAction.NO_ACTION,
                    queue_name=queue_name,
                    current_workers=0,
                    target_workers=0,
                    reason="Cooldown period active",
                    confidence=1.0
                )
        
        # Estimate current workers for this queue (simplified)
        current_workers = max(1, metrics.worker_count // 5)  # Rough estimate
        
        # Scale up conditions
        scale_up_reasons = []
        if queue_length > self.queue_length_scale_up_threshold:
            scale_up_reasons.append(f"Queue length ({queue_length}) exceeds threshold")
        
        if metrics.cpu_percent > self.cpu_scale_up_threshold:
            scale_up_reasons.append(f"CPU usage ({metrics.cpu_percent}%) is high")
        
        if metrics.memory_percent > self.memory_scale_up_threshold:
            scale_up_reasons.append(f"Memory usage ({metrics.memory_percent}%) is high")
        
        if metrics.error_rate > self.error_rate_threshold:
            scale_up_reasons.append(f"Error rate ({metrics.error_rate}%) is high")
        
        # Scale down conditions
        scale_down_reasons = []
        if (queue_length < self.queue_length_scale_down_threshold and
            metrics.cpu_percent < self.cpu_scale_down_threshold and
            current_workers > self.min_workers_per_queue):
            scale_down_reasons.append("Low queue length and CPU usage")
        
        # Make scaling decision
        if scale_up_reasons and current_workers < self.max_workers_per_queue:
            target_workers = min(current_workers + 1, self.max_workers_per_queue)
            return ScalingDecision(
                action=ScalingAction.SCALE_UP,
                queue_name=queue_name,
                current_workers=current_workers,
                target_workers=target_workers,
                reason="; ".join(scale_up_reasons),
                confidence=0.8
            )
        
        elif scale_down_reasons and current_workers > self.min_workers_per_queue:
            target_workers = max(current_workers - 1, self.min_workers_per_queue)
            return ScalingDecision(
                action=ScalingAction.SCALE_DOWN,
                queue_name=queue_name,
                current_workers=current_workers,
                target_workers=target_workers,
                reason="; ".join(scale_down_reasons),
                confidence=0.7
            )
        
        else:
            return ScalingDecision(
                action=ScalingAction.NO_ACTION,
                queue_name=queue_name,
                current_workers=current_workers,
                target_workers=current_workers,
                reason="No scaling needed",
                confidence=0.9
            )
    
    def execute_scaling_decision(self, decision: ScalingDecision) -> bool:
        """
        Execute a scaling decision.
        
        Args:
            decision: Scaling decision to execute
            
        Returns:
            bool: Whether the scaling action was successful
        """
        try:
            logger.info(
                "Executing scaling decision",
                action=decision.action.value,
                queue=decision.queue_name,
                current_workers=decision.current_workers,
                target_workers=decision.target_workers,
                reason=decision.reason
            )
            
            # In production, this would integrate with container orchestration
            # systems like Kubernetes, Docker Swarm, or AWS ECS to actually
            # scale the number of worker containers
            
            if decision.action == ScalingAction.SCALE_UP:
                success = self._scale_up_workers(decision.queue_name, decision.target_workers)
            elif decision.action == ScalingAction.SCALE_DOWN:
                success = self._scale_down_workers(decision.queue_name, decision.target_workers)
            else:
                success = True  # No action needed
            
            if success:
                self.last_scaling_actions[decision.queue_name] = datetime.utcnow()
                logger.info(
                    "Scaling action completed successfully",
                    queue=decision.queue_name,
                    action=decision.action.value
                )
            else:
                logger.error(
                    "Scaling action failed",
                    queue=decision.queue_name,
                    action=decision.action.value
                )
            
            return success
            
        except Exception as e:
            logger.error(
                "Failed to execute scaling decision",
                queue=decision.queue_name,
                action=decision.action.value,
                error=str(e)
            )
            return False
    
    def _scale_up_workers(self, queue_name: str, target_workers: int) -> bool:
        """
        Scale up workers for a specific queue.
        
        Args:
            queue_name: Name of the queue
            target_workers: Target number of workers
            
        Returns:
            bool: Whether scaling was successful
        """
        # Placeholder for actual scaling implementation
        # In production, would use container orchestration APIs
        logger.info(f"Scaling up {queue_name} workers to {target_workers}")
        return True
    
    def _scale_down_workers(self, queue_name: str, target_workers: int) -> bool:
        """
        Scale down workers for a specific queue.
        
        Args:
            queue_name: Name of the queue
            target_workers: Target number of workers
            
        Returns:
            bool: Whether scaling was successful
        """
        # Placeholder for actual scaling implementation
        # In production, would use container orchestration APIs
        logger.info(f"Scaling down {queue_name} workers to {target_workers}")
        return True
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get performance summary and recommendations.
        
        Returns:
            Dict: Performance summary
        """
        if not self.metrics_history:
            return {"error": "No metrics available"}
        
        latest_metrics = self.metrics_history[-1]
        
        # Calculate averages over recent history
        recent_metrics = self.metrics_history[-10:]
        avg_cpu = sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m.memory_percent for m in recent_metrics) / len(recent_metrics)
        avg_throughput = sum(m.throughput for m in recent_metrics) / len(recent_metrics)
        
        return {
            "timestamp": latest_metrics.timestamp.isoformat(),
            "current_metrics": {
                "cpu_percent": latest_metrics.cpu_percent,
                "memory_percent": latest_metrics.memory_percent,
                "disk_percent": latest_metrics.disk_percent,
                "active_tasks": latest_metrics.active_tasks,
                "worker_count": latest_metrics.worker_count,
                "total_queue_length": sum(latest_metrics.queue_lengths.values())
            },
            "averages": {
                "cpu_percent": round(avg_cpu, 2),
                "memory_percent": round(avg_memory, 2),
                "throughput": round(avg_throughput, 2)
            },
            "queue_lengths": latest_metrics.queue_lengths,
            "performance_status": self._get_performance_status(latest_metrics),
            "recommendations": self._get_recommendations(latest_metrics)
        }
    
    def _get_performance_status(self, metrics: PerformanceMetrics) -> str:
        """Get overall performance status."""
        if (metrics.cpu_percent > 90 or metrics.memory_percent > 90 or
            sum(metrics.queue_lengths.values()) > 50):
            return "critical"
        elif (metrics.cpu_percent > 75 or metrics.memory_percent > 75 or
              sum(metrics.queue_lengths.values()) > 20):
            return "warning"
        else:
            return "healthy"
    
    def _get_recommendations(self, metrics: PerformanceMetrics) -> List[str]:
        """Get performance recommendations."""
        recommendations = []
        
        if metrics.cpu_percent > 80:
            recommendations.append("Consider scaling up workers due to high CPU usage")
        
        if metrics.memory_percent > 85:
            recommendations.append("Monitor memory usage - consider increasing worker memory limits")
        
        if sum(metrics.queue_lengths.values()) > 30:
            recommendations.append("High queue backlog detected - consider scaling up workers")
        
        if metrics.error_rate > 5:
            recommendations.append("High error rate detected - investigate task failures")
        
        if not recommendations:
            recommendations.append("System performance is optimal")
        
        return recommendations


# Global performance monitor instance
_performance_monitor = None


def get_performance_monitor(celery_app: Celery) -> PerformanceMonitor:
    """
    Get global performance monitor instance.
    
    Args:
        celery_app: Celery application instance
        
    Returns:
        PerformanceMonitor: Performance monitor instance
    """
    global _performance_monitor
    
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor(celery_app)
    
    return _performance_monitor
