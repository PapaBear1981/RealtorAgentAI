"""
Database Query Optimization for AI Agent Operations.

This module provides database query optimization, connection pooling,
transaction management, and query result caching for improved performance.
"""

import asyncio
import time
import hashlib
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import structlog
from collections import defaultdict, deque
import statistics

logger = structlog.get_logger(__name__)


class QueryType(Enum):
    """Types of database queries."""
    SELECT = "select"
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    BULK_INSERT = "bulk_insert"
    BULK_UPDATE = "bulk_update"


class OptimizationStrategy(Enum):
    """Query optimization strategies."""
    INDEX_HINT = "index_hint"
    QUERY_REWRITE = "query_rewrite"
    BATCH_PROCESSING = "batch_processing"
    RESULT_CACHING = "result_caching"
    CONNECTION_POOLING = "connection_pooling"


@dataclass
class QueryMetrics:
    """Query performance metrics."""
    query_hash: str
    query_type: QueryType
    execution_count: int = 0
    total_execution_time: float = 0.0
    avg_execution_time: float = 0.0
    min_execution_time: float = float('inf')
    max_execution_time: float = 0.0
    last_executed: Optional[datetime] = None
    error_count: int = 0
    rows_affected: int = 0
    cache_hits: int = 0
    cache_misses: int = 0


@dataclass
class ConnectionPoolStats:
    """Connection pool statistics."""
    pool_size: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    total_connections_created: int = 0
    total_connections_closed: int = 0
    avg_connection_lifetime: float = 0.0
    connection_errors: int = 0
    queue_size: int = 0
    avg_wait_time: float = 0.0


class QueryOptimizer:
    """Advanced query optimizer for agent operations."""
    
    def __init__(self):
        self.query_metrics: Dict[str, QueryMetrics] = {}
        self.optimization_rules: Dict[str, Dict[str, Any]] = {}
        self.query_cache: Dict[str, Tuple[Any, datetime]] = {}
        self.cache_ttl = timedelta(minutes=15)
        
        # Connection pool configuration
        self.pool_config = {
            "min_connections": 5,
            "max_connections": 50,
            "connection_timeout": 30,
            "idle_timeout": 300,
            "max_lifetime": 3600
        }
        
        self.pool_stats = ConnectionPoolStats()
        self.active_connections: Dict[str, datetime] = {}
        self.connection_queue = asyncio.Queue()
        
        # Initialize optimization rules
        self._initialize_optimization_rules()
    
    def _initialize_optimization_rules(self):
        """Initialize query optimization rules."""
        self.optimization_rules = {
            # Agent tool queries
            "agent_tools_select": {
                "pattern": "SELECT * FROM agent_tools WHERE agent_role = %s",
                "optimization": {
                    "strategy": OptimizationStrategy.INDEX_HINT,
                    "hint": "USE INDEX (idx_agent_role)",
                    "cache_ttl": 3600
                }
            },
            
            # Contract queries
            "contracts_by_user": {
                "pattern": "SELECT * FROM contracts WHERE user_id = %s ORDER BY created_at DESC",
                "optimization": {
                    "strategy": OptimizationStrategy.INDEX_HINT,
                    "hint": "USE INDEX (idx_user_created)",
                    "cache_ttl": 300
                }
            },
            
            # Template queries
            "templates_by_type": {
                "pattern": "SELECT * FROM templates WHERE template_type = %s AND active = true",
                "optimization": {
                    "strategy": OptimizationStrategy.RESULT_CACHING,
                    "cache_ttl": 1800
                }
            },
            
            # Workflow state queries
            "workflow_states": {
                "pattern": "SELECT * FROM workflow_states WHERE workflow_id = %s",
                "optimization": {
                    "strategy": OptimizationStrategy.RESULT_CACHING,
                    "cache_ttl": 60
                }
            },
            
            # Bulk operations
            "bulk_insert_pattern": {
                "pattern": "INSERT INTO .+ VALUES",
                "optimization": {
                    "strategy": OptimizationStrategy.BATCH_PROCESSING,
                    "batch_size": 1000
                }
            }
        }
    
    async def execute_optimized_query(
        self,
        query: str,
        params: Tuple = None,
        query_type: QueryType = QueryType.SELECT,
        cache_key: str = None
    ) -> Any:
        """Execute query with optimization strategies applied."""
        start_time = time.time()
        query_hash = self._get_query_hash(query, params)
        
        try:
            # Check cache first for SELECT queries
            if query_type == QueryType.SELECT and cache_key:
                cached_result = await self._get_cached_result(cache_key)
                if cached_result is not None:
                    self._update_query_metrics(query_hash, query_type, time.time() - start_time, cache_hit=True)
                    return cached_result
            
            # Apply optimization strategies
            optimized_query, optimized_params = await self._apply_optimizations(query, params, query_type)
            
            # Execute query
            result = await self._execute_query(optimized_query, optimized_params, query_type)
            
            # Cache result if applicable
            if query_type == QueryType.SELECT and cache_key:
                await self._cache_result(cache_key, result)
            
            # Update metrics
            execution_time = time.time() - start_time
            self._update_query_metrics(query_hash, query_type, execution_time, cache_hit=False)
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._update_query_metrics(query_hash, query_type, execution_time, error=True)
            logger.error(f"Query execution failed: {e}")
            raise
    
    async def _apply_optimizations(
        self,
        query: str,
        params: Tuple,
        query_type: QueryType
    ) -> Tuple[str, Tuple]:
        """Apply optimization strategies to query."""
        optimized_query = query
        optimized_params = params or ()
        
        # Find matching optimization rule
        optimization_rule = self._find_optimization_rule(query)
        
        if optimization_rule:
            strategy = optimization_rule.get("strategy")
            
            if strategy == OptimizationStrategy.INDEX_HINT:
                hint = optimization_rule.get("hint", "")
                optimized_query = self._add_index_hint(query, hint)
            
            elif strategy == OptimizationStrategy.QUERY_REWRITE:
                optimized_query = self._rewrite_query(query, optimization_rule)
            
            elif strategy == OptimizationStrategy.BATCH_PROCESSING:
                # For batch processing, the calling code should handle batching
                pass
        
        # Apply general optimizations
        optimized_query = self._apply_general_optimizations(optimized_query, query_type)
        
        return optimized_query, optimized_params
    
    def _find_optimization_rule(self, query: str) -> Optional[Dict[str, Any]]:
        """Find matching optimization rule for query."""
        query_lower = query.lower().strip()
        
        for rule_name, rule_config in self.optimization_rules.items():
            pattern = rule_config.get("pattern", "").lower()
            
            # Simple pattern matching (could be enhanced with regex)
            if pattern in query_lower or self._pattern_matches(pattern, query_lower):
                return rule_config.get("optimization", {})
        
        return None
    
    def _pattern_matches(self, pattern: str, query: str) -> bool:
        """Check if pattern matches query (simple implementation)."""
        # This could be enhanced with proper regex matching
        pattern_words = pattern.split()
        query_words = query.split()
        
        # Check if all pattern words are in query
        return all(word in query_words for word in pattern_words if word not in ["%s", "=", "WHERE"])
    
    def _add_index_hint(self, query: str, hint: str) -> str:
        """Add index hint to query."""
        if not hint or "USE INDEX" not in hint.upper():
            return query
        
        # Find the table name and add hint after it
        query_upper = query.upper()
        from_index = query_upper.find("FROM")
        
        if from_index != -1:
            # Find the table name after FROM
            from_part = query[from_index + 4:].strip()
            table_end = from_part.find(" ")
            
            if table_end == -1:
                table_end = len(from_part)
            
            table_name = from_part[:table_end]
            
            # Insert hint after table name
            optimized_query = (
                query[:from_index + 4] + " " + table_name + " " + hint + " " + from_part[table_end:]
            )
            
            return optimized_query
        
        return query
    
    def _rewrite_query(self, query: str, rule: Dict[str, Any]) -> str:
        """Rewrite query based on optimization rule."""
        # Implement query rewriting logic based on rule
        # This is a placeholder for more sophisticated query rewriting
        return query
    
    def _apply_general_optimizations(self, query: str, query_type: QueryType) -> str:
        """Apply general optimization strategies."""
        optimized_query = query
        
        # Add LIMIT if not present in SELECT queries without explicit LIMIT
        if query_type == QueryType.SELECT and "LIMIT" not in query.upper():
            # Only add LIMIT for queries that might return many rows
            if any(keyword in query.upper() for keyword in ["ORDER BY", "GROUP BY"]):
                optimized_query += " LIMIT 1000"
        
        # Optimize JOIN order (simplified)
        if "JOIN" in query.upper():
            optimized_query = self._optimize_join_order(optimized_query)
        
        return optimized_query
    
    def _optimize_join_order(self, query: str) -> str:
        """Optimize JOIN order (simplified implementation)."""
        # This is a placeholder for more sophisticated JOIN optimization
        # In practice, this would analyze table sizes and selectivity
        return query
    
    async def _execute_query(self, query: str, params: Tuple, query_type: QueryType) -> Any:
        """Execute the actual database query."""
        # This is a placeholder for actual database execution
        # In practice, this would use the actual database connection
        
        # Simulate query execution
        await asyncio.sleep(0.01)  # Simulate database latency
        
        if query_type == QueryType.SELECT:
            return [{"id": 1, "data": "mock_result"}]
        elif query_type in [QueryType.INSERT, QueryType.UPDATE, QueryType.DELETE]:
            return {"rows_affected": 1}
        else:
            return {"status": "success"}
    
    async def _get_cached_result(self, cache_key: str) -> Optional[Any]:
        """Get cached query result."""
        if cache_key in self.query_cache:
            result, cached_at = self.query_cache[cache_key]
            
            # Check if cache is still valid
            if datetime.utcnow() - cached_at < self.cache_ttl:
                return result
            else:
                # Remove expired cache entry
                del self.query_cache[cache_key]
        
        return None
    
    async def _cache_result(self, cache_key: str, result: Any):
        """Cache query result."""
        self.query_cache[cache_key] = (result, datetime.utcnow())
        
        # Clean up old cache entries periodically
        if len(self.query_cache) > 1000:
            await self._cleanup_cache()
    
    async def _cleanup_cache(self):
        """Clean up expired cache entries."""
        current_time = datetime.utcnow()
        expired_keys = []
        
        for cache_key, (result, cached_at) in self.query_cache.items():
            if current_time - cached_at > self.cache_ttl:
                expired_keys.append(cache_key)
        
        for key in expired_keys:
            del self.query_cache[key]
        
        logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def _get_query_hash(self, query: str, params: Tuple = None) -> str:
        """Generate hash for query identification."""
        query_normalized = " ".join(query.split()).lower()
        params_str = str(params) if params else ""
        return hashlib.md5(f"{query_normalized}{params_str}".encode()).hexdigest()
    
    def _update_query_metrics(
        self,
        query_hash: str,
        query_type: QueryType,
        execution_time: float,
        cache_hit: bool = False,
        error: bool = False
    ):
        """Update query performance metrics."""
        if query_hash not in self.query_metrics:
            self.query_metrics[query_hash] = QueryMetrics(
                query_hash=query_hash,
                query_type=query_type
            )
        
        metrics = self.query_metrics[query_hash]
        metrics.execution_count += 1
        metrics.last_executed = datetime.utcnow()
        
        if cache_hit:
            metrics.cache_hits += 1
        else:
            metrics.cache_misses += 1
        
        if error:
            metrics.error_count += 1
        else:
            # Update timing metrics
            metrics.total_execution_time += execution_time
            metrics.avg_execution_time = metrics.total_execution_time / (metrics.execution_count - metrics.error_count)
            metrics.min_execution_time = min(metrics.min_execution_time, execution_time)
            metrics.max_execution_time = max(metrics.max_execution_time, execution_time)
    
    async def get_slow_queries(self, threshold_seconds: float = 1.0, limit: int = 10) -> List[Dict[str, Any]]:
        """Get slow queries that exceed the threshold."""
        slow_queries = []
        
        for query_hash, metrics in self.query_metrics.items():
            if metrics.avg_execution_time > threshold_seconds:
                slow_queries.append({
                    "query_hash": query_hash,
                    "query_type": metrics.query_type.value,
                    "avg_execution_time": round(metrics.avg_execution_time, 4),
                    "max_execution_time": round(metrics.max_execution_time, 4),
                    "execution_count": metrics.execution_count,
                    "error_count": metrics.error_count,
                    "cache_hit_rate": round(
                        (metrics.cache_hits / (metrics.cache_hits + metrics.cache_misses)) * 100, 2
                    ) if (metrics.cache_hits + metrics.cache_misses) > 0 else 0
                })
        
        # Sort by average execution time (descending)
        slow_queries.sort(key=lambda x: x["avg_execution_time"], reverse=True)
        
        return slow_queries[:limit]
    
    def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Get optimization recommendations based on query metrics."""
        recommendations = []
        
        for query_hash, metrics in self.query_metrics.items():
            # Recommend caching for frequently executed SELECT queries
            if (metrics.query_type == QueryType.SELECT and
                metrics.execution_count > 100 and
                metrics.cache_hits == 0):
                recommendations.append({
                    "type": "caching",
                    "query_hash": query_hash,
                    "reason": f"Frequently executed query ({metrics.execution_count} times) with no caching",
                    "priority": "high" if metrics.avg_execution_time > 0.5 else "medium"
                })
            
            # Recommend indexing for slow queries
            if metrics.avg_execution_time > 1.0 and metrics.execution_count > 10:
                recommendations.append({
                    "type": "indexing",
                    "query_hash": query_hash,
                    "reason": f"Slow query (avg: {metrics.avg_execution_time:.2f}s) executed {metrics.execution_count} times",
                    "priority": "high"
                })
            
            # Recommend query rewriting for high error rate
            if metrics.error_count > 0 and metrics.execution_count > 0:
                error_rate = (metrics.error_count / metrics.execution_count) * 100
                if error_rate > 5:
                    recommendations.append({
                        "type": "query_rewrite",
                        "query_hash": query_hash,
                        "reason": f"High error rate ({error_rate:.1f}%)",
                        "priority": "high"
                    })
        
        return recommendations
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive database performance statistics."""
        total_queries = sum(m.execution_count for m in self.query_metrics.values())
        total_errors = sum(m.error_count for m in self.query_metrics.values())
        total_cache_hits = sum(m.cache_hits for m in self.query_metrics.values())
        total_cache_requests = sum(m.cache_hits + m.cache_misses for m in self.query_metrics.values())
        
        avg_execution_times = [m.avg_execution_time for m in self.query_metrics.values() if m.avg_execution_time > 0]
        overall_avg_time = statistics.mean(avg_execution_times) if avg_execution_times else 0
        
        return {
            "query_performance": {
                "total_queries": total_queries,
                "total_errors": total_errors,
                "error_rate": round((total_errors / total_queries) * 100, 2) if total_queries > 0 else 0,
                "avg_execution_time": round(overall_avg_time, 4),
                "unique_queries": len(self.query_metrics)
            },
            "cache_performance": {
                "total_cache_requests": total_cache_requests,
                "cache_hits": total_cache_hits,
                "cache_hit_rate": round((total_cache_hits / total_cache_requests) * 100, 2) if total_cache_requests > 0 else 0,
                "cached_entries": len(self.query_cache)
            },
            "optimization_rules": len(self.optimization_rules),
            "connection_pool": {
                "pool_size": self.pool_stats.pool_size,
                "active_connections": self.pool_stats.active_connections,
                "idle_connections": self.pool_stats.idle_connections
            }
        }


# Global database optimizer instance
_db_optimizer = None


def get_database_optimizer() -> QueryOptimizer:
    """Get the global database optimizer instance."""
    global _db_optimizer
    if _db_optimizer is None:
        _db_optimizer = QueryOptimizer()
    return _db_optimizer
