"""
Integration tests for health check endpoints using FastAPI TestClient.

This module tests the health check endpoints to ensure they respond correctly
and provide proper status information.
"""

import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock

from app.main import app


@pytest.fixture
def client():
    """Create test client for FastAPI application."""
    return TestClient(app)


def test_basic_health_endpoint(client):
    """Test the basic health check endpoint."""
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    
    # Check required fields
    assert "status" in data
    assert "timestamp" in data
    assert "version" in data
    assert "environment" in data
    assert "startup_complete" in data
    assert "ready_for_traffic" in data
    assert "services_healthy" in data
    assert "total_services" in data
    
    # Check data types
    assert isinstance(data["timestamp"], (int, float))
    assert isinstance(data["services_healthy"], int)
    assert isinstance(data["total_services"], int)
    assert data["version"] == "0.1.0"


def test_detailed_health_endpoint(client):
    """Test the detailed health check endpoint."""
    response = client.get("/health/detailed")
    
    assert response.status_code == 200
    data = response.json()
    
    # Check required fields
    assert "overall_status" in data
    assert "startup_complete" in data
    assert "ready_for_traffic" in data
    assert "services" in data
    assert "critical_errors" in data
    assert "warnings" in data
    assert "timestamp" in data
    assert "version" in data
    assert "environment" in data
    
    # Check data types
    assert isinstance(data["services"], dict)
    assert isinstance(data["critical_errors"], list)
    assert isinstance(data["warnings"], list)
    
    # Check service structure if services exist
    if data["services"]:
        service_name = list(data["services"].keys())[0]
        service = data["services"][service_name]
        
        assert "status" in service
        assert "response_time_ms" in service
        assert "last_check" in service
        assert "details" in service
        
        assert isinstance(service["response_time_ms"], (int, float))
        assert service["response_time_ms"] >= 0


def test_readiness_probe_endpoint(client):
    """Test the readiness probe endpoint."""
    response = client.get("/health/ready")
    
    # Should return 200 if ready, 503 if not ready
    assert response.status_code in [200, 503]
    
    if response.status_code == 200:
        data = response.json()
        assert "ready" in data
        assert "startup_complete" in data
        assert "overall_status" in data
        assert "critical_services_healthy" in data
        assert "timestamp" in data
        
        assert data["ready"] is True
        assert isinstance(data["critical_services_healthy"], bool)


def test_liveness_probe_endpoint(client):
    """Test the liveness probe endpoint."""
    response = client.get("/health/live")
    
    assert response.status_code == 200
    data = response.json()
    
    # Check required fields
    assert "alive" in data
    assert "startup_time" in data
    assert "uptime_seconds" in data
    assert "timestamp" in data
    
    # Check data types and values
    assert data["alive"] is True
    assert isinstance(data["uptime_seconds"], (int, float))
    assert data["uptime_seconds"] >= 0


@pytest.mark.parametrize("endpoint", [
    "/health",
    "/health/detailed", 
    "/health/ready",
    "/health/live"
])
def test_health_endpoints_response_time(client, endpoint):
    """Test that health endpoints respond within reasonable time."""
    import time
    
    start_time = time.time()
    response = client.get(endpoint)
    end_time = time.time()
    
    response_time = end_time - start_time
    
    # Health checks should respond within 5 seconds
    assert response_time < 5.0
    
    # Should return valid HTTP status codes
    assert response.status_code in [200, 503]


def test_health_endpoints_content_type(client):
    """Test that health endpoints return JSON content."""
    endpoints = ["/health", "/health/detailed", "/health/live"]
    
    for endpoint in endpoints:
        response = client.get(endpoint)
        assert response.headers["content-type"] == "application/json"
        
        # Should be valid JSON
        try:
            json.loads(response.content)
        except json.JSONDecodeError:
            pytest.fail(f"Endpoint {endpoint} did not return valid JSON")


def test_health_endpoint_with_mocked_unhealthy_service(client):
    """Test health endpoint behavior when services are unhealthy."""
    with patch('app.core.startup_validation.get_startup_validation_service') as mock_service:
        # Mock an unhealthy service
        mock_startup_service = Mock()
        mock_health_status = Mock()
        mock_health_status.overall_status.value = "unhealthy"
        mock_health_status.startup_complete = False
        mock_health_status.ready_for_traffic = False
        mock_health_status.services = {}
        mock_health_status.critical_errors = ["Database connection failed"]
        mock_health_status.warnings = []
        
        mock_startup_service.perform_health_check.return_value = mock_health_status
        mock_service.return_value = mock_startup_service
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["startup_complete"] is False
        assert data["ready_for_traffic"] is False


def test_readiness_probe_not_ready(client):
    """Test readiness probe when application is not ready."""
    with patch('app.core.startup_validation.get_startup_validation_service') as mock_service:
        # Mock a not-ready service
        mock_startup_service = Mock()
        mock_readiness_status = {
            "ready": False,
            "startup_complete": False,
            "overall_status": "unhealthy",
            "critical_services_healthy": False,
            "timestamp": "2025-01-01T00:00:00"
        }
        
        mock_startup_service.get_readiness_status.return_value = mock_readiness_status
        mock_service.return_value = mock_startup_service
        
        response = client.get("/health/ready")
        
        assert response.status_code == 503
        assert "detail" in response.json()


def test_detailed_health_with_service_details(client):
    """Test detailed health endpoint with service details."""
    with patch('app.core.startup_validation.get_startup_validation_service') as mock_service:
        # Mock detailed service information
        mock_startup_service = Mock()
        mock_health_status = Mock()
        mock_health_status.overall_status.value = "healthy"
        mock_health_status.startup_complete = True
        mock_health_status.ready_for_traffic = True
        mock_health_status.startup_time.isoformat.return_value = "2025-01-01T00:00:00"
        mock_health_status.last_health_check.isoformat.return_value = "2025-01-01T00:01:00"
        mock_health_status.critical_errors = []
        mock_health_status.warnings = ["Redis connection slow"]
        
        # Mock service details
        mock_service_check = Mock()
        mock_service_check.status.value = "healthy"
        mock_service_check.response_time_ms = 150.5
        mock_service_check.last_check.isoformat.return_value = "2025-01-01T00:01:00"
        mock_service_check.details = {"connection": "active", "user_count": 10}
        mock_service_check.error_message = None
        
        mock_health_status.services = {"database": mock_service_check}
        
        mock_startup_service.perform_health_check.return_value = mock_health_status
        mock_service.return_value = mock_startup_service
        
        response = client.get("/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["overall_status"] == "healthy"
        assert data["startup_complete"] is True
        assert data["ready_for_traffic"] is True
        assert len(data["warnings"]) == 1
        assert data["warnings"][0] == "Redis connection slow"
        
        # Check service details
        assert "database" in data["services"]
        db_service = data["services"]["database"]
        assert db_service["status"] == "healthy"
        assert db_service["response_time_ms"] == 150.5
        assert db_service["details"]["user_count"] == 10
        assert db_service["error_message"] is None


def test_health_endpoints_cors_headers(client):
    """Test that health endpoints include proper CORS headers if configured."""
    response = client.get("/health")
    
    # The response should be successful
    assert response.status_code == 200
    
    # Note: CORS headers would be added by middleware in the actual application
    # This test verifies the endpoint works and can be extended for CORS testing
