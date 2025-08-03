"""
Template management service layer.

This module provides high-level template operations including CRUD,
versioning, inheritance, validation, and template library management.
"""

import logging
import json
import difflib
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from sqlmodel import Session, select, and_, or_, func
from fastapi import HTTPException, status

from ..core.database import get_session_context
from ..core.storage import get_storage_client, StorageError
from ..core.template_engine import get_template_engine, TemplateRenderingError
from ..models.template import (
    Template, TemplateCreate, TemplateUpdate, TemplatePublic, TemplateWithDetails,
    TemplateVersion, TemplateVariable, TemplateStatus, TemplateType,
    TemplateVersionResponse, TemplateDiffRequest, TemplateDiffResponse,
    TemplatePreviewRequest, TemplatePreviewResponse
)
from ..models.user import User
from ..models.audit_log import AuditLog, AuditAction

logger = logging.getLogger(__name__)


class TemplateManagementError(Exception):
    """Exception raised during template management operations."""
    pass


class TemplateVersioningError(Exception):
    """Exception raised during template versioning operations."""
    pass


class TemplateService:
    """
    High-level template management service.

    Provides comprehensive template operations including CRUD, versioning,
    inheritance, validation, and template library management.
    """

    def __init__(self):
        """Initialize template service."""
        self.storage_client = get_storage_client()
        self.template_engine = get_template_engine()

    async def create_template(
        self,
        template_data: TemplateCreate,
        user: User,
        session: Session
    ) -> TemplatePublic:
        """
        Create new template.

        Args:
            template_data: Template creation data
            user: User creating the template
            session: Database session

        Returns:
            TemplatePublic: Created template information
        """
        try:
            # Validate template data
            await self._validate_template_data(template_data, session)

            # Handle template inheritance
            if template_data.parent_template_id:
                parent_template = session.get(Template, template_data.parent_template_id)
                if not parent_template:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Parent template not found"
                    )

                # Inherit properties from parent
                template_data = await self._inherit_from_parent(template_data, parent_template)

            # Create template record
            template = Template(
                **template_data.dict(exclude={'variables'}),
                created_by=user.id,
                created_at=datetime.utcnow(),
                is_current_version=True
            )

            # Handle variables
            if template_data.variables:
                template.variables = [var.dict() for var in template_data.variables]

            session.add(template)
            session.commit()
            session.refresh(template)

            # Create initial version
            await self._create_template_version(
                template,
                user,
                "Initial template creation",
                is_major=True,
                session=session
            )

            # Log creation
            audit_log = AuditLog(
                user_id=user.id,
                actor=f"user:{user.id}",
                action=AuditAction.TEMPLATE_CREATED,
                success=True,
                meta={
                    "template_id": template.id,
                    "template_name": template.name,
                    "template_type": template.template_type.value
                }
            )
            session.add(audit_log)
            session.commit()

            return self._to_public_model(template)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Template creation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create template"
            )

    async def get_template(
        self,
        template_id: int,
        user: User,
        session: Session,
        include_details: bool = False
    ) -> TemplatePublic:
        """
        Get template information.

        Args:
            template_id: Template ID
            user: User requesting template
            session: Database session
            include_details: Whether to include detailed information

        Returns:
            TemplatePublic: Template information
        """
        try:
            # Get template
            template = session.get(Template, template_id)
            if not template:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Template not found"
                )

            # Check access permissions
            if not await self._check_template_access(template, user, session):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied"
                )

            if include_details:
                return await self._to_detailed_model(template, session)
            else:
                return self._to_public_model(template)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Get template failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get template"
            )

    async def list_templates(
        self,
        user: User,
        session: Session,
        template_type: Optional[TemplateType] = None,
        status: Optional[TemplateStatus] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        include_public: bool = True,
        limit: int = 50,
        offset: int = 0
    ) -> List[TemplatePublic]:
        """
        List templates with filtering.

        Args:
            user: User requesting templates
            session: Database session
            template_type: Filter by template type
            status: Filter by status
            category: Filter by category
            search: Search term
            include_public: Whether to include public templates
            limit: Maximum results
            offset: Results offset

        Returns:
            List[TemplatePublic]: List of templates
        """
        try:
            # Build query
            query = select(Template)

            # Access control
            if include_public:
                query = query.where(
                    or_(
                        Template.created_by == user.id,
                        Template.is_public == True,
                        Template.access_level == "public"
                    )
                )
            else:
                query = query.where(Template.created_by == user.id)

            # Apply filters
            if template_type:
                query = query.where(Template.template_type == template_type)

            if status:
                query = query.where(Template.status == status)

            if category:
                query = query.where(Template.category == category)

            if search:
                search_term = f"%{search}%"
                query = query.where(
                    or_(
                        Template.name.ilike(search_term),
                        Template.description.ilike(search_term)
                    )
                )

            # Apply ordering and pagination
            query = query.order_by(Template.created_at.desc()).offset(offset).limit(limit)

            # Execute query
            templates = session.exec(query).all()

            return [self._to_public_model(template) for template in templates]

        except Exception as e:
            logger.error(f"List templates failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to list templates"
            )

    async def update_template(
        self,
        template_id: int,
        template_update: TemplateUpdate,
        user: User,
        session: Session,
        create_version: bool = True
    ) -> TemplatePublic:
        """
        Update template information.

        Args:
            template_id: Template ID to update
            template_update: Update data
            user: User performing update
            session: Database session
            create_version: Whether to create a new version

        Returns:
            TemplatePublic: Updated template information
        """
        try:
            # Get template
            template = session.get(Template, template_id)
            if not template:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Template not found"
                )

            # Check permissions
            if not await self._check_template_edit_access(template, user, session):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied"
                )

            # Store original content for version tracking
            original_content = {
                'html_content': template.html_content,
                'variables': template.variables,
                'schema': template.schema,
                'ruleset': template.ruleset,
                'conditional_logic': template.conditional_logic,
                'business_rules': template.business_rules
            }

            # Update template
            update_data = template_update.dict(exclude_unset=True, exclude={'variables'})
            for field, value in update_data.items():
                setattr(template, field, value)

            # Handle variables separately
            if template_update.variables is not None:
                template.variables = [var.dict() for var in template_update.variables]

            template.updated_at = datetime.utcnow()
            template.updated_by = user.id

            session.add(template)
            session.commit()
            session.refresh(template)

            # Create version if content changed and requested
            if create_version and self._has_content_changed(original_content, template):
                change_summary = template_update.version_notes or "Template updated"
                await self._create_template_version(
                    template,
                    user,
                    change_summary,
                    is_major=self._is_major_change(original_content, template),
                    session=session
                )

            # Log update
            audit_log = AuditLog(
                user_id=user.id,
                actor=f"user:{user.id}",
                action=AuditAction.TEMPLATE_UPDATED,
                success=True,
                meta={
                    "template_id": template.id,
                    "updated_fields": list(update_data.keys())
                }
            )
            session.add(audit_log)
            session.commit()

            return self._to_public_model(template)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Template update failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update template"
            )

    async def delete_template(
        self,
        template_id: int,
        user: User,
        session: Session,
        soft_delete: bool = True
    ) -> bool:
        """
        Delete template.

        Args:
            template_id: Template ID to delete
            user: User requesting deletion
            session: Database session
            soft_delete: Whether to soft delete (archive) or hard delete

        Returns:
            bool: True if deleted successfully
        """
        try:
            # Get template
            template = session.get(Template, template_id)
            if not template:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Template not found"
                )

            # Check permissions
            if not await self._check_template_delete_access(template, user, session):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied"
                )

            # Check if template is in use
            from ..models.contract import Contract
            contracts_count = session.exec(
                select(func.count(Contract.id)).where(Contract.template_id == template_id)
            ).first() or 0

            if contracts_count > 0 and not soft_delete:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot delete template that is in use by contracts"
                )

            if soft_delete:
                # Soft delete - archive template
                template.status = TemplateStatus.ARCHIVED
                template.updated_at = datetime.utcnow()
                template.updated_by = user.id
                session.add(template)
                session.commit()
            else:
                # Hard delete - remove from database
                session.delete(template)
                session.commit()

            # Log deletion
            audit_log = AuditLog(
                user_id=user.id,
                actor=f"user:{user.id}",
                action=AuditAction.TEMPLATE_DELETED,
                success=True,
                meta={
                    "template_id": template.id,
                    "template_name": template.name,
                    "soft_delete": soft_delete,
                    "deleted_by": user.id
                }
            )
            session.add(audit_log)
            session.commit()

            return True

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Template deletion failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete template"
            )

    # Helper methods
    async def _validate_template_data(self, template_data: TemplateCreate, session: Session):
        """Validate template creation data."""
        # Check for duplicate names in same category
        existing = session.exec(
            select(Template).where(
                and_(
                    Template.name == template_data.name,
                    Template.category == template_data.category,
                    Template.status != TemplateStatus.ARCHIVED
                )
            )
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Template with this name already exists in category"
            )

    async def _inherit_from_parent(
        self,
        template_data: TemplateCreate,
        parent_template: Template
    ) -> TemplateCreate:
        """Inherit properties from parent template."""
        # Inherit basic properties if not specified
        if not template_data.description:
            template_data.description = parent_template.description

        if not template_data.category:
            template_data.category = parent_template.category

        if not template_data.tags:
            template_data.tags = parent_template.tags or []

        # Inherit variables if not specified
        if not template_data.variables and parent_template.variables:
            template_data.variables = [
                TemplateVariable(**var) for var in parent_template.variables
            ]

        # Inherit schema and rules
        if not template_data.schema:
            template_data.schema = parent_template.schema

        if not template_data.ruleset:
            template_data.ruleset = parent_template.ruleset

        if not template_data.business_rules:
            template_data.business_rules = parent_template.business_rules

        return template_data

    async def _create_template_version(
        self,
        template: Template,
        user: User,
        change_summary: str,
        is_major: bool = False,
        session: Session = None
    ):
        """Create a new template version."""
        try:
            # Create content snapshot
            content_snapshot = {
                'name': template.name,
                'version': template.version,
                'html_content': template.html_content,
                'variables': template.variables,
                'schema': template.schema,
                'ruleset': template.ruleset,
                'conditional_logic': template.conditional_logic,
                'business_rules': template.business_rules,
                'supported_formats': [f.value for f in template.supported_formats] if template.supported_formats else []
            }

            # Create version record
            version = TemplateVersion(
                template_id=template.id,
                version_number=template.version,
                created_by=user.id,
                content_snapshot=content_snapshot,
                changes_summary=change_summary,
                is_major_version=is_major,
                change_type="major" if is_major else "minor"
            )

            session.add(version)
            session.commit()

        except Exception as e:
            logger.error(f"Failed to create template version: {e}")

    def _has_content_changed(self, original_content: Dict[str, Any], template: Template) -> bool:
        """Check if template content has changed."""
        current_content = {
            'html_content': template.html_content,
            'variables': template.variables,
            'schema': template.schema,
            'ruleset': template.ruleset,
            'conditional_logic': template.conditional_logic,
            'business_rules': template.business_rules
        }

        return original_content != current_content

    def _is_major_change(self, original_content: Dict[str, Any], template: Template) -> bool:
        """Determine if changes constitute a major version."""
        # Consider it major if variables structure changed significantly
        original_vars = original_content.get('variables', [])
        current_vars = template.variables or []

        # Check if required variables were added/removed
        original_required = {v.get('name') for v in original_vars if v.get('required')}
        current_required = {v.get('name') for v in current_vars if v.get('required')}

        if original_required != current_required:
            return True

        # Check if business rules changed significantly
        if original_content.get('business_rules') != template.business_rules:
            return True

        return False

    async def _check_template_access(self, template: Template, user: User, session: Session) -> bool:
        """Check if user has access to template."""
        # Owner has access
        if template.created_by == user.id:
            return True

        # Admin has access
        if user.role == "admin":
            return True

        # Public templates are accessible
        if template.is_public or template.access_level == "public":
            return True

        # Team access (implement team-based access control as needed)
        if template.access_level == "team":
            # For now, allow access - implement team membership check
            return True

        return False

    async def _check_template_edit_access(self, template: Template, user: User, session: Session) -> bool:
        """Check if user can edit template."""
        # Only owner or admin can edit
        return template.created_by == user.id or user.role == "admin"

    async def _check_template_delete_access(self, template: Template, user: User, session: Session) -> bool:
        """Check if user can delete template."""
        # Only owner or admin can delete
        return template.created_by == user.id or user.role == "admin"

    def _to_public_model(self, template: Template) -> TemplatePublic:
        """Convert template to public model."""
        return TemplatePublic(
            id=template.id,
            name=template.name,
            version=template.version,
            template_type=template.template_type,
            status=template.status,
            docx_key=template.docx_key,
            html_content=template.html_content,
            description=template.description,
            category=template.category,
            tags=template.tags or [],
            supported_formats=template.supported_formats or [],
            created_at=template.created_at,
            updated_at=template.updated_at,
            parent_template_id=template.parent_template_id,
            usage_count=template.usage_count,
            last_used=template.last_used,
            success_rate=template.success_rate,
            is_current_version=template.is_current_version,
            is_public=template.is_public,
            access_level=template.access_level
        )

    async def _to_detailed_model(self, template: Template, session: Session) -> TemplateWithDetails:
        """Convert template to detailed model."""
        public_model = self._to_public_model(template)

        # Get parent template if exists
        parent_template = None
        if template.parent_template_id:
            parent = session.get(Template, template.parent_template_id)
            if parent:
                parent_template = self._to_public_model(parent)

        # Get child templates
        child_templates = session.exec(
            select(Template).where(Template.parent_template_id == template.id)
        ).all()

        # Convert variables
        variables = []
        if template.variables:
            variables = [TemplateVariable(**var) for var in template.variables]

        return TemplateWithDetails(
            **public_model.dict(),
            variables=variables,
            schema=template.schema,
            ruleset=template.ruleset,
            conditional_logic=template.conditional_logic,
            business_rules=template.business_rules,
            parent_template=parent_template,
            child_templates=[self._to_public_model(child) for child in child_templates]
        )


# Global template service instance
_template_service: Optional[TemplateService] = None


def get_template_service() -> TemplateService:
    """
    Get global template service instance.

    Returns:
        TemplateService: Configured template service
    """
    global _template_service

    if _template_service is None:
        _template_service = TemplateService()

    return _template_service


# Export service
__all__ = [
    "TemplateService",
    "TemplateManagementError",
    "TemplateVersioningError",
    "get_template_service",
]
