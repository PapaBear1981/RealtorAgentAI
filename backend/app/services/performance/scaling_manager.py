"""
Horizontal Scaling and Auto-Scaling Manager for AI Agent System.

This module provides horizontal scaling capabilities, load distribution,
auto-scaling based on metrics, and service discovery for scaled instances.
"""

import asyncio
import time
import uuid
from typing import Dict, List, Any, Optional, Set, Callable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import structlog
from collections import defaultdict, deque
import statistics
import json

logger = structlog.get_logger(__name__)


class ScalingDirection(Enum):
    """Scaling direction."""
    UP = "up"
    DOWN = "down"
    STABLE = "stable"


class InstanceStatus(Enum):
    """Instance status."""
    STARTING = "starting"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    TERMINATING = "terminating"
    TERMINATED = "terminated"


class ScalingTrigger(Enum):
    """Scaling trigger types."""
    CPU_UTILIZATION = "cpu_utilization"
    MEMORY_UTILIZATION = "memory_utilization"
    REQUEST_RATE = "request_rate"
    RESPONSE_TIME = "response_time"
    QUEUE_LENGTH = "queue_length"
    CUSTOM_METRIC = "custom_metric"


@dataclass
class ServiceInstance:
    """Service instance information."""
    instance_id: str
    host: str
    port: int
    status: InstanceStatus = InstanceStatus.STARTING
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_health_check: Optional[datetime] = None
    health_check_failures: int = 0
    current_load: float = 0.0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    request_count: int = 0
    avg_response_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScalingPolicy:
    """Auto-scaling policy configuration."""
    policy_id: str
    service_name: str
    min_instances: int = 1
    max_instances: int = 10
    target_cpu_utilization: float = 70.0
    target_memory_utilization: float = 80.0
    target_response_time: float = 1.0
    scale_up_threshold: float = 80.0
    scale_down_threshold: float = 30.0
    scale_up_cooldown: timedelta = field(default_factory=lambda: timedelta(minutes=5))
    scale_down_cooldown: timedelta = field(default_factory=lambda: timedelta(minutes=10))
    evaluation_period: timedelta = field(default_factory=lambda: timedelta(minutes=2))
    enabled: bool = True


@dataclass
class ScalingEvent:
    """Scaling event record."""
    event_id: str
    service_name: str
    direction: ScalingDirection
    trigger: ScalingTrigger
    trigger_value: float
    threshold: float
    instances_before: int
    instances_after: int
    timestamp: datetime = field(default_factory=datetime.utcnow)
    success: bool = True
    error_message: Optional[str] = None


class HorizontalScalingManager:
    """Advanced horizontal scaling and auto-scaling manager."""

    def __init__(self):
        self.services: Dict[str, Dict[str, ServiceInstance]] = defaultdict(dict)
        self.scaling_policies: Dict[str, ScalingPolicy] = {}
        self.scaling_events: deque = deque(maxlen=1000)
        self.last_scaling_action: Dict[str, datetime] = {}
        self.metrics_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))

        # Service discovery
        self.service_registry: Dict[str, Set[str]] = defaultdict(set)
        self.health_check_interval = 30  # seconds
        self.health_check_timeout = 5  # seconds

        # Load balancing
        self.load_balancer_strategies = {
            "round_robin": self._round_robin_select,
            "least_connections": self._least_connections_select,
            "weighted_round_robin": self._weighted_round_robin_select,
            "health_aware": self._health_aware_select
        }

        self.round_robin_counters: Dict[str, int] = defaultdict(int)

        # Initialize default scaling policies
        self._initialize_default_policies()

        # Background tasks will be started when needed
        self._background_tasks_started = False

    def _initialize_default_policies(self):
        """Initialize default scaling policies for agent services."""
        agent_services = [
            "data-extraction-service",
            "contract-generator-service",
            "compliance-checker-service",
            "signature-tracker-service",
            "summary-service",
            "help-service"
        ]

        for service in agent_services:
            policy_id = f"policy_{service}"
            self.scaling_policies[policy_id] = ScalingPolicy(
                policy_id=policy_id,
                service_name=service,
                min_instances=2,
                max_instances=15,
                target_cpu_utilization=70.0,
                target_memory_utilization=80.0,
                target_response_time=2.0,
                scale_up_threshold=80.0,
                scale_down_threshold=30.0
            )

    def _start_background_tasks(self):
        """Start background monitoring and scaling tasks."""
        if not self._background_tasks_started:
            try:
                asyncio.create_task(self._health_check_loop())
                asyncio.create_task(self._auto_scaling_loop())
                asyncio.create_task(self._metrics_collection_loop())
                self._background_tasks_started = True
            except RuntimeError:
                # No event loop running, tasks will be started when needed
                pass

    async def register_service_instance(
        self,
        service_name: str,
        host: str,
        port: int,
        metadata: Dict[str, Any] = None
    ) -> str:
        """Register a new service instance."""
        instance_id = f"{service_name}-{uuid.uuid4().hex[:8]}"

        instance = ServiceInstance(
            instance_id=instance_id,
            host=host,
            port=port,
            metadata=metadata or {}
        )

        self.services[service_name][instance_id] = instance
        self.service_registry[service_name].add(instance_id)

        logger.info(f"Registered service instance: {instance_id} at {host}:{port}")

        # Perform initial health check
        await self._perform_health_check(service_name, instance_id)

        return instance_id

    async def deregister_service_instance(self, service_name: str, instance_id: str) -> bool:
        """Deregister a service instance."""
        if service_name in self.services and instance_id in self.services[service_name]:
            instance = self.services[service_name][instance_id]
            instance.status = InstanceStatus.TERMINATED

            del self.services[service_name][instance_id]
            self.service_registry[service_name].discard(instance_id)

            logger.info(f"Deregistered service instance: {instance_id}")
            return True

        return False

    async def get_healthy_instance(
        self,
        service_name: str,
        strategy: str = "health_aware"
    ) -> Optional[ServiceInstance]:
        """Get a healthy service instance using the specified strategy."""
        if service_name not in self.services:
            return None

        healthy_instances = [
            instance for instance in self.services[service_name].values()
            if instance.status == InstanceStatus.HEALTHY
        ]

        if not healthy_instances:
            logger.warning(f"No healthy instances available for service: {service_name}")
            return None

        # Select instance based on strategy
        selection_func = self.load_balancer_strategies.get(strategy, self._health_aware_select)
        selected_instance = selection_func(service_name, healthy_instances)

        if selected_instance:
            selected_instance.request_count += 1
            selected_instance.current_load += 1

        return selected_instance

    def _round_robin_select(self, service_name: str, instances: List[ServiceInstance]) -> ServiceInstance:
        """Round robin instance selection."""
        counter = self.round_robin_counters[service_name]
        selected = instances[counter % len(instances)]
        self.round_robin_counters[service_name] = (counter + 1) % len(instances)
        return selected

    def _least_connections_select(self, service_name: str, instances: List[ServiceInstance]) -> ServiceInstance:
        """Select instance with least current connections."""
        return min(instances, key=lambda x: x.current_load)

    def _weighted_round_robin_select(self, service_name: str, instances: List[ServiceInstance]) -> ServiceInstance:
        """Weighted round robin based on instance capacity."""
        # Simple implementation - could be enhanced with actual weights
        return min(instances, key=lambda x: x.current_load / max(x.cpu_usage + 1, 1))

    def _health_aware_select(self, service_name: str, instances: List[ServiceInstance]) -> ServiceInstance:
        """Health-aware selection considering multiple factors."""
        def health_score(instance: ServiceInstance) -> float:
            # Lower score is better
            load_factor = instance.current_load / 10.0  # Normalize load
            cpu_factor = instance.cpu_usage / 100.0
            memory_factor = instance.memory_usage / 100.0
            response_time_factor = min(instance.avg_response_time / 5.0, 1.0)  # Cap at 5 seconds

            # Health check failure penalty
            failure_penalty = instance.health_check_failures * 0.1

            return load_factor + cpu_factor + memory_factor + response_time_factor + failure_penalty

        return min(instances, key=health_score)

    async def update_instance_metrics(
        self,
        service_name: str,
        instance_id: str,
        cpu_usage: float,
        memory_usage: float,
        response_time: float = None
    ):
        """Update instance performance metrics."""
        if service_name in self.services and instance_id in self.services[service_name]:
            instance = self.services[service_name][instance_id]
            instance.cpu_usage = cpu_usage
            instance.memory_usage = memory_usage

            if response_time is not None:
                # Update average response time
                if instance.avg_response_time == 0:
                    instance.avg_response_time = response_time
                else:
                    instance.avg_response_time = (instance.avg_response_time * 0.9 + response_time * 0.1)

            # Store metrics history for scaling decisions
            self.metrics_history[f"{service_name}:{instance_id}"].append({
                "timestamp": datetime.utcnow(),
                "cpu_usage": cpu_usage,
                "memory_usage": memory_usage,
                "response_time": response_time or 0,
                "current_load": instance.current_load
            })

    async def _health_check_loop(self):
        """Background health check loop."""
        while True:
            try:
                for service_name, instances in self.services.items():
                    for instance_id in list(instances.keys()):
                        await self._perform_health_check(service_name, instance_id)

                await asyncio.sleep(self.health_check_interval)

            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(5)

    async def _perform_health_check(self, service_name: str, instance_id: str):
        """Perform health check on a service instance."""
        if service_name not in self.services or instance_id not in self.services[service_name]:
            return

        instance = self.services[service_name][instance_id]

        try:
            # Simulate health check (in practice, this would make HTTP request)
            # For now, we'll use a simple heuristic based on metrics
            is_healthy = (
                instance.cpu_usage < 95.0 and
                instance.memory_usage < 95.0 and
                instance.avg_response_time < 10.0 and
                instance.health_check_failures < 3
            )

            if is_healthy:
                instance.status = InstanceStatus.HEALTHY
                instance.health_check_failures = 0
                instance.last_health_check = datetime.utcnow()
            else:
                instance.health_check_failures += 1
                if instance.health_check_failures >= 3:
                    instance.status = InstanceStatus.UNHEALTHY
                    logger.warning(f"Instance {instance_id} marked as unhealthy")

        except Exception as e:
            instance.health_check_failures += 1
            if instance.health_check_failures >= 3:
                instance.status = InstanceStatus.UNHEALTHY
            logger.error(f"Health check failed for {instance_id}: {e}")

    async def _auto_scaling_loop(self):
        """Background auto-scaling loop."""
        while True:
            try:
                for policy_id, policy in self.scaling_policies.items():
                    if policy.enabled:
                        await self._evaluate_scaling_policy(policy)

                await asyncio.sleep(30)  # Check every 30 seconds

            except Exception as e:
                logger.error(f"Auto-scaling loop error: {e}")
                await asyncio.sleep(10)

    async def _evaluate_scaling_policy(self, policy: ScalingPolicy):
        """Evaluate scaling policy and take action if needed."""
        service_name = policy.service_name

        if service_name not in self.services:
            return

        # Check cooldown period
        if service_name in self.last_scaling_action:
            time_since_last_action = datetime.utcnow() - self.last_scaling_action[service_name]
            if time_since_last_action < policy.scale_up_cooldown:
                return

        # Get current metrics
        instances = list(self.services[service_name].values())
        healthy_instances = [i for i in instances if i.status == InstanceStatus.HEALTHY]

        if not healthy_instances:
            return

        # Calculate aggregate metrics
        avg_cpu = statistics.mean([i.cpu_usage for i in healthy_instances])
        avg_memory = statistics.mean([i.memory_usage for i in healthy_instances])
        avg_response_time = statistics.mean([i.avg_response_time for i in healthy_instances if i.avg_response_time > 0])
        total_load = sum([i.current_load for i in healthy_instances])

        current_instance_count = len(healthy_instances)

        # Determine scaling action
        scaling_needed = ScalingDirection.STABLE
        trigger = None
        trigger_value = 0
        threshold = 0

        # Check scale-up conditions
        if (avg_cpu > policy.scale_up_threshold or
            avg_memory > policy.scale_up_threshold or
            avg_response_time > policy.target_response_time * 2):

            if current_instance_count < policy.max_instances:
                scaling_needed = ScalingDirection.UP

                if avg_cpu > policy.scale_up_threshold:
                    trigger = ScalingTrigger.CPU_UTILIZATION
                    trigger_value = avg_cpu
                    threshold = policy.scale_up_threshold
                elif avg_memory > policy.scale_up_threshold:
                    trigger = ScalingTrigger.MEMORY_UTILIZATION
                    trigger_value = avg_memory
                    threshold = policy.scale_up_threshold
                else:
                    trigger = ScalingTrigger.RESPONSE_TIME
                    trigger_value = avg_response_time
                    threshold = policy.target_response_time * 2

        # Check scale-down conditions
        elif (avg_cpu < policy.scale_down_threshold and
              avg_memory < policy.scale_down_threshold and
              avg_response_time < policy.target_response_time):

            if current_instance_count > policy.min_instances:
                scaling_needed = ScalingDirection.DOWN
                trigger = ScalingTrigger.CPU_UTILIZATION
                trigger_value = avg_cpu
                threshold = policy.scale_down_threshold

        # Execute scaling action
        if scaling_needed != ScalingDirection.STABLE:
            success = await self._execute_scaling_action(
                service_name, scaling_needed, trigger, trigger_value, threshold
            )

            if success:
                self.last_scaling_action[service_name] = datetime.utcnow()

    async def _execute_scaling_action(
        self,
        service_name: str,
        direction: ScalingDirection,
        trigger: ScalingTrigger,
        trigger_value: float,
        threshold: float
    ) -> bool:
        """Execute scaling action."""
        instances_before = len([i for i in self.services[service_name].values()
                              if i.status == InstanceStatus.HEALTHY])

        try:
            if direction == ScalingDirection.UP:
                # Scale up - add new instance
                new_instance_id = await self._create_new_instance(service_name)
                if new_instance_id:
                    instances_after = instances_before + 1
                    logger.info(f"Scaled up {service_name}: {instances_before} -> {instances_after}")
                else:
                    return False

            elif direction == ScalingDirection.DOWN:
                # Scale down - remove instance
                removed = await self._remove_instance(service_name)
                if removed:
                    instances_after = instances_before - 1
                    logger.info(f"Scaled down {service_name}: {instances_before} -> {instances_after}")
                else:
                    return False

            # Record scaling event
            event = ScalingEvent(
                event_id=str(uuid.uuid4()),
                service_name=service_name,
                direction=direction,
                trigger=trigger,
                trigger_value=trigger_value,
                threshold=threshold,
                instances_before=instances_before,
                instances_after=instances_after,
                success=True
            )

            self.scaling_events.append(event)
            return True

        except Exception as e:
            # Record failed scaling event
            event = ScalingEvent(
                event_id=str(uuid.uuid4()),
                service_name=service_name,
                direction=direction,
                trigger=trigger,
                trigger_value=trigger_value,
                threshold=threshold,
                instances_before=instances_before,
                instances_after=instances_before,
                success=False,
                error_message=str(e)
            )

            self.scaling_events.append(event)
            logger.error(f"Scaling action failed for {service_name}: {e}")
            return False

    async def _create_new_instance(self, service_name: str) -> Optional[str]:
        """Create a new service instance."""
        # In practice, this would integrate with container orchestration
        # For now, simulate instance creation

        # Generate new port (in practice, this would be handled by orchestrator)
        base_port = 8000
        existing_ports = {i.port for i in self.services[service_name].values()}
        new_port = base_port
        while new_port in existing_ports:
            new_port += 1

        # Register new instance
        instance_id = await self.register_service_instance(
            service_name=service_name,
            host="localhost",  # In practice, this would be actual host
            port=new_port,
            metadata={"created_by": "auto_scaler"}
        )

        return instance_id

    async def _remove_instance(self, service_name: str) -> bool:
        """Remove a service instance."""
        # Find instance with lowest load to remove
        instances = [i for i in self.services[service_name].values()
                    if i.status == InstanceStatus.HEALTHY]

        if not instances:
            return False

        # Select instance with lowest current load
        instance_to_remove = min(instances, key=lambda x: x.current_load)

        # Mark for termination and deregister
        instance_to_remove.status = InstanceStatus.TERMINATING
        await self.deregister_service_instance(service_name, instance_to_remove.instance_id)

        return True

    async def _metrics_collection_loop(self):
        """Background metrics collection loop."""
        while True:
            try:
                # Simulate metrics collection (in practice, would collect from monitoring system)
                for service_name, instances in self.services.items():
                    for instance_id, instance in instances.items():
                        if instance.status == InstanceStatus.HEALTHY:
                            # Simulate varying metrics
                            import random
                            cpu_usage = random.uniform(20, 90)
                            memory_usage = random.uniform(30, 85)
                            response_time = random.uniform(0.1, 3.0)

                            await self.update_instance_metrics(
                                service_name, instance_id, cpu_usage, memory_usage, response_time
                            )

                await asyncio.sleep(10)  # Collect metrics every 10 seconds

            except Exception as e:
                logger.error(f"Metrics collection loop error: {e}")
                await asyncio.sleep(5)

    def get_service_overview(self, service_name: str = None) -> Dict[str, Any]:
        """Get service overview and scaling status."""
        if service_name:
            services_to_check = {service_name: self.services.get(service_name, {})}
        else:
            services_to_check = self.services

        overview = {}

        for svc_name, instances in services_to_check.items():
            healthy_count = sum(1 for i in instances.values() if i.status == InstanceStatus.HEALTHY)
            unhealthy_count = sum(1 for i in instances.values() if i.status == InstanceStatus.UNHEALTHY)

            if instances:
                healthy_instances = [i for i in instances.values() if i.status == InstanceStatus.HEALTHY]
                avg_cpu = statistics.mean([i.cpu_usage for i in healthy_instances]) if healthy_instances else 0
                avg_memory = statistics.mean([i.memory_usage for i in healthy_instances]) if healthy_instances else 0
                avg_response_time = statistics.mean([i.avg_response_time for i in healthy_instances if i.avg_response_time > 0]) if healthy_instances else 0
                total_requests = sum([i.request_count for i in instances.values()])
            else:
                avg_cpu = avg_memory = avg_response_time = total_requests = 0

            # Get scaling policy
            policy = None
            for p in self.scaling_policies.values():
                if p.service_name == svc_name:
                    policy = p
                    break

            overview[svc_name] = {
                "instance_count": {
                    "healthy": healthy_count,
                    "unhealthy": unhealthy_count,
                    "total": len(instances)
                },
                "metrics": {
                    "avg_cpu_usage": round(avg_cpu, 2),
                    "avg_memory_usage": round(avg_memory, 2),
                    "avg_response_time": round(avg_response_time, 3),
                    "total_requests": total_requests
                },
                "scaling_policy": {
                    "enabled": policy.enabled if policy else False,
                    "min_instances": policy.min_instances if policy else 0,
                    "max_instances": policy.max_instances if policy else 0,
                    "target_cpu": policy.target_cpu_utilization if policy else 0
                } if policy else None,
                "last_scaling_action": self.last_scaling_action.get(svc_name, "Never").isoformat() if isinstance(self.last_scaling_action.get(svc_name), datetime) else "Never"
            }

        return overview

    def get_scaling_history(self, service_name: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get scaling event history."""
        events = list(self.scaling_events)

        if service_name:
            events = [e for e in events if e.service_name == service_name]

        # Sort by timestamp (most recent first)
        events.sort(key=lambda x: x.timestamp, reverse=True)

        return [
            {
                "event_id": e.event_id,
                "service_name": e.service_name,
                "direction": e.direction.value,
                "trigger": e.trigger.value,
                "trigger_value": round(e.trigger_value, 2),
                "threshold": round(e.threshold, 2),
                "instances_before": e.instances_before,
                "instances_after": e.instances_after,
                "timestamp": e.timestamp.isoformat(),
                "success": e.success,
                "error_message": e.error_message
            }
            for e in events[:limit]
        ]


# Global scaling manager instance
_scaling_manager = None


def get_scaling_manager() -> HorizontalScalingManager:
    """Get the global scaling manager instance."""
    global _scaling_manager
    if _scaling_manager is None:
        _scaling_manager = HorizontalScalingManager()
    return _scaling_manager
