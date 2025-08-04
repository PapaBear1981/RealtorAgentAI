"""
Performance Optimization Tools for AI Agents.

This module provides performance optimization features including caching,
connection pooling, and resource management for agent operations.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, Union, Callable
from datetime import datetime, timedelta
from functools import wraps
import hashlib
import json

import structlog
from pydantic import BaseModel, Field

from .base import BaseTool, ToolInput, ToolResult, ToolCategory
from ...core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class CacheInput(ToolInput):
    """Input for cache operations."""
    operation: str = Field(..., description="Cache operation: get, set, delete, clear")
    key: str = Field(..., description="Cache key")
    value: Optional[Any] = Field(None, description="Value to cache (for set operation)")
    ttl: Optional[int] = Field(None, description="Time to live in seconds")


class PerformanceMonitorInput(ToolInput):
    """Input for performance monitoring."""
    operation: str = Field(..., description="Monitor operation: start, stop, report")
    metric_name: str = Field(..., description="Name of the metric to monitor")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ResourcePoolInput(ToolInput):
    """Input for resource pool operations."""
    pool_type: str = Field(..., description="Type of resource pool")
    operation: str = Field(..., description="Pool operation: acquire, release, status")
    resource_id: Optional[str] = Field(None, description="Resource identifier")
    pool_config: Dict[str, Any] = Field(default_factory=dict, description="Pool configuration")


class CacheManager:
    """In-memory cache manager with TTL support."""
    
    def __init__(self):
        self._cache = {}
        self._ttl_cache = {}
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0
        }
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        # Check if key has expired
        if key in self._ttl_cache:
            if datetime.utcnow() > self._ttl_cache[key]:
                self.delete(key)
                self._stats["misses"] += 1
                return None
        
        if key in self._cache:
            self._stats["hits"] += 1
            return self._cache[key]
        
        self._stats["misses"] += 1
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL."""
        try:
            self._cache[key] = value
            
            if ttl:
                self._ttl_cache[key] = datetime.utcnow() + timedelta(seconds=ttl)
            elif key in self._ttl_cache:
                del self._ttl_cache[key]
            
            self._stats["sets"] += 1
            return True
        except Exception as e:
            logger.error(f"Cache set failed: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        try:
            if key in self._cache:
                del self._cache[key]
                self._stats["deletes"] += 1
            
            if key in self._ttl_cache:
                del self._ttl_cache[key]
            
            return True
        except Exception as e:
            logger.error(f"Cache delete failed: {e}")
            return False
    
    def clear(self) -> bool:
        """Clear all cache entries."""
        try:
            self._cache.clear()
            self._ttl_cache.clear()
            return True
        except Exception as e:
            logger.error(f"Cache clear failed: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total_requests if total_requests > 0 else 0
        
        return {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "sets": self._stats["sets"],
            "deletes": self._stats["deletes"],
            "hit_rate": round(hit_rate, 3),
            "cache_size": len(self._cache),
            "ttl_entries": len(self._ttl_cache)
        }


class PerformanceMonitor:
    """Performance monitoring and metrics collection."""
    
    def __init__(self):
        self._active_timers = {}
        self._metrics = {}
        self._counters = {}
    
    def start_timer(self, metric_name: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Start a performance timer."""
        timer_id = f"{metric_name}_{int(time.time() * 1000000)}"
        self._active_timers[timer_id] = {
            "metric_name": metric_name,
            "start_time": time.time(),
            "metadata": metadata or {}
        }
        return timer_id
    
    def stop_timer(self, timer_id: str) -> Optional[float]:
        """Stop a performance timer and record the duration."""
        if timer_id not in self._active_timers:
            return None
        
        timer_data = self._active_timers.pop(timer_id)
        duration = time.time() - timer_data["start_time"]
        
        metric_name = timer_data["metric_name"]
        if metric_name not in self._metrics:
            self._metrics[metric_name] = []
        
        self._metrics[metric_name].append({
            "duration": duration,
            "timestamp": datetime.utcnow(),
            "metadata": timer_data["metadata"]
        })
        
        # Keep only recent metrics (last 1000)
        if len(self._metrics[metric_name]) > 1000:
            self._metrics[metric_name] = self._metrics[metric_name][-1000:]
        
        return duration
    
    def increment_counter(self, counter_name: str, value: int = 1) -> int:
        """Increment a performance counter."""
        if counter_name not in self._counters:
            self._counters[counter_name] = 0
        
        self._counters[counter_name] += value
        return self._counters[counter_name]
    
    def get_metrics(self, metric_name: Optional[str] = None) -> Dict[str, Any]:
        """Get performance metrics."""
        if metric_name:
            if metric_name in self._metrics:
                metrics = self._metrics[metric_name]
                durations = [m["duration"] for m in metrics]
                
                return {
                    "metric_name": metric_name,
                    "count": len(durations),
                    "avg_duration": sum(durations) / len(durations) if durations else 0,
                    "min_duration": min(durations) if durations else 0,
                    "max_duration": max(durations) if durations else 0,
                    "recent_metrics": metrics[-10:]  # Last 10 metrics
                }
            else:
                return {"metric_name": metric_name, "count": 0}
        
        # Return all metrics summary
        summary = {}
        for name, metrics in self._metrics.items():
            durations = [m["duration"] for m in metrics]
            summary[name] = {
                "count": len(durations),
                "avg_duration": sum(durations) / len(durations) if durations else 0
            }
        
        summary["counters"] = self._counters.copy()
        summary["active_timers"] = len(self._active_timers)
        
        return summary


class ResourcePool:
    """Generic resource pool for managing connections and resources."""
    
    def __init__(self, pool_type: str, max_size: int = 10, min_size: int = 2):
        self.pool_type = pool_type
        self.max_size = max_size
        self.min_size = min_size
        self._available = []
        self._in_use = {}
        self._created_count = 0
        self._stats = {
            "acquired": 0,
            "released": 0,
            "created": 0,
            "destroyed": 0
        }
    
    async def acquire(self) -> Optional[str]:
        """Acquire a resource from the pool."""
        try:
            # Try to get from available pool
            if self._available:
                resource_id = self._available.pop()
                self._in_use[resource_id] = datetime.utcnow()
                self._stats["acquired"] += 1
                return resource_id
            
            # Create new resource if under max size
            if len(self._in_use) < self.max_size:
                resource_id = await self._create_resource()
                if resource_id:
                    self._in_use[resource_id] = datetime.utcnow()
                    self._stats["acquired"] += 1
                    return resource_id
            
            # Pool is full
            return None
            
        except Exception as e:
            logger.error(f"Resource acquisition failed: {e}")
            return None
    
    async def release(self, resource_id: str) -> bool:
        """Release a resource back to the pool."""
        try:
            if resource_id in self._in_use:
                del self._in_use[resource_id]
                
                # Add back to available pool if under max size
                if len(self._available) + len(self._in_use) < self.max_size:
                    self._available.append(resource_id)
                else:
                    await self._destroy_resource(resource_id)
                
                self._stats["released"] += 1
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Resource release failed: {e}")
            return False
    
    async def _create_resource(self) -> Optional[str]:
        """Create a new resource."""
        try:
            self._created_count += 1
            resource_id = f"{self.pool_type}_resource_{self._created_count}"
            self._stats["created"] += 1
            return resource_id
        except Exception as e:
            logger.error(f"Resource creation failed: {e}")
            return None
    
    async def _destroy_resource(self, resource_id: str) -> bool:
        """Destroy a resource."""
        try:
            # Resource cleanup would happen here
            self._stats["destroyed"] += 1
            return True
        except Exception as e:
            logger.error(f"Resource destruction failed: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get pool status."""
        return {
            "pool_type": self.pool_type,
            "max_size": self.max_size,
            "min_size": self.min_size,
            "available": len(self._available),
            "in_use": len(self._in_use),
            "total": len(self._available) + len(self._in_use),
            "stats": self._stats.copy()
        }


# Global instances
_cache_manager = CacheManager()
_performance_monitor = PerformanceMonitor()
_resource_pools = {}


class CacheTool(BaseTool):
    """Tool for cache operations."""
    
    @property
    def name(self) -> str:
        return "cache_manager"
    
    @property
    def description(self) -> str:
        return "Manage in-memory cache for performance optimization"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.WORKFLOW_MANAGEMENT
    
    async def execute(self, input_data: CacheInput) -> ToolResult:
        """Execute cache operation."""
        try:
            global _cache_manager
            
            if input_data.operation == "get":
                value = _cache_manager.get(input_data.key)
                result = {
                    "operation": "get",
                    "key": input_data.key,
                    "value": value,
                    "found": value is not None
                }
            
            elif input_data.operation == "set":
                success = _cache_manager.set(input_data.key, input_data.value, input_data.ttl)
                result = {
                    "operation": "set",
                    "key": input_data.key,
                    "success": success,
                    "ttl": input_data.ttl
                }
            
            elif input_data.operation == "delete":
                success = _cache_manager.delete(input_data.key)
                result = {
                    "operation": "delete",
                    "key": input_data.key,
                    "success": success
                }
            
            elif input_data.operation == "clear":
                success = _cache_manager.clear()
                result = {
                    "operation": "clear",
                    "success": success
                }
            
            elif input_data.operation == "stats":
                result = {
                    "operation": "stats",
                    "stats": _cache_manager.get_stats()
                }
            
            else:
                raise ValueError(f"Unknown cache operation: {input_data.operation}")
            
            return ToolResult(
                success=True,
                data=result,
                metadata={
                    "timestamp": datetime.utcnow().isoformat(),
                    "user_id": input_data.user_id
                },
                execution_time=0.0,
                tool_name=self.name
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                errors=[f"Cache operation failed: {str(e)}"],
                execution_time=0.0,
                tool_name=self.name
            )


class PerformanceMonitorTool(BaseTool):
    """Tool for performance monitoring."""
    
    @property
    def name(self) -> str:
        return "performance_monitor"
    
    @property
    def description(self) -> str:
        return "Monitor and track performance metrics for optimization"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.WORKFLOW_MANAGEMENT
    
    async def execute(self, input_data: PerformanceMonitorInput) -> ToolResult:
        """Execute performance monitoring operation."""
        try:
            global _performance_monitor
            
            if input_data.operation == "start":
                timer_id = _performance_monitor.start_timer(input_data.metric_name, input_data.metadata)
                result = {
                    "operation": "start",
                    "metric_name": input_data.metric_name,
                    "timer_id": timer_id
                }
            
            elif input_data.operation == "stop":
                timer_id = input_data.metadata.get("timer_id")
                if not timer_id:
                    raise ValueError("Timer ID required for stop operation")
                
                duration = _performance_monitor.stop_timer(timer_id)
                result = {
                    "operation": "stop",
                    "metric_name": input_data.metric_name,
                    "timer_id": timer_id,
                    "duration": duration
                }
            
            elif input_data.operation == "increment":
                count = _performance_monitor.increment_counter(
                    input_data.metric_name,
                    input_data.metadata.get("value", 1)
                )
                result = {
                    "operation": "increment",
                    "metric_name": input_data.metric_name,
                    "count": count
                }
            
            elif input_data.operation == "report":
                metrics = _performance_monitor.get_metrics(input_data.metric_name)
                result = {
                    "operation": "report",
                    "metrics": metrics
                }
            
            else:
                raise ValueError(f"Unknown monitor operation: {input_data.operation}")
            
            return ToolResult(
                success=True,
                data=result,
                metadata={
                    "timestamp": datetime.utcnow().isoformat(),
                    "user_id": input_data.user_id
                },
                execution_time=0.0,
                tool_name=self.name
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                errors=[f"Performance monitoring failed: {str(e)}"],
                execution_time=0.0,
                tool_name=self.name
            )


def performance_cache(ttl: int = 300, key_func: Optional[Callable] = None):
    """Decorator for caching function results."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default key generation
                key_data = {
                    "func": func.__name__,
                    "args": str(args),
                    "kwargs": str(sorted(kwargs.items()))
                }
                cache_key = hashlib.md5(json.dumps(key_data, sort_keys=True).encode()).hexdigest()
            
            # Try to get from cache
            cached_result = _cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            _cache_manager.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator


def performance_timer(metric_name: Optional[str] = None):
    """Decorator for timing function execution."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            timer_metric = metric_name or f"{func.__module__}.{func.__name__}"
            timer_id = _performance_monitor.start_timer(timer_metric)
            
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                _performance_monitor.stop_timer(timer_id)
        
        return wrapper
    return decorator
