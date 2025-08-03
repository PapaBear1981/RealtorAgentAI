"""
Authentication API endpoints.

This module provides authentication endpoints including login, registration,
token refresh, and user management following OAuth2 password flow.
"""

from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from pydantic import BaseModel, EmailStr

from ..core.database import get_session
from ..core.auth import (
    hash_password,
    verify_password,
    create_token_response,
    validate_refresh_token
)
from ..core.dependencies import get_current_active_user, get_optional_user
from ..models.user import User, UserCreate, UserPublic
from ..models.audit_log import AuditLog, AuditAction

router = APIRouter()


class LoginResponse(BaseModel):
    """Response model for login endpoint."""
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: Dict[str, Any]


class RefreshTokenRequest(BaseModel):
    """Request model for token refresh."""
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    """Request model for password change."""
    current_password: str
    new_password: str


@router.post("/login", response_model=LoginResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session)
):
    """
    OAuth2 password flow login endpoint.

    Authenticates user with username/password and returns JWT tokens.

    Args:
        form_data: OAuth2 form data with username and password
        session: Database session

    Returns:
        LoginResponse: Access token, refresh token, and user info

    Raises:
        HTTPException: If authentication fails
    """
    # Find user by email (username field contains email)
    statement = select(User).where(User.email == form_data.username)
    user = session.exec(statement).first()

    # Verify user exists and password is correct
    if not user or not verify_password(form_data.password, user.password_hash):
        # Log failed login attempt
        audit_log = AuditLog(
            actor=f"user:{form_data.username}",
            action=AuditAction.USER_LOGIN,
            success=False,
            error_message="Invalid credentials",
            meta={"email": form_data.username}
        )
        session.add(audit_log)
        session.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is disabled
    if user.disabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is disabled"
        )

    # Update user login info
    user.last_login = datetime.utcnow()
    user.login_count += 1
    session.add(user)

    # Log successful login
    audit_log = AuditLog(
        user_id=user.id,
        actor=f"user:{user.id}",
        action=AuditAction.USER_LOGIN,
        success=True,
        meta={"email": user.email, "role": user.role}
    )
    session.add(audit_log)
    session.commit()

    # Create and return tokens
    return create_token_response(user.id, user.email, user.role)


@router.post("/register", response_model=UserPublic)
async def register(
    user_data: UserCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_optional_user)
):
    """
    Register a new user.

    Only admins can register new users, or if no users exist (first user).

    Args:
        user_data: User registration data
        session: Database session
        current_user: Current authenticated user (optional)

    Returns:
        UserPublic: Created user information

    Raises:
        HTTPException: If registration fails
    """
    # Check if any users exist
    existing_users = session.exec(select(User)).all()
    existing_users_count = len(existing_users)

    # If users exist, only admin can register new users
    if existing_users_count > 0:
        if not current_user or current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can register new users"
            )

    # Check if user already exists
    statement = select(User).where(User.email == user_data.email)
    existing_user = session.exec(statement).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )

    # Create new user
    hashed_password = hash_password(user_data.password)

    # First user becomes admin
    role = user_data.role
    if existing_users_count == 0:
        role = "admin"

    new_user = User(
        email=user_data.email,
        name=user_data.name,
        role=role,
        password_hash=hashed_password,
        disabled=user_data.disabled
    )

    session.add(new_user)
    session.commit()
    session.refresh(new_user)

    # Log user creation
    audit_log = AuditLog(
        user_id=current_user.id if current_user else new_user.id,
        actor=f"user:{current_user.id}" if current_user else f"user:{new_user.id}",
        action=AuditAction.USER_CREATE,
        success=True,
        meta={
            "created_user_id": new_user.id,
            "created_user_email": new_user.email,
            "created_user_role": new_user.role
        }
    )
    session.add(audit_log)
    session.commit()

    return new_user


@router.post("/refresh", response_model=LoginResponse)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    session: Session = Depends(get_session)
):
    """
    Refresh access token using refresh token.

    Args:
        refresh_data: Refresh token request data
        session: Database session

    Returns:
        LoginResponse: New access token and refresh token

    Raises:
        HTTPException: If refresh token is invalid
    """
    # Validate refresh token
    payload = validate_refresh_token(refresh_data.refresh_token)

    user_email = payload.get("sub")
    user_id = payload.get("user_id")

    # Get user from database
    statement = select(User).where(User.email == user_email)
    user = session.exec(statement).first()

    if not user or user.disabled:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or disabled"
        )

    # Create new tokens
    return create_token_response(user.id, user.email, user.role)


@router.get("/me", response_model=UserPublic)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current user information.

    Args:
        current_user: Current authenticated user

    Returns:
        UserPublic: Current user information
    """
    return current_user


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Logout current user.

    Note: With JWT tokens, logout is primarily client-side.
    This endpoint logs the logout action for audit purposes.

    Args:
        current_user: Current authenticated user
        session: Database session

    Returns:
        Dict: Logout confirmation
    """
    # Log logout action
    audit_log = AuditLog(
        user_id=current_user.id,
        actor=f"user:{current_user.id}",
        action=AuditAction.USER_LOGOUT,
        success=True,
        meta={"email": current_user.email}
    )
    session.add(audit_log)
    session.commit()

    return {"message": "Successfully logged out"}


@router.post("/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Change user password.

    Args:
        password_data: Password change request data
        current_user: Current authenticated user
        session: Database session

    Returns:
        Dict: Password change confirmation

    Raises:
        HTTPException: If current password is incorrect
    """
    # Verify current password
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    # Update password
    current_user.password_hash = hash_password(password_data.new_password)
    session.add(current_user)

    # Log password change
    audit_log = AuditLog(
        user_id=current_user.id,
        actor=f"user:{current_user.id}",
        action="user.password_change",
        success=True,
        meta={"email": current_user.email}
    )
    session.add(audit_log)
    session.commit()

    return {"message": "Password changed successfully"}
