"""
Agent Memory Management System for multi-agent collaboration.

This module provides shared memory and context management for agents,
enabling collaboration, workflow continuity, and knowledge sharing.
"""

import json
import asyncio
from typing import Dict, Any, List, Optional, Set, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

import structlog
from redis import Redis
from redis.exceptions import RedisError

from ..core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class MemoryType(Enum):
    """Types of memory storage."""
    SHORT_TERM = "short_term"  # Session-based, expires quickly
    LONG_TERM = "long_term"    # Persistent across sessions
    SHARED = "shared"          # Shared between agents
    WORKFLOW = "workflow"      # Workflow-specific context


class MemoryScope(Enum):
    """Scope of memory access."""
    AGENT = "agent"           # Agent-specific memory
    WORKFLOW = "workflow"     # Workflow-specific memory
    GLOBAL = "global"         # Global system memory
    USER = "user"            # User-specific memory


@dataclass
class MemoryEntry:
    """A single memory entry."""
    id: str
    content: Dict[str, Any]
    memory_type: MemoryType
    scope: MemoryScope
    agent_id: Optional[str] = None
    workflow_id: Optional[str] = None
    user_id: Optional[str] = None
    tags: Set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    access_count: int = 0
    last_accessed: Optional[datetime] = None


class AgentMemoryManager:
    """
    Manages memory and context for multi-agent collaboration.

    Provides persistent storage, retrieval, and sharing of information
    between agents to enable workflow continuity and knowledge sharing.
    """

    def __init__(self):
        self.settings = get_settings()
        self._redis_client = None
        self._memory_cache: Dict[str, MemoryEntry] = {}

        # Memory configuration
        self.default_ttl = {
            MemoryType.SHORT_TERM: timedelta(hours=1),
            MemoryType.LONG_TERM: timedelta(days=30),
            MemoryType.SHARED: timedelta(days=7),
            MemoryType.WORKFLOW: timedelta(days=1)
        }

        # Enhanced features for Phase 4
        self._workflow_states = {}
        self._agent_collaboration_data = defaultdict(dict)
        self._performance_metrics = defaultdict(list)
        self._event_listeners = defaultdict(list)

        logger.info("Agent Memory Manager initialized with enhanced collaboration features")

    @property
    def redis_client(self) -> Optional[Redis]:
        """Get Redis client for persistent storage."""
        if self._redis_client is None:
            try:
                self._redis_client = Redis.from_url(
                    self.settings.REDIS_URL,
                    decode_responses=True,
                    socket_timeout=5,
                    socket_connect_timeout=5
                )
                # Test connection
                self._redis_client.ping()
                logger.info("Connected to Redis for agent memory")
            except (RedisError, Exception) as e:
                logger.warning(f"Redis connection failed, using in-memory storage: {e}")
                self._redis_client = None

        return self._redis_client

    def _generate_key(self, memory_type: MemoryType, scope: MemoryScope,
                     identifier: str) -> str:
        """Generate a unique key for memory storage."""
        return f"agent_memory:{memory_type.value}:{scope.value}:{identifier}"

    def _serialize_entry(self, entry: MemoryEntry) -> str:
        """Serialize memory entry for storage."""
        data = {
            "id": entry.id,
            "content": entry.content,
            "memory_type": entry.memory_type.value,
            "scope": entry.scope.value,
            "agent_id": entry.agent_id,
            "workflow_id": entry.workflow_id,
            "user_id": entry.user_id,
            "tags": list(entry.tags),
            "created_at": entry.created_at.isoformat(),
            "expires_at": entry.expires_at.isoformat() if entry.expires_at else None,
            "access_count": entry.access_count,
            "last_accessed": entry.last_accessed.isoformat() if entry.last_accessed else None
        }
        return json.dumps(data)

    def _deserialize_entry(self, data: str) -> MemoryEntry:
        """Deserialize memory entry from storage."""
        parsed = json.loads(data)
        return MemoryEntry(
            id=parsed["id"],
            content=parsed["content"],
            memory_type=MemoryType(parsed["memory_type"]),
            scope=MemoryScope(parsed["scope"]),
            agent_id=parsed.get("agent_id"),
            workflow_id=parsed.get("workflow_id"),
            user_id=parsed.get("user_id"),
            tags=set(parsed.get("tags", [])),
            created_at=datetime.fromisoformat(parsed["created_at"]),
            expires_at=datetime.fromisoformat(parsed["expires_at"]) if parsed.get("expires_at") else None,
            access_count=parsed.get("access_count", 0),
            last_accessed=datetime.fromisoformat(parsed["last_accessed"]) if parsed.get("last_accessed") else None
        )

    async def store_memory(self,
                          content: Dict[str, Any],
                          memory_type: MemoryType,
                          scope: MemoryScope,
                          identifier: str,
                          agent_id: Optional[str] = None,
                          workflow_id: Optional[str] = None,
                          user_id: Optional[str] = None,
                          tags: Optional[Set[str]] = None,
                          ttl: Optional[timedelta] = None) -> str:
        """
        Store a memory entry.

        Args:
            content: The content to store
            memory_type: Type of memory
            scope: Scope of memory access
            identifier: Unique identifier for the memory
            agent_id: Optional agent ID
            workflow_id: Optional workflow ID
            user_id: Optional user ID
            tags: Optional tags for categorization
            ttl: Optional time-to-live override

        Returns:
            Memory entry ID
        """
        try:
            # Generate unique ID
            memory_id = f"{identifier}_{datetime.utcnow().timestamp()}"

            # Calculate expiration
            expires_at = None
            if ttl:
                expires_at = datetime.utcnow() + ttl
            elif memory_type in self.default_ttl:
                expires_at = datetime.utcnow() + self.default_ttl[memory_type]

            # Create memory entry
            entry = MemoryEntry(
                id=memory_id,
                content=content,
                memory_type=memory_type,
                scope=scope,
                agent_id=agent_id,
                workflow_id=workflow_id,
                user_id=user_id,
                tags=tags or set(),
                expires_at=expires_at
            )

            # Store in cache
            self._memory_cache[memory_id] = entry

            # Store in Redis if available
            if self.redis_client:
                key = self._generate_key(memory_type, scope, identifier)
                serialized = self._serialize_entry(entry)

                if expires_at:
                    ttl_seconds = int((expires_at - datetime.utcnow()).total_seconds())
                    self.redis_client.setex(key, ttl_seconds, serialized)
                else:
                    self.redis_client.set(key, serialized)

            logger.info(
                "Memory stored",
                memory_id=memory_id,
                memory_type=memory_type.value,
                scope=scope.value,
                agent_id=agent_id,
                workflow_id=workflow_id
            )

            return memory_id

        except Exception as e:
            logger.error(f"Failed to store memory: {e}")
            raise

    async def retrieve_memory(self,
                             memory_type: MemoryType,
                             scope: MemoryScope,
                             identifier: str) -> Optional[MemoryEntry]:
        """
        Retrieve a memory entry.

        Args:
            memory_type: Type of memory
            scope: Scope of memory access
            identifier: Memory identifier

        Returns:
            Memory entry if found, None otherwise
        """
        try:
            key = self._generate_key(memory_type, scope, identifier)

            # Try cache first
            for entry in self._memory_cache.values():
                if (entry.memory_type == memory_type and
                    entry.scope == scope and
                    identifier in entry.id):

                    # Check expiration
                    if entry.expires_at and datetime.utcnow() > entry.expires_at:
                        await self._cleanup_expired_entry(entry.id)
                        continue

                    # Update access tracking
                    entry.access_count += 1
                    entry.last_accessed = datetime.utcnow()

                    return entry

            # Try Redis if available
            if self.redis_client:
                data = self.redis_client.get(key)
                if data:
                    entry = self._deserialize_entry(data)

                    # Check expiration
                    if entry.expires_at and datetime.utcnow() > entry.expires_at:
                        self.redis_client.delete(key)
                        return None

                    # Update access tracking
                    entry.access_count += 1
                    entry.last_accessed = datetime.utcnow()

                    # Update in cache and Redis
                    self._memory_cache[entry.id] = entry
                    self.redis_client.set(key, self._serialize_entry(entry))

                    return entry

            return None

        except Exception as e:
            logger.error(f"Failed to retrieve memory: {e}")
            return None

    async def search_memories(self,
                             memory_type: Optional[MemoryType] = None,
                             scope: Optional[MemoryScope] = None,
                             agent_id: Optional[str] = None,
                             workflow_id: Optional[str] = None,
                             user_id: Optional[str] = None,
                             tags: Optional[Set[str]] = None,
                             limit: int = 100) -> List[MemoryEntry]:
        """
        Search for memory entries based on criteria.

        Args:
            memory_type: Optional memory type filter
            scope: Optional scope filter
            agent_id: Optional agent ID filter
            workflow_id: Optional workflow ID filter
            user_id: Optional user ID filter
            tags: Optional tags filter (any matching tag)
            limit: Maximum number of results

        Returns:
            List of matching memory entries
        """
        try:
            results = []

            # Search in cache
            for entry in self._memory_cache.values():
                # Check expiration
                if entry.expires_at and datetime.utcnow() > entry.expires_at:
                    await self._cleanup_expired_entry(entry.id)
                    continue

                # Apply filters
                if memory_type and entry.memory_type != memory_type:
                    continue
                if scope and entry.scope != scope:
                    continue
                if agent_id and entry.agent_id != agent_id:
                    continue
                if workflow_id and entry.workflow_id != workflow_id:
                    continue
                if user_id and entry.user_id != user_id:
                    continue
                if tags and not tags.intersection(entry.tags):
                    continue

                results.append(entry)

                if len(results) >= limit:
                    break

            # Sort by creation time (newest first)
            results.sort(key=lambda x: x.created_at, reverse=True)

            logger.info(
                "Memory search completed",
                results_count=len(results),
                memory_type=memory_type.value if memory_type else None,
                scope=scope.value if scope else None
            )

            return results[:limit]

        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return []

    async def _cleanup_expired_entry(self, memory_id: str):
        """Clean up an expired memory entry."""
        try:
            # Remove from cache
            if memory_id in self._memory_cache:
                del self._memory_cache[memory_id]

            # Remove from Redis if available
            if self.redis_client:
                # Find and delete the key (this is inefficient but necessary for cleanup)
                for key in self.redis_client.scan_iter(match="agent_memory:*"):
                    data = self.redis_client.get(key)
                    if data:
                        entry = self._deserialize_entry(data)
                        if entry.id == memory_id:
                            self.redis_client.delete(key)
                            break

            logger.debug(f"Cleaned up expired memory entry: {memory_id}")

        except Exception as e:
            logger.error(f"Failed to cleanup expired memory entry {memory_id}: {e}")

    async def clear_workflow_memory(self, workflow_id: str):
        """Clear all memory entries for a specific workflow."""
        try:
            # Clear from cache
            to_remove = [
                entry_id for entry_id, entry in self._memory_cache.items()
                if entry.workflow_id == workflow_id
            ]

            for entry_id in to_remove:
                del self._memory_cache[entry_id]

            # Clear from Redis if available
            if self.redis_client:
                for key in self.redis_client.scan_iter(match="agent_memory:*"):
                    data = self.redis_client.get(key)
                    if data:
                        entry = self._deserialize_entry(data)
                        if entry.workflow_id == workflow_id:
                            self.redis_client.delete(key)

            logger.info(f"Cleared workflow memory for workflow: {workflow_id}")

        except Exception as e:
            logger.error(f"Failed to clear workflow memory: {e}")

    async def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory usage statistics."""
        try:
            stats = {
                "total_entries": len(self._memory_cache),
                "by_type": {},
                "by_scope": {},
                "redis_connected": self.redis_client is not None
            }

            for entry in self._memory_cache.values():
                # Count by type
                type_key = entry.memory_type.value
                stats["by_type"][type_key] = stats["by_type"].get(type_key, 0) + 1

                # Count by scope
                scope_key = entry.scope.value
                stats["by_scope"][scope_key] = stats["by_scope"].get(scope_key, 0) + 1

            return stats

        except Exception as e:
            logger.error(f"Failed to get memory stats: {e}")
            return {"error": str(e)}

    # Enhanced Phase 4 Methods for Agent Collaboration

    async def set_workflow_state(self, workflow_id: str, state: Dict[str, Any]) -> bool:
        """Set workflow state for agent collaboration."""
        try:
            self._workflow_states[workflow_id] = {
                "state": state,
                "updated_at": datetime.utcnow(),
                "version": self._workflow_states.get(workflow_id, {}).get("version", 0) + 1
            }

            # Persist to Redis if available
            if self.redis_client:
                key = f"workflow_state:{workflow_id}"
                await self._redis_set(key, self._workflow_states[workflow_id])

            # Notify listeners
            await self._notify_event_listeners("workflow_state_changed", {
                "workflow_id": workflow_id,
                "state": state
            })

            return True
        except Exception as e:
            logger.error(f"Failed to set workflow state: {e}")
            return False

    async def get_workflow_state(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow state for agent collaboration."""
        try:
            # Check local cache first
            if workflow_id in self._workflow_states:
                return self._workflow_states[workflow_id]["state"]

            # Check Redis if available
            if self.redis_client:
                key = f"workflow_state:{workflow_id}"
                data = await self._redis_get(key)
                if data:
                    self._workflow_states[workflow_id] = data
                    return data["state"]

            return None
        except Exception as e:
            logger.error(f"Failed to get workflow state: {e}")
            return None

    async def share_agent_data(self, agent_id: str, data_key: str, data: Any) -> bool:
        """Share data between agents."""
        try:
            if agent_id not in self._agent_collaboration_data:
                self._agent_collaboration_data[agent_id] = {}

            self._agent_collaboration_data[agent_id][data_key] = {
                "data": data,
                "shared_at": datetime.utcnow(),
                "agent_id": agent_id
            }

            # Persist to Redis if available
            if self.redis_client:
                key = f"agent_data:{agent_id}:{data_key}"
                await self._redis_set(key, self._agent_collaboration_data[agent_id][data_key])

            # Notify listeners
            await self._notify_event_listeners("agent_data_shared", {
                "agent_id": agent_id,
                "data_key": data_key,
                "data": data
            })

            return True
        except Exception as e:
            logger.error(f"Failed to share agent data: {e}")
            return False

    async def get_agent_data(self, agent_id: str, data_key: str) -> Optional[Any]:
        """Get shared data from another agent."""
        try:
            # Check local cache first
            if agent_id in self._agent_collaboration_data:
                if data_key in self._agent_collaboration_data[agent_id]:
                    return self._agent_collaboration_data[agent_id][data_key]["data"]

            # Check Redis if available
            if self.redis_client:
                key = f"agent_data:{agent_id}:{data_key}"
                data = await self._redis_get(key)
                if data:
                    if agent_id not in self._agent_collaboration_data:
                        self._agent_collaboration_data[agent_id] = {}
                    self._agent_collaboration_data[agent_id][data_key] = data
                    return data["data"]

            return None
        except Exception as e:
            logger.error(f"Failed to get agent data: {e}")
            return None

    async def record_performance_metric(self, metric_name: str, value: float, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Record performance metrics for monitoring."""
        try:
            metric_entry = {
                "value": value,
                "timestamp": datetime.utcnow(),
                "metadata": metadata or {}
            }

            self._performance_metrics[metric_name].append(metric_entry)

            # Keep only recent metrics (last 1000 entries)
            if len(self._performance_metrics[metric_name]) > 1000:
                self._performance_metrics[metric_name] = self._performance_metrics[metric_name][-1000:]

            # Persist to Redis if available
            if self.redis_client:
                key = f"performance_metrics:{metric_name}"
                await self._redis_set(key, self._performance_metrics[metric_name])

            return True
        except Exception as e:
            logger.error(f"Failed to record performance metric: {e}")
            return False

    async def get_performance_metrics(self, metric_name: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get performance metrics for analysis."""
        try:
            # Check local cache first
            if metric_name in self._performance_metrics:
                return self._performance_metrics[metric_name][-limit:]

            # Check Redis if available
            if self.redis_client:
                key = f"performance_metrics:{metric_name}"
                data = await self._redis_get(key)
                if data:
                    self._performance_metrics[metric_name] = data
                    return data[-limit:]

            return []
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return []

    async def add_event_listener(self, event_type: str, callback: Callable) -> bool:
        """Add event listener for real-time notifications."""
        try:
            self._event_listeners[event_type].append(callback)
            return True
        except Exception as e:
            logger.error(f"Failed to add event listener: {e}")
            return False

    async def _notify_event_listeners(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Notify all listeners of an event."""
        try:
            for callback in self._event_listeners.get(event_type, []):
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event_data)
                    else:
                        callback(event_data)
                except Exception as e:
                    logger.error(f"Event listener callback failed: {e}")
        except Exception as e:
            logger.error(f"Failed to notify event listeners: {e}")

    async def get_collaboration_summary(self, workflow_id: Optional[str] = None) -> Dict[str, Any]:
        """Get summary of agent collaboration activities."""
        try:
            summary = {
                "workflow_states": len(self._workflow_states),
                "active_agents": len(self._agent_collaboration_data),
                "performance_metrics": len(self._performance_metrics),
                "event_listeners": sum(len(listeners) for listeners in self._event_listeners.values()),
                "timestamp": datetime.utcnow().isoformat()
            }

            if workflow_id:
                workflow_state = await self.get_workflow_state(workflow_id)
                summary["workflow_specific"] = {
                    "workflow_id": workflow_id,
                    "has_state": workflow_state is not None,
                    "state_keys": list(workflow_state.keys()) if workflow_state else []
                }

            return summary
        except Exception as e:
            logger.error(f"Failed to get collaboration summary: {e}")
            return {}

    # Advanced Cross-Agent Memory Sharing Methods

    async def create_shared_context(self, context_id: str, context_data: Dict[str, Any],
                                  access_agents: List[str] = None) -> bool:
        """Create a shared context accessible by multiple agents."""
        try:
            shared_context = {
                "context_id": context_id,
                "data": context_data,
                "access_agents": access_agents or [],
                "created_at": datetime.utcnow(),
                "last_modified": datetime.utcnow(),
                "version": 1,
                "modification_history": []
            }

            # Store in workflow states for persistence
            await self.set_workflow_state(f"shared_context_{context_id}", shared_context)

            # Notify agents with access
            if access_agents:
                for agent_id in access_agents:
                    await self.notify_event(f"shared_context_created:{context_id}", {
                        "context_id": context_id,
                        "agent_id": agent_id,
                        "data_keys": list(context_data.keys())
                    })

            logger.info(f"Created shared context: {context_id} for agents: {access_agents}")
            return True

        except Exception as e:
            logger.error(f"Failed to create shared context {context_id}: {e}")
            return False

    async def update_shared_context(self, context_id: str, updates: Dict[str, Any],
                                  agent_id: str) -> bool:
        """Update a shared context with change tracking."""
        try:
            context_key = f"shared_context_{context_id}"
            context = await self.get_workflow_state(context_key)

            if not context:
                logger.warning(f"Shared context {context_id} not found")
                return False

            # Check access permissions
            if context["access_agents"] and agent_id not in context["access_agents"]:
                logger.warning(f"Agent {agent_id} denied access to context {context_id}")
                return False

            # Track changes
            context["data"].update(updates)
            context["last_modified"] = datetime.utcnow()
            context["version"] += 1

            # Record modification history
            context["modification_history"].append({
                "agent_id": agent_id,
                "timestamp": datetime.utcnow(),
                "changes": updates,
                "version": context["version"]
            })

            # Update stored context
            await self.set_workflow_state(context_key, context)

            # Notify other agents with access
            for other_agent in context["access_agents"]:
                if other_agent != agent_id:
                    await self.notify_event(f"shared_context_updated:{context_id}", {
                        "context_id": context_id,
                        "updated_by": agent_id,
                        "changes": updates,
                        "version": context["version"]
                    })

            logger.info(f"Updated shared context: {context_id} by agent: {agent_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update shared context {context_id}: {e}")
            return False

    async def get_shared_context(self, context_id: str, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get shared context data for an agent."""
        try:
            context_key = f"shared_context_{context_id}"
            context = await self.get_workflow_state(context_key)

            if not context:
                return None

            # Check access permissions
            if context["access_agents"] and agent_id not in context["access_agents"]:
                logger.warning(f"Agent {agent_id} denied access to context {context_id}")
                return None

            return {
                "context_id": context_id,
                "data": context["data"],
                "version": context["version"],
                "last_modified": context["last_modified"].isoformat() if isinstance(context["last_modified"], datetime) else context["last_modified"],
                "access_level": "read_write" if not context["access_agents"] or agent_id in context["access_agents"] else "none"
            }

        except Exception as e:
            logger.error(f"Failed to get shared context {context_id}: {e}")
            return None

    async def create_agent_session(self, agent_id: str, session_data: Dict[str, Any]) -> str:
        """Create a persistent session for an agent."""
        try:
            session_id = f"session_{agent_id}_{int(datetime.utcnow().timestamp())}"

            session = {
                "session_id": session_id,
                "agent_id": agent_id,
                "data": session_data,
                "created_at": datetime.utcnow(),
                "last_accessed": datetime.utcnow(),
                "access_count": 0,
                "is_active": True
            }

            # Store session in workflow states
            await self.set_workflow_state(f"agent_session_{session_id}", session)

            logger.info(f"Created session {session_id} for agent {agent_id}")
            return session_id

        except Exception as e:
            logger.error(f"Failed to create session for agent {agent_id}: {e}")
            return ""

    async def get_agent_session(self, agent_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        """Get agent session data."""
        try:
            session = await self.get_workflow_state(f"agent_session_{session_id}")

            if not session or session.get("agent_id") != agent_id:
                return None

            # Update access tracking
            session["last_accessed"] = datetime.utcnow()
            session["access_count"] += 1
            await self.set_workflow_state(f"agent_session_{session_id}", session)

            return session["data"]

        except Exception as e:
            logger.error(f"Failed to get session {session_id} for agent {agent_id}: {e}")
            return None

    async def get_cross_agent_insights(self, agent_id: str) -> Dict[str, Any]:
        """Get insights about other agents for collaboration."""
        try:
            insights = {
                "active_agents": [],
                "shared_contexts": [],
                "collaboration_opportunities": [],
                "performance_comparisons": {}
            }

            # Get active agents from collaboration data
            for other_agent, data in self._agent_collaboration_data.items():
                if other_agent != agent_id:
                    insights["active_agents"].append({
                        "agent_id": other_agent,
                        "last_activity": data.get("last_activity", ""),
                        "current_tasks": data.get("current_tasks", []),
                        "capabilities": data.get("capabilities", [])
                    })

            # Get accessible shared contexts
            for workflow_id, state in self._workflow_states.items():
                if workflow_id.startswith("shared_context_") and isinstance(state, dict):
                    context_id = workflow_id.replace("shared_context_", "")
                    access_agents = state.get("access_agents", [])

                    if not access_agents or agent_id in access_agents:
                        insights["shared_contexts"].append({
                            "context_id": context_id,
                            "last_modified": state.get("last_modified", ""),
                            "version": state.get("version", 1),
                            "data_size": len(state.get("data", {}))
                        })

            return insights

        except Exception as e:
            logger.error(f"Failed to get cross-agent insights for {agent_id}: {e}")
            return {}


# Global memory manager instance
_memory_manager = None


def get_memory_manager() -> AgentMemoryManager:
    """Get the global memory manager instance."""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = AgentMemoryManager()
    return _memory_manager
