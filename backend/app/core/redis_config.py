"""
Redis configuration and connection management.

This module provides Redis connection pooling, clustering support,
and high availability configuration for the RealtorAgentAI platform.
"""

import logging
import redis
from redis.sentinel import Sentinel
from redis.connection import ConnectionPool
from typing import Dict, Any, Optional, List
import structlog
from contextlib import contextmanager

from .config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class RedisManager:
    """
    Redis connection manager with clustering and high availability support.
    
    Provides connection pooling, failover handling, and monitoring
    for Redis-based caching and message brokering.
    """
    
    def __init__(self):
        self._redis_client = None
        self._sentinel_client = None
        self._connection_pool = None
        self._cluster_nodes = None
        self._is_cluster = False
        self._is_sentinel = False
        
        self._initialize_redis()
    
    def _initialize_redis(self):
        """Initialize Redis connection based on configuration."""
        try:
            # Parse Redis URL to determine connection type
            redis_url = settings.REDIS_URL
            
            # Check if using Redis Sentinel
            if hasattr(settings, 'REDIS_SENTINEL_HOSTS') and settings.REDIS_SENTINEL_HOSTS:
                self._setup_sentinel()
            # Check if using Redis Cluster
            elif hasattr(settings, 'REDIS_CLUSTER_NODES') and settings.REDIS_CLUSTER_NODES:
                self._setup_cluster()
            else:
                self._setup_single_instance()
                
            logger.info(
                "Redis connection initialized",
                connection_type="sentinel" if self._is_sentinel else "cluster" if self._is_cluster else "single",
                redis_url=redis_url
            )
            
        except Exception as e:
            logger.error("Failed to initialize Redis connection", error=str(e))
            raise
    
    def _setup_single_instance(self):
        """Set up single Redis instance connection."""
        try:
            # Create connection pool
            self._connection_pool = ConnectionPool.from_url(
                settings.REDIS_URL,
                max_connections=getattr(settings, 'REDIS_MAX_CONNECTIONS', 20),
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=30
            )
            
            # Create Redis client
            self._redis_client = redis.Redis(
                connection_pool=self._connection_pool,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # Test connection
            self._redis_client.ping()
            
            logger.info("Single Redis instance connection established")
            
        except Exception as e:
            logger.error("Failed to setup single Redis instance", error=str(e))
            raise
    
    def _setup_sentinel(self):
        """Set up Redis Sentinel for high availability."""
        try:
            sentinel_hosts = getattr(settings, 'REDIS_SENTINEL_HOSTS', [])
            master_name = getattr(settings, 'REDIS_MASTER_NAME', 'mymaster')
            
            # Parse sentinel hosts
            sentinel_list = []
            for host in sentinel_hosts:
                if ':' in host:
                    host_part, port_part = host.split(':')
                    sentinel_list.append((host_part, int(port_part)))
                else:
                    sentinel_list.append((host, 26379))  # Default Sentinel port
            
            # Create Sentinel client
            self._sentinel_client = Sentinel(
                sentinel_list,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            
            # Get master connection
            self._redis_client = self._sentinel_client.master_for(
                master_name,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True
            )
            
            # Test connection
            self._redis_client.ping()
            
            self._is_sentinel = True
            
            logger.info(
                "Redis Sentinel connection established",
                master_name=master_name,
                sentinel_hosts=sentinel_list
            )
            
        except Exception as e:
            logger.error("Failed to setup Redis Sentinel", error=str(e))
            raise
    
    def _setup_cluster(self):
        """Set up Redis Cluster connection."""
        try:
            from rediscluster import RedisCluster
            
            cluster_nodes = getattr(settings, 'REDIS_CLUSTER_NODES', [])
            
            # Parse cluster nodes
            startup_nodes = []
            for node in cluster_nodes:
                if ':' in node:
                    host, port = node.split(':')
                    startup_nodes.append({"host": host, "port": int(port)})
                else:
                    startup_nodes.append({"host": node, "port": 6379})
            
            # Create cluster client
            self._redis_client = RedisCluster(
                startup_nodes=startup_nodes,
                decode_responses=True,
                skip_full_coverage_check=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True,
                max_connections=getattr(settings, 'REDIS_MAX_CONNECTIONS', 20)
            )
            
            # Test connection
            self._redis_client.ping()
            
            self._is_cluster = True
            self._cluster_nodes = startup_nodes
            
            logger.info(
                "Redis Cluster connection established",
                cluster_nodes=startup_nodes
            )
            
        except ImportError:
            logger.error("redis-py-cluster not installed, falling back to single instance")
            self._setup_single_instance()
        except Exception as e:
            logger.error("Failed to setup Redis Cluster", error=str(e))
            raise
    
    def get_client(self) -> redis.Redis:
        """
        Get Redis client instance.
        
        Returns:
            redis.Redis: Redis client instance
        """
        if not self._redis_client:
            self._initialize_redis()
        
        return self._redis_client
    
    def get_connection_info(self) -> Dict[str, Any]:
        """
        Get Redis connection information.
        
        Returns:
            Dict: Connection information and status
        """
        try:
            client = self.get_client()
            info = client.info()
            
            connection_info = {
                "connection_type": "sentinel" if self._is_sentinel else "cluster" if self._is_cluster else "single",
                "redis_version": info.get("redis_version"),
                "connected_clients": info.get("connected_clients"),
                "used_memory": info.get("used_memory"),
                "used_memory_human": info.get("used_memory_human"),
                "total_commands_processed": info.get("total_commands_processed"),
                "keyspace_hits": info.get("keyspace_hits"),
                "keyspace_misses": info.get("keyspace_misses"),
                "uptime_in_seconds": info.get("uptime_in_seconds"),
                "role": info.get("role")
            }
            
            if self._is_cluster:
                connection_info["cluster_nodes"] = self._cluster_nodes
            
            return connection_info
            
        except Exception as e:
            logger.error("Failed to get Redis connection info", error=str(e))
            return {"error": str(e)}
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform Redis health check.
        
        Returns:
            Dict: Health check results
        """
        try:
            client = self.get_client()
            
            # Test basic operations
            test_key = "health_check_test"
            test_value = "test_value"
            
            # Set and get test
            client.set(test_key, test_value, ex=10)  # Expire in 10 seconds
            retrieved_value = client.get(test_key)
            
            # Clean up
            client.delete(test_key)
            
            # Check if operation was successful
            success = retrieved_value == test_value
            
            health_status = {
                "status": "healthy" if success else "unhealthy",
                "connection_active": True,
                "test_operation_success": success,
                "connection_info": self.get_connection_info()
            }
            
            if self._is_sentinel:
                # Check sentinel status
                try:
                    sentinel_info = self._sentinel_client.sentinel_masters()
                    health_status["sentinel_masters"] = len(sentinel_info)
                except Exception as e:
                    health_status["sentinel_error"] = str(e)
            
            return health_status
            
        except Exception as e:
            logger.error("Redis health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "connection_active": False,
                "error": str(e)
            }
    
    @contextmanager
    def get_lock(self, name: str, timeout: int = 10, blocking_timeout: int = 5):
        """
        Get distributed lock using Redis.
        
        Args:
            name: Lock name
            timeout: Lock timeout in seconds
            blocking_timeout: Time to wait for lock acquisition
            
        Yields:
            Lock object
        """
        client = self.get_client()
        lock = client.lock(name, timeout=timeout, blocking_timeout=blocking_timeout)
        
        try:
            acquired = lock.acquire()
            if not acquired:
                raise TimeoutError(f"Could not acquire lock '{name}' within {blocking_timeout} seconds")
            
            yield lock
            
        finally:
            try:
                lock.release()
            except Exception as e:
                logger.warning("Failed to release lock", lock_name=name, error=str(e))
    
    def close(self):
        """Close Redis connections."""
        try:
            if self._redis_client:
                if hasattr(self._redis_client, 'close'):
                    self._redis_client.close()
                
            if self._connection_pool:
                self._connection_pool.disconnect()
                
            logger.info("Redis connections closed")
            
        except Exception as e:
            logger.error("Error closing Redis connections", error=str(e))


# Global Redis manager instance
_redis_manager = None


def get_redis_manager() -> RedisManager:
    """
    Get global Redis manager instance.
    
    Returns:
        RedisManager: Redis manager instance
    """
    global _redis_manager
    
    if _redis_manager is None:
        _redis_manager = RedisManager()
    
    return _redis_manager


def get_redis_client() -> redis.Redis:
    """
    Get Redis client instance.
    
    Returns:
        redis.Redis: Redis client
    """
    return get_redis_manager().get_client()


# Export for easy importing
__all__ = [
    "RedisManager",
    "get_redis_manager",
    "get_redis_client"
]
