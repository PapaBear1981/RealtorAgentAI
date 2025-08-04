"""
Admin API endpoints for system administration.

This module provides comprehensive admin management endpoints including
user management, audit trail access, system monitoring, and analytics.
"""

import logging
from typing import List, Dict, Any, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from fastapi.responses import PlainTextResponse, JSONResponse
from sqlmodel import Session

from ..core.dependencies import require_admin, get_session
from ..models.user import User, UserCreate, UserUpdate, UserPublic
from ..models.audit_log import AuditLogFilter, AuditLogPublic
from ..models.template import TemplatePublic, TemplateWithDetails, TemplateStatus, TemplateType
from ..services.admin_service import get_admin_service, AdminService

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/admin", tags=["admin"])

# Get admin service
admin_service = get_admin_service()


# User Management Endpoints
@router.post("/users", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(require_admin()),
    session: Session = Depends(get_session)
):
    """
    Create a new user.

    Requires admin privileges. Creates a new user with the specified
    role and permissions.

    Args:
        user_data: User creation data
        current_user: Current authenticated admin user
        session: Database session

    Returns:
        UserPublic: Created user information
    """
    return await admin_service.create_user(user_data, current_user, session)


@router.get("/users", response_model=Dict[str, Any])
async def list_users(
    role: Optional[str] = Query(None, description="Filter by role"),
    disabled: Optional[bool] = Query(None, description="Filter by disabled status"),
    search: Optional[str] = Query(None, description="Search in name and email"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results offset"),
    current_user: User = Depends(require_admin()),
    session: Session = Depends(get_session)
):
    """
    List users with filtering and pagination.

    Allows administrators to view all users in the system with
    comprehensive filtering options.

    Args:
        role: Filter by user role
        disabled: Filter by disabled status
        search: Search query for name and email
        limit: Maximum results
        offset: Results offset
        current_user: Current authenticated admin user
        session: Database session

    Returns:
        Dict: Users list with metadata
    """
    return await admin_service.list_users(
        current_user, session, role, disabled, search, limit, offset
    )


@router.get("/users/{user_id}", response_model=UserPublic)
async def get_user(
    user_id: int,
    current_user: User = Depends(require_admin()),
    session: Session = Depends(get_session)
):
    """
    Get user details by ID.

    Allows administrators to view detailed information about
    any user in the system.

    Args:
        user_id: User ID to retrieve
        current_user: Current authenticated admin user
        session: Database session

    Returns:
        UserPublic: User information
    """
    return await admin_service.get_user(user_id, current_user, session)


@router.patch("/users/{user_id}", response_model=UserPublic)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(require_admin()),
    session: Session = Depends(get_session)
):
    """
    Update user information.

    Allows administrators to update user details including
    role, status, and profile information.

    Args:
        user_id: User ID to update
        user_data: User update data
        current_user: Current authenticated admin user
        session: Database session

    Returns:
        UserPublic: Updated user information
    """
    return await admin_service.update_user(user_id, user_data, current_user, session)


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_admin()),
    session: Session = Depends(get_session)
):
    """
    Delete a user (soft delete).

    Disables the user account rather than permanently deleting it.
    Administrators cannot delete their own accounts.

    Args:
        user_id: User ID to delete
        current_user: Current authenticated admin user
        session: Database session

    Returns:
        Dict: Deletion confirmation
    """
    success = await admin_service.delete_user(user_id, current_user, session)

    if success:
        return {"message": "User deleted successfully", "user_id": user_id}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user"
        )


# Audit Trail Endpoints
@router.get("/audit-logs", response_model=Dict[str, Any])
async def search_audit_logs(
    deal_id: Optional[int] = Query(None, description="Filter by deal ID"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    actor: Optional[str] = Query(None, description="Filter by actor"),
    action: Optional[str] = Query(None, description="Filter by action"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    success: Optional[bool] = Query(None, description="Filter by success status"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results offset"),
    current_user: User = Depends(require_admin()),
    session: Session = Depends(get_session)
):
    """
    Search audit logs with comprehensive filtering.

    Provides administrators with detailed audit trail information
    for compliance and system monitoring.

    Args:
        deal_id: Filter by deal ID
        user_id: Filter by user ID
        actor: Filter by actor
        action: Filter by action
        resource_type: Filter by resource type
        success: Filter by success status
        start_date: Start date filter
        end_date: End date filter
        limit: Maximum results
        offset: Results offset
        current_user: Current authenticated admin user
        session: Database session

    Returns:
        Dict: Audit logs with metadata
    """
    # Parse dates if provided
    from datetime import datetime

    parsed_start_date = None
    parsed_end_date = None

    if start_date:
        try:
            parsed_start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid start_date format. Use ISO format."
            )

    if end_date:
        try:
            parsed_end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid end_date format. Use ISO format."
            )

    # Create filter object
    filters = AuditLogFilter(
        deal_id=deal_id,
        user_id=user_id,
        actor=actor,
        action=action,
        resource_type=resource_type,
        success=success,
        start_date=parsed_start_date,
        end_date=parsed_end_date
    )

    return await admin_service.search_audit_logs(
        current_user, session, filters, limit, offset
    )


@router.get("/audit-logs/export")
async def export_audit_logs(
    format: str = Query("csv", pattern="^(csv|json)$", description="Export format"),
    deal_id: Optional[int] = Query(None, description="Filter by deal ID"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    actor: Optional[str] = Query(None, description="Filter by actor"),
    action: Optional[str] = Query(None, description="Filter by action"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    success: Optional[bool] = Query(None, description="Filter by success status"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    limit: int = Query(1000, ge=1, le=5000, description="Maximum records to export"),
    current_user: User = Depends(require_admin()),
    session: Session = Depends(get_session)
):
    """
    Export audit logs in CSV or JSON format.

    Allows administrators to export audit trail data for
    external analysis and compliance reporting.

    Args:
        format: Export format (csv or json)
        deal_id: Filter by deal ID
        user_id: Filter by user ID
        actor: Filter by actor
        action: Filter by action
        resource_type: Filter by resource type
        success: Filter by success status
        start_date: Start date filter
        end_date: End date filter
        limit: Maximum records to export
        current_user: Current authenticated admin user
        session: Database session

    Returns:
        Response: Exported data as CSV or JSON
    """
    # Parse dates if provided
    from datetime import datetime

    parsed_start_date = None
    parsed_end_date = None

    if start_date:
        try:
            parsed_start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid start_date format. Use ISO format."
            )

    if end_date:
        try:
            parsed_end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid end_date format. Use ISO format."
            )

    # Create filter object
    filters = AuditLogFilter(
        deal_id=deal_id,
        user_id=user_id,
        actor=actor,
        action=action,
        resource_type=resource_type,
        success=success,
        start_date=parsed_start_date,
        end_date=parsed_end_date
    )

    # Export data
    exported_data = await admin_service.export_audit_logs(
        current_user, session, filters, format, limit
    )

    if format == "csv":
        return PlainTextResponse(
            content=exported_data,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=audit_logs.csv"}
        )
    else:
        return JSONResponse(
            content=exported_data,
            headers={"Content-Disposition": "attachment; filename=audit_logs.json"}
        )


# System Monitoring Endpoints
@router.get("/health", response_model=Dict[str, Any])
async def get_system_health(
    current_user: User = Depends(require_admin()),
    session: Session = Depends(get_session)
):
    """
    Get comprehensive system health metrics.

    Provides administrators with real-time system health information
    including database status, user activity, and performance metrics.

    Args:
        current_user: Current authenticated admin user
        session: Database session

    Returns:
        Dict: System health information
    """
    return await admin_service.get_system_health(current_user, session)


@router.get("/analytics", response_model=Dict[str, Any])
async def get_usage_analytics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(require_admin()),
    session: Session = Depends(get_session)
):
    """
    Get usage analytics for the specified period.

    Provides comprehensive analytics including user activity,
    template usage, contract statistics, and error analytics.

    Args:
        days: Number of days to analyze
        current_user: Current authenticated admin user
        session: Database session

    Returns:
        Dict: Usage analytics
    """
    return await admin_service.get_usage_analytics(current_user, session, days)


# Configuration Management Endpoints
@router.get("/config", response_model=Dict[str, Any])
async def get_system_configuration(
    current_user: User = Depends(require_admin()),
    session: Session = Depends(get_session)
):
    """
    Get system configuration settings.

    Returns current system configuration including environment
    variables and application settings.

    Args:
        current_user: Current authenticated admin user
        session: Database session

    Returns:
        Dict: System configuration
    """
    from ..core.config import get_settings

    settings = get_settings()

    # Return safe configuration (no secrets)
    config = {
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
        "database_url": "***HIDDEN***",
        "jwt_settings": {
            "algorithm": settings.JWT_ALGORITHM,
            "access_token_expire_minutes": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
            "refresh_token_expire_days": settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        },
        "cors_settings": {
            "allow_origins": settings.ALLOWED_HOSTS,
            "allow_credentials": True  # Hardcoded as configured in main.py
        },
        "file_settings": {
            "max_file_size": settings.MAX_FILE_SIZE,
            "allowed_file_types": settings.ALLOWED_FILE_TYPES
        },
        "rate_limiting": {
            "enabled": True,
            "requests_per_minute": 60
        }
    }

    # Log configuration access
    from ..models.audit_log import AuditLog
    audit_log = AuditLog(
        user_id=current_user.id,
        actor=f"admin:{current_user.id}",
        action="CONFIG_ACCESS",
        success=True,
        meta={"accessed_sections": list(config.keys())}
    )
    session.add(audit_log)
    session.commit()

    return config


@router.patch("/config", response_model=Dict[str, Any])
async def update_system_configuration(
    config_updates: Dict[str, Any],
    current_user: User = Depends(require_admin()),
    session: Session = Depends(get_session)
):
    """
    Update system configuration settings.

    Allows administrators to update certain system configuration
    settings. Some settings require application restart.

    Args:
        config_updates: Configuration updates
        current_user: Current authenticated admin user
        session: Database session

    Returns:
        Dict: Update confirmation
    """
    # For now, this is a placeholder - actual config updates would
    # require more sophisticated handling and validation

    # Log configuration update attempt
    from ..models.audit_log import AuditLog
    audit_log = AuditLog(
        user_id=current_user.id,
        actor=f"admin:{current_user.id}",
        action="CONFIG_UPDATE",
        success=False,
        error_message="Configuration updates not yet implemented",
        meta={"attempted_updates": list(config_updates.keys())}
    )
    session.add(audit_log)
    session.commit()

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Configuration updates not yet implemented"
    )


# Model Routing and AI Configuration Endpoints
@router.get("/models", response_model=Dict[str, Any])
async def list_ai_models(
    current_user: User = Depends(require_admin()),
    session: Session = Depends(get_session)
):
    """
    List available AI models and their configurations.

    Returns information about available LLM models, their
    capabilities, and current routing configuration.

    Args:
        current_user: Current authenticated admin user
        session: Database session

    Returns:
        Dict: AI models information
    """
    # Placeholder for AI model management
    models_info = {
        "available_models": [
            {
                "id": "gpt-4",
                "name": "GPT-4",
                "provider": "openai",
                "capabilities": ["text_generation", "contract_analysis"],
                "status": "active",
                "cost_per_token": 0.00003
            },
            {
                "id": "claude-3-sonnet",
                "name": "Claude 3 Sonnet",
                "provider": "anthropic",
                "capabilities": ["text_generation", "contract_analysis", "legal_review"],
                "status": "active",
                "cost_per_token": 0.000015
            }
        ],
        "routing_config": {
            "default_model": "gpt-4",
            "fallback_model": "claude-3-sonnet",
            "routing_rules": [
                {
                    "condition": "contract_analysis",
                    "model": "claude-3-sonnet",
                    "reason": "Better legal understanding"
                }
            ]
        },
        "usage_stats": {
            "total_requests_24h": 0,
            "total_tokens_24h": 0,
            "cost_24h": 0.0
        }
    }

    # Log model access
    from ..models.audit_log import AuditLog
    audit_log = AuditLog(
        user_id=current_user.id,
        actor=f"admin:{current_user.id}",
        action="MODEL_LIST",
        success=True,
        meta={"model_count": len(models_info["available_models"])}
    )
    session.add(audit_log)
    session.commit()

    return models_info


@router.patch("/models/routing", response_model=Dict[str, Any])
async def update_model_routing(
    routing_config: Dict[str, Any],
    current_user: User = Depends(require_admin()),
    session: Session = Depends(get_session)
):
    """
    Update AI model routing configuration.

    Allows administrators to configure how requests are routed
    to different AI models based on use case and requirements.

    Args:
        routing_config: New routing configuration
        current_user: Current authenticated admin user
        session: Database session

    Returns:
        Dict: Update confirmation
    """
    # Log routing update attempt
    from ..models.audit_log import AuditLog
    audit_log = AuditLog(
        user_id=current_user.id,
        actor=f"admin:{current_user.id}",
        action="MODEL_ROUTING_UPDATE",
        success=False,
        error_message="Model routing updates not yet implemented",
        meta={"attempted_config": routing_config}
    )
    session.add(audit_log)
    session.commit()

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Model routing updates not yet implemented"
    )


# Template Management Endpoints
@router.get("/templates", response_model=Dict[str, Any])
async def list_templates(
    status: Optional[TemplateStatus] = Query(None, description="Filter by template status"),
    template_type: Optional[TemplateType] = Query(None, description="Filter by template type"),
    search: Optional[str] = Query(None, description="Search in name and description"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results offset"),
    current_user: User = Depends(require_admin()),
    session: Session = Depends(get_session)
):
    """
    List templates with filtering and pagination.

    Allows administrators to view all templates in the system with
    comprehensive filtering options for management and oversight.

    Args:
        status: Filter by template status
        template_type: Filter by template type
        search: Search query for name and description
        limit: Maximum results
        offset: Results offset
        current_user: Current authenticated admin user
        session: Database session

    Returns:
        Dict: Templates list with metadata
    """
    return await admin_service.list_templates(
        current_user, session, status, template_type, search, limit, offset
    )


@router.get("/templates/{template_id}", response_model=Union[TemplatePublic, TemplateWithDetails])
async def get_template(
    template_id: int,
    include_details: bool = Query(False, description="Include detailed template information"),
    current_user: User = Depends(require_admin()),
    session: Session = Depends(get_session)
):
    """
    Get template details by ID.

    Allows administrators to view detailed information about
    any template in the system.

    Args:
        template_id: Template ID to retrieve
        include_details: Whether to include detailed information
        current_user: Current authenticated admin user
        session: Database session

    Returns:
        Union[TemplatePublic, TemplateWithDetails]: Template information
    """
    return await admin_service.get_template(template_id, current_user, session, include_details)


@router.patch("/templates/{template_id}/status", response_model=TemplatePublic)
async def update_template_status(
    template_id: int,
    status_update: Dict[str, TemplateStatus],
    current_user: User = Depends(require_admin()),
    session: Session = Depends(get_session)
):
    """
    Update template status (activate, deactivate, archive).

    Allows administrators to change template status for
    lifecycle management and access control.

    Args:
        template_id: Template ID to update
        status_update: New status information
        current_user: Current authenticated admin user
        session: Database session

    Returns:
        TemplatePublic: Updated template information
    """
    if "status" not in status_update:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status field is required"
        )

    new_status = status_update["status"]
    return await admin_service.update_template_status(template_id, new_status, current_user, session)


@router.get("/templates/{template_id}/analytics", response_model=Dict[str, Any])
async def get_template_analytics(
    template_id: int,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(require_admin()),
    session: Session = Depends(get_session)
):
    """
    Get template usage analytics.

    Provides comprehensive analytics about template usage including
    contract generation statistics and usage patterns.

    Args:
        template_id: Template ID to analyze
        days: Number of days to analyze
        current_user: Current authenticated admin user
        session: Database session

    Returns:
        Dict: Template usage analytics
    """
    return await admin_service.get_template_usage_analytics(template_id, current_user, session, days)


# Export router
__all__ = ["router"]
