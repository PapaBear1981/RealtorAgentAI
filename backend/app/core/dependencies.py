"""
FastAPI dependencies for authentication and authorization.

This module provides dependency functions for user authentication,
role-based access control, and security enforcement.
"""

from typing import Optional, List
from fastapi import Depends, HTTPException, status, Security
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from sqlmodel import Session, select

from .auth import verify_token, get_token_subject
from .database import get_session
from ..models.user import User

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login",
    scopes={
        "admin": "Full administrative access",
        "agent": "Real estate agent access",
        "tc": "Transaction coordinator access",
        "signer": "Document signer access",
    },
    auto_error=False  # Don't auto-error for optional authentication
)


async def get_current_user(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session)
) -> User:
    """
    Get the current authenticated user from JWT token.

    Args:
        security_scopes: Required security scopes
        token: JWT token from Authorization header
        session: Database session

    Returns:
        User: Current authenticated user

    Raises:
        HTTPException: If authentication fails
    """
    if security_scopes.scopes:
        authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
    else:
        authenticate_value = "Bearer"

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": authenticate_value},
    )

    # Check if token is provided
    if not token:
        raise credentials_exception

    try:
        # Verify and decode token
        payload = verify_token(token)
        user_email: str = payload.get("sub")
        user_role: str = payload.get("role")

        if user_email is None:
            raise credentials_exception

    except HTTPException:
        raise credentials_exception

    # Get user from database
    statement = select(User).where(User.email == user_email)
    user = session.exec(statement).first()

    if user is None:
        raise credentials_exception

    # Check if user is disabled
    if user.disabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    # Check scopes if required
    if security_scopes.scopes:
        # Map user roles to scopes
        user_scopes = get_user_scopes(user.role)

        for scope in security_scopes.scopes:
            if scope not in user_scopes:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not enough permissions",
                    headers={"WWW-Authenticate": authenticate_value},
                )

    return user


async def get_current_active_user(
    current_user: User = Security(get_current_user)
) -> User:
    """
    Get the current active user (alias for get_current_user).

    Args:
        current_user: Current user from get_current_user dependency

    Returns:
        User: Current active user
    """
    return current_user


def get_user_scopes(role: str) -> List[str]:
    """
    Get available scopes for a user role.

    Args:
        role: User role

    Returns:
        List[str]: Available scopes for the role
    """
    role_scopes = {
        "admin": ["admin", "agent", "tc", "signer"],  # Admin has all scopes
        "agent": ["agent", "signer"],  # Agent can sign documents
        "tc": ["tc", "signer"],  # TC can sign documents
        "signer": ["signer"],  # Signer can only sign
    }

    return role_scopes.get(role, [])


def require_role(allowed_roles: List[str]):
    """
    Create a dependency that requires specific user roles.

    Args:
        allowed_roles: List of allowed user roles

    Returns:
        Dependency function that checks user role
    """
    async def role_checker(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(allowed_roles)}"
            )
        return current_user

    return role_checker


def require_admin():
    """
    Dependency that requires admin role.

    Returns:
        User: Current user if admin
    """
    return require_role(["admin"])


def require_agent_or_admin():
    """
    Dependency that requires agent or admin role.

    Returns:
        User: Current user if agent or admin
    """
    return require_role(["agent", "admin"])


def require_tc_or_admin():
    """
    Dependency that requires transaction coordinator or admin role.

    Returns:
        User: Current user if TC or admin
    """
    return require_role(["tc", "admin"])


async def get_optional_user(
    session: Session = Depends(get_session),
    token: Optional[str] = Depends(oauth2_scheme)
) -> Optional[User]:
    """
    Get the current user if authenticated, None otherwise.

    This dependency doesn't raise exceptions for unauthenticated requests.

    Args:
        session: Database session
        token: Optional JWT token

    Returns:
        Optional[User]: Current user if authenticated, None otherwise
    """
    if not token:
        return None

    try:
        user_email = get_token_subject(token)
        if not user_email:
            return None

        statement = select(User).where(User.email == user_email)
        user = session.exec(statement).first()

        if user and not user.disabled:
            return user

    except Exception:
        pass

    return None


def check_resource_access(resource_owner_id: int):
    """
    Create a dependency that checks if user can access a resource.

    Users can access resources they own, or if they're admin.

    Args:
        resource_owner_id: ID of the resource owner

    Returns:
        Dependency function that checks resource access
    """
    async def access_checker(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        # Admin can access everything
        if current_user.role == "admin":
            return current_user

        # Users can access their own resources
        if current_user.id == resource_owner_id:
            return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only access your own resources."
        )

    return access_checker


# Export dependencies
__all__ = [
    "oauth2_scheme",
    "get_current_user",
    "get_current_active_user",
    "get_user_scopes",
    "require_role",
    "require_admin",
    "require_agent_or_admin",
    "require_tc_or_admin",
    "get_optional_user",
    "check_resource_access",
]
