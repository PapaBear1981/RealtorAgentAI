"""
Tests for Role-Based Access Control (RBAC) system.

This module tests role-based permissions, access control,
and authorization functionality.
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import get_session
from app.core.security import auth_rate_limiter, general_rate_limiter
from app.core.dependencies import (
    get_user_scopes,
    require_role,
    require_admin,
    require_agent_or_admin,
    require_tc_or_admin
)
from app.models.user import User


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

    # Clear rate limiters for testing
    auth_rate_limiter.requests.clear()
    general_rate_limiter.requests.clear()

    with TestClient(app) as test_client:
        yield test_client

    # Clean up
    SQLModel.metadata.drop_all(test_engine)


@pytest.fixture
def admin_user(client):
    """Create admin user and return login token."""
    user_data = {
        "email": "admin@example.com",
        "name": "Admin User",
        "role": "admin",
        "password": "adminpassword123"
    }

    # Register user (first user becomes admin)
    register_response = client.post("/auth/register", json=user_data)
    assert register_response.status_code == 200

    # Login to get token
    login_data = {
        "username": user_data["email"],
        "password": user_data["password"]
    }
    login_response = client.post("/auth/login", data=login_data)
    assert login_response.status_code == 200
    return login_response.json()["access_token"]


@pytest.fixture
def agent_user(client, admin_user):
    """Create agent user and return login token."""
    user_data = {
        "email": "agent@example.com",
        "name": "Agent User",
        "role": "agent",
        "password": "agentpassword123"
    }

    # Register user as admin
    headers = {"Authorization": f"Bearer {admin_user}"}
    client.post("/auth/register", json=user_data, headers=headers)

    # Login to get token
    login_data = {
        "username": user_data["email"],
        "password": user_data["password"]
    }
    response = client.post("/auth/login", data=login_data)
    return response.json()["access_token"]


@pytest.fixture
def tc_user(client, admin_user):
    """Create transaction coordinator user and return login token."""
    user_data = {
        "email": "tc@example.com",
        "name": "TC User",
        "role": "tc",
        "password": "tcpassword123"
    }

    # Register user as admin
    headers = {"Authorization": f"Bearer {admin_user}"}
    client.post("/auth/register", json=user_data, headers=headers)

    # Login to get token
    login_data = {
        "username": user_data["email"],
        "password": user_data["password"]
    }
    response = client.post("/auth/login", data=login_data)
    return response.json()["access_token"]


@pytest.fixture
def signer_user(client, admin_user):
    """Create signer user and return login token."""
    user_data = {
        "email": "signer@example.com",
        "name": "Signer User",
        "role": "signer",
        "password": "signerpassword123"
    }

    # Register user as admin
    headers = {"Authorization": f"Bearer {admin_user}"}
    client.post("/auth/register", json=user_data, headers=headers)

    # Login to get token
    login_data = {
        "username": user_data["email"],
        "password": user_data["password"]
    }
    response = client.post("/auth/login", data=login_data)
    return response.json()["access_token"]


class TestUserScopes:
    """Test user scope assignment based on roles."""

    def test_admin_scopes(self):
        """Test admin user has all scopes."""
        scopes = get_user_scopes("admin")
        expected_scopes = ["admin", "agent", "tc", "signer"]
        assert set(scopes) == set(expected_scopes)

    def test_agent_scopes(self):
        """Test agent user has agent and signer scopes."""
        scopes = get_user_scopes("agent")
        expected_scopes = ["agent", "signer"]
        assert set(scopes) == set(expected_scopes)

    def test_tc_scopes(self):
        """Test TC user has tc and signer scopes."""
        scopes = get_user_scopes("tc")
        expected_scopes = ["tc", "signer"]
        assert set(scopes) == set(expected_scopes)

    def test_signer_scopes(self):
        """Test signer user has only signer scope."""
        scopes = get_user_scopes("signer")
        expected_scopes = ["signer"]
        assert set(scopes) == set(expected_scopes)

    def test_invalid_role_scopes(self):
        """Test invalid role returns empty scopes."""
        scopes = get_user_scopes("invalid_role")
        assert scopes == []


class TestUserRegistration:
    """Test user registration with different roles."""

    def test_first_user_becomes_admin(self, client):
        """Test that first user automatically becomes admin."""
        user_data = {
            "email": "first@example.com",
            "name": "First User",
            "role": "agent",  # Requested role
            "password": "password123"
        }

        response = client.post("/auth/register", json=user_data)

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "admin"  # Should be admin regardless of requested role

    def test_non_admin_cannot_register_users(self, client, agent_user):
        """Test that non-admin users cannot register new users."""
        user_data = {
            "email": "newuser@example.com",
            "name": "New User",
            "role": "agent",
            "password": "password123"
        }

        headers = {"Authorization": f"Bearer {agent_user}"}
        response = client.post("/auth/register", json=user_data, headers=headers)

        assert response.status_code == 403
        assert "Only administrators can register" in response.json()["detail"]

    def test_admin_can_register_users(self, client, admin_user):
        """Test that admin users can register new users."""
        user_data = {
            "email": "newuser@example.com",
            "name": "New User",
            "role": "agent",
            "password": "password123"
        }

        headers = {"Authorization": f"Bearer {admin_user}"}
        response = client.post("/auth/register", json=user_data, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["role"] == user_data["role"]  # Should keep requested role

    def test_unauthenticated_cannot_register_users(self, client, admin_user):
        """Test that unauthenticated users cannot register new users."""
        user_data = {
            "email": "newuser@example.com",
            "name": "New User",
            "role": "agent",
            "password": "password123"
        }

        # Don't provide authorization header
        response = client.post("/auth/register", json=user_data)

        assert response.status_code == 403
        assert "Only administrators can register" in response.json()["detail"]


class TestRoleValidation:
    """Test role validation in user creation."""

    def test_valid_roles(self, client, admin_user):
        """Test that valid roles are accepted."""
        valid_roles = ["admin", "agent", "tc", "signer"]

        for i, role in enumerate(valid_roles):
            user_data = {
                "email": f"user{i}@example.com",
                "name": f"User {i}",
                "role": role,
                "password": "password123"
            }

            headers = {"Authorization": f"Bearer {admin_user}"}
            response = client.post("/auth/register", json=user_data, headers=headers)

            assert response.status_code == 200
            assert response.json()["role"] == role

    def test_invalid_role(self, client, admin_user):
        """Test that invalid roles are rejected."""
        user_data = {
            "email": "invalid@example.com",
            "name": "Invalid User",
            "role": "invalid_role",
            "password": "password123"
        }

        headers = {"Authorization": f"Bearer {admin_user}"}
        response = client.post("/auth/register", json=user_data, headers=headers)

        assert response.status_code == 422  # Validation error


class TestTokenAuthentication:
    """Test token-based authentication for different user roles."""

    def test_admin_token_authentication(self, client, admin_user):
        """Test admin user can authenticate with token."""
        headers = {"Authorization": f"Bearer {admin_user}"}
        response = client.get("/auth/me", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "admin"

    def test_agent_token_authentication(self, client, agent_user):
        """Test agent user can authenticate with token."""
        headers = {"Authorization": f"Bearer {agent_user}"}
        response = client.get("/auth/me", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "agent"

    def test_tc_token_authentication(self, client, tc_user):
        """Test TC user can authenticate with token."""
        headers = {"Authorization": f"Bearer {tc_user}"}
        response = client.get("/auth/me", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "tc"

    def test_signer_token_authentication(self, client, signer_user):
        """Test signer user can authenticate with token."""
        headers = {"Authorization": f"Bearer {signer_user}"}
        response = client.get("/auth/me", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "signer"

    def test_invalid_token_authentication(self, client):
        """Test authentication fails with invalid token."""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/auth/me", headers=headers)

        assert response.status_code == 401

    def test_missing_token_authentication(self, client):
        """Test authentication fails without token."""
        response = client.get("/auth/me")

        assert response.status_code == 401


class TestUserDisabling:
    """Test user account disabling functionality."""

    def test_disabled_user_cannot_login(self, client, admin_user):
        """Test that disabled users cannot login."""
        # Create user
        user_data = {
            "email": "disabled@example.com",
            "name": "Disabled User",
            "role": "agent",
            "password": "password123",
            "disabled": True
        }

        headers = {"Authorization": f"Bearer {admin_user}"}
        client.post("/auth/register", json=user_data, headers=headers)

        # Try to login
        login_data = {
            "username": user_data["email"],
            "password": user_data["password"]
        }
        response = client.post("/auth/login", data=login_data)

        assert response.status_code == 400
        assert "disabled" in response.json()["detail"]
