"""
Security middleware and utilities.

This module provides security middleware for rate limiting,
security headers, and request validation.
"""

import time
from typing import Dict, Optional
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from collections import defaultdict, deque
import logging

from .config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Simple in-memory rate limiter using sliding window.
    
    In production, consider using Redis for distributed rate limiting.
    """
    
    def __init__(self, requests_per_minute: int = 100, window_seconds: int = 60):
        self.requests_per_minute = requests_per_minute
        self.window_seconds = window_seconds
        self.requests: Dict[str, deque] = defaultdict(deque)
    
    def is_allowed(self, identifier: str) -> bool:
        """
        Check if request is allowed for the given identifier.
        
        Args:
            identifier: Client identifier (IP address, user ID, etc.)
            
        Returns:
            bool: True if request is allowed, False if rate limited
        """
        now = time.time()
        window_start = now - self.window_seconds
        
        # Clean old requests
        client_requests = self.requests[identifier]
        while client_requests and client_requests[0] < window_start:
            client_requests.popleft()
        
        # Check if under limit
        if len(client_requests) >= self.requests_per_minute:
            return False
        
        # Add current request
        client_requests.append(now)
        return True
    
    def get_reset_time(self, identifier: str) -> int:
        """
        Get the time when rate limit resets for the identifier.
        
        Args:
            identifier: Client identifier
            
        Returns:
            int: Unix timestamp when rate limit resets
        """
        client_requests = self.requests[identifier]
        if not client_requests:
            return int(time.time())
        
        return int(client_requests[0] + self.window_seconds)


# Global rate limiter instances
auth_rate_limiter = RateLimiter(
    requests_per_minute=10,  # Stricter limit for auth endpoints
    window_seconds=60
)

general_rate_limiter = RateLimiter(
    requests_per_minute=settings.RATE_LIMIT_REQUESTS,
    window_seconds=settings.RATE_LIMIT_WINDOW
)


def get_client_ip(request: Request) -> str:
    """
    Get client IP address from request.
    
    Args:
        request: FastAPI request object
        
    Returns:
        str: Client IP address
    """
    # Check for forwarded headers (when behind proxy)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fallback to direct connection
    return request.client.host if request.client else "unknown"


async def rate_limit_middleware(request: Request, call_next):
    """
    Rate limiting middleware.
    
    Args:
        request: FastAPI request object
        call_next: Next middleware/endpoint in chain
        
    Returns:
        Response: HTTP response
    """
    client_ip = get_client_ip(request)
    path = request.url.path
    
    # Choose appropriate rate limiter
    if path.startswith("/auth/"):
        limiter = auth_rate_limiter
        limit_type = "auth"
    else:
        limiter = general_rate_limiter
        limit_type = "general"
    
    # Check rate limit
    if not limiter.is_allowed(client_ip):
        reset_time = limiter.get_reset_time(client_ip)
        
        logger.warning(
            f"Rate limit exceeded for {client_ip} on {path}",
            extra={
                "client_ip": client_ip,
                "path": path,
                "limit_type": limit_type
            }
        )
        
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "detail": "Rate limit exceeded",
                "retry_after": reset_time - int(time.time())
            },
            headers={
                "Retry-After": str(reset_time - int(time.time())),
                "X-RateLimit-Limit": str(limiter.requests_per_minute),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset_time)
            }
        )
    
    # Process request
    response = await call_next(request)
    
    # Add rate limit headers
    remaining = limiter.requests_per_minute - len(limiter.requests[client_ip])
    reset_time = limiter.get_reset_time(client_ip)
    
    response.headers["X-RateLimit-Limit"] = str(limiter.requests_per_minute)
    response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
    response.headers["X-RateLimit-Reset"] = str(reset_time)
    
    return response


async def security_headers_middleware(request: Request, call_next):
    """
    Security headers middleware.
    
    Adds security headers to all responses.
    
    Args:
        request: FastAPI request object
        call_next: Next middleware/endpoint in chain
        
    Returns:
        Response: HTTP response with security headers
    """
    response = await call_next(request)
    
    # Security headers
    security_headers = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    }
    
    # Add Content Security Policy for HTML responses
    if response.headers.get("content-type", "").startswith("text/html"):
        security_headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
    
    # Add HSTS header for HTTPS
    if request.url.scheme == "https":
        security_headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    # Apply headers
    for header, value in security_headers.items():
        response.headers[header] = value
    
    return response


def validate_request_size(max_size: int = 10 * 1024 * 1024):  # 10MB default
    """
    Create middleware to validate request size.
    
    Args:
        max_size: Maximum allowed request size in bytes
        
    Returns:
        Middleware function
    """
    async def request_size_middleware(request: Request, call_next):
        """
        Request size validation middleware.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/endpoint in chain
            
        Returns:
            Response: HTTP response
        """
        content_length = request.headers.get("content-length")
        
        if content_length:
            content_length = int(content_length)
            if content_length > max_size:
                return JSONResponse(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    content={
                        "detail": f"Request too large. Maximum size: {max_size} bytes"
                    }
                )
        
        return await call_next(request)
    
    return request_size_middleware


async def log_requests_middleware(request: Request, call_next):
    """
    Request logging middleware.
    
    Args:
        request: FastAPI request object
        call_next: Next middleware/endpoint in chain
        
    Returns:
        Response: HTTP response
    """
    start_time = time.time()
    client_ip = get_client_ip(request)
    
    # Process request
    response = await call_next(request)
    
    # Calculate processing time
    process_time = time.time() - start_time
    
    # Log request
    logger.info(
        f"{request.method} {request.url.path} - {response.status_code}",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "process_time": process_time,
            "client_ip": client_ip,
            "user_agent": request.headers.get("user-agent", ""),
        }
    )
    
    return response


def sanitize_input(value: str, max_length: int = 1000) -> str:
    """
    Sanitize user input to prevent injection attacks.
    
    Args:
        value: Input value to sanitize
        max_length: Maximum allowed length
        
    Returns:
        str: Sanitized input
    """
    if not isinstance(value, str):
        return str(value)
    
    # Truncate if too long
    if len(value) > max_length:
        value = value[:max_length]
    
    # Remove potentially dangerous characters
    dangerous_chars = ["<", ">", "&", "\"", "'", "\x00"]
    for char in dangerous_chars:
        value = value.replace(char, "")
    
    return value.strip()


# Export middleware and utilities
__all__ = [
    "RateLimiter",
    "auth_rate_limiter",
    "general_rate_limiter",
    "get_client_ip",
    "rate_limit_middleware",
    "security_headers_middleware",
    "validate_request_size",
    "log_requests_middleware",
    "sanitize_input",
]
