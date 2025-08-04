"""
Advanced Memory Management and Monitoring System.

This module provides memory optimization, garbage collection management,
memory leak detection, and comprehensive memory usage monitoring.
"""

import gc
import sys
import psutil
import asyncio
import time
import tracemalloc
from typing import Dict, List, Any, Optional, Callable, Set
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import structlog
from collections import defaultdict, deque
import statistics
import weakref

logger = structlog.get_logger(__name__)


class MemoryAlert(Enum):
    """Memory alert levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class GCStrategy(Enum):
    """Garbage collection strategies."""
    AUTOMATIC = "automatic"
    SCHEDULED = "scheduled"
    THRESHOLD_BASED = "threshold_based"
    ADAPTIVE = "adaptive"


@dataclass
class MemorySnapshot:
    """Memory usage snapshot."""
    timestamp: datetime
    total_memory_mb: float
    available_memory_mb: float
    used_memory_mb: float
    memory_percent: float
    process_memory_mb: float
    process_memory_percent: float
    gc_collections: Dict[int, int]
    object_counts: Dict[str, int]
    top_memory_consumers: List[Dict[str, Any]]


@dataclass
class MemoryLeak:
    """Memory leak detection result."""
    leak_id: str
    object_type: str
    growth_rate_mb_per_hour: float
    current_count: int
    baseline_count: int
    first_detected: datetime
    last_updated: datetime
    severity: MemoryAlert
    stack_trace: Optional[str] = None


@dataclass
class GCStats:
    """Garbage collection statistics."""
    generation: int
    collections: int
    collected: int
    uncollectable: int
    collection_time: float


class AdvancedMemoryManager:
    """Advanced memory management with leak detection and optimization."""

    def __init__(self):
        self.monitoring_enabled = True
        self.memory_snapshots: deque = deque(maxlen=1000)
        self.memory_alerts: deque = deque(maxlen=100)
        self.detected_leaks: Dict[str, MemoryLeak] = {}

        # Memory thresholds (percentages)
        self.alert_thresholds = {
            MemoryAlert.LOW: 60.0,
            MemoryAlert.MEDIUM: 75.0,
            MemoryAlert.HIGH: 85.0,
            MemoryAlert.CRITICAL: 95.0
        }

        # GC configuration
        self.gc_strategy = GCStrategy.ADAPTIVE
        self.gc_stats_history: deque = deque(maxlen=100)
        self.last_gc_time = time.time()
        self.gc_threshold_multiplier = 1.0

        # Memory tracking
        self.object_trackers: Dict[str, weakref.WeakSet] = defaultdict(weakref.WeakSet)
        self.memory_baselines: Dict[str, int] = {}
        self.leak_detection_enabled = True
        self.leak_detection_interval = 300  # 5 minutes

        # Performance optimization
        self.optimization_callbacks: List[Callable] = []
        self.memory_pressure_callbacks: List[Callable] = []

        # Start tracemalloc for detailed memory tracking
        if not tracemalloc.is_tracing():
            tracemalloc.start(10)  # Keep 10 frames

        # Background tasks will be started when needed
        self._monitoring_tasks_started = False

    def _start_monitoring(self):
        """Start background memory monitoring tasks."""
        if not self._monitoring_tasks_started:
            try:
                asyncio.create_task(self._memory_monitoring_loop())
                asyncio.create_task(self._leak_detection_loop())
                asyncio.create_task(self._gc_optimization_loop())
                self._monitoring_tasks_started = True
            except RuntimeError:
                # No event loop running, tasks will be started when needed
                pass

    async def _memory_monitoring_loop(self):
        """Background memory monitoring loop."""
        while self.monitoring_enabled:
            try:
                snapshot = await self._take_memory_snapshot()
                self.memory_snapshots.append(snapshot)

                # Check for memory alerts
                await self._check_memory_alerts(snapshot)

                # Trigger optimization if needed
                if snapshot.memory_percent > self.alert_thresholds[MemoryAlert.HIGH]:
                    await self._trigger_memory_optimization()

                await asyncio.sleep(30)  # Monitor every 30 seconds

            except Exception as e:
                logger.error(f"Memory monitoring loop error: {e}")
                await asyncio.sleep(10)

    async def _take_memory_snapshot(self) -> MemorySnapshot:
        """Take a comprehensive memory snapshot."""
        # System memory info
        memory_info = psutil.virtual_memory()

        # Process memory info
        process = psutil.Process()
        process_memory = process.memory_info()

        # GC statistics
        gc_stats = {}
        for generation in range(3):
            stats = gc.get_stats()[generation]
            gc_stats[generation] = stats['collections']

        # Object counts
        object_counts = {}
        for obj_type in ['dict', 'list', 'tuple', 'set', 'function']:
            count = len([obj for obj in gc.get_objects() if type(obj).__name__ == obj_type])
            object_counts[obj_type] = count

        # Top memory consumers (using tracemalloc)
        top_consumers = []
        if tracemalloc.is_tracing():
            current, peak = tracemalloc.get_traced_memory()
            snapshot = tracemalloc.take_snapshot()
            top_stats = snapshot.statistics('lineno')[:10]

            for stat in top_stats:
                top_consumers.append({
                    'filename': stat.traceback.format()[-1] if stat.traceback else 'unknown',
                    'size_mb': stat.size / (1024 * 1024),
                    'count': stat.count
                })

        return MemorySnapshot(
            timestamp=datetime.utcnow(),
            total_memory_mb=memory_info.total / (1024 * 1024),
            available_memory_mb=memory_info.available / (1024 * 1024),
            used_memory_mb=memory_info.used / (1024 * 1024),
            memory_percent=memory_info.percent,
            process_memory_mb=process_memory.rss / (1024 * 1024),
            process_memory_percent=(process_memory.rss / memory_info.total) * 100,
            gc_collections=gc_stats,
            object_counts=object_counts,
            top_memory_consumers=top_consumers
        )

    async def _check_memory_alerts(self, snapshot: MemorySnapshot):
        """Check for memory alerts and trigger notifications."""
        current_level = None

        for level, threshold in self.alert_thresholds.items():
            if snapshot.memory_percent >= threshold:
                current_level = level

        if current_level and current_level != MemoryAlert.LOW:
            alert = {
                'level': current_level,
                'memory_percent': snapshot.memory_percent,
                'process_memory_mb': snapshot.process_memory_mb,
                'timestamp': snapshot.timestamp,
                'message': f"Memory usage at {snapshot.memory_percent:.1f}% ({current_level.value} alert)"
            }

            self.memory_alerts.append(alert)
            logger.warning(f"Memory alert: {alert['message']}")

            # Trigger memory pressure callbacks
            if current_level in [MemoryAlert.HIGH, MemoryAlert.CRITICAL]:
                await self._trigger_memory_pressure_callbacks(snapshot)

    async def _trigger_memory_optimization(self):
        """Trigger memory optimization strategies."""
        logger.info("Triggering memory optimization")

        # Force garbage collection
        collected = await self._force_garbage_collection()
        logger.info(f"Garbage collection freed {collected} objects")

        # Clear caches
        await self._clear_memory_caches()

        # Run optimization callbacks
        for callback in self.optimization_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                logger.error(f"Memory optimization callback failed: {e}")

    async def _trigger_memory_pressure_callbacks(self, snapshot: MemorySnapshot):
        """Trigger memory pressure callbacks."""
        for callback in self.memory_pressure_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(snapshot)
                else:
                    callback(snapshot)
            except Exception as e:
                logger.error(f"Memory pressure callback failed: {e}")

    async def _force_garbage_collection(self) -> int:
        """Force garbage collection and return number of collected objects."""
        collected_total = 0

        # Collect each generation
        for generation in range(3):
            collected = gc.collect(generation)
            collected_total += collected

        # Update GC stats
        gc_stats = []
        for generation in range(3):
            stats = gc.get_stats()[generation]
            gc_stats.append(GCStats(
                generation=generation,
                collections=stats['collections'],
                collected=stats['collected'],
                uncollectable=stats['uncollectable'],
                collection_time=time.time() - self.last_gc_time
            ))

        self.gc_stats_history.append(gc_stats)
        self.last_gc_time = time.time()

        return collected_total

    async def _clear_memory_caches(self):
        """Clear various memory caches."""
        # Clear function caches
        for obj in gc.get_objects():
            if hasattr(obj, 'cache_clear') and callable(obj.cache_clear):
                try:
                    obj.cache_clear()
                except:
                    pass

        # Clear sys modules cache
        if hasattr(sys, '_clear_type_cache'):
            sys._clear_type_cache()

    async def _leak_detection_loop(self):
        """Background memory leak detection loop."""
        while self.leak_detection_enabled:
            try:
                await self._detect_memory_leaks()
                await asyncio.sleep(self.leak_detection_interval)

            except Exception as e:
                logger.error(f"Leak detection loop error: {e}")
                await asyncio.sleep(60)

    async def _detect_memory_leaks(self):
        """Detect potential memory leaks."""
        if not self.memory_snapshots:
            return

        # Analyze object count trends
        if len(self.memory_snapshots) < 5:
            return  # Need enough data points

        recent_snapshots = list(self.memory_snapshots)[-10:]  # Last 10 snapshots

        for obj_type in ['dict', 'list', 'tuple', 'set', 'function']:
            counts = [s.object_counts.get(obj_type, 0) for s in recent_snapshots]

            if len(counts) < 5:
                continue

            # Calculate growth rate
            time_span_hours = (recent_snapshots[-1].timestamp - recent_snapshots[0].timestamp).total_seconds() / 3600
            if time_span_hours == 0:
                continue

            growth_rate = (counts[-1] - counts[0]) / time_span_hours

            # Check if this represents a potential leak
            if growth_rate > 100:  # More than 100 objects per hour growth
                leak_id = f"leak_{obj_type}_{int(time.time())}"

                # Determine severity
                if growth_rate > 1000:
                    severity = MemoryAlert.CRITICAL
                elif growth_rate > 500:
                    severity = MemoryAlert.HIGH
                elif growth_rate > 200:
                    severity = MemoryAlert.MEDIUM
                else:
                    severity = MemoryAlert.LOW

                # Create or update leak record
                if leak_id not in self.detected_leaks:
                    self.detected_leaks[leak_id] = MemoryLeak(
                        leak_id=leak_id,
                        object_type=obj_type,
                        growth_rate_mb_per_hour=growth_rate * 0.001,  # Rough estimate
                        current_count=counts[-1],
                        baseline_count=counts[0],
                        first_detected=datetime.utcnow(),
                        last_updated=datetime.utcnow(),
                        severity=severity
                    )

                    logger.warning(f"Potential memory leak detected: {obj_type} growing at {growth_rate:.1f} objects/hour")
                else:
                    leak = self.detected_leaks[leak_id]
                    leak.current_count = counts[-1]
                    leak.growth_rate_mb_per_hour = growth_rate * 0.001
                    leak.last_updated = datetime.utcnow()
                    leak.severity = severity

    async def _gc_optimization_loop(self):
        """Background garbage collection optimization loop."""
        while self.monitoring_enabled:
            try:
                if self.gc_strategy == GCStrategy.ADAPTIVE:
                    await self._adaptive_gc_tuning()
                elif self.gc_strategy == GCStrategy.THRESHOLD_BASED:
                    await self._threshold_based_gc()
                elif self.gc_strategy == GCStrategy.SCHEDULED:
                    await self._scheduled_gc()

                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                logger.error(f"GC optimization loop error: {e}")
                await asyncio.sleep(30)

    async def _adaptive_gc_tuning(self):
        """Adaptive garbage collection tuning based on memory pressure."""
        if not self.memory_snapshots:
            return

        latest_snapshot = self.memory_snapshots[-1]
        memory_pressure = latest_snapshot.memory_percent

        # Adjust GC thresholds based on memory pressure
        if memory_pressure > 80:
            # High memory pressure - more aggressive GC
            self.gc_threshold_multiplier = 0.5
            gc.set_threshold(350, 5, 5)  # More frequent GC
        elif memory_pressure > 60:
            # Medium memory pressure - moderate GC
            self.gc_threshold_multiplier = 0.75
            gc.set_threshold(500, 10, 10)
        else:
            # Low memory pressure - standard GC
            self.gc_threshold_multiplier = 1.0
            gc.set_threshold(700, 10, 10)  # Default thresholds

    async def _threshold_based_gc(self):
        """Threshold-based garbage collection."""
        if not self.memory_snapshots:
            return

        latest_snapshot = self.memory_snapshots[-1]

        if latest_snapshot.memory_percent > 75:
            await self._force_garbage_collection()

    async def _scheduled_gc(self):
        """Scheduled garbage collection."""
        # Force GC every 5 minutes
        if time.time() - self.last_gc_time > 300:
            await self._force_garbage_collection()

    def register_object_tracker(self, category: str, obj: Any):
        """Register an object for tracking."""
        self.object_trackers[category].add(obj)

    def register_optimization_callback(self, callback: Callable):
        """Register a callback for memory optimization."""
        self.optimization_callbacks.append(callback)

    def register_memory_pressure_callback(self, callback: Callable):
        """Register a callback for memory pressure events."""
        self.memory_pressure_callbacks.append(callback)

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics."""
        if not self.memory_snapshots:
            return {}

        latest_snapshot = self.memory_snapshots[-1]

        # Calculate trends
        if len(self.memory_snapshots) >= 2:
            previous_snapshot = self.memory_snapshots[-2]
            memory_trend = latest_snapshot.memory_percent - previous_snapshot.memory_percent
            process_memory_trend = latest_snapshot.process_memory_mb - previous_snapshot.process_memory_mb
        else:
            memory_trend = 0
            process_memory_trend = 0

        # GC statistics
        gc_stats = {}
        if self.gc_stats_history:
            latest_gc = self.gc_stats_history[-1]
            gc_stats = {
                f"generation_{i}": {
                    "collections": stat.collections,
                    "collected": stat.collected,
                    "uncollectable": stat.uncollectable
                }
                for i, stat in enumerate(latest_gc)
            }

        return {
            "current_memory": {
                "total_mb": round(latest_snapshot.total_memory_mb, 2),
                "used_mb": round(latest_snapshot.used_memory_mb, 2),
                "available_mb": round(latest_snapshot.available_memory_mb, 2),
                "usage_percent": round(latest_snapshot.memory_percent, 2),
                "trend_percent": round(memory_trend, 2)
            },
            "process_memory": {
                "used_mb": round(latest_snapshot.process_memory_mb, 2),
                "usage_percent": round(latest_snapshot.process_memory_percent, 2),
                "trend_mb": round(process_memory_trend, 2)
            },
            "object_counts": latest_snapshot.object_counts,
            "gc_statistics": gc_stats,
            "memory_leaks": {
                "detected_count": len(self.detected_leaks),
                "critical_leaks": len([l for l in self.detected_leaks.values() if l.severity == MemoryAlert.CRITICAL]),
                "high_leaks": len([l for l in self.detected_leaks.values() if l.severity == MemoryAlert.HIGH])
            },
            "alerts": {
                "recent_alerts": len([a for a in self.memory_alerts if (datetime.utcnow() - a['timestamp']).total_seconds() < 3600]),
                "critical_alerts": len([a for a in self.memory_alerts if a['level'] == MemoryAlert.CRITICAL])
            },
            "optimization": {
                "gc_strategy": self.gc_strategy.value,
                "gc_threshold_multiplier": self.gc_threshold_multiplier,
                "optimization_callbacks": len(self.optimization_callbacks),
                "pressure_callbacks": len(self.memory_pressure_callbacks)
            },
            "monitoring": {
                "snapshots_collected": len(self.memory_snapshots),
                "leak_detection_enabled": self.leak_detection_enabled,
                "tracemalloc_enabled": tracemalloc.is_tracing()
            }
        }

    def get_memory_leaks(self) -> List[Dict[str, Any]]:
        """Get detected memory leaks."""
        return [
            {
                "leak_id": leak.leak_id,
                "object_type": leak.object_type,
                "growth_rate_mb_per_hour": round(leak.growth_rate_mb_per_hour, 4),
                "current_count": leak.current_count,
                "baseline_count": leak.baseline_count,
                "growth_count": leak.current_count - leak.baseline_count,
                "first_detected": leak.first_detected.isoformat(),
                "last_updated": leak.last_updated.isoformat(),
                "severity": leak.severity.value,
                "duration_hours": (datetime.utcnow() - leak.first_detected).total_seconds() / 3600
            }
            for leak in self.detected_leaks.values()
        ]

    def get_recent_alerts(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent memory alerts."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        return [
            alert for alert in self.memory_alerts
            if alert['timestamp'] >= cutoff_time
        ]

    async def cleanup_resources(self):
        """Cleanup resources and stop monitoring."""
        self.monitoring_enabled = False
        self.leak_detection_enabled = False

        # Force final garbage collection
        await self._force_garbage_collection()

        # Stop tracemalloc
        if tracemalloc.is_tracing():
            tracemalloc.stop()


# Global memory manager instance
_memory_manager = None


def get_memory_manager() -> AdvancedMemoryManager:
    """Get the global memory manager instance."""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = AdvancedMemoryManager()
    return _memory_manager
