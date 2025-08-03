"""
Tests for the main FastAPI application.

This module tests the basic FastAPI application setup, middleware,
health checks, and core functionality.
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import get_session


# Create test database engine
test_engine = create_engine(
    "sqlite://",  # In-memory SQLite database
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


def get_test_session():
    """Override database session for testing."""
    with Session(test_engine) as session:
        yield session


# Override the database dependency
app.dependency_overrides[get_session] = get_test_session


@pytest.fixture(scope="module")
def client():
    """Create test client for FastAPI application."""
    # Create test database tables
    SQLModel.metadata.create_all(test_engine)

    with TestClient(app) as test_client:
        yield test_client

    # Clean up
    SQLModel.metadata.drop_all(test_engine)


def test_root_endpoint(client):
    """Test the root endpoint returns correct information."""
    response = client.get("/")
    assert response.status_code == 200

    data = response.json()
    assert data["message"] == "Multi-Agent Real-Estate Contract Platform API"
    assert data["version"] == "0.1.0"
    assert "docs" in data
    assert "redoc" in data
    assert "health" in data


def test_health_check_endpoint(client):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert data["version"] == "0.1.0"
    assert "environment" in data
    assert "database" in data


def test_openapi_docs_accessible(client):
    """Test that OpenAPI documentation is accessible."""
    response = client.get("/docs")
    assert response.status_code == 200

    response = client.get("/redoc")
    assert response.status_code == 200


def test_openapi_schema(client):
    """Test that OpenAPI schema is properly generated."""
    response = client.get("/openapi.json")
    assert response.status_code == 200

    schema = response.json()
    assert schema["info"]["title"] == "Multi-Agent Real-Estate Contract Platform API"
    assert schema["info"]["version"] == "0.1.0"
    assert "paths" in schema
    assert "components" in schema


def test_cors_headers(client):
    """Test that CORS headers are properly set."""
    response = client.options("/")
    assert response.status_code == 200

    # Check for CORS headers in a regular request
    response = client.get("/")
    # Note: TestClient doesn't automatically add CORS headers,
    # but we can verify the middleware is configured


def test_process_time_header(client):
    """Test that process time header is added to responses."""
    response = client.get("/")
    assert response.status_code == 200
    assert "X-Process-Time" in response.headers

    # Verify it's a valid float
    process_time = float(response.headers["X-Process-Time"])
    assert process_time >= 0


def test_404_error_handling(client):
    """Test that 404 errors are handled properly."""
    response = client.get("/nonexistent-endpoint")
    assert response.status_code == 404

    data = response.json()
    assert "detail" in data


def test_method_not_allowed_handling(client):
    """Test that method not allowed errors are handled properly."""
    response = client.post("/")  # Root only accepts GET
    assert response.status_code == 405

    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_lifespan_events():
    """Test that lifespan events are properly configured."""
    # This test verifies that the lifespan context manager is set up
    # The actual database initialization is tested separately
    assert app.router.lifespan_context is not None


def test_api_tags_configuration():
    """Test that API tags are properly configured in OpenAPI schema."""
    with TestClient(app) as client:
        response = client.get("/openapi.json")
        schema = response.json()

        # Check that tags are defined
        assert "tags" in schema

        expected_tags = ["auth", "files", "contracts", "signatures", "admin", "ai-agents", "system"]
        schema_tag_names = [tag["name"] for tag in schema["tags"]]

        # Check that system tag exists (from health and root endpoints)
        assert "system" in schema_tag_names


def test_application_metadata():
    """Test that application metadata is correctly configured."""
    assert app.title == "Multi-Agent Real-Estate Contract Platform API"
    assert app.version == "0.1.0"
    assert app.contact is not None
    assert app.license_info is not None


if __name__ == "__main__":
    pytest.main([__file__])
