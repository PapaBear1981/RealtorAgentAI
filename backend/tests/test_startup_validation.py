"""
Tests for startup validation service.

This module tests the comprehensive startup validation and health checking
functionality for all system dependencies.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from app.core.startup_validation import (
    StartupValidationService,
    ServiceStatus,
    ServiceType,
    get_startup_validation_service
)


@pytest.fixture
def startup_service():
    """Create a fresh startup validation service for testing."""
    return StartupValidationService()


@pytest.mark.asyncio
async def test_startup_validation_service_initialization(startup_service):
    """Test that startup validation service initializes correctly."""
    assert startup_service.startup_time is not None
    assert startup_service.startup_complete is False
    assert startup_service.ready_for_traffic is False
    assert startup_service.health_status.overall_status == ServiceStatus.UNKNOWN


@pytest.mark.asyncio
async def test_configuration_check_success(startup_service):
    """Test successful configuration validation."""
    with patch('app.core.startup_validation.settings') as mock_settings:
        mock_settings.DATABASE_URL = "sqlite:///test.db"
        mock_settings.REDIS_URL = "redis://localhost:6379"
        mock_settings.SECRET_KEY = "test-secret-key"
        mock_settings.ENVIRONMENT = "test"

        await startup_service._check_configuration()

        config_service = startup_service.health_status.services.get("configuration")
        assert config_service is not None
        assert config_service.status == ServiceStatus.HEALTHY
        assert "validated_configs" in config_service.details


@pytest.mark.asyncio
async def test_configuration_check_missing_config(startup_service):
    """Test configuration validation with missing required config."""
    with patch('app.core.startup_validation.settings') as mock_settings:
        mock_settings.DATABASE_URL = ""  # Missing
        mock_settings.REDIS_URL = "redis://localhost:6379"
        mock_settings.SECRET_KEY = "test-secret-key"
        mock_settings.ENVIRONMENT = "test"

        await startup_service._check_configuration()

        config_service = startup_service.health_status.services.get("configuration")
        assert config_service is not None
        assert config_service.status == ServiceStatus.UNHEALTHY
        assert "database_url" in config_service.details["missing_configs"]


@pytest.mark.asyncio
async def test_database_connection_check_success(startup_service):
    """Test successful database connection check."""
    with patch('app.core.startup_validation.check_database_connection', return_value=True), \
         patch('app.core.startup_validation.get_session_context') as mock_session_context:

        # Mock database session
        mock_session = Mock()
        mock_session.exec.return_value.first.return_value = 5  # Mock user count

        # Mock the generator that returns a context manager
        def mock_generator():
            yield mock_session

        mock_session_context.return_value = mock_generator()

        await startup_service._check_database_connection()

        db_service = startup_service.health_status.services.get("database")
        assert db_service is not None
        assert db_service.status == ServiceStatus.HEALTHY
        assert db_service.details["user_count"] == 5


@pytest.mark.asyncio
async def test_database_connection_check_failure(startup_service):
    """Test database connection check failure."""
    with patch('app.core.startup_validation.check_database_connection', return_value=False):

        await startup_service._check_database_connection()

        db_service = startup_service.health_status.services.get("database")
        assert db_service is not None
        assert db_service.status == ServiceStatus.UNHEALTHY
        assert "Database connection failed" in startup_service.health_status.critical_errors


@pytest.mark.asyncio
async def test_redis_connection_check_success(startup_service):
    """Test successful Redis connection check."""
    with patch('app.core.startup_validation.get_redis_manager') as mock_redis_manager:
        mock_manager = Mock()
        mock_manager.health_check.return_value = {
            "status": "healthy",
            "connection_info": {"host": "localhost", "port": 6379}
        }
        mock_redis_manager.return_value = mock_manager

        await startup_service._check_redis_connection()

        redis_service = startup_service.health_status.services.get("redis")
        assert redis_service is not None
        assert redis_service.status == ServiceStatus.HEALTHY


@pytest.mark.asyncio
async def test_redis_connection_check_failure(startup_service):
    """Test Redis connection check failure."""
    with patch('app.core.startup_validation.get_redis_manager') as mock_redis_manager:
        mock_manager = Mock()
        mock_manager.health_check.return_value = {
            "status": "unhealthy",
            "error": "Connection refused"
        }
        mock_redis_manager.return_value = mock_manager

        await startup_service._check_redis_connection()

        redis_service = startup_service.health_status.services.get("redis")
        assert redis_service is not None
        assert redis_service.status == ServiceStatus.UNHEALTHY


@pytest.mark.asyncio
async def test_storage_connection_check_success(startup_service):
    """Test successful storage connection check."""
    with patch('app.core.startup_validation.get_storage_client') as mock_storage_client:
        mock_client = Mock()
        mock_client.upload_file.return_value = {"key": "test_key"}
        mock_client.get_file.return_value = b"test content"
        mock_client.delete_file.return_value = True
        mock_storage_client.return_value = mock_client

        await startup_service._check_storage_connection()

        storage_service = startup_service.health_status.services.get("storage")
        assert storage_service is not None
        assert storage_service.status == ServiceStatus.HEALTHY
        assert storage_service.details["upload_test"] is True
        assert storage_service.details["download_test"] is True


@pytest.mark.asyncio
async def test_overall_status_calculation(startup_service):
    """Test overall status calculation based on individual service statuses."""
    # Add some mock services
    from app.core.startup_validation import ServiceHealthCheck

    startup_service.health_status.services["database"] = ServiceHealthCheck(
        service_name="database",
        service_type=ServiceType.DATABASE,
        status=ServiceStatus.HEALTHY,
        response_time_ms=100.0,
        last_check=datetime.utcnow()
    )

    startup_service.health_status.services["redis"] = ServiceHealthCheck(
        service_name="redis",
        service_type=ServiceType.REDIS,
        status=ServiceStatus.DEGRADED,
        response_time_ms=200.0,
        last_check=datetime.utcnow()
    )

    startup_service._calculate_overall_status()

    # Should be degraded due to Redis being degraded
    assert startup_service.health_status.overall_status == ServiceStatus.DEGRADED


@pytest.mark.asyncio
async def test_overall_status_unhealthy_critical_service(startup_service):
    """Test overall status when critical service is unhealthy."""
    from app.core.startup_validation import ServiceHealthCheck

    startup_service.health_status.services["database"] = ServiceHealthCheck(
        service_name="database",
        service_type=ServiceType.DATABASE,
        status=ServiceStatus.UNHEALTHY,
        response_time_ms=100.0,
        last_check=datetime.utcnow()
    )

    startup_service._calculate_overall_status()

    # Should be unhealthy due to critical service (database) being unhealthy
    assert startup_service.health_status.overall_status == ServiceStatus.UNHEALTHY


def test_readiness_status(startup_service):
    """Test readiness status generation."""
    startup_service.ready_for_traffic = True
    startup_service.startup_complete = True
    startup_service.health_status.overall_status = ServiceStatus.HEALTHY

    readiness = startup_service.get_readiness_status()

    assert readiness["ready"] is True
    assert readiness["startup_complete"] is True
    assert readiness["overall_status"] == "healthy"
    assert readiness["critical_services_healthy"] is True


def test_liveness_status(startup_service):
    """Test liveness status generation."""
    liveness = startup_service.get_liveness_status()

    assert liveness["alive"] is True
    assert "startup_time" in liveness
    assert "uptime_seconds" in liveness
    assert liveness["uptime_seconds"] >= 0


def test_singleton_service():
    """Test that get_startup_validation_service returns singleton instance."""
    service1 = get_startup_validation_service()
    service2 = get_startup_validation_service()

    assert service1 is service2
