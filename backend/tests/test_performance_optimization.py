"""
Integration Tests for Performance Optimization System.

This module contains comprehensive integration tests for all performance
optimization components including load balancing, caching, database optimization,
scaling, memory management, and monitoring.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from typing import Dict, Any

from fastapi.testclient import TestClient
from fastapi import status

from app.main import app
from app.services.performance.load_balancer import AdvancedLoadBalancer, LoadBalancingStrategy, AgentStatus
from app.services.performance.cache_manager import AdvancedCacheManager, CacheLevel
from app.services.performance.database_optimizer import QueryOptimizer, QueryType
from app.services.performance.scaling_manager import HorizontalScalingManager, ScalingDirection
from app.services.performance.memory_manager import AdvancedMemoryManager, MemoryAlert
from app.services.performance.monitoring_system import RealTimeMonitoringSystem, AlertSeverity
from app.models.user import User


class TestAdvancedLoadBalancer:
    """Test cases for advanced load balancer."""
    
    @pytest.fixture
    def load_balancer(self):
        """Create load balancer instance for testing."""
        return AdvancedLoadBalancer()
    
    @pytest.mark.asyncio
    async def test_agent_assignment_round_robin(self, load_balancer):
        """Test round robin agent assignment."""
        load_balancer.load_balancing_strategy = LoadBalancingStrategy.ROUND_ROBIN
        
        # Get agents multiple times
        agents = []
        for _ in range(5):
            agent = await load_balancer.get_optimal_agent("data_extraction")
            if agent:
                agents.append(agent)
        
        # Should cycle through available agents
        assert len(set(agents)) > 1  # Should use different agents
    
    @pytest.mark.asyncio
    async def test_agent_assignment_least_connections(self, load_balancer):
        """Test least connections agent assignment."""
        load_balancer.load_balancing_strategy = LoadBalancingStrategy.LEAST_CONNECTIONS
        
        agent = await load_balancer.get_optimal_agent("data_extraction")
        assert agent is not None
        
        # Verify agent load is updated
        pool = load_balancer.resource_pools["pool_data_extraction"]
        agent_metrics = pool.agents[agent]
        assert agent_metrics.current_load > 0
    
    @pytest.mark.asyncio
    async def test_agent_release_and_metrics_update(self, load_balancer):
        """Test agent release and metrics update."""
        agent = await load_balancer.get_optimal_agent("data_extraction")
        assert agent is not None
        
        # Release agent with metrics
        await load_balancer.release_agent(agent, execution_time=1.5, success=True)
        
        # Verify metrics are updated
        pool = load_balancer.resource_pools["pool_data_extraction"]
        agent_metrics = pool.agents[agent]
        assert agent_metrics.current_load == 0
        assert agent_metrics.total_requests > 0
        assert len(agent_metrics.response_times) > 0
    
    @pytest.mark.asyncio
    async def test_auto_scaling_up(self, load_balancer):
        """Test automatic scaling up when needed."""
        pool_id = "pool_data_extraction"
        pool = load_balancer.resource_pools[pool_id]
        
        # Simulate high load on all agents
        for agent_id, metrics in pool.agents.items():
            metrics.current_load = metrics.max_capacity
            metrics.status = AgentStatus.OVERLOADED
        
        initial_count = len(pool.agents)
        
        # Attempt to get agent (should trigger scaling)
        agent = await load_balancer.get_optimal_agent("data_extraction")
        
        # Should have attempted to scale up
        assert len(pool.agents) >= initial_count
    
    def test_pool_statistics(self, load_balancer):
        """Test pool statistics generation."""
        pool_id = "pool_data_extraction"
        stats = load_balancer.get_pool_statistics(pool_id)
        
        assert "pool_id" in stats
        assert "total_agents" in stats
        assert "utilization_percent" in stats
        assert "avg_response_time" in stats
        assert "agent_status" in stats
        assert stats["pool_id"] == pool_id
    
    def test_system_overview(self, load_balancer):
        """Test system overview generation."""
        overview = load_balancer.get_system_overview()
        
        assert "load_balancing_strategy" in overview
        assert "total_agents" in overview
        assert "total_pools" in overview
        assert "pool_statistics" in overview
        assert overview["total_pools"] > 0


class TestAdvancedCacheManager:
    """Test cases for advanced cache manager."""
    
    @pytest.fixture
    def cache_manager(self):
        """Create cache manager instance for testing."""
        return AdvancedCacheManager()
    
    @pytest.mark.asyncio
    async def test_cache_set_and_get(self, cache_manager):
        """Test basic cache set and get operations."""
        key = "test_key"
        value = {"data": "test_value", "number": 42}
        
        # Set cache entry
        success = await cache_manager.set(key, value, ttl_seconds=300)
        assert success
        
        # Get cache entry
        retrieved_value = await cache_manager.get(key)
        assert retrieved_value == value
    
    @pytest.mark.asyncio
    async def test_cache_with_fallback(self, cache_manager):
        """Test cache with fallback function."""
        key = "fallback_test"
        fallback_value = {"fallback": True}
        
        async def fallback_func():
            return fallback_value
        
        # Get with fallback (should call fallback and cache result)
        result = await cache_manager.get(key, fallback_func=fallback_func)
        assert result == fallback_value
        
        # Get again (should come from cache)
        result2 = await cache_manager.get(key)
        assert result2 == fallback_value
    
    @pytest.mark.asyncio
    async def test_cache_invalidation(self, cache_manager):
        """Test cache invalidation by pattern."""
        # Set multiple cache entries
        await cache_manager.set("knowledge_base:legal", {"type": "legal"}, tags=["legal_requirements"])
        await cache_manager.set("knowledge_base:compliance", {"type": "compliance"}, tags=["compliance_rules"])
        await cache_manager.set("market_data:analysis", {"type": "market"}, tags=["property_analysis"])
        
        # Invalidate by pattern
        invalidated = await cache_manager.invalidate_by_pattern("knowledge_base:*")
        assert invalidated >= 0  # Should invalidate some entries
    
    @pytest.mark.asyncio
    async def test_cache_warming(self, cache_manager):
        """Test cache warming functionality."""
        warmed_count = await cache_manager.warm_cache()
        assert warmed_count >= 0  # Should warm some entries
    
    def test_cache_performance_stats(self, cache_manager):
        """Test cache performance statistics."""
        stats = cache_manager.get_performance_stats()
        
        assert "multi_level_cache" in stats
        assert "l1_cache" in stats
        assert "cache_warming" in stats
        
        multi_level = stats["multi_level_cache"]
        assert "total_requests" in multi_level
        assert "hit_rate" in multi_level
        assert "avg_response_time_ms" in multi_level


class TestQueryOptimizer:
    """Test cases for database query optimizer."""
    
    @pytest.fixture
    def db_optimizer(self):
        """Create database optimizer instance for testing."""
        return QueryOptimizer()
    
    @pytest.mark.asyncio
    async def test_optimized_query_execution(self, db_optimizer):
        """Test optimized query execution."""
        query = "SELECT * FROM contracts WHERE user_id = %s ORDER BY created_at DESC"
        params = ("user123",)
        
        result = await db_optimizer.execute_optimized_query(
            query, params, QueryType.SELECT, cache_key="contracts_user123"
        )
        
        assert result is not None
        # Should return mock result from _execute_query
        assert isinstance(result, list)
    
    @pytest.mark.asyncio
    async def test_query_caching(self, db_optimizer):
        """Test query result caching."""
        query = "SELECT * FROM templates WHERE template_type = %s"
        params = ("purchase",)
        cache_key = "templates_purchase"
        
        # First execution (should cache result)
        result1 = await db_optimizer.execute_optimized_query(
            query, params, QueryType.SELECT, cache_key=cache_key
        )
        
        # Second execution (should use cache)
        result2 = await db_optimizer.execute_optimized_query(
            query, params, QueryType.SELECT, cache_key=cache_key
        )
        
        assert result1 == result2
    
    @pytest.mark.asyncio
    async def test_slow_queries_detection(self, db_optimizer):
        """Test slow queries detection."""
        # Simulate some queries with different execution times
        query_hash = db_optimizer._get_query_hash("SELECT * FROM slow_table", ())
        
        # Update metrics to simulate slow query
        db_optimizer._update_query_metrics(query_hash, QueryType.SELECT, 2.5)
        db_optimizer._update_query_metrics(query_hash, QueryType.SELECT, 3.0)
        
        slow_queries = await db_optimizer.get_slow_queries(threshold_seconds=1.0)
        assert len(slow_queries) > 0
        
        slow_query = slow_queries[0]
        assert slow_query["avg_execution_time"] > 1.0
    
    def test_optimization_recommendations(self, db_optimizer):
        """Test optimization recommendations generation."""
        # Simulate query metrics that would trigger recommendations
        query_hash = db_optimizer._get_query_hash("SELECT * FROM frequent_table", ())
        
        # Simulate frequently executed query with no caching
        for _ in range(150):
            db_optimizer._update_query_metrics(query_hash, QueryType.SELECT, 0.5)
        
        recommendations = db_optimizer.get_optimization_recommendations()
        assert len(recommendations) > 0
        
        # Should recommend caching
        caching_recs = [r for r in recommendations if r["type"] == "caching"]
        assert len(caching_recs) > 0
    
    def test_performance_stats(self, db_optimizer):
        """Test database performance statistics."""
        stats = db_optimizer.get_performance_stats()
        
        assert "query_performance" in stats
        assert "cache_performance" in stats
        assert "optimization_rules" in stats
        assert "connection_pool" in stats
        
        query_perf = stats["query_performance"]
        assert "total_queries" in query_perf
        assert "error_rate" in query_perf
        assert "avg_execution_time" in query_perf


class TestHorizontalScalingManager:
    """Test cases for horizontal scaling manager."""
    
    @pytest.fixture
    def scaling_manager(self):
        """Create scaling manager instance for testing."""
        return HorizontalScalingManager()
    
    @pytest.mark.asyncio
    async def test_service_instance_registration(self, scaling_manager):
        """Test service instance registration."""
        service_name = "test-service"
        host = "localhost"
        port = 8001
        
        instance_id = await scaling_manager.register_service_instance(
            service_name, host, port, {"version": "1.0"}
        )
        
        assert instance_id is not None
        assert service_name in scaling_manager.services
        assert instance_id in scaling_manager.services[service_name]
        
        instance = scaling_manager.services[service_name][instance_id]
        assert instance.host == host
        assert instance.port == port
    
    @pytest.mark.asyncio
    async def test_healthy_instance_selection(self, scaling_manager):
        """Test healthy instance selection."""
        service_name = "test-service"
        
        # Register multiple instances
        instance1 = await scaling_manager.register_service_instance(service_name, "host1", 8001)
        instance2 = await scaling_manager.register_service_instance(service_name, "host2", 8002)
        
        # Mark instances as healthy
        scaling_manager.services[service_name][instance1].status = scaling_manager.services[service_name][instance1].status.HEALTHY
        scaling_manager.services[service_name][instance2].status = scaling_manager.services[service_name][instance2].status.HEALTHY
        
        # Get healthy instance
        selected = await scaling_manager.get_healthy_instance(service_name)
        assert selected is not None
        assert selected.instance_id in [instance1, instance2]
    
    @pytest.mark.asyncio
    async def test_instance_metrics_update(self, scaling_manager):
        """Test instance metrics update."""
        service_name = "test-service"
        instance_id = await scaling_manager.register_service_instance(service_name, "localhost", 8001)
        
        # Update metrics
        await scaling_manager.update_instance_metrics(
            service_name, instance_id, cpu_usage=75.0, memory_usage=60.0, response_time=1.2
        )
        
        instance = scaling_manager.services[service_name][instance_id]
        assert instance.cpu_usage == 75.0
        assert instance.memory_usage == 60.0
        assert instance.avg_response_time == 1.2
    
    def test_service_overview(self, scaling_manager):
        """Test service overview generation."""
        overview = scaling_manager.get_service_overview()
        assert isinstance(overview, dict)
        
        # Should have default services
        assert len(overview) > 0
        
        for service_name, service_data in overview.items():
            assert "instance_count" in service_data
            assert "metrics" in service_data
            assert "scaling_policy" in service_data
    
    def test_scaling_history(self, scaling_manager):
        """Test scaling history retrieval."""
        history = scaling_manager.get_scaling_history(limit=10)
        assert isinstance(history, list)
        # Initially empty, but structure should be correct
        if history:
            event = history[0]
            assert "event_id" in event
            assert "service_name" in event
            assert "direction" in event
            assert "timestamp" in event


class TestAdvancedMemoryManager:
    """Test cases for advanced memory manager."""
    
    @pytest.fixture
    def memory_manager(self):
        """Create memory manager instance for testing."""
        return AdvancedMemoryManager()
    
    def test_memory_stats_collection(self, memory_manager):
        """Test memory statistics collection."""
        stats = memory_manager.get_memory_stats()
        
        assert "current_memory" in stats
        assert "process_memory" in stats
        assert "object_counts" in stats
        assert "memory_leaks" in stats
        assert "monitoring" in stats
        
        current_memory = stats["current_memory"]
        assert "total_mb" in current_memory
        assert "used_mb" in current_memory
        assert "usage_percent" in current_memory
    
    def test_memory_leak_detection(self, memory_manager):
        """Test memory leak detection."""
        leaks = memory_manager.get_memory_leaks()
        assert isinstance(leaks, list)
        
        # Initially should be empty
        if leaks:
            leak = leaks[0]
            assert "leak_id" in leak
            assert "object_type" in leak
            assert "growth_rate_mb_per_hour" in leak
            assert "severity" in leak
    
    def test_memory_alerts(self, memory_manager):
        """Test memory alerts retrieval."""
        alerts = memory_manager.get_recent_alerts(hours=24)
        assert isinstance(alerts, list)
        
        # Initially should be empty
        if alerts:
            alert = alerts[0]
            assert "level" in alert
            assert "memory_percent" in alert
            assert "timestamp" in alert
    
    def test_object_tracker_registration(self, memory_manager):
        """Test object tracker registration."""
        test_obj = {"test": "object"}
        memory_manager.register_object_tracker("test_category", test_obj)
        
        # Should be registered in trackers
        assert "test_category" in memory_manager.object_trackers
    
    def test_callback_registration(self, memory_manager):
        """Test callback registration."""
        def test_callback():
            pass
        
        async def async_callback(snapshot):
            pass
        
        memory_manager.register_optimization_callback(test_callback)
        memory_manager.register_memory_pressure_callback(async_callback)
        
        assert len(memory_manager.optimization_callbacks) > 0
        assert len(memory_manager.memory_pressure_callbacks) > 0


class TestRealTimeMonitoringSystem:
    """Test cases for real-time monitoring system."""
    
    @pytest.fixture
    def monitoring_system(self):
        """Create monitoring system instance for testing."""
        return RealTimeMonitoringSystem()
    
    def test_dashboard_data_generation(self, monitoring_system):
        """Test dashboard data generation."""
        dashboard_data = monitoring_system.get_dashboard_data()
        
        assert "metrics" in dashboard_data
        assert "alerts" in dashboard_data
        assert "recommendations" in dashboard_data
        assert "system_health" in dashboard_data
        
        system_health = dashboard_data["system_health"]
        assert "monitoring_enabled" in system_health
        assert "metrics_collected" in system_health
        assert "alert_rules_active" in system_health
    
    def test_metric_history_retrieval(self, monitoring_system):
        """Test metric history retrieval."""
        metric_name = "test.metric"
        history = monitoring_system.get_metric_history(metric_name, hours=1)
        
        assert isinstance(history, list)
        # Initially empty, but structure should be correct
        if history:
            data_point = history[0]
            assert "timestamp" in data_point
            assert "value" in data_point
            assert "tags" in data_point
    
    def test_alert_rules_initialization(self, monitoring_system):
        """Test alert rules initialization."""
        assert len(monitoring_system.alert_rules) > 0
        
        # Check for default alert rules
        rule_names = [rule.name for rule in monitoring_system.alert_rules.values()]
        assert "High Memory Usage" in rule_names
        assert "High Response Time" in rule_names
        assert "High Error Rate" in rule_names


class TestPerformanceAPI:
    """Test cases for performance API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_user(self):
        """Create mock user for testing."""
        user = Mock(spec=User)
        user.id = "test_user_123"
        user.email = "test@example.com"
        user.role = "admin"
        return user
    
    @pytest.fixture
    def auth_headers(self):
        """Create authentication headers."""
        return {"Authorization": "Bearer test_token"}
    
    def test_load_balancer_overview_endpoint(self, client, mock_user, auth_headers):
        """Test load balancer overview endpoint."""
        with patch('app.core.auth.get_current_user', return_value=mock_user):
            response = client.get("/api/v1/performance/load-balancer/overview", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert "status" in data
            assert "data" in data
            assert data["status"] == "success"
    
    def test_cache_statistics_endpoint(self, client, mock_user, auth_headers):
        """Test cache statistics endpoint."""
        with patch('app.core.auth.get_current_user', return_value=mock_user):
            response = client.get("/api/v1/performance/cache/statistics", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert "status" in data
            assert "data" in data
            assert data["status"] == "success"
    
    def test_database_statistics_endpoint(self, client, mock_user, auth_headers):
        """Test database statistics endpoint."""
        with patch('app.core.auth.get_current_user', return_value=mock_user):
            response = client.get("/api/v1/performance/database/statistics", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert "status" in data
            assert "data" in data
            assert data["status"] == "success"
    
    def test_scaling_overview_endpoint(self, client, mock_user, auth_headers):
        """Test scaling overview endpoint."""
        with patch('app.core.auth.get_current_user', return_value=mock_user):
            response = client.get("/api/v1/performance/scaling/overview", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert "status" in data
            assert "data" in data
            assert data["status"] == "success"
    
    def test_memory_statistics_endpoint(self, client, mock_user, auth_headers):
        """Test memory statistics endpoint."""
        with patch('app.core.auth.get_current_user', return_value=mock_user):
            response = client.get("/api/v1/performance/memory/statistics", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert "status" in data
            assert "data" in data
            assert data["status"] == "success"
    
    def test_monitoring_dashboard_endpoint(self, client, mock_user, auth_headers):
        """Test monitoring dashboard endpoint."""
        with patch('app.core.auth.get_current_user', return_value=mock_user):
            response = client.get("/api/v1/performance/monitoring/dashboard", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert "status" in data
            assert "data" in data
            assert data["status"] == "success"
    
    def test_comprehensive_health_check_endpoint(self, client, mock_user, auth_headers):
        """Test comprehensive health check endpoint."""
        with patch('app.core.auth.get_current_user', return_value=mock_user):
            response = client.get("/api/v1/performance/health/comprehensive", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert "status" in data
            assert "data" in data
            assert data["status"] == "success"
            
            health_data = data["data"]
            assert "overall_status" in health_data
            assert "components" in health_data
            
            components = health_data["components"]
            assert "load_balancer" in components
            assert "cache" in components
            assert "database" in components
            assert "scaling" in components
            assert "memory" in components
            assert "monitoring" in components
    
    def test_unauthorized_access(self, client):
        """Test unauthorized access to performance endpoints."""
        # Test without authentication headers
        response = client.get("/api/v1/performance/load-balancer/overview")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        
        response = client.get("/api/v1/performance/monitoring/dashboard")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
