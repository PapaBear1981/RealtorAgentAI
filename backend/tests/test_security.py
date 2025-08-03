"""
Tests for security features including rate limiting, security headers,
and input validation.
"""

import pytest
import time
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import get_session
from app.core.security import (
    RateLimiter,
    sanitize_input,
    get_client_ip
)


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


@pytest.fixture
def test_user_data():
    """Test user data for registration."""
    return {
        "email": "test@example.com",
        "name": "Test User",
        "role": "agent",
        "password": "testpassword123"
    }


class TestRateLimiter:
    """Test rate limiting functionality."""
    
    def test_rate_limiter_allows_requests_under_limit(self):
        """Test that rate limiter allows requests under the limit."""
        limiter = RateLimiter(requests_per_minute=5, window_seconds=60)
        client_id = "test_client"
        
        # Should allow 5 requests
        for i in range(5):
            assert limiter.is_allowed(client_id) is True
    
    def test_rate_limiter_blocks_requests_over_limit(self):
        """Test that rate limiter blocks requests over the limit."""
        limiter = RateLimiter(requests_per_minute=3, window_seconds=60)
        client_id = "test_client"
        
        # Allow 3 requests
        for i in range(3):
            assert limiter.is_allowed(client_id) is True
        
        # Block 4th request
        assert limiter.is_allowed(client_id) is False
    
    def test_rate_limiter_resets_after_window(self):
        """Test that rate limiter resets after time window."""
        limiter = RateLimiter(requests_per_minute=2, window_seconds=1)
        client_id = "test_client"
        
        # Use up the limit
        assert limiter.is_allowed(client_id) is True
        assert limiter.is_allowed(client_id) is True
        assert limiter.is_allowed(client_id) is False
        
        # Wait for window to reset
        time.sleep(1.1)
        
        # Should allow requests again
        assert limiter.is_allowed(client_id) is True
    
    def test_rate_limiter_different_clients(self):
        """Test that rate limiter tracks different clients separately."""
        limiter = RateLimiter(requests_per_minute=2, window_seconds=60)
        
        # Client 1 uses up limit
        assert limiter.is_allowed("client1") is True
        assert limiter.is_allowed("client1") is True
        assert limiter.is_allowed("client1") is False
        
        # Client 2 should still be allowed
        assert limiter.is_allowed("client2") is True
        assert limiter.is_allowed("client2") is True
        assert limiter.is_allowed("client2") is False
    
    def test_get_reset_time(self):
        """Test getting rate limit reset time."""
        limiter = RateLimiter(requests_per_minute=1, window_seconds=60)
        client_id = "test_client"
        
        # Make a request
        start_time = time.time()
        limiter.is_allowed(client_id)
        
        # Get reset time
        reset_time = limiter.get_reset_time(client_id)
        
        # Should be approximately 60 seconds from now
        expected_reset = start_time + 60
        assert abs(reset_time - expected_reset) < 2  # Allow 2 second tolerance


class TestSecurityHeaders:
    """Test security headers in responses."""
    
    def test_security_headers_present(self, client):
        """Test that security headers are present in responses."""
        response = client.get("/health")
        
        # Check for security headers
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        
        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"
        
        assert "X-XSS-Protection" in response.headers
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        
        assert "Referrer-Policy" in response.headers
        assert "Permissions-Policy" in response.headers
    
    def test_rate_limit_headers(self, client):
        """Test that rate limit headers are present."""
        response = client.get("/health")
        
        # Check for rate limit headers
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers
    
    def test_process_time_header(self, client):
        """Test that process time header is present."""
        response = client.get("/health")
        
        assert "X-Process-Time" in response.headers
        # Should be a valid float
        process_time = float(response.headers["X-Process-Time"])
        assert process_time >= 0


class TestInputSanitization:
    """Test input sanitization utilities."""
    
    def test_sanitize_input_normal_text(self):
        """Test sanitizing normal text."""
        input_text = "This is normal text"
        result = sanitize_input(input_text)
        assert result == "This is normal text"
    
    def test_sanitize_input_removes_dangerous_chars(self):
        """Test that dangerous characters are removed."""
        input_text = "Hello <script>alert('xss')</script> world"
        result = sanitize_input(input_text)
        assert "<" not in result
        assert ">" not in result
        assert "script" in result  # Text content should remain
    
    def test_sanitize_input_truncates_long_text(self):
        """Test that long text is truncated."""
        input_text = "a" * 2000
        result = sanitize_input(input_text, max_length=100)
        assert len(result) == 100
    
    def test_sanitize_input_removes_null_bytes(self):
        """Test that null bytes are removed."""
        input_text = "Hello\x00World"
        result = sanitize_input(input_text)
        assert "\x00" not in result
        assert result == "HelloWorld"
    
    def test_sanitize_input_strips_whitespace(self):
        """Test that leading/trailing whitespace is stripped."""
        input_text = "  Hello World  "
        result = sanitize_input(input_text)
        assert result == "Hello World"
    
    def test_sanitize_input_handles_non_string(self):
        """Test that non-string input is converted to string."""
        result = sanitize_input(123)
        assert result == "123"
        
        result = sanitize_input(None)
        assert result == "None"


class TestAuthenticationSecurity:
    """Test authentication-specific security features."""
    
    def test_login_rate_limiting(self, client, test_user_data):
        """Test that login endpoint has stricter rate limiting."""
        # Register a user first
        client.post("/auth/register", json=test_user_data)
        
        login_data = {
            "username": test_user_data["email"],
            "password": "wrongpassword"
        }
        
        # Make multiple failed login attempts
        # Note: This test depends on the rate limiter configuration
        # In a real test, you might want to mock the rate limiter
        responses = []
        for i in range(15):  # Exceed the auth rate limit
            response = client.post("/auth/login", data=login_data)
            responses.append(response.status_code)
        
        # Should eventually get rate limited (429)
        # Note: The exact number depends on rate limiter configuration
        assert any(status == 429 for status in responses[-5:])
    
    def test_password_validation_in_registration(self, client):
        """Test password validation during registration."""
        user_data = {
            "email": "test@example.com",
            "name": "Test User",
            "role": "agent",
            "password": "123"  # Too short
        }
        
        response = client.post("/auth/register", json=user_data)
        
        # Should fail validation
        assert response.status_code == 422
    
    def test_email_validation_in_registration(self, client):
        """Test email validation during registration."""
        user_data = {
            "email": "invalid-email",  # Invalid email format
            "name": "Test User",
            "role": "agent",
            "password": "validpassword123"
        }
        
        response = client.post("/auth/register", json=user_data)
        
        # Should fail validation
        assert response.status_code == 422


class TestRequestSizeValidation:
    """Test request size validation."""
    
    def test_large_request_rejected(self, client):
        """Test that very large requests are rejected."""
        # Create a large payload
        large_data = {
            "email": "test@example.com",
            "name": "Test User",
            "role": "agent",
            "password": "password123",
            "large_field": "x" * (15 * 1024 * 1024)  # 15MB
        }
        
        response = client.post("/auth/register", json=large_data)
        
        # Should be rejected due to size
        assert response.status_code == 413


class TestErrorHandling:
    """Test security-related error handling."""
    
    def test_authentication_error_doesnt_leak_info(self, client):
        """Test that authentication errors don't leak sensitive information."""
        login_data = {
            "username": "nonexistent@example.com",
            "password": "password"
        }
        
        response = client.post("/auth/login", data=login_data)
        
        assert response.status_code == 401
        # Should not reveal whether user exists or not
        assert "Incorrect username or password" in response.json()["detail"]
        assert "nonexistent" not in response.json()["detail"]
    
    def test_token_error_handling(self, client):
        """Test that token errors are handled securely."""
        headers = {"Authorization": "Bearer malformed.token.here"}
        response = client.get("/auth/me", headers=headers)
        
        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]
        # Should not reveal token parsing details
        assert "malformed" not in response.json()["detail"]
