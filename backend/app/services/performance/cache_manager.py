"""
Advanced Multi-Level Caching System for AI Agents.

This module provides intelligent caching strategies, cache invalidation,
distributed caching, and cache warming for optimal performance.
"""

import asyncio
import json
import hashlib
import time
from typing import Dict, List, Any, Optional, Union, Callable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import structlog
from collections import OrderedDict
import pickle
import zlib

logger = structlog.get_logger(__name__)


class CacheLevel(Enum):
    """Cache levels in the hierarchy."""
    L1_MEMORY = "l1_memory"
    L2_REDIS = "l2_redis"
    L3_DATABASE = "l3_database"


class CacheStrategy(Enum):
    """Cache replacement strategies."""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    FIFO = "fifo"  # First In, First Out
    TTL = "ttl"  # Time To Live based


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    ttl_seconds: Optional[int] = None
    size_bytes: int = 0
    tags: List[str] = field(default_factory=list)
    compressed: bool = False


@dataclass
class CacheStats:
    """Cache performance statistics."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size_bytes: int = 0
    entry_count: int = 0
    avg_access_time: float = 0.0
    hit_rate: float = 0.0


class MemoryCache:
    """High-performance in-memory cache (L1)."""
    
    def __init__(self, max_size: int = 1000, max_memory_mb: int = 512):
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.stats = CacheStats()
        self.strategy = CacheStrategy.LRU
        
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        start_time = time.time()
        
        if key in self.cache:
            entry = self.cache[key]
            
            # Check TTL
            if entry.ttl_seconds:
                age = (datetime.utcnow() - entry.created_at).total_seconds()
                if age > entry.ttl_seconds:
                    await self.delete(key)
                    self.stats.misses += 1
                    return None
            
            # Update access metadata
            entry.last_accessed = datetime.utcnow()
            entry.access_count += 1
            
            # Move to end for LRU
            if self.strategy == CacheStrategy.LRU:
                self.cache.move_to_end(key)
            
            self.stats.hits += 1
            
            # Decompress if needed
            value = entry.value
            if entry.compressed:
                value = pickle.loads(zlib.decompress(value))
            
            access_time = time.time() - start_time
            self._update_avg_access_time(access_time)
            
            return value
        
        self.stats.misses += 1
        return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
        tags: List[str] = None,
        compress: bool = False
    ) -> bool:
        """Set value in cache."""
        try:
            # Serialize and optionally compress
            serialized_value = value
            compressed = False
            
            if compress and self._should_compress(value):
                serialized_value = zlib.compress(pickle.dumps(value))
                compressed = True
            
            # Calculate size
            size_bytes = self._calculate_size(serialized_value)
            
            # Check if we need to evict entries
            await self._ensure_capacity(size_bytes)
            
            # Create cache entry
            entry = CacheEntry(
                key=key,
                value=serialized_value,
                created_at=datetime.utcnow(),
                last_accessed=datetime.utcnow(),
                ttl_seconds=ttl_seconds,
                size_bytes=size_bytes,
                tags=tags or [],
                compressed=compressed
            )
            
            # Remove existing entry if present
            if key in self.cache:
                old_entry = self.cache[key]
                self.stats.size_bytes -= old_entry.size_bytes
                del self.cache[key]
            
            # Add new entry
            self.cache[key] = entry
            self.stats.size_bytes += size_bytes
            self.stats.entry_count = len(self.cache)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to set cache entry {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete entry from cache."""
        if key in self.cache:
            entry = self.cache[key]
            self.stats.size_bytes -= entry.size_bytes
            del self.cache[key]
            self.stats.entry_count = len(self.cache)
            return True
        return False
    
    async def clear_by_tags(self, tags: List[str]) -> int:
        """Clear entries by tags."""
        keys_to_delete = []
        
        for key, entry in self.cache.items():
            if any(tag in entry.tags for tag in tags):
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            await self.delete(key)
        
        return len(keys_to_delete)
    
    async def _ensure_capacity(self, new_entry_size: int):
        """Ensure cache has capacity for new entry."""
        # Check size limit
        while (self.stats.size_bytes + new_entry_size > self.max_memory_bytes or
               len(self.cache) >= self.max_size):
            
            if not self.cache:
                break
            
            # Evict based on strategy
            if self.strategy == CacheStrategy.LRU:
                # Remove least recently used (first item)
                key, entry = self.cache.popitem(last=False)
            elif self.strategy == CacheStrategy.LFU:
                # Remove least frequently used
                key = min(self.cache.keys(), key=lambda k: self.cache[k].access_count)
                entry = self.cache.pop(key)
            elif self.strategy == CacheStrategy.FIFO:
                # Remove oldest entry
                key, entry = self.cache.popitem(last=False)
            else:  # TTL or default to LRU
                key, entry = self.cache.popitem(last=False)
            
            self.stats.size_bytes -= entry.size_bytes
            self.stats.evictions += 1
        
        self.stats.entry_count = len(self.cache)
    
    def _should_compress(self, value: Any) -> bool:
        """Determine if value should be compressed."""
        try:
            size = self._calculate_size(value)
            return size > 1024  # Compress if larger than 1KB
        except:
            return False
    
    def _calculate_size(self, value: Any) -> int:
        """Calculate approximate size of value in bytes."""
        try:
            if isinstance(value, (str, bytes)):
                return len(value)
            elif isinstance(value, (int, float)):
                return 8
            elif isinstance(value, (list, dict)):
                return len(json.dumps(value, default=str).encode())
            else:
                return len(pickle.dumps(value))
        except:
            return 100  # Default estimate
    
    def _update_avg_access_time(self, access_time: float):
        """Update average access time."""
        total_accesses = self.stats.hits + self.stats.misses
        if total_accesses > 0:
            self.stats.avg_access_time = (
                (self.stats.avg_access_time * (total_accesses - 1) + access_time) / total_accesses
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.stats.hits + self.stats.misses
        hit_rate = (self.stats.hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "level": "L1_MEMORY",
            "hits": self.stats.hits,
            "misses": self.stats.misses,
            "hit_rate": round(hit_rate, 2),
            "evictions": self.stats.evictions,
            "entry_count": self.stats.entry_count,
            "size_mb": round(self.stats.size_bytes / (1024 * 1024), 2),
            "max_size_mb": round(self.max_memory_bytes / (1024 * 1024), 2),
            "avg_access_time_ms": round(self.stats.avg_access_time * 1000, 3),
            "strategy": self.strategy.value
        }


class AdvancedCacheManager:
    """Multi-level cache manager with intelligent strategies."""
    
    def __init__(self):
        # Initialize cache levels
        self.l1_cache = MemoryCache(max_size=2000, max_memory_mb=1024)
        self.l2_cache = None  # Redis cache (would be initialized with Redis connection)
        self.l3_cache = None  # Database cache (would be initialized with DB connection)
        
        # Cache warming configuration
        self.warm_cache_enabled = True
        self.warm_cache_keys = [
            "knowledge_base:legal_requirements",
            "knowledge_base:compliance_rules",
            "knowledge_base:document_templates",
            "market_data:recent_analysis",
            "agent_tools:configurations"
        ]
        
        # Cache invalidation patterns
        self.invalidation_patterns = {
            "knowledge_base:*": ["legal_requirements", "compliance_rules", "templates"],
            "market_data:*": ["property_analysis", "valuations"],
            "agent_tools:*": ["tool_configs", "agent_capabilities"]
        }
        
        # Performance monitoring
        self.performance_metrics = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "avg_response_time": 0.0,
            "last_reset": datetime.utcnow()
        }
    
    async def get(
        self,
        key: str,
        fallback_func: Optional[Callable] = None,
        ttl_seconds: Optional[int] = None,
        tags: List[str] = None
    ) -> Optional[Any]:
        """Get value from multi-level cache with fallback."""
        start_time = time.time()
        self.performance_metrics["total_requests"] += 1
        
        # Try L1 cache first
        value = await self.l1_cache.get(key)
        if value is not None:
            self.performance_metrics["cache_hits"] += 1
            self._update_response_time(time.time() - start_time)
            return value
        
        # Try L2 cache (Redis) if available
        if self.l2_cache:
            value = await self._get_from_l2(key)
            if value is not None:
                # Promote to L1
                await self.l1_cache.set(key, value, ttl_seconds, tags)
                self.performance_metrics["cache_hits"] += 1
                self._update_response_time(time.time() - start_time)
                return value
        
        # Try L3 cache (Database) if available
        if self.l3_cache:
            value = await self._get_from_l3(key)
            if value is not None:
                # Promote to L1 and L2
                await self.l1_cache.set(key, value, ttl_seconds, tags)
                if self.l2_cache:
                    await self._set_to_l2(key, value, ttl_seconds, tags)
                self.performance_metrics["cache_hits"] += 1
                self._update_response_time(time.time() - start_time)
                return value
        
        # Use fallback function if provided
        if fallback_func:
            try:
                value = await fallback_func() if asyncio.iscoroutinefunction(fallback_func) else fallback_func()
                if value is not None:
                    # Cache the result
                    await self.set(key, value, ttl_seconds, tags)
                    self.performance_metrics["cache_hits"] += 1
                    self._update_response_time(time.time() - start_time)
                    return value
            except Exception as e:
                logger.error(f"Fallback function failed for key {key}: {e}")
        
        self.performance_metrics["cache_misses"] += 1
        self._update_response_time(time.time() - start_time)
        return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
        tags: List[str] = None,
        levels: List[CacheLevel] = None
    ) -> bool:
        """Set value in specified cache levels."""
        if levels is None:
            levels = [CacheLevel.L1_MEMORY]
        
        success = True
        
        # Set in L1 cache
        if CacheLevel.L1_MEMORY in levels:
            result = await self.l1_cache.set(key, value, ttl_seconds, tags, compress=True)
            success = success and result
        
        # Set in L2 cache (Redis)
        if CacheLevel.L2_REDIS in levels and self.l2_cache:
            result = await self._set_to_l2(key, value, ttl_seconds, tags)
            success = success and result
        
        # Set in L3 cache (Database)
        if CacheLevel.L3_DATABASE in levels and self.l3_cache:
            result = await self._set_to_l3(key, value, ttl_seconds, tags)
            success = success and result
        
        return success
    
    async def delete(self, key: str, levels: List[CacheLevel] = None) -> bool:
        """Delete key from specified cache levels."""
        if levels is None:
            levels = [CacheLevel.L1_MEMORY, CacheLevel.L2_REDIS, CacheLevel.L3_DATABASE]
        
        success = True
        
        if CacheLevel.L1_MEMORY in levels:
            result = await self.l1_cache.delete(key)
            success = success and result
        
        if CacheLevel.L2_REDIS in levels and self.l2_cache:
            result = await self._delete_from_l2(key)
            success = success and result
        
        if CacheLevel.L3_DATABASE in levels and self.l3_cache:
            result = await self._delete_from_l3(key)
            success = success and result
        
        return success
    
    async def invalidate_by_pattern(self, pattern: str) -> int:
        """Invalidate cache entries matching pattern."""
        total_invalidated = 0
        
        # Get tags to invalidate based on pattern
        tags_to_invalidate = []
        for pattern_key, tags in self.invalidation_patterns.items():
            if self._pattern_matches(pattern, pattern_key):
                tags_to_invalidate.extend(tags)
        
        if tags_to_invalidate:
            # Invalidate by tags in L1
            count = await self.l1_cache.clear_by_tags(tags_to_invalidate)
            total_invalidated += count
            
            # Invalidate in L2 and L3 if available
            if self.l2_cache:
                count = await self._clear_l2_by_tags(tags_to_invalidate)
                total_invalidated += count
            
            if self.l3_cache:
                count = await self._clear_l3_by_tags(tags_to_invalidate)
                total_invalidated += count
        
        logger.info(f"Invalidated {total_invalidated} cache entries for pattern: {pattern}")
        return total_invalidated
    
    async def warm_cache(self, keys: List[str] = None) -> int:
        """Warm cache with frequently accessed data."""
        if not self.warm_cache_enabled:
            return 0
        
        keys_to_warm = keys or self.warm_cache_keys
        warmed_count = 0
        
        for key in keys_to_warm:
            try:
                # Check if already cached
                if await self.l1_cache.get(key) is not None:
                    continue
                
                # Load data based on key pattern
                data = await self._load_warm_data(key)
                if data is not None:
                    await self.set(key, data, ttl_seconds=3600, tags=["warm_cache"])
                    warmed_count += 1
                    
            except Exception as e:
                logger.error(f"Failed to warm cache for key {key}: {e}")
        
        logger.info(f"Warmed cache with {warmed_count} entries")
        return warmed_count
    
    async def _load_warm_data(self, key: str) -> Optional[Any]:
        """Load data for cache warming based on key pattern."""
        # This would integrate with actual data sources
        # For now, return mock data based on key patterns
        
        if key.startswith("knowledge_base:"):
            return {"type": "knowledge_base", "data": f"warm_data_for_{key}"}
        elif key.startswith("market_data:"):
            return {"type": "market_data", "data": f"warm_data_for_{key}"}
        elif key.startswith("agent_tools:"):
            return {"type": "agent_tools", "data": f"warm_data_for_{key}"}
        
        return None
    
    def _pattern_matches(self, pattern: str, key: str) -> bool:
        """Check if pattern matches key (simple wildcard matching)."""
        if "*" not in pattern:
            return pattern == key
        
        # Simple wildcard matching
        pattern_parts = pattern.split("*")
        if len(pattern_parts) == 2:
            prefix, suffix = pattern_parts
            return key.startswith(prefix) and key.endswith(suffix)
        
        return False
    
    def _update_response_time(self, response_time: float):
        """Update average response time."""
        total_requests = self.performance_metrics["total_requests"]
        current_avg = self.performance_metrics["avg_response_time"]
        
        self.performance_metrics["avg_response_time"] = (
            (current_avg * (total_requests - 1) + response_time) / total_requests
        )
    
    # Placeholder methods for L2 and L3 cache operations
    async def _get_from_l2(self, key: str) -> Optional[Any]:
        """Get from L2 cache (Redis)."""
        # Would implement Redis operations
        return None
    
    async def _set_to_l2(self, key: str, value: Any, ttl_seconds: Optional[int], tags: List[str]) -> bool:
        """Set to L2 cache (Redis)."""
        # Would implement Redis operations
        return True
    
    async def _delete_from_l2(self, key: str) -> bool:
        """Delete from L2 cache (Redis)."""
        # Would implement Redis operations
        return True
    
    async def _clear_l2_by_tags(self, tags: List[str]) -> int:
        """Clear L2 cache by tags."""
        # Would implement Redis operations
        return 0
    
    async def _get_from_l3(self, key: str) -> Optional[Any]:
        """Get from L3 cache (Database)."""
        # Would implement database operations
        return None
    
    async def _set_to_l3(self, key: str, value: Any, ttl_seconds: Optional[int], tags: List[str]) -> bool:
        """Set to L3 cache (Database)."""
        # Would implement database operations
        return True
    
    async def _delete_from_l3(self, key: str) -> bool:
        """Delete from L3 cache (Database)."""
        # Would implement database operations
        return True
    
    async def _clear_l3_by_tags(self, tags: List[str]) -> int:
        """Clear L3 cache by tags."""
        # Would implement database operations
        return 0
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache performance statistics."""
        total_requests = self.performance_metrics["total_requests"]
        hit_rate = (self.performance_metrics["cache_hits"] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "multi_level_cache": {
                "total_requests": total_requests,
                "cache_hits": self.performance_metrics["cache_hits"],
                "cache_misses": self.performance_metrics["cache_misses"],
                "hit_rate": round(hit_rate, 2),
                "avg_response_time_ms": round(self.performance_metrics["avg_response_time"] * 1000, 3)
            },
            "l1_cache": self.l1_cache.get_stats(),
            "cache_warming": {
                "enabled": self.warm_cache_enabled,
                "warm_keys_count": len(self.warm_cache_keys)
            },
            "invalidation_patterns": len(self.invalidation_patterns),
            "last_reset": self.performance_metrics["last_reset"].isoformat()
        }


# Global cache manager instance
_cache_manager = None


def get_cache_manager() -> AdvancedCacheManager:
    """Get the global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = AdvancedCacheManager()
    return _cache_manager
