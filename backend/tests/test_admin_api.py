"""
Tests for admin API endpoints.

This module contains comprehensive tests for all admin functionality including
user management, audit trails, system monitoring, and configuration management.
"""

import pytest
import json
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, select, create_engine
from sqlalchemy.pool import StaticPool

from app.main import app
from app.models.user import User, UserCreate
from app.models.audit_log import AuditLog
from app.core.auth import hash_password, create_access_token
from app.core.database import get_session


# Test database engine
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


@pytest.fixture(scope="function")
def client():
    """Create test client for FastAPI application."""
    # Create test database tables
    SQLModel.metadata.create_all(test_engine)

    with TestClient(app) as test_client:
        yield test_client

    # Clean up
    SQLModel.metadata.drop_all(test_engine)


@pytest.fixture(scope="function")
def admin_user():
    """Create admin user for testing."""
    with Session(test_engine) as session:
        admin = User(
            email="admin@example.com",
            name="Admin User",
            role="admin",
            password_hash=hash_password("adminpassword"),
            disabled=False,
            created_at=datetime.utcnow()
        )
        session.add(admin)
        session.commit()
        session.refresh(admin)
        return admin


@pytest.fixture(scope="function")
def test_user():
    """Create test user for testing."""
    with Session(test_engine) as session:
        user = User(
            email="testuser@example.com",
            name="Test User",
            role="agent",
            password_hash=hash_password("testpassword"),
            disabled=False,
            created_at=datetime.utcnow()
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


@pytest.fixture(scope="function")
def admin_token(admin_user):
    """Create admin JWT token for testing."""
    token_data = {
        "sub": admin_user.email,
        "role": admin_user.role,
        "user_id": admin_user.id
    }
    return create_access_token(token_data)


@pytest.fixture(scope="function")
def agent_token():
    """Create agent JWT token for testing."""
    with Session(test_engine) as session:
        agent = User(
            email="agent@example.com",
            name="Agent User",
            role="agent",
            password_hash=hash_password("agentpassword"),
            disabled=False,
            created_at=datetime.utcnow()
        )
        session.add(agent)
        session.commit()
        session.refresh(agent)

        token_data = {
            "sub": agent.email,
            "role": agent.role,
            "user_id": agent.id
        }
        return create_access_token(token_data)


class TestAdminUserManagement:
    """Test admin user management endpoints."""

    def test_create_user_success(self, client: TestClient, admin_token: str):
        """Test successful user creation."""
        user_data = {
            "email": "newuser@example.com",
            "name": "New User",
            "role": "agent",
            "password": "testpassword123",
            "disabled": False
        }

        response = client.post(
            "/admin/users",
            json=user_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["name"] == user_data["name"]
        assert data["role"] == user_data["role"]
        assert data["disabled"] == user_data["disabled"]
        assert "id" in data
        assert "created_at" in data

    def test_create_user_duplicate_email(self, client: TestClient, admin_token: str):
        """Test user creation with duplicate email."""
        user_data = {
            "email": "admin@example.com",  # Already exists
            "name": "Duplicate User",
            "role": "agent",
            "password": "testpassword123",
            "disabled": False
        }

        response = client.post(
            "/admin/users",
            json=user_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_create_user_invalid_role(self, client: TestClient, admin_token: str):
        """Test user creation with invalid role."""
        user_data = {
            "email": "invalidrole@example.com",
            "name": "Invalid Role User",
            "role": "invalid_role",
            "password": "testpassword123",
            "disabled": False
        }

        response = client.post(
            "/admin/users",
            json=user_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 422  # Validation error

    def test_list_users_success(self, client: TestClient, admin_token: str):
        """Test successful user listing."""
        response = client.get(
            "/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert "total_count" in data
        assert "limit" in data
        assert "offset" in data
        assert "has_more" in data
        assert isinstance(data["users"], list)

    def test_list_users_with_filters(self, client: TestClient, admin_token: str):
        """Test user listing with filters."""
        response = client.get(
            "/admin/users?role=admin&disabled=false&limit=10",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "users" in data

        # Check that all returned users match the filters
        for user in data["users"]:
            assert user["role"] == "admin"
            assert user["disabled"] == False

    def test_list_users_with_search(self, client: TestClient, admin_token: str):
        """Test user listing with search query."""
        response = client.get(
            "/admin/users?search=admin",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "users" in data

    def test_get_user_success(self, client: TestClient, admin_token: str, test_user: User):
        """Test successful user retrieval."""
        response = client.get(
            f"/admin/users/{test_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user.id
        assert data["email"] == test_user.email
        assert data["name"] == test_user.name
        assert data["role"] == test_user.role

    def test_get_user_not_found(self, client: TestClient, admin_token: str):
        """Test user retrieval with non-existent ID."""
        response = client.get(
            "/admin/users/99999",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_update_user_success(self, client: TestClient, admin_token: str, test_user: User):
        """Test successful user update."""
        update_data = {
            "name": "Updated Name",
            "role": "tc"
        }

        response = client.patch(
            f"/admin/users/{test_user.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["role"] == update_data["role"]

    def test_update_user_not_found(self, client: TestClient, admin_token: str):
        """Test user update with non-existent ID."""
        update_data = {"name": "Updated Name"}

        response = client.patch(
            "/admin/users/99999",
            json=update_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 404

    def test_delete_user_success(self, client: TestClient, admin_token: str, test_user: User):
        """Test successful user deletion."""
        response = client.delete(
            f"/admin/users/{test_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "deleted successfully" in data["message"]
        assert data["user_id"] == test_user.id

    def test_delete_user_self(self, client: TestClient, admin_token: str, admin_user: User):
        """Test that admin cannot delete their own account."""
        response = client.delete(
            f"/admin/users/{admin_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 400
        assert "Cannot delete your own account" in response.json()["detail"]

    def test_delete_user_not_found(self, client: TestClient, admin_token: str):
        """Test user deletion with non-existent ID."""
        response = client.delete(
            "/admin/users/99999",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 404


class TestAdminAuditTrail:
    """Test admin audit trail endpoints."""

    def test_search_audit_logs_success(self, client: TestClient, admin_token: str):
        """Test successful audit log search."""
        response = client.get(
            "/admin/audit-logs",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "audit_logs" in data
        assert "total_count" in data
        assert "limit" in data
        assert "offset" in data
        assert "has_more" in data
        assert isinstance(data["audit_logs"], list)

    def test_search_audit_logs_with_filters(self, client: TestClient, admin_token: str, admin_user: User):
        """Test audit log search with filters."""
        response = client.get(
            f"/admin/audit-logs?user_id={admin_user.id}&success=true",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "audit_logs" in data

    def test_search_audit_logs_with_date_filters(self, client: TestClient, admin_token: str):
        """Test audit log search with date filters."""
        start_date = (datetime.utcnow() - timedelta(days=1)).isoformat()
        end_date = datetime.utcnow().isoformat()

        response = client.get(
            f"/admin/audit-logs?start_date={start_date}&end_date={end_date}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "audit_logs" in data

    def test_search_audit_logs_invalid_date(self, client: TestClient, admin_token: str):
        """Test audit log search with invalid date format."""
        response = client.get(
            "/admin/audit-logs?start_date=invalid-date",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 400
        assert "Invalid start_date format" in response.json()["detail"]

    def test_export_audit_logs_csv(self, client: TestClient, admin_token: str):
        """Test audit log export in CSV format."""
        response = client.get(
            "/admin/audit-logs/export?format=csv",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in response.headers["content-disposition"]
        assert "audit_logs.csv" in response.headers["content-disposition"]

    def test_export_audit_logs_json(self, client: TestClient, admin_token: str):
        """Test audit log export in JSON format."""
        response = client.get(
            "/admin/audit-logs/export?format=json",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        assert "attachment" in response.headers["content-disposition"]
        assert "audit_logs.json" in response.headers["content-disposition"]

        # Verify JSON structure
        data = response.json()
        assert "export_timestamp" in data
        assert "exported_by" in data
        assert "audit_logs" in data

    def test_export_audit_logs_invalid_format(self, client: TestClient, admin_token: str):
        """Test audit log export with invalid format."""
        response = client.get(
            "/admin/audit-logs/export?format=xml",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 422  # Validation error


class TestAdminSystemMonitoring:
    """Test admin system monitoring endpoints."""

    def test_get_system_health_success(self, client: TestClient, admin_token: str):
        """Test successful system health check."""
        response = client.get(
            "/admin/health",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "timestamp" in data
        assert "overall_status" in data
        assert "database" in data
        assert "users" in data
        assert "activity" in data
        assert "performance" in data

        # Check database health structure
        assert "healthy" in data["database"]
        assert "user_count" in data["database"]

        # Check user statistics structure
        assert "total_users" in data["users"]
        assert "active_users" in data["users"]
        assert "role_distribution" in data["users"]

    def test_get_usage_analytics_success(self, client: TestClient, admin_token: str):
        """Test successful usage analytics retrieval."""
        response = client.get(
            "/admin/analytics?days=7",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "period" in data
        assert "user_activity" in data
        assert "template_usage" in data
        assert "contracts" in data
        assert "errors" in data
        assert "generated_at" in data

        # Check period structure
        assert data["period"]["days"] == 7
        assert "start_date" in data["period"]
        assert "end_date" in data["period"]

    def test_get_usage_analytics_invalid_days(self, client: TestClient, admin_token: str):
        """Test usage analytics with invalid days parameter."""
        response = client.get(
            "/admin/analytics?days=0",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 422  # Validation error

    def test_get_usage_analytics_max_days(self, client: TestClient, admin_token: str):
        """Test usage analytics with maximum days parameter."""
        response = client.get(
            "/admin/analytics?days=365",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["period"]["days"] == 365


class TestAdminConfiguration:
    """Test admin configuration management endpoints."""

    def test_get_system_configuration_success(self, client: TestClient, admin_token: str):
        """Test successful system configuration retrieval."""
        response = client.get(
            "/admin/config",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "environment" in data
        assert "debug" in data
        assert "jwt_settings" in data
        assert "cors_settings" in data
        assert "file_settings" in data
        assert "rate_limiting" in data

        # Check that sensitive data is hidden
        assert data["database_url"] == "***HIDDEN***"

        # Check JWT settings structure
        assert "algorithm" in data["jwt_settings"]
        assert "access_token_expire_minutes" in data["jwt_settings"]

    def test_update_system_configuration_not_implemented(self, client: TestClient, admin_token: str):
        """Test system configuration update (not yet implemented)."""
        config_updates = {
            "debug": False,
            "rate_limiting": {"requests_per_minute": 120}
        }

        response = client.patch(
            "/admin/config",
            json=config_updates,
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 501
        assert "not yet implemented" in response.json()["detail"]


class TestAdminModelManagement:
    """Test admin AI model management endpoints."""

    def test_list_ai_models_success(self, client: TestClient, admin_token: str):
        """Test successful AI models listing."""
        response = client.get(
            "/admin/models",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "available_models" in data
        assert "routing_config" in data
        assert "usage_stats" in data

        # Check available models structure
        assert isinstance(data["available_models"], list)
        if data["available_models"]:
            model = data["available_models"][0]
            assert "id" in model
            assert "name" in model
            assert "provider" in model
            assert "capabilities" in model
            assert "status" in model

        # Check routing config structure
        assert "default_model" in data["routing_config"]
        assert "fallback_model" in data["routing_config"]
        assert "routing_rules" in data["routing_config"]

        # Check usage stats structure
        assert "total_requests_24h" in data["usage_stats"]
        assert "total_tokens_24h" in data["usage_stats"]
        assert "cost_24h" in data["usage_stats"]

    def test_update_model_routing_not_implemented(self, client: TestClient, admin_token: str):
        """Test model routing update (not yet implemented)."""
        routing_config = {
            "default_model": "claude-3-sonnet",
            "routing_rules": [
                {
                    "condition": "legal_analysis",
                    "model": "claude-3-sonnet",
                    "reason": "Better legal understanding"
                }
            ]
        }

        response = client.patch(
            "/admin/models/routing",
            json=routing_config,
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 501
        assert "not yet implemented" in response.json()["detail"]


class TestAdminAuthorization:
    """Test admin endpoint authorization."""

    def test_admin_endpoints_require_admin_role(self, client: TestClient, agent_token: str):
        """Test that admin endpoints require admin role."""
        endpoints = [
            "/admin/users",
            "/admin/audit-logs",
            "/admin/health",
            "/admin/analytics",
            "/admin/config",
            "/admin/models"
        ]

        for endpoint in endpoints:
            response = client.get(
                endpoint,
                headers={"Authorization": f"Bearer {agent_token}"}
            )
            assert response.status_code == 403
            assert "Access denied" in response.json()["detail"]

    def test_admin_endpoints_require_authentication(self, client: TestClient):
        """Test that admin endpoints require authentication."""
        endpoints = [
            "/admin/users",
            "/admin/audit-logs",
            "/admin/health",
            "/admin/analytics",
            "/admin/config",
            "/admin/models"
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 401

    def test_admin_post_endpoints_require_admin_role(self, client: TestClient, agent_token: str):
        """Test that admin POST endpoints require admin role."""
        user_data = {
            "email": "test@example.com",
            "name": "Test User",
            "role": "agent",
            "password": "testpassword123",
            "disabled": False
        }

        response = client.post(
            "/admin/users",
            json=user_data,
            headers={"Authorization": f"Bearer {agent_token}"}
        )

        assert response.status_code == 403
        assert "Access denied" in response.json()["detail"]


class TestAdminAuditLogging:
    """Test that admin actions are properly logged."""

    def test_admin_actions_create_audit_logs(self, client: TestClient, admin_token: str):
        """Test that admin actions create appropriate audit logs."""
        # Perform an admin action
        response = client.get(
            "/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200

        # Check that audit log was created
        with Session(test_engine) as session:
            audit_logs = session.exec(
                select(AuditLog).where(AuditLog.action == "USER_LIST")
            ).all()
            assert len(audit_logs) > 0

            latest_log = audit_logs[-1]
            assert latest_log.success == True
            assert "admin:" in latest_log.actor

    def test_admin_user_creation_audit_log(self, client: TestClient, admin_token: str):
        """Test that user creation creates detailed audit log."""
        user_data = {
            "email": "audittest@example.com",
            "name": "Audit Test User",
            "role": "agent",
            "password": "testpassword123",
            "disabled": False
        }

        response = client.post(
            "/admin/users",
            json=user_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 201

        # Check audit log
        with Session(test_engine) as session:
            audit_logs = session.exec(
                select(AuditLog).where(AuditLog.action == "USER_CREATE")
            ).all()
            assert len(audit_logs) > 0

            latest_log = audit_logs[-1]
            assert latest_log.success == True
            assert latest_log.meta is not None
            assert "created_user_email" in latest_log.meta
            assert latest_log.meta["created_user_email"] == user_data["email"]
