"""
Comprehensive tests for authentication system.

This module tests all authentication endpoints, JWT token handling,
password hashing, and security features.
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import get_session
from app.core.security import auth_rate_limiter, general_rate_limiter
from app.core.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
    create_token_response
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
def test_user_data():
    """Test user data for registration."""
    return {
        "email": "test@example.com",
        "name": "Test User",
        "role": "agent",
        "password": "testpassword123"
    }


@pytest.fixture
def created_user(client, test_user_data):
    """Create a test user and return user data."""
    # Register user (first user becomes admin)
    response = client.post("/auth/register", json=test_user_data)
    assert response.status_code == 200
    return response.json()


class TestPasswordHashing:
    """Test password hashing utilities."""

    def test_hash_password(self):
        """Test password hashing."""
        password = "testpassword123"
        hashed = hash_password(password)

        assert hashed != password
        assert len(hashed) > 50  # Bcrypt hashes are long
        assert hashed.startswith("$2b$")  # Bcrypt prefix

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "testpassword123"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "testpassword123"
        wrong_password = "wrongpassword"
        hashed = hash_password(password)

        assert verify_password(wrong_password, hashed) is False


class TestJWTTokens:
    """Test JWT token creation and verification."""

    def test_create_access_token(self):
        """Test access token creation."""
        data = {"sub": "test@example.com", "user_id": 1, "role": "agent"}
        token = create_access_token(data)

        assert isinstance(token, str)
        assert len(token) > 100  # JWT tokens are long

    def test_create_refresh_token(self):
        """Test refresh token creation."""
        data = {"sub": "test@example.com", "user_id": 1, "role": "agent"}
        token = create_refresh_token(data)

        assert isinstance(token, str)
        assert len(token) > 100

    def test_verify_token_valid(self):
        """Test token verification with valid token."""
        data = {"sub": "test@example.com", "user_id": 1, "role": "agent"}
        token = create_access_token(data)

        payload = verify_token(token)
        assert payload["sub"] == "test@example.com"
        assert payload["user_id"] == 1
        assert payload["role"] == "agent"

    def test_verify_token_expired(self):
        """Test token verification with expired token."""
        data = {"sub": "test@example.com", "user_id": 1, "role": "agent"}
        # Create token that expires immediately
        token = create_access_token(data, expires_delta=timedelta(seconds=-1))

        with pytest.raises(Exception):  # Should raise HTTPException
            verify_token(token)

    def test_create_token_response(self):
        """Test complete token response creation."""
        response = create_token_response(1, "test@example.com", "agent")

        assert "access_token" in response
        assert "refresh_token" in response
        assert response["token_type"] == "bearer"
        assert "expires_in" in response
        assert response["user"]["email"] == "test@example.com"


class TestAuthEndpoints:
    """Test authentication API endpoints."""

    def test_register_first_user(self, client, test_user_data):
        """Test registering the first user (becomes admin)."""
        response = client.post("/auth/register", json=test_user_data)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user_data["email"]
        assert data["name"] == test_user_data["name"]
        assert data["role"] == "admin"  # First user becomes admin
        assert data["disabled"] is False

    def test_register_duplicate_user(self, client, test_user_data, created_user):
        """Test registering user with duplicate email."""
        response = client.post("/auth/register", json=test_user_data)

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_login_valid_credentials(self, client, test_user_data, created_user):
        """Test login with valid credentials."""
        login_data = {
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        }

        response = client.post("/auth/login", data=login_data)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == test_user_data["email"]

    def test_login_invalid_credentials(self, client, test_user_data, created_user):
        """Test login with invalid credentials."""
        login_data = {
            "username": test_user_data["email"],
            "password": "wrongpassword"
        }

        response = client.post("/auth/login", data=login_data)

        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]

    def test_login_nonexistent_user(self, client):
        """Test login with nonexistent user."""
        login_data = {
            "username": "nonexistent@example.com",
            "password": "password"
        }

        response = client.post("/auth/login", data=login_data)

        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]

    def test_get_current_user_valid_token(self, client, test_user_data, created_user):
        """Test getting current user with valid token."""
        # Login to get token
        login_data = {
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        }
        login_response = client.post("/auth/login", data=login_data)
        token = login_response.json()["access_token"]

        # Get current user
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/auth/me", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user_data["email"]
        assert data["name"] == test_user_data["name"]

    def test_get_current_user_invalid_token(self, client):
        """Test getting current user with invalid token."""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/auth/me", headers=headers)

        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]

    def test_get_current_user_no_token(self, client):
        """Test getting current user without token."""
        response = client.get("/auth/me")

        assert response.status_code == 401

    def test_refresh_token_valid(self, client, test_user_data, created_user):
        """Test token refresh with valid refresh token."""
        # Login to get tokens
        login_data = {
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        }
        login_response = client.post("/auth/login", data=login_data)
        refresh_token = login_response.json()["refresh_token"]

        # Refresh token
        refresh_data = {"refresh_token": refresh_token}
        response = client.post("/auth/refresh", json=refresh_data)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_refresh_token_invalid(self, client):
        """Test token refresh with invalid refresh token."""
        refresh_data = {"refresh_token": "invalid_refresh_token"}
        response = client.post("/auth/refresh", json=refresh_data)

        assert response.status_code == 401

    def test_logout(self, client, test_user_data, created_user):
        """Test user logout."""
        # Login to get token
        login_data = {
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        }
        login_response = client.post("/auth/login", data=login_data)
        token = login_response.json()["access_token"]

        # Logout
        headers = {"Authorization": f"Bearer {token}"}
        response = client.post("/auth/logout", headers=headers)

        assert response.status_code == 200
        assert "Successfully logged out" in response.json()["message"]

    def test_change_password_valid(self, client, test_user_data, created_user):
        """Test password change with valid current password."""
        # Login to get token
        login_data = {
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        }
        login_response = client.post("/auth/login", data=login_data)
        token = login_response.json()["access_token"]

        # Change password
        password_data = {
            "current_password": test_user_data["password"],
            "new_password": "newpassword123"
        }
        headers = {"Authorization": f"Bearer {token}"}
        response = client.post("/auth/change-password", json=password_data, headers=headers)

        assert response.status_code == 200
        assert "Password changed successfully" in response.json()["message"]

    def test_change_password_invalid_current(self, client, test_user_data, created_user):
        """Test password change with invalid current password."""
        # Login to get token
        login_data = {
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        }
        login_response = client.post("/auth/login", data=login_data)
        token = login_response.json()["access_token"]

        # Try to change password with wrong current password
        password_data = {
            "current_password": "wrongpassword",
            "new_password": "newpassword123"
        }
        headers = {"Authorization": f"Bearer {token}"}
        response = client.post("/auth/change-password", json=password_data, headers=headers)

        assert response.status_code == 400
        assert "Current password is incorrect" in response.json()["detail"]
