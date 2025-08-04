"""
Database Access Tools for AI Agents.

This module provides specialized tools for agents to interact with the database
using existing models (contracts, templates, files, users) for agent operations.
"""

from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc

import structlog
from pydantic import BaseModel, Field

from .base import BaseTool, ToolInput, ToolResult, ToolCategory
from ...core.database import get_session
from ...models.contract import Contract
from ...models.template import Template
from ...models.file import File
from ...models.user import User
from ...core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class DatabaseQueryInput(ToolInput):
    """Input for database query operations."""
    model_type: str = Field(..., description="Type of model to query (contract, template, file, user)")
    query_params: Dict[str, Any] = Field(default_factory=dict, description="Query parameters")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Filter conditions")
    limit: int = Field(default=100, description="Maximum number of results")
    offset: int = Field(default=0, description="Offset for pagination")


class DatabaseCreateInput(ToolInput):
    """Input for database create operations."""
    model_type: str = Field(..., description="Type of model to create")
    data: Dict[str, Any] = Field(..., description="Data for creating the model")


class DatabaseUpdateInput(ToolInput):
    """Input for database update operations."""
    model_type: str = Field(..., description="Type of model to update")
    record_id: Union[str, int] = Field(..., description="ID of the record to update")
    data: Dict[str, Any] = Field(..., description="Data for updating the model")


class ContractDatabaseTool(BaseTool):
    """Tool for accessing contract data from the database."""

    @property
    def name(self) -> str:
        return "contract_db_access"

    @property
    def description(self) -> str:
        return "Access and manage contract data from the database"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.WORKFLOW_MANAGEMENT

    async def execute(self, input_data: DatabaseQueryInput) -> ToolResult:
        """Execute contract database operations."""
        try:
            with get_session() as db:
                if input_data.query_params.get("operation") == "create":
                    result = await self._create_contract(db, input_data)
                elif input_data.query_params.get("operation") == "update":
                    result = await self._update_contract(db, input_data)
                elif input_data.query_params.get("operation") == "delete":
                    result = await self._delete_contract(db, input_data)
                else:
                    result = await self._query_contracts(db, input_data)

            return ToolResult(
                success=True,
                data=result,
                metadata={
                    "operation": input_data.query_params.get("operation", "query"),
                    "timestamp": datetime.utcnow().isoformat(),
                    "user_id": input_data.user_id
                },
                execution_time=0.0,
                tool_name=self.name
            )

        except Exception as e:
            return ToolResult(
                success=False,
                errors=[f"Contract database operation failed: {str(e)}"],
                execution_time=0.0,
                tool_name=self.name
            )

    async def _query_contracts(self, db: Session, input_data: DatabaseQueryInput) -> Dict[str, Any]:
        """Query contracts from database."""
        query = db.query(Contract)

        # Apply filters
        filters = input_data.filters
        if filters.get("user_id"):
            query = query.filter(Contract.user_id == filters["user_id"])
        if filters.get("status"):
            query = query.filter(Contract.status == filters["status"])
        if filters.get("template_id"):
            query = query.filter(Contract.template_id == filters["template_id"])
        if filters.get("created_after"):
            query = query.filter(Contract.created_at >= filters["created_after"])
        if filters.get("created_before"):
            query = query.filter(Contract.created_at <= filters["created_before"])

        # Apply ordering
        order_by = input_data.query_params.get("order_by", "created_at")
        order_dir = input_data.query_params.get("order_dir", "desc")

        if hasattr(Contract, order_by):
            if order_dir.lower() == "asc":
                query = query.order_by(asc(getattr(Contract, order_by)))
            else:
                query = query.order_by(desc(getattr(Contract, order_by)))

        # Apply pagination
        total_count = query.count()
        contracts = query.offset(input_data.offset).limit(input_data.limit).all()

        return {
            "contracts": [self._serialize_contract(contract) for contract in contracts],
            "total_count": total_count,
            "limit": input_data.limit,
            "offset": input_data.offset,
            "has_more": total_count > (input_data.offset + input_data.limit)
        }

    async def _create_contract(self, db: Session, input_data: DatabaseQueryInput) -> Dict[str, Any]:
        """Create a new contract."""
        contract_data = input_data.query_params.get("data", {})

        contract = Contract(
            title=contract_data.get("title", "New Contract"),
            content=contract_data.get("content", ""),
            status=contract_data.get("status", "draft"),
            template_id=contract_data.get("template_id"),
            user_id=input_data.user_id,
            metadata=contract_data.get("metadata", {})
        )

        db.add(contract)
        db.commit()
        db.refresh(contract)

        return {
            "contract": self._serialize_contract(contract),
            "operation": "created"
        }

    async def _update_contract(self, db: Session, input_data: DatabaseQueryInput) -> Dict[str, Any]:
        """Update an existing contract."""
        contract_id = input_data.query_params.get("contract_id")
        update_data = input_data.query_params.get("data", {})

        contract = db.query(Contract).filter(Contract.id == contract_id).first()
        if not contract:
            raise ValueError(f"Contract with ID {contract_id} not found")

        # Update fields
        for field, value in update_data.items():
            if hasattr(contract, field):
                setattr(contract, field, value)

        contract.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(contract)

        return {
            "contract": self._serialize_contract(contract),
            "operation": "updated"
        }

    async def _delete_contract(self, db: Session, input_data: DatabaseQueryInput) -> Dict[str, Any]:
        """Delete a contract."""
        contract_id = input_data.query_params.get("contract_id")

        contract = db.query(Contract).filter(Contract.id == contract_id).first()
        if not contract:
            raise ValueError(f"Contract with ID {contract_id} not found")

        db.delete(contract)
        db.commit()

        return {
            "contract_id": contract_id,
            "operation": "deleted"
        }

    def _serialize_contract(self, contract: Contract) -> Dict[str, Any]:
        """Serialize contract model to dictionary."""
        return {
            "id": contract.id,
            "title": contract.title,
            "content": contract.content,
            "status": contract.status,
            "template_id": contract.template_id,
            "user_id": contract.user_id,
            "metadata": contract.metadata,
            "created_at": contract.created_at.isoformat() if contract.created_at else None,
            "updated_at": contract.updated_at.isoformat() if contract.updated_at else None
        }


class TemplateDatabaseTool(BaseTool):
    """Tool for accessing template data from the database."""

    @property
    def name(self) -> str:
        return "template_db_access"

    @property
    def description(self) -> str:
        return "Access and manage template data from the database"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.WORKFLOW_MANAGEMENT

    async def execute(self, input_data: DatabaseQueryInput) -> ToolResult:
        """Execute template database operations."""
        try:
            with get_session() as db:
                if input_data.query_params.get("operation") == "query":
                    result = await self._query_templates(db, input_data)
                elif input_data.query_params.get("operation") == "get_by_id":
                    result = await self._get_template_by_id(db, input_data)
                elif input_data.query_params.get("operation") == "search":
                    result = await self._search_templates(db, input_data)
                else:
                    result = await self._query_templates(db, input_data)

            return ToolResult(
                success=True,
                data=result,
                metadata={
                    "operation": input_data.query_params.get("operation", "query"),
                    "timestamp": datetime.utcnow().isoformat(),
                    "user_id": input_data.user_id
                },
                execution_time=0.0,
                tool_name=self.name
            )

        except Exception as e:
            return ToolResult(
                success=False,
                errors=[f"Template database operation failed: {str(e)}"],
                execution_time=0.0,
                tool_name=self.name
            )


    async def _query_templates(self, db: Session, input_data: DatabaseQueryInput) -> Dict[str, Any]:
        """Query templates from database."""
        query = db.query(Template)

        # Apply filters
        filters = input_data.filters
        if filters.get("category"):
            query = query.filter(Template.category == filters["category"])
        if filters.get("is_active") is not None:
            query = query.filter(Template.is_active == filters["is_active"])
        if filters.get("user_id"):
            query = query.filter(Template.user_id == filters["user_id"])

        # Apply ordering
        query = query.order_by(desc(Template.created_at))

        # Apply pagination
        total_count = query.count()
        templates = query.offset(input_data.offset).limit(input_data.limit).all()

        return {
            "templates": [self._serialize_template(template) for template in templates],
            "total_count": total_count,
            "limit": input_data.limit,
            "offset": input_data.offset
        }

    async def _get_template_by_id(self, db: Session, input_data: DatabaseQueryInput) -> Dict[str, Any]:
        """Get a specific template by ID."""
        template_id = input_data.query_params.get("template_id")

        template = db.query(Template).filter(Template.id == template_id).first()
        if not template:
            raise ValueError(f"Template with ID {template_id} not found")

        return {
            "template": self._serialize_template(template, include_content=True)
        }

    async def _search_templates(self, db: Session, input_data: DatabaseQueryInput) -> Dict[str, Any]:
        """Search templates by name or description."""
        search_term = input_data.query_params.get("search_term", "")

        query = db.query(Template).filter(
            or_(
                Template.name.ilike(f"%{search_term}%"),
                Template.description.ilike(f"%{search_term}%")
            )
        )

        templates = query.limit(input_data.limit).all()

        return {
            "templates": [self._serialize_template(template) for template in templates],
            "search_term": search_term,
            "count": len(templates)
        }

    def _serialize_template(self, template: Template, include_content: bool = False) -> Dict[str, Any]:
        """Serialize template model to dictionary."""
        data = {
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "category": template.category,
            "is_active": template.is_active,
            "user_id": template.user_id,
            "created_at": template.created_at.isoformat() if template.created_at else None,
            "updated_at": template.updated_at.isoformat() if template.updated_at else None
        }

        if include_content:
            data.update({
                "content": template.content,
                "variables": template.variables,
                "metadata": template.metadata
            })

        return data


class FileDatabaseTool(BaseTool):
    """Tool for accessing file data from the database."""

    @property
    def name(self) -> str:
        return "file_db_access"

    @property
    def description(self) -> str:
        return "Access and manage file metadata from the database"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.DOCUMENT_PROCESSING

    async def execute(self, input_data: DatabaseQueryInput) -> ToolResult:
        """Execute file database operations."""
        try:
            with get_session() as db:
                if input_data.query_params.get("operation") == "query":
                    result = await self._query_files(db, input_data)
                elif input_data.query_params.get("operation") == "get_by_id":
                    result = await self._get_file_by_id(db, input_data)
                elif input_data.query_params.get("operation") == "update_metadata":
                    result = await self._update_file_metadata(db, input_data)
                else:
                    result = await self._query_files(db, input_data)

            return ToolResult(
                success=True,
                data=result,
                metadata={
                    "operation": input_data.query_params.get("operation", "query"),
                    "timestamp": datetime.utcnow().isoformat(),
                    "user_id": input_data.user_id
                },
                execution_time=0.0,
                tool_name=self.name
            )

        except Exception as e:
            return ToolResult(
                success=False,
                errors=[f"File database operation failed: {str(e)}"],
                execution_time=0.0,
                tool_name=self.name
            )


    async def _query_files(self, db: Session, input_data: DatabaseQueryInput) -> Dict[str, Any]:
        """Query files from database."""
        query = db.query(File)

        # Apply filters
        filters = input_data.filters
        if filters.get("user_id"):
            query = query.filter(File.user_id == filters["user_id"])
        if filters.get("file_type"):
            query = query.filter(File.file_type == filters["file_type"])
        if filters.get("status"):
            query = query.filter(File.status == filters["status"])

        # Apply ordering
        query = query.order_by(desc(File.created_at))

        # Apply pagination
        total_count = query.count()
        files = query.offset(input_data.offset).limit(input_data.limit).all()

        return {
            "files": [self._serialize_file(file) for file in files],
            "total_count": total_count,
            "limit": input_data.limit,
            "offset": input_data.offset
        }

    async def _get_file_by_id(self, db: Session, input_data: DatabaseQueryInput) -> Dict[str, Any]:
        """Get a specific file by ID."""
        file_id = input_data.query_params.get("file_id")

        file = db.query(File).filter(File.id == file_id).first()
        if not file:
            raise ValueError(f"File with ID {file_id} not found")

        return {
            "file": self._serialize_file(file, include_metadata=True)
        }

    async def _update_file_metadata(self, db: Session, input_data: DatabaseQueryInput) -> Dict[str, Any]:
        """Update file metadata."""
        file_id = input_data.query_params.get("file_id")
        metadata_updates = input_data.query_params.get("metadata", {})

        file = db.query(File).filter(File.id == file_id).first()
        if not file:
            raise ValueError(f"File with ID {file_id} not found")

        # Update metadata
        if file.metadata:
            file.metadata.update(metadata_updates)
        else:
            file.metadata = metadata_updates

        file.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(file)

        return {
            "file": self._serialize_file(file, include_metadata=True),
            "operation": "metadata_updated"
        }

    def _serialize_file(self, file: File, include_metadata: bool = False) -> Dict[str, Any]:
        """Serialize file model to dictionary."""
        data = {
            "id": file.id,
            "filename": file.filename,
            "file_type": file.file_type,
            "file_size": file.file_size,
            "status": file.status,
            "user_id": file.user_id,
            "created_at": file.created_at.isoformat() if file.created_at else None,
            "updated_at": file.updated_at.isoformat() if file.updated_at else None
        }

        if include_metadata:
            data["metadata"] = file.metadata

        return data


class UserDatabaseTool(BaseTool):
    """Tool for accessing user data from the database."""

    @property
    def name(self) -> str:
        return "user_db_access"

    @property
    def description(self) -> str:
        return "Access user information from the database (read-only for security)"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.WORKFLOW_MANAGEMENT

    async def execute(self, input_data: DatabaseQueryInput) -> ToolResult:
        """Execute user database operations (read-only)."""
        try:
            with get_session() as db:
                if input_data.query_params.get("operation") == "get_by_id":
                    result = await self._get_user_by_id(db, input_data)
                elif input_data.query_params.get("operation") == "get_profile":
                    result = await self._get_user_profile(db, input_data)
                else:
                    result = await self._get_user_profile(db, input_data)

            return ToolResult(
                success=True,
                data=result,
                metadata={
                    "operation": input_data.query_params.get("operation", "get_profile"),
                    "timestamp": datetime.utcnow().isoformat(),
                    "user_id": input_data.user_id
                },
                execution_time=0.0,
                tool_name=self.name
            )

        except Exception as e:
            return ToolResult(
                success=False,
                errors=[f"User database operation failed: {str(e)}"],
                execution_time=0.0,
                tool_name=self.name
            )


    async def _get_user_by_id(self, db: Session, input_data: DatabaseQueryInput) -> Dict[str, Any]:
        """Get user by ID (limited information for security)."""
        user_id = input_data.query_params.get("user_id", input_data.user_id)

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User with ID {user_id} not found")

        return {
            "user": self._serialize_user(user)
        }

    async def _get_user_profile(self, db: Session, input_data: DatabaseQueryInput) -> Dict[str, Any]:
        """Get current user profile."""
        user = db.query(User).filter(User.id == input_data.user_id).first()
        if not user:
            raise ValueError(f"User with ID {input_data.user_id} not found")

        return {
            "user": self._serialize_user(user, include_profile=True)
        }

    def _serialize_user(self, user: User, include_profile: bool = False) -> Dict[str, Any]:
        """Serialize user model to dictionary (limited for security)."""
        data = {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None
        }

        if include_profile:
            data.update({
                "role": getattr(user, 'role', 'user'),
                "preferences": getattr(user, 'preferences', {}),
                "last_login": getattr(user, 'last_login', None)
            })

        return data
