"""
Real-Time Monitoring and Alerting System for AI Agent Performance.

This module provides comprehensive performance monitoring, real-time alerting,
metrics collection, and automated performance optimization recommendations.
"""

import asyncio
import time
import json
from typing import Dict, List, Any, Optional, Callable, Union
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import structlog
from collections import defaultdict, deque
import statistics
import uuid

from .load_balancer import get_load_balancer
from .cache_manager import get_cache_manager
from .database_optimizer import get_database_optimizer
from .scaling_manager import get_scaling_manager
from .memory_manager import get_memory_manager

logger = structlog.get_logger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MetricType(Enum):
    """Types of metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class AlertChannel(Enum):
    """Alert notification channels."""
    LOG = "log"
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    SMS = "sms"


@dataclass
class Metric:
    """Performance metric data point."""
    name: str
    value: float
    metric_type: MetricType
    timestamp: datetime = field(default_factory=datetime.utcnow)
    tags: Dict[str, str] = field(default_factory=dict)
    unit: str = ""


@dataclass
class Alert:
    """Performance alert."""
    alert_id: str
    name: str
    severity: AlertSeverity
    message: str
    metric_name: str
    current_value: float
    threshold: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class AlertRule:
    """Alert rule configuration."""
    rule_id: str
    name: str
    metric_name: str
    condition: str  # "gt", "lt", "eq", "ne"
    threshold: float
    severity: AlertSeverity
    evaluation_window: timedelta = field(default_factory=lambda: timedelta(minutes=5))
    cooldown_period: timedelta = field(default_factory=lambda: timedelta(minutes=15))
    enabled: bool = True
    channels: List[AlertChannel] = field(default_factory=list)
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class PerformanceRecommendation:
    """Performance optimization recommendation."""
    recommendation_id: str
    category: str
    title: str
    description: str
    impact: str  # "low", "medium", "high"
    effort: str  # "low", "medium", "high"
    priority_score: float
    metrics_evidence: List[str]
    suggested_actions: List[str]
    created_at: datetime = field(default_factory=datetime.utcnow)


class RealTimeMonitoringSystem:
    """Comprehensive real-time monitoring and alerting system."""

    def __init__(self):
        self.metrics_buffer: deque = deque(maxlen=10000)
        self.metrics_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: deque = deque(maxlen=1000)
        self.alert_rules: Dict[str, AlertRule] = {}
        self.alert_cooldowns: Dict[str, datetime] = {}

        # Performance recommendations
        self.recommendations: Dict[str, PerformanceRecommendation] = {}
        self.recommendation_engine_enabled = True

        # Monitoring configuration
        self.monitoring_enabled = True
        self.metrics_collection_interval = 10  # seconds
        self.alert_evaluation_interval = 30  # seconds
        self.recommendation_generation_interval = 300  # 5 minutes

        # Alert channels and callbacks
        self.alert_callbacks: Dict[AlertChannel, List[Callable]] = defaultdict(list)
        self.webhook_urls: Dict[str, str] = {}

        # Performance baselines
        self.performance_baselines: Dict[str, float] = {}
        self.baseline_calculation_window = timedelta(hours=24)

        # Initialize default alert rules
        self._initialize_default_alert_rules()

        # Background tasks will be started when needed
        self._monitoring_tasks_started = False

    def _initialize_default_alert_rules(self):
        """Initialize default alert rules for system monitoring."""
        default_rules = [
            # Memory alerts
            AlertRule(
                rule_id="memory_usage_high",
                name="High Memory Usage",
                metric_name="system.memory.usage_percent",
                condition="gt",
                threshold=85.0,
                severity=AlertSeverity.WARNING,
                channels=[AlertChannel.LOG, AlertChannel.WEBHOOK]
            ),
            AlertRule(
                rule_id="memory_usage_critical",
                name="Critical Memory Usage",
                metric_name="system.memory.usage_percent",
                condition="gt",
                threshold=95.0,
                severity=AlertSeverity.CRITICAL,
                channels=[AlertChannel.LOG, AlertChannel.WEBHOOK]
            ),

            # Response time alerts
            AlertRule(
                rule_id="response_time_high",
                name="High Response Time",
                metric_name="agent.avg_response_time",
                condition="gt",
                threshold=5.0,
                severity=AlertSeverity.WARNING,
                channels=[AlertChannel.LOG]
            ),
            AlertRule(
                rule_id="response_time_critical",
                name="Critical Response Time",
                metric_name="agent.avg_response_time",
                condition="gt",
                threshold=10.0,
                severity=AlertSeverity.CRITICAL,
                channels=[AlertChannel.LOG, AlertChannel.WEBHOOK]
            ),

            # Error rate alerts
            AlertRule(
                rule_id="error_rate_high",
                name="High Error Rate",
                metric_name="agent.error_rate",
                condition="gt",
                threshold=5.0,
                severity=AlertSeverity.WARNING,
                channels=[AlertChannel.LOG]
            ),
            AlertRule(
                rule_id="error_rate_critical",
                name="Critical Error Rate",
                metric_name="agent.error_rate",
                condition="gt",
                threshold=15.0,
                severity=AlertSeverity.CRITICAL,
                channels=[AlertChannel.LOG, AlertChannel.WEBHOOK]
            ),

            # Cache performance alerts
            AlertRule(
                rule_id="cache_hit_rate_low",
                name="Low Cache Hit Rate",
                metric_name="cache.hit_rate",
                condition="lt",
                threshold=70.0,
                severity=AlertSeverity.WARNING,
                channels=[AlertChannel.LOG]
            ),

            # Database performance alerts
            AlertRule(
                rule_id="db_query_time_high",
                name="High Database Query Time",
                metric_name="database.avg_query_time",
                condition="gt",
                threshold=2.0,
                severity=AlertSeverity.WARNING,
                channels=[AlertChannel.LOG]
            )
        ]

        for rule in default_rules:
            self.alert_rules[rule.rule_id] = rule

    def _start_monitoring_tasks(self):
        """Start background monitoring tasks."""
        if not self._monitoring_tasks_started:
            try:
                asyncio.create_task(self._metrics_collection_loop())
                asyncio.create_task(self._alert_evaluation_loop())
                asyncio.create_task(self._recommendation_generation_loop())
                asyncio.create_task(self._baseline_calculation_loop())
                self._monitoring_tasks_started = True
            except RuntimeError:
                # No event loop running, tasks will be started when needed
                pass

    async def _metrics_collection_loop(self):
        """Background metrics collection loop."""
        while self.monitoring_enabled:
            try:
                await self._collect_system_metrics()
                await asyncio.sleep(self.metrics_collection_interval)

            except Exception as e:
                logger.error(f"Metrics collection loop error: {e}")
                await asyncio.sleep(5)

    async def _collect_system_metrics(self):
        """Collect comprehensive system metrics."""
        timestamp = datetime.utcnow()

        # Load balancer metrics
        load_balancer = get_load_balancer()
        lb_stats = load_balancer.get_system_overview()

        for pool_id, pool_stats in lb_stats.get("pool_statistics", {}).items():
            await self._record_metric(f"loadbalancer.{pool_id}.utilization", pool_stats["utilization_percent"], MetricType.GAUGE, {"pool": pool_id})
            await self._record_metric(f"loadbalancer.{pool_id}.response_time", pool_stats["avg_response_time"], MetricType.GAUGE, {"pool": pool_id})
            await self._record_metric(f"loadbalancer.{pool_id}.error_rate", pool_stats["error_rate"], MetricType.GAUGE, {"pool": pool_id})

        # Cache metrics
        cache_manager = get_cache_manager()
        cache_stats = cache_manager.get_performance_stats()

        multi_level_stats = cache_stats.get("multi_level_cache", {})
        await self._record_metric("cache.hit_rate", multi_level_stats.get("hit_rate", 0), MetricType.GAUGE)
        await self._record_metric("cache.response_time", multi_level_stats.get("avg_response_time_ms", 0), MetricType.GAUGE)

        l1_stats = cache_stats.get("l1_cache", {})
        await self._record_metric("cache.l1.size_mb", l1_stats.get("size_mb", 0), MetricType.GAUGE)
        await self._record_metric("cache.l1.hit_rate", l1_stats.get("hit_rate", 0), MetricType.GAUGE)

        # Database metrics
        db_optimizer = get_database_optimizer()
        db_stats = db_optimizer.get_performance_stats()

        query_stats = db_stats.get("query_performance", {})
        await self._record_metric("database.total_queries", query_stats.get("total_queries", 0), MetricType.COUNTER)
        await self._record_metric("database.error_rate", query_stats.get("error_rate", 0), MetricType.GAUGE)
        await self._record_metric("database.avg_query_time", query_stats.get("avg_execution_time", 0), MetricType.GAUGE)

        cache_perf = db_stats.get("cache_performance", {})
        await self._record_metric("database.cache_hit_rate", cache_perf.get("cache_hit_rate", 0), MetricType.GAUGE)

        # Scaling metrics
        scaling_manager = get_scaling_manager()
        scaling_overview = scaling_manager.get_service_overview()

        for service_name, service_stats in scaling_overview.items():
            instance_stats = service_stats.get("instance_count", {})
            metrics_stats = service_stats.get("metrics", {})

            await self._record_metric(f"scaling.{service_name}.healthy_instances", instance_stats.get("healthy", 0), MetricType.GAUGE, {"service": service_name})
            await self._record_metric(f"scaling.{service_name}.cpu_usage", metrics_stats.get("avg_cpu_usage", 0), MetricType.GAUGE, {"service": service_name})
            await self._record_metric(f"scaling.{service_name}.memory_usage", metrics_stats.get("avg_memory_usage", 0), MetricType.GAUGE, {"service": service_name})
            await self._record_metric(f"scaling.{service_name}.response_time", metrics_stats.get("avg_response_time", 0), MetricType.GAUGE, {"service": service_name})

        # Memory metrics
        memory_manager = get_memory_manager()
        memory_stats = memory_manager.get_memory_stats()

        current_memory = memory_stats.get("current_memory", {})
        await self._record_metric("system.memory.usage_percent", current_memory.get("usage_percent", 0), MetricType.GAUGE)
        await self._record_metric("system.memory.used_mb", current_memory.get("used_mb", 0), MetricType.GAUGE)
        await self._record_metric("system.memory.available_mb", current_memory.get("available_mb", 0), MetricType.GAUGE)

        process_memory = memory_stats.get("process_memory", {})
        await self._record_metric("system.process.memory_mb", process_memory.get("used_mb", 0), MetricType.GAUGE)
        await self._record_metric("system.process.memory_percent", process_memory.get("usage_percent", 0), MetricType.GAUGE)

        leak_stats = memory_stats.get("memory_leaks", {})
        await self._record_metric("system.memory.leaks_detected", leak_stats.get("detected_count", 0), MetricType.GAUGE)
        await self._record_metric("system.memory.critical_leaks", leak_stats.get("critical_leaks", 0), MetricType.GAUGE)

    async def _record_metric(self, name: str, value: float, metric_type: MetricType, tags: Dict[str, str] = None):
        """Record a metric data point."""
        metric = Metric(
            name=name,
            value=value,
            metric_type=metric_type,
            tags=tags or {}
        )

        self.metrics_buffer.append(metric)
        self.metrics_history[name].append(metric)

    async def _alert_evaluation_loop(self):
        """Background alert evaluation loop."""
        while self.monitoring_enabled:
            try:
                await self._evaluate_alert_rules()
                await asyncio.sleep(self.alert_evaluation_interval)

            except Exception as e:
                logger.error(f"Alert evaluation loop error: {e}")
                await asyncio.sleep(10)

    async def _evaluate_alert_rules(self):
        """Evaluate all alert rules against current metrics."""
        for rule_id, rule in self.alert_rules.items():
            if not rule.enabled:
                continue

            # Check cooldown
            if rule_id in self.alert_cooldowns:
                if datetime.utcnow() - self.alert_cooldowns[rule_id] < rule.cooldown_period:
                    continue

            # Get recent metrics for this rule
            if rule.metric_name not in self.metrics_history:
                continue

            recent_metrics = [
                m for m in self.metrics_history[rule.metric_name]
                if datetime.utcnow() - m.timestamp <= rule.evaluation_window
            ]

            if not recent_metrics:
                continue

            # Calculate aggregate value (using average for now)
            current_value = statistics.mean([m.value for m in recent_metrics])

            # Evaluate condition
            alert_triggered = False
            if rule.condition == "gt" and current_value > rule.threshold:
                alert_triggered = True
            elif rule.condition == "lt" and current_value < rule.threshold:
                alert_triggered = True
            elif rule.condition == "eq" and abs(current_value - rule.threshold) < 0.001:
                alert_triggered = True
            elif rule.condition == "ne" and abs(current_value - rule.threshold) >= 0.001:
                alert_triggered = True

            if alert_triggered:
                await self._trigger_alert(rule, current_value)

    async def _trigger_alert(self, rule: AlertRule, current_value: float):
        """Trigger an alert based on rule violation."""
        alert_id = f"{rule.rule_id}_{int(time.time())}"

        alert = Alert(
            alert_id=alert_id,
            name=rule.name,
            severity=rule.severity,
            message=f"{rule.name}: {rule.metric_name} is {current_value:.2f} (threshold: {rule.threshold:.2f})",
            metric_name=rule.metric_name,
            current_value=current_value,
            threshold=rule.threshold,
            tags=rule.tags
        )

        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)
        self.alert_cooldowns[rule.rule_id] = datetime.utcnow()

        logger.warning(f"Alert triggered: {alert.message}")

        # Send notifications
        await self._send_alert_notifications(alert, rule.channels)

    async def _send_alert_notifications(self, alert: Alert, channels: List[AlertChannel]):
        """Send alert notifications through specified channels."""
        for channel in channels:
            try:
                if channel == AlertChannel.LOG:
                    logger.warning(f"ALERT [{alert.severity.value.upper()}]: {alert.message}")

                elif channel == AlertChannel.WEBHOOK:
                    await self._send_webhook_alert(alert)

                # Other channels would be implemented here
                # elif channel == AlertChannel.EMAIL:
                #     await self._send_email_alert(alert)
                # elif channel == AlertChannel.SLACK:
                #     await self._send_slack_alert(alert)

            except Exception as e:
                logger.error(f"Failed to send alert via {channel.value}: {e}")

    async def _send_webhook_alert(self, alert: Alert):
        """Send alert via webhook."""
        # This would implement actual webhook sending
        webhook_payload = {
            "alert_id": alert.alert_id,
            "name": alert.name,
            "severity": alert.severity.value,
            "message": alert.message,
            "metric_name": alert.metric_name,
            "current_value": alert.current_value,
            "threshold": alert.threshold,
            "timestamp": alert.timestamp.isoformat(),
            "tags": alert.tags
        }

        logger.info(f"Webhook alert payload: {json.dumps(webhook_payload, indent=2)}")

    async def _recommendation_generation_loop(self):
        """Background performance recommendation generation loop."""
        while self.recommendation_engine_enabled:
            try:
                await self._generate_performance_recommendations()
                await asyncio.sleep(self.recommendation_generation_interval)

            except Exception as e:
                logger.error(f"Recommendation generation loop error: {e}")
                await asyncio.sleep(60)

    async def _generate_performance_recommendations(self):
        """Generate performance optimization recommendations."""
        recommendations = []

        # Analyze cache performance
        cache_manager = get_cache_manager()
        cache_stats = cache_manager.get_performance_stats()

        hit_rate = cache_stats.get("multi_level_cache", {}).get("hit_rate", 0)
        if hit_rate < 70:
            recommendations.append(PerformanceRecommendation(
                recommendation_id=f"cache_hit_rate_{int(time.time())}",
                category="caching",
                title="Improve Cache Hit Rate",
                description=f"Cache hit rate is {hit_rate:.1f}%, which is below optimal (>70%)",
                impact="medium",
                effort="low",
                priority_score=70 - hit_rate,
                metrics_evidence=[f"cache.hit_rate: {hit_rate:.1f}%"],
                suggested_actions=[
                    "Review cache TTL settings",
                    "Implement cache warming for frequently accessed data",
                    "Analyze cache eviction patterns",
                    "Consider increasing cache size"
                ]
            ))

        # Analyze database performance
        db_optimizer = get_database_optimizer()
        slow_queries = await db_optimizer.get_slow_queries(threshold_seconds=1.0, limit=5)

        if slow_queries:
            recommendations.append(PerformanceRecommendation(
                recommendation_id=f"slow_queries_{int(time.time())}",
                category="database",
                title="Optimize Slow Database Queries",
                description=f"Found {len(slow_queries)} slow queries with avg execution time > 1s",
                impact="high",
                effort="medium",
                priority_score=len(slow_queries) * 10,
                metrics_evidence=[f"slow_queries_count: {len(slow_queries)}"],
                suggested_actions=[
                    "Add database indexes for slow queries",
                    "Implement query result caching",
                    "Review and optimize query structure",
                    "Consider database connection pooling"
                ]
            ))

        # Analyze memory usage
        memory_manager = get_memory_manager()
        memory_stats = memory_manager.get_memory_stats()

        memory_usage = memory_stats.get("current_memory", {}).get("usage_percent", 0)
        if memory_usage > 80:
            recommendations.append(PerformanceRecommendation(
                recommendation_id=f"memory_usage_{int(time.time())}",
                category="memory",
                title="Optimize Memory Usage",
                description=f"Memory usage is {memory_usage:.1f}%, approaching critical levels",
                impact="high",
                effort="medium",
                priority_score=memory_usage - 50,
                metrics_evidence=[f"memory_usage: {memory_usage:.1f}%"],
                suggested_actions=[
                    "Implement more aggressive garbage collection",
                    "Review memory-intensive operations",
                    "Optimize object lifecycle management",
                    "Consider horizontal scaling"
                ]
            ))

        # Store recommendations
        for rec in recommendations:
            self.recommendations[rec.recommendation_id] = rec

        if recommendations:
            logger.info(f"Generated {len(recommendations)} performance recommendations")

    async def _baseline_calculation_loop(self):
        """Background performance baseline calculation loop."""
        while self.monitoring_enabled:
            try:
                await self._calculate_performance_baselines()
                await asyncio.sleep(3600)  # Update baselines every hour

            except Exception as e:
                logger.error(f"Baseline calculation loop error: {e}")
                await asyncio.sleep(300)

    async def _calculate_performance_baselines(self):
        """Calculate performance baselines for key metrics."""
        cutoff_time = datetime.utcnow() - self.baseline_calculation_window

        for metric_name, metric_history in self.metrics_history.items():
            recent_metrics = [
                m for m in metric_history
                if m.timestamp >= cutoff_time
            ]

            if len(recent_metrics) >= 10:  # Need sufficient data
                baseline_value = statistics.median([m.value for m in recent_metrics])
                self.performance_baselines[metric_name] = baseline_value

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data."""
        # Recent metrics summary
        recent_metrics = {}
        for metric_name, history in self.metrics_history.items():
            if history:
                latest = history[-1]
                recent_metrics[metric_name] = {
                    "current_value": latest.value,
                    "timestamp": latest.timestamp.isoformat(),
                    "baseline": self.performance_baselines.get(metric_name, 0)
                }

        # Active alerts summary
        active_alerts_summary = {
            "total": len(self.active_alerts),
            "critical": len([a for a in self.active_alerts.values() if a.severity == AlertSeverity.CRITICAL]),
            "warning": len([a for a in self.active_alerts.values() if a.severity == AlertSeverity.WARNING]),
            "error": len([a for a in self.active_alerts.values() if a.severity == AlertSeverity.ERROR])
        }

        # Recent recommendations
        recent_recommendations = sorted(
            self.recommendations.values(),
            key=lambda x: x.created_at,
            reverse=True
        )[:5]

        return {
            "metrics": recent_metrics,
            "alerts": {
                "active": active_alerts_summary,
                "recent": [
                    {
                        "alert_id": a.alert_id,
                        "name": a.name,
                        "severity": a.severity.value,
                        "message": a.message,
                        "timestamp": a.timestamp.isoformat()
                    }
                    for a in list(self.alert_history)[-10:]
                ]
            },
            "recommendations": [
                {
                    "recommendation_id": r.recommendation_id,
                    "category": r.category,
                    "title": r.title,
                    "description": r.description,
                    "impact": r.impact,
                    "priority_score": r.priority_score
                }
                for r in recent_recommendations
            ],
            "system_health": {
                "monitoring_enabled": self.monitoring_enabled,
                "metrics_collected": len(self.metrics_buffer),
                "alert_rules_active": len([r for r in self.alert_rules.values() if r.enabled]),
                "baselines_calculated": len(self.performance_baselines)
            }
        }

    def get_metric_history(self, metric_name: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get metric history for specified time period."""
        if metric_name not in self.metrics_history:
            return []

        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        return [
            {
                "timestamp": m.timestamp.isoformat(),
                "value": m.value,
                "tags": m.tags
            }
            for m in self.metrics_history[metric_name]
            if m.timestamp >= cutoff_time
        ]


# Global monitoring system instance
_monitoring_system = None


def get_monitoring_system() -> RealTimeMonitoringSystem:
    """Get the global monitoring system instance."""
    global _monitoring_system
    if _monitoring_system is None:
        _monitoring_system = RealTimeMonitoringSystem()
    return _monitoring_system
