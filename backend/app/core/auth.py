"""
Authentication and security utilities for the Multi-Agent Real-Estate Contract Platform.

This module provides JWT token generation/validation, password hashing,
and authentication utilities following FastAPI best practices.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import HTTPException, status

from .config import get_settings

settings = get_settings()

# Password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password to hash

    Returns:
        str: Hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to verify against

    Returns:
        bool: True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Data to encode in the token (typically user info)
        expires_delta: Token expiration time delta

    Returns:
        str: Encoded JWT token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    Create a JWT refresh token with longer expiration.

    Args:
        data: Data to encode in the token

    Returns:
        str: Encoded JWT refresh token
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

    return encoded_jwt


def verify_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token to verify

    Returns:
        Dict: Decoded token payload

    Raises:
        HTTPException: If token is invalid or expired
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )

        # Check if token has expired
        exp = payload.get("exp")
        if exp is None:
            raise credentials_exception

        # Add a buffer for clock skew and testing
        current_time = datetime.utcnow().timestamp()
        if current_time > (exp + 30):  # 30 second buffer for testing
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return payload

    except JWTError:
        raise credentials_exception


def get_token_subject(token: str) -> Optional[str]:
    """
    Extract the subject (user identifier) from a JWT token.

    Args:
        token: JWT token

    Returns:
        Optional[str]: Token subject (typically user email or ID)
    """
    try:
        payload = verify_token(token)
        return payload.get("sub")
    except HTTPException:
        return None


def create_token_response(user_id: int, user_email: str, user_role: str) -> Dict[str, Any]:
    """
    Create a complete token response with access and refresh tokens.

    Args:
        user_id: User ID
        user_email: User email
        user_role: User role

    Returns:
        Dict: Token response with access_token, refresh_token, and metadata
    """
    # Create token data
    token_data = {
        "sub": user_email,
        "user_id": user_id,
        "role": user_role,
        "type": "access"
    }

    # Create tokens
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # seconds
        "user": {
            "id": user_id,
            "email": user_email,
            "role": user_role
        }
    }


def validate_refresh_token(refresh_token: str) -> Dict[str, Any]:
    """
    Validate a refresh token and extract user data.

    Args:
        refresh_token: JWT refresh token

    Returns:
        Dict: User data from token

    Raises:
        HTTPException: If refresh token is invalid
    """
    try:
        payload = verify_token(refresh_token)

        # Check if it's actually a refresh token
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return payload

    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# Export functions
__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    "get_token_subject",
    "create_token_response",
    "validate_refresh_token",
]
