"""
Template management API endpoints.

This module provides REST API endpoints for template CRUD operations,
versioning, inheritance, and template library management.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File as FastAPIFile
from sqlmodel import Session

from ..core.database import get_session
from ..core.dependencies import get_current_active_user, require_admin
from ..services.template_service import get_template_service
from ..models.user import User
from ..models.template import (
    TemplatePublic, TemplateWithDetails, TemplateCreate, TemplateUpdate,
    TemplateStatus, TemplateType, TemplatePreviewRequest, TemplatePreviewResponse,
    TemplateVersionResponse, TemplateDiffRequest, TemplateDiffResponse
)

router = APIRouter()
template_service = get_template_service()


@router.post("/", response_model=TemplatePublic)
async def create_template(
    template_data: TemplateCreate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Create new template.
    
    Creates a new contract template with variables, validation rules,
    and business logic. Supports template inheritance.
    
    Args:
        template_data: Template creation data
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        TemplatePublic: Created template information
    """
    return await template_service.create_template(template_data, current_user, session)


@router.get("/{template_id}", response_model=TemplatePublic)
async def get_template(
    template_id: int,
    include_details: bool = Query(False, description="Include detailed information"),
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Get template information.
    
    Retrieves detailed information about a specific template including
    variables, schema, business rules, and inheritance relationships.
    
    Args:
        template_id: Template ID
        include_details: Whether to include detailed information
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        TemplatePublic or TemplateWithDetails: Template information
    """
    return await template_service.get_template(
        template_id, current_user, session, include_details
    )


@router.get("/", response_model=List[TemplatePublic])
async def list_templates(
    template_type: Optional[TemplateType] = Query(None, description="Filter by template type"),
    status: Optional[TemplateStatus] = Query(None, description="Filter by status"),
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search term"),
    include_public: bool = Query(True, description="Include public templates"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results offset"),
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    List templates with filtering.
    
    Retrieves a paginated list of templates with optional filtering
    by type, status, category, or search terms.
    
    Args:
        template_type: Filter by template type
        status: Filter by status
        category: Filter by category
        search: Search term
        include_public: Whether to include public templates
        limit: Maximum results
        offset: Results offset
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        List[TemplatePublic]: List of templates
    """
    return await template_service.list_templates(
        current_user,
        session,
        template_type=template_type,
        status=status,
        category=category,
        search=search,
        include_public=include_public,
        limit=limit,
        offset=offset
    )


@router.put("/{template_id}", response_model=TemplatePublic)
async def update_template(
    template_id: int,
    template_update: TemplateUpdate,
    create_version: bool = Query(True, description="Create new version"),
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Update template information.
    
    Updates template metadata, content, variables, or business rules.
    Optionally creates a new version for change tracking.
    
    Args:
        template_id: Template ID to update
        template_update: Update data
        create_version: Whether to create a new version
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        TemplatePublic: Updated template information
    """
    return await template_service.update_template(
        template_id, template_update, current_user, session, create_version
    )


@router.delete("/{template_id}")
async def delete_template(
    template_id: int,
    soft_delete: bool = Query(True, description="Soft delete (archive) template"),
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Delete template.
    
    Removes template from active use. By default performs soft delete
    (archiving) to preserve data integrity for existing contracts.
    
    Args:
        template_id: Template ID to delete
        soft_delete: Whether to soft delete (archive) or hard delete
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        Dict: Deletion confirmation
    """
    success = await template_service.delete_template(
        template_id, current_user, session, soft_delete
    )
    
    if success:
        return {"message": "Template deleted successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete template"
        )


@router.post("/{template_id}/preview", response_model=TemplatePreviewResponse)
async def preview_template(
    template_id: int,
    preview_request: TemplatePreviewRequest,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Preview template with sample data.
    
    Generates a preview of how the template will render with provided
    variables without creating a permanent contract.
    
    Args:
        template_id: Template ID to preview
        preview_request: Preview parameters
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        TemplatePreviewResponse: Preview content and metadata
    """
    # Override template ID in request
    preview_request.template_id = template_id
    
    from ..services.contract_service import get_contract_service
    contract_service = get_contract_service()
    
    return await contract_service.preview_contract(preview_request, current_user, session)


@router.post("/{template_id}/duplicate", response_model=TemplatePublic)
async def duplicate_template(
    template_id: int,
    new_name: str = Query(..., description="Name for the duplicated template"),
    new_version: str = Query("1.0", description="Version for the duplicated template"),
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Duplicate existing template.
    
    Creates a copy of an existing template with a new name and version.
    Useful for creating variations or new versions of templates.
    
    Args:
        template_id: Template ID to duplicate
        new_name: Name for the duplicated template
        new_version: Version for the duplicated template
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        TemplatePublic: Duplicated template information
    """
    # Get original template
    original = await template_service.get_template(template_id, current_user, session, True)
    
    # Create duplicate data
    duplicate_data = TemplateCreate(
        name=new_name,
        version=new_version,
        template_type=original.template_type,
        status=TemplateStatus.DRAFT,
        html_content=original.html_content,
        description=f"Copy of {original.name}",
        category=original.category,
        tags=original.tags or [],
        supported_formats=original.supported_formats or [],
        variables=original.variables or [],
        schema=original.schema,
        ruleset=original.ruleset,
        conditional_logic=original.conditional_logic,
        business_rules=original.business_rules,
        is_public=False,
        access_level="private"
    )
    
    return await template_service.create_template(duplicate_data, current_user, session)


@router.get("/{template_id}/versions", response_model=List[TemplateVersionResponse])
async def get_template_versions(
    template_id: int,
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results offset"),
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Get template version history.
    
    Retrieves all versions of a template with change summaries
    and metadata for version control.
    
    Args:
        template_id: Template ID
        limit: Maximum results
        offset: Results offset
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        List[TemplateVersionResponse]: Template versions
    """
    # Verify access to template
    await template_service.get_template(template_id, current_user, session)
    
    # Get versions
    from ..models.template import TemplateVersion
    from sqlmodel import select
    
    versions = session.exec(
        select(TemplateVersion).where(TemplateVersion.template_id == template_id)
        .order_by(TemplateVersion.created_at.desc())
        .offset(offset).limit(limit)
    ).all()
    
    return [
        TemplateVersionResponse(
            id=v.id,
            template_id=v.template_id,
            version_number=v.version_number,
            created_at=v.created_at,
            created_by=v.created_by,
            changes_summary=v.changes_summary,
            is_major_version=v.is_major_version,
            rollback_safe=v.rollback_safe,
            change_type=v.change_type
        )
        for v in versions
    ]


@router.post("/{template_id}/versions/{version_id}/rollback", response_model=TemplatePublic)
async def rollback_template_version(
    template_id: int,
    version_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Rollback template to previous version.
    
    Restores template content to a previous version, creating a new
    version entry for the rollback operation.
    
    Args:
        template_id: Template ID
        version_id: Version ID to rollback to
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        TemplatePublic: Updated template information
    """
    # TODO: Implement template rollback functionality
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Template rollback not yet implemented"
    )


@router.post("/{template_id}/diff", response_model=TemplateDiffResponse)
async def compare_template_versions(
    template_id: int,
    diff_request: TemplateDiffRequest,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Compare template versions.
    
    Generates a diff between two versions of a template showing
    changes in content, variables, and configuration.
    
    Args:
        template_id: Template ID
        diff_request: Diff comparison parameters
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        TemplateDiffResponse: Diff comparison results
    """
    # Override template ID in request
    diff_request.template_id = template_id
    
    # TODO: Implement template diff functionality
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Template diff not yet implemented"
    )


@router.get("/categories/list")
async def list_template_categories(
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    List all template categories.
    
    Retrieves a list of all available template categories
    for filtering and organization.
    
    Args:
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        List: Available categories
    """
    from ..models.template import Template
    from sqlmodel import select, func
    
    categories = session.exec(
        select(Template.category, func.count(Template.id).label('count'))
        .where(Template.category.isnot(None))
        .group_by(Template.category)
        .order_by(Template.category)
    ).all()
    
    return [
        {"name": category, "count": count}
        for category, count in categories
        if category
    ]


# Admin endpoints
@router.get("/admin/all", response_model=List[TemplatePublic])
async def admin_list_all_templates(
    limit: int = Query(50, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results offset"),
    current_user: User = Depends(require_admin()),
    session: Session = Depends(get_session)
):
    """
    Admin: List all templates in the system.
    
    Allows administrators to view all templates across all users
    for system management and oversight.
    
    Args:
        limit: Maximum results
        offset: Results offset
        current_user: Current authenticated admin user
        session: Database session
        
    Returns:
        List[TemplatePublic]: List of all templates
    """
    # TODO: Implement admin template listing
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Admin template listing not yet implemented"
    )


@router.put("/admin/{template_id}/status")
async def admin_update_template_status(
    template_id: int,
    new_status: TemplateStatus,
    current_user: User = Depends(require_admin()),
    session: Session = Depends(get_session)
):
    """
    Admin: Update template status.
    
    Allows administrators to change template status for
    system management and content moderation.
    
    Args:
        template_id: Template ID
        new_status: New template status
        current_user: Current authenticated admin user
        session: Database session
        
    Returns:
        Dict: Status update confirmation
    """
    template_update = TemplateUpdate(status=new_status)
    
    await template_service.update_template(
        template_id, template_update, current_user, session, create_version=False
    )
    
    return {"message": f"Template status updated to {new_status.value}"}


# Export router
__all__ = ["router"]
