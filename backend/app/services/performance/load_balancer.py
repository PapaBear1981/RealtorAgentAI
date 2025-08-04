"""
Advanced Load Balancer and Resource Management for AI Agents.

This module provides intelligent load balancing algorithms, resource management,
and dynamic scaling capabilities for optimal agent utilization.
"""

import asyncio
import time
import uuid
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import structlog
from collections import defaultdict, deque
import statistics

logger = structlog.get_logger(__name__)


class LoadBalancingStrategy(Enum):
    """Load balancing strategies."""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    RESOURCE_BASED = "resource_based"
    RESPONSE_TIME_BASED = "response_time_based"
    ADAPTIVE = "adaptive"


class AgentStatus(Enum):
    """Agent status states."""
    IDLE = "idle"
    BUSY = "busy"
    OVERLOADED = "overloaded"
    MAINTENANCE = "maintenance"
    FAILED = "failed"


@dataclass
class AgentMetrics:
    """Agent performance metrics."""
    agent_id: str
    current_load: int = 0
    max_capacity: int = 10
    avg_response_time: float = 0.0
    success_rate: float = 100.0
    memory_usage: float = 0.0
    cpu_usage: float = 0.0
    last_activity: datetime = field(default_factory=datetime.utcnow)
    total_requests: int = 0
    failed_requests: int = 0
    response_times: deque = field(default_factory=lambda: deque(maxlen=100))
    status: AgentStatus = AgentStatus.IDLE


@dataclass
class ResourcePool:
    """Resource pool for agent management."""
    pool_id: str
    agent_type: str
    agents: Dict[str, AgentMetrics] = field(default_factory=dict)
    min_agents: int = 2
    max_agents: int = 20
    target_utilization: float = 0.7
    scale_up_threshold: float = 0.8
    scale_down_threshold: float = 0.3
    created_at: datetime = field(default_factory=datetime.utcnow)


class AdvancedLoadBalancer:
    """Advanced load balancer with intelligent resource management."""
    
    def __init__(self):
        self.resource_pools: Dict[str, ResourcePool] = {}
        self.load_balancing_strategy = LoadBalancingStrategy.ADAPTIVE
        self.round_robin_counters: Dict[str, int] = defaultdict(int)
        self.performance_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.scaling_cooldown: Dict[str, datetime] = {}
        self.monitoring_enabled = True
        
        # Performance thresholds
        self.response_time_threshold = 5.0  # seconds
        self.error_rate_threshold = 0.05  # 5%
        self.memory_threshold = 0.85  # 85%
        self.cpu_threshold = 0.80  # 80%
        
        # Auto-scaling parameters
        self.scale_up_cooldown = timedelta(minutes=5)
        self.scale_down_cooldown = timedelta(minutes=10)
        
        # Initialize default pools
        self._initialize_default_pools()
    
    def _initialize_default_pools(self):
        """Initialize default resource pools for each agent type."""
        agent_types = [
            "data_extraction", "contract_generator", "compliance_checker",
            "signature_tracker", "summary_agent", "help_agent"
        ]
        
        for agent_type in agent_types:
            pool_id = f"pool_{agent_type}"
            self.resource_pools[pool_id] = ResourcePool(
                pool_id=pool_id,
                agent_type=agent_type,
                min_agents=2,
                max_agents=15,
                target_utilization=0.7
            )
            
            # Initialize minimum agents
            for i in range(2):
                agent_id = f"{agent_type}_agent_{i}_{uuid.uuid4().hex[:8]}"
                self.resource_pools[pool_id].agents[agent_id] = AgentMetrics(
                    agent_id=agent_id,
                    max_capacity=10
                )
    
    async def get_optimal_agent(
        self,
        agent_type: str,
        task_priority: str = "normal",
        estimated_duration: float = None
    ) -> Optional[str]:
        """Get the optimal agent for a task using the current load balancing strategy."""
        pool_id = f"pool_{agent_type}"
        
        if pool_id not in self.resource_pools:
            logger.error(f"Resource pool not found: {pool_id}")
            return None
        
        pool = self.resource_pools[pool_id]
        available_agents = [
            agent_id for agent_id, metrics in pool.agents.items()
            if metrics.status in [AgentStatus.IDLE, AgentStatus.BUSY] and
            metrics.current_load < metrics.max_capacity
        ]
        
        if not available_agents:
            # Try to scale up if possible
            await self._attempt_scale_up(pool_id)
            # Retry after potential scaling
            available_agents = [
                agent_id for agent_id, metrics in pool.agents.items()
                if metrics.status in [AgentStatus.IDLE, AgentStatus.BUSY] and
                metrics.current_load < metrics.max_capacity
            ]
        
        if not available_agents:
            logger.warning(f"No available agents in pool {pool_id}")
            return None
        
        # Select agent based on strategy
        selected_agent = await self._select_agent_by_strategy(
            pool, available_agents, task_priority, estimated_duration
        )
        
        if selected_agent:
            # Update agent metrics
            metrics = pool.agents[selected_agent]
            metrics.current_load += 1
            metrics.last_activity = datetime.utcnow()
            metrics.status = AgentStatus.BUSY if metrics.current_load > 0 else AgentStatus.IDLE
            
            logger.info(f"Assigned agent {selected_agent} (load: {metrics.current_load}/{metrics.max_capacity})")
        
        return selected_agent
    
    async def _select_agent_by_strategy(
        self,
        pool: ResourcePool,
        available_agents: List[str],
        task_priority: str,
        estimated_duration: float
    ) -> Optional[str]:
        """Select agent based on the current load balancing strategy."""
        if self.load_balancing_strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return self._round_robin_selection(pool.pool_id, available_agents)
        
        elif self.load_balancing_strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return self._least_connections_selection(pool, available_agents)
        
        elif self.load_balancing_strategy == LoadBalancingStrategy.RESOURCE_BASED:
            return self._resource_based_selection(pool, available_agents)
        
        elif self.load_balancing_strategy == LoadBalancingStrategy.RESPONSE_TIME_BASED:
            return self._response_time_based_selection(pool, available_agents)
        
        elif self.load_balancing_strategy == LoadBalancingStrategy.ADAPTIVE:
            return await self._adaptive_selection(pool, available_agents, task_priority, estimated_duration)
        
        else:
            # Default to round robin
            return self._round_robin_selection(pool.pool_id, available_agents)
    
    def _round_robin_selection(self, pool_id: str, available_agents: List[str]) -> str:
        """Round robin agent selection."""
        counter = self.round_robin_counters[pool_id]
        selected = available_agents[counter % len(available_agents)]
        self.round_robin_counters[pool_id] = (counter + 1) % len(available_agents)
        return selected
    
    def _least_connections_selection(self, pool: ResourcePool, available_agents: List[str]) -> str:
        """Select agent with least current connections."""
        return min(available_agents, key=lambda agent_id: pool.agents[agent_id].current_load)
    
    def _resource_based_selection(self, pool: ResourcePool, available_agents: List[str]) -> str:
        """Select agent based on resource utilization."""
        def resource_score(agent_id: str) -> float:
            metrics = pool.agents[agent_id]
            load_factor = metrics.current_load / metrics.max_capacity
            memory_factor = metrics.memory_usage
            cpu_factor = metrics.cpu_usage
            return load_factor * 0.5 + memory_factor * 0.3 + cpu_factor * 0.2
        
        return min(available_agents, key=resource_score)
    
    def _response_time_based_selection(self, pool: ResourcePool, available_agents: List[str]) -> str:
        """Select agent with best average response time."""
        def avg_response_time(agent_id: str) -> float:
            metrics = pool.agents[agent_id]
            if not metrics.response_times:
                return 0.0
            return statistics.mean(metrics.response_times)
        
        return min(available_agents, key=avg_response_time)
    
    async def _adaptive_selection(
        self,
        pool: ResourcePool,
        available_agents: List[str],
        task_priority: str,
        estimated_duration: float
    ) -> str:
        """Adaptive selection based on multiple factors."""
        def adaptive_score(agent_id: str) -> float:
            metrics = pool.agents[agent_id]
            
            # Load factor (0-1)
            load_factor = metrics.current_load / metrics.max_capacity
            
            # Response time factor (normalized)
            avg_response_time = statistics.mean(metrics.response_times) if metrics.response_times else 1.0
            response_time_factor = min(avg_response_time / 10.0, 1.0)  # Normalize to 0-1
            
            # Success rate factor (inverted, so lower is better)
            success_rate_factor = 1.0 - (metrics.success_rate / 100.0)
            
            # Resource utilization factor
            resource_factor = (metrics.memory_usage + metrics.cpu_usage) / 2.0
            
            # Priority adjustment
            priority_weight = 1.0
            if task_priority == "high":
                priority_weight = 0.8  # Prefer less loaded agents for high priority
            elif task_priority == "low":
                priority_weight = 1.2  # Can use more loaded agents for low priority
            
            # Combined score (lower is better)
            score = (
                load_factor * 0.4 +
                response_time_factor * 0.3 +
                success_rate_factor * 0.2 +
                resource_factor * 0.1
            ) * priority_weight
            
            return score
        
        return min(available_agents, key=adaptive_score)
    
    async def release_agent(self, agent_id: str, execution_time: float, success: bool):
        """Release an agent after task completion and update metrics."""
        # Find the pool containing this agent
        pool = None
        for p in self.resource_pools.values():
            if agent_id in p.agents:
                pool = p
                break
        
        if not pool:
            logger.warning(f"Agent {agent_id} not found in any pool")
            return
        
        metrics = pool.agents[agent_id]
        metrics.current_load = max(0, metrics.current_load - 1)
        metrics.total_requests += 1
        
        if not success:
            metrics.failed_requests += 1
        
        # Update response times
        metrics.response_times.append(execution_time)
        
        # Update average response time
        if metrics.response_times:
            metrics.avg_response_time = statistics.mean(metrics.response_times)
        
        # Update success rate
        metrics.success_rate = ((metrics.total_requests - metrics.failed_requests) / metrics.total_requests) * 100
        
        # Update status
        if metrics.current_load == 0:
            metrics.status = AgentStatus.IDLE
        elif metrics.current_load >= metrics.max_capacity:
            metrics.status = AgentStatus.OVERLOADED
        else:
            metrics.status = AgentStatus.BUSY
        
        # Record performance history
        self.performance_history[agent_id].append({
            "timestamp": datetime.utcnow(),
            "execution_time": execution_time,
            "success": success,
            "load": metrics.current_load
        })
        
        logger.debug(f"Released agent {agent_id} (load: {metrics.current_load}/{metrics.max_capacity})")
        
        # Check if scaling down is needed
        await self._check_scale_down(pool.pool_id)
    
    async def _attempt_scale_up(self, pool_id: str) -> bool:
        """Attempt to scale up the resource pool."""
        if pool_id not in self.resource_pools:
            return False
        
        pool = self.resource_pools[pool_id]
        
        # Check cooldown
        if pool_id in self.scaling_cooldown:
            if datetime.utcnow() - self.scaling_cooldown[pool_id] < self.scale_up_cooldown:
                return False
        
        # Check if we can scale up
        current_agents = len(pool.agents)
        if current_agents >= pool.max_agents:
            logger.warning(f"Pool {pool_id} already at maximum capacity ({pool.max_agents})")
            return False
        
        # Calculate current utilization
        total_load = sum(metrics.current_load for metrics in pool.agents.values())
        total_capacity = sum(metrics.max_capacity for metrics in pool.agents.values())
        utilization = total_load / total_capacity if total_capacity > 0 else 0
        
        if utilization >= pool.scale_up_threshold:
            # Scale up
            new_agent_id = f"{pool.agent_type}_agent_{current_agents}_{uuid.uuid4().hex[:8]}"
            pool.agents[new_agent_id] = AgentMetrics(
                agent_id=new_agent_id,
                max_capacity=10
            )
            
            self.scaling_cooldown[pool_id] = datetime.utcnow()
            
            logger.info(f"Scaled up pool {pool_id}: added agent {new_agent_id} (total: {len(pool.agents)})")
            return True
        
        return False
    
    async def _check_scale_down(self, pool_id: str):
        """Check if the pool should be scaled down."""
        if pool_id not in self.resource_pools:
            return
        
        pool = self.resource_pools[pool_id]
        
        # Check cooldown
        if pool_id in self.scaling_cooldown:
            if datetime.utcnow() - self.scaling_cooldown[pool_id] < self.scale_down_cooldown:
                return
        
        # Don't scale below minimum
        current_agents = len(pool.agents)
        if current_agents <= pool.min_agents:
            return
        
        # Calculate utilization
        total_load = sum(metrics.current_load for metrics in pool.agents.values())
        total_capacity = sum(metrics.max_capacity for metrics in pool.agents.values())
        utilization = total_load / total_capacity if total_capacity > 0 else 0
        
        if utilization <= pool.scale_down_threshold:
            # Find idle agent to remove
            idle_agents = [
                agent_id for agent_id, metrics in pool.agents.items()
                if metrics.status == AgentStatus.IDLE and metrics.current_load == 0
            ]
            
            if idle_agents:
                # Remove the least recently used idle agent
                agent_to_remove = min(idle_agents, key=lambda aid: pool.agents[aid].last_activity)
                del pool.agents[agent_to_remove]
                
                self.scaling_cooldown[pool_id] = datetime.utcnow()
                
                logger.info(f"Scaled down pool {pool_id}: removed agent {agent_to_remove} (total: {len(pool.agents)})")
    
    def get_pool_statistics(self, pool_id: str) -> Dict[str, Any]:
        """Get comprehensive statistics for a resource pool."""
        if pool_id not in self.resource_pools:
            return {}
        
        pool = self.resource_pools[pool_id]
        
        # Calculate aggregate metrics
        total_agents = len(pool.agents)
        idle_agents = sum(1 for m in pool.agents.values() if m.status == AgentStatus.IDLE)
        busy_agents = sum(1 for m in pool.agents.values() if m.status == AgentStatus.BUSY)
        overloaded_agents = sum(1 for m in pool.agents.values() if m.status == AgentStatus.OVERLOADED)
        
        total_load = sum(m.current_load for m in pool.agents.values())
        total_capacity = sum(m.max_capacity for m in pool.agents.values())
        utilization = (total_load / total_capacity) * 100 if total_capacity > 0 else 0
        
        avg_response_time = statistics.mean([
            m.avg_response_time for m in pool.agents.values() if m.avg_response_time > 0
        ]) if any(m.avg_response_time > 0 for m in pool.agents.values()) else 0
        
        avg_success_rate = statistics.mean([m.success_rate for m in pool.agents.values()])
        
        total_requests = sum(m.total_requests for m in pool.agents.values())
        total_failures = sum(m.failed_requests for m in pool.agents.values())
        
        return {
            "pool_id": pool_id,
            "agent_type": pool.agent_type,
            "total_agents": total_agents,
            "agent_status": {
                "idle": idle_agents,
                "busy": busy_agents,
                "overloaded": overloaded_agents
            },
            "utilization_percent": round(utilization, 2),
            "avg_response_time": round(avg_response_time, 3),
            "avg_success_rate": round(avg_success_rate, 2),
            "total_requests": total_requests,
            "total_failures": total_failures,
            "error_rate": round((total_failures / total_requests) * 100, 2) if total_requests > 0 else 0,
            "scaling_limits": {
                "min_agents": pool.min_agents,
                "max_agents": pool.max_agents,
                "target_utilization": pool.target_utilization * 100
            }
        }
    
    def get_system_overview(self) -> Dict[str, Any]:
        """Get system-wide load balancer overview."""
        total_agents = sum(len(pool.agents) for pool in self.resource_pools.values())
        total_requests = sum(
            sum(m.total_requests for m in pool.agents.values())
            for pool in self.resource_pools.values()
        )
        
        pool_stats = {}
        for pool_id in self.resource_pools.keys():
            pool_stats[pool_id] = self.get_pool_statistics(pool_id)
        
        return {
            "load_balancing_strategy": self.load_balancing_strategy.value,
            "total_agents": total_agents,
            "total_pools": len(self.resource_pools),
            "total_requests_processed": total_requests,
            "pool_statistics": pool_stats,
            "monitoring_enabled": self.monitoring_enabled,
            "last_updated": datetime.utcnow().isoformat()
        }


# Global load balancer instance
_load_balancer = None


def get_load_balancer() -> AdvancedLoadBalancer:
    """Get the global load balancer instance."""
    global _load_balancer
    if _load_balancer is None:
        _load_balancer = AdvancedLoadBalancer()
    return _load_balancer
