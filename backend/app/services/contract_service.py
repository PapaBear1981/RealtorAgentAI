"""
Contract generation and management service layer.

This module provides high-level contract operations including template-based
generation, version control, validation, and multi-format output.
"""

import asyncio
import logging
import json
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from sqlmodel import Session, select, and_, or_, func
from fastapi import HTTPException, status

from ..core.database import get_session_context
from ..core.storage import get_storage_client, StorageError
from ..core.template_engine import get_template_engine, TemplateRenderingError
from ..models.contract import (
    Contract, ContractCreate, ContractUpdate, ContractPublic, ContractWithDetails
)
from ..models.template import (
    Template, TemplatePublic, TemplateWithDetails, TemplateVariable,
    TemplateGenerationRequest, TemplateGenerationResponse,
    TemplatePreviewRequest, TemplatePreviewResponse,
    OutputFormat, TemplateStatus
)
from ..models.version import Version, VersionCreate, VersionPublic
from ..models.validation import Validation, ValidationCreate, ValidationPublic
from ..models.user import User
from ..models.audit_log import AuditLog, AuditAction

logger = logging.getLogger(__name__)


class ContractGenerationError(Exception):
    """Exception raised during contract generation."""
    pass


class ContractValidationError(Exception):
    """Exception raised during contract validation."""
    pass


class ContractService:
    """
    High-level contract generation and management service.

    Provides comprehensive contract operations including template-based
    generation, version control, validation, and business rules processing.
    """

    def __init__(self):
        """Initialize contract service."""
        self.storage_client = get_storage_client()
        self.template_engine = get_template_engine()

    async def create_contract(
        self,
        contract_data: ContractCreate,
        user: User,
        session: Session
    ) -> ContractPublic:
        """
        Create a new contract with comprehensive validation.

        Args:
            contract_data: Contract creation data
            user: User creating the contract
            session: Database session

        Returns:
            ContractPublic: Created contract information
        """
        try:
            # Validate deal exists and user has access
            from ..models.deal import Deal
            deal = session.get(Deal, contract_data.deal_id)
            if not deal:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Deal not found"
                )

            # Validate template exists and is active
            template = session.get(Template, contract_data.template_id)
            if not template:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Template not found"
                )

            if template.status != TemplateStatus.ACTIVE:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Template is not active"
                )

            # Validate contract variables if provided
            if contract_data.variables and template.variables:
                validation_result = await self._validate_contract_variables(
                    contract_data.variables,
                    template,
                    session
                )
                if not validation_result['is_valid']:
                    raise ContractValidationError(
                        f"Variable validation failed: {validation_result['errors']}"
                    )

            # Create contract
            contract = Contract(
                **contract_data.dict(),
                created_at=datetime.utcnow()
            )

            session.add(contract)
            session.commit()
            session.refresh(contract)

            # Create initial version
            await self._create_contract_version(contract, user, "Initial creation", session)

            # Log creation
            audit_log = AuditLog(
                user_id=user.id,
                actor=f"user:{user.id}",
                action=AuditAction.CONTRACT_CREATED,
                success=True,
                meta={
                    "contract_id": contract.id,
                    "deal_id": contract.deal_id,
                    "template_id": contract.template_id
                }
            )
            session.add(audit_log)
            session.commit()

            return self._to_public_model(contract)

        except HTTPException:
            raise
        except (ContractValidationError, ContractGenerationError) as e:
            logger.error(f"Contract creation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"Unexpected error during contract creation: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Contract creation failed"
            )

    async def generate_contract(
        self,
        generation_request: TemplateGenerationRequest,
        user: User,
        session: Session
    ) -> TemplateGenerationResponse:
        """
        Generate contract from template.

        Args:
            generation_request: Contract generation request
            user: User generating the contract
            session: Database session

        Returns:
            TemplateGenerationResponse: Generation results
        """
        try:
            start_time = datetime.utcnow()

            # Get template
            template = session.get(Template, generation_request.template_id)
            if not template:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Template not found"
                )

            # Check template status
            if template.status != TemplateStatus.ACTIVE:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Template is not active"
                )

            # Validate variables if requested
            validation_results = None
            if generation_request.validate_before_generation:
                validation_results = await self._validate_contract_variables(
                    generation_request.variables,
                    template,
                    session
                )

                if not validation_results['is_valid']:
                    raise ContractValidationError(
                        f"Variable validation failed: {validation_results['errors']}"
                    )

            # Apply business rules if requested
            if generation_request.apply_business_rules and template.business_rules:
                generation_request.variables = await self._apply_business_rules(
                    generation_request.variables,
                    template.business_rules,
                    session
                )

            # Get template content
            template_content = await self._get_template_content(template, session)

            # Render template
            render_result = self.template_engine.render_template(
                template_content=template_content,
                variables=generation_request.variables,
                variable_definitions=template.variables or [],
                validate_variables=generation_request.validate_before_generation,
                output_format=generation_request.output_format
            )

            # Create contract record
            contract_data = ContractCreate(
                deal_id=generation_request.deal_id or 0,  # Default deal if not provided
                template_id=generation_request.template_id,
                title=generation_request.custom_title or f"Contract from {template.name}",
                status="draft"
            )

            contract = Contract(
                **contract_data.dict(),
                variables=generation_request.variables,
                created_at=datetime.utcnow()
            )

            session.add(contract)
            session.commit()
            session.refresh(contract)

            # Store generated content
            file_key = await self._store_generated_content(
                contract.id,
                render_result['content'],
                generation_request.output_format,
                session
            )

            # Update contract with file key
            if generation_request.output_format == OutputFormat.PDF:
                contract.generated_pdf_key = file_key
            elif generation_request.output_format == OutputFormat.DOCX:
                contract.generated_docx_key = file_key

            session.add(contract)
            session.commit()

            # Create initial version
            await self._create_contract_version(contract, user, "Initial generation", session)

            # Update template usage
            template.usage_count += 1
            template.last_used = datetime.utcnow()
            session.add(template)
            session.commit()

            # Log generation
            audit_log = AuditLog(
                user_id=user.id,
                actor=f"user:{user.id}",
                action=AuditAction.CONTRACT_GENERATED,
                success=True,
                meta={
                    "contract_id": contract.id,
                    "template_id": template.id,
                    "output_format": generation_request.output_format.value,
                    "generation_time_ms": render_result['render_time_ms']
                }
            )
            session.add(audit_log)
            session.commit()

            end_time = datetime.utcnow()
            total_time = (end_time - start_time).total_seconds() * 1000

            return TemplateGenerationResponse(
                contract_id=contract.id,
                generated_file_key=file_key,
                output_format=generation_request.output_format,
                generation_time_ms=int(total_time),
                validation_results=validation_results,
                warnings=render_result.get('validation_results', {}).get('warnings', [])
            )

        except HTTPException:
            raise
        except (ContractValidationError, ContractGenerationError) as e:
            logger.error(f"Contract generation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"Unexpected error during contract generation: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Contract generation failed"
            )

    async def preview_contract(
        self,
        preview_request: TemplatePreviewRequest,
        user: User,
        session: Session
    ) -> TemplatePreviewResponse:
        """
        Generate contract preview without saving.

        Args:
            preview_request: Preview request
            user: User requesting preview
            session: Database session

        Returns:
            TemplatePreviewResponse: Preview results
        """
        try:
            # Get template
            template = session.get(Template, preview_request.template_id)
            if not template:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Template not found"
                )

            # Get template content
            template_content = await self._get_template_content(template, session)

            # Prepare variables with placeholders if requested
            variables = preview_request.variables.copy()
            missing_variables = []

            if preview_request.include_placeholders and template.variables:
                for var_def in template.variables:
                    if var_def.name not in variables:
                        missing_variables.append(var_def.name)
                        variables[var_def.name] = f"[{var_def.label or var_def.name}]"

            # Render template
            render_result = self.template_engine.render_template(
                template_content=template_content,
                variables=variables,
                variable_definitions=template.variables or [],
                validate_variables=False,  # Don't validate for preview
                output_format=preview_request.output_format
            )

            validation_warnings = []
            if render_result.get('validation_results'):
                validation_warnings = render_result['validation_results'].get('warnings', [])

            return TemplatePreviewResponse(
                preview_content=render_result['content'],
                output_format=preview_request.output_format,
                missing_variables=missing_variables,
                validation_warnings=validation_warnings
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Contract preview failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Contract preview failed"
            )

    async def get_contract(
        self,
        contract_id: int,
        user: User,
        session: Session,
        include_details: bool = False
    ) -> ContractPublic:
        """
        Get contract information.

        Args:
            contract_id: Contract ID
            user: User requesting contract
            session: Database session
            include_details: Whether to include detailed information

        Returns:
            ContractPublic: Contract information
        """
        try:
            # Get contract
            contract = session.get(Contract, contract_id)
            if not contract:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Contract not found"
                )

            # Check access permissions
            if not await self._check_contract_access(contract, user, session):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied"
                )

            if include_details:
                return self._to_detailed_model(contract, session)
            else:
                return self._to_public_model(contract)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Get contract failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get contract"
            )

    async def search_contracts(
        self,
        user: User,
        session: Session,
        search_query: Optional[str] = None,
        deal_id: Optional[int] = None,
        template_id: Optional[int] = None,
        status: Optional[str] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Advanced contract search with filtering and sorting.

        Args:
            user: User performing search
            session: Database session
            search_query: Text search in title and variables
            deal_id: Filter by deal ID
            template_id: Filter by template ID
            status: Filter by status
            created_after: Filter contracts created after date
            created_before: Filter contracts created before date
            sort_by: Field to sort by
            sort_order: Sort order (asc/desc)
            limit: Maximum results
            offset: Results offset

        Returns:
            Dict: Search results with metadata
        """
        try:
            # Build base query
            query = select(Contract)

            # Apply filters
            filters = []

            if deal_id is not None:
                filters.append(Contract.deal_id == deal_id)

            if template_id is not None:
                filters.append(Contract.template_id == template_id)

            if status:
                filters.append(Contract.status == status)

            if created_after:
                filters.append(Contract.created_at >= created_after)

            if created_before:
                filters.append(Contract.created_at <= created_before)

            # Text search in title and variables
            if search_query:
                search_filters = []
                if hasattr(Contract, 'title'):
                    search_filters.append(Contract.title.ilike(f"%{search_query}%"))

                # Search in variables JSON (database-specific implementation)
                # This is a simplified version - in production, use full-text search
                search_filters.append(
                    func.cast(Contract.variables, String).ilike(f"%{search_query}%")
                )

                if search_filters:
                    filters.append(or_(*search_filters))

            # Apply all filters
            if filters:
                query = query.where(and_(*filters))

            # Get total count for pagination
            count_query = select(func.count(Contract.id)).where(and_(*filters)) if filters else select(func.count(Contract.id))
            total_count = session.exec(count_query).first() or 0

            # Apply sorting
            sort_column = getattr(Contract, sort_by, Contract.created_at)
            if sort_order.lower() == "desc":
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())

            # Apply pagination
            query = query.offset(offset).limit(limit)

            # Execute query
            contracts = session.exec(query).all()

            return {
                "contracts": [self._to_public_model(contract) for contract in contracts],
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + len(contracts) < total_count
            }

        except Exception as e:
            logger.error(f"Contract search failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to search contracts"
            )

    async def list_contracts(
        self,
        user: User,
        session: Session,
        deal_id: Optional[int] = None,
        template_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ContractPublic]:
        """
        List user's contracts with filtering.

        Args:
            user: User requesting contracts
            session: Database session
            deal_id: Filter by deal ID
            template_id: Filter by template ID
            status: Filter by status
            limit: Maximum results
            offset: Results offset

        Returns:
            List[ContractPublic]: List of contracts
        """
        try:
            # Build query - for now, show all contracts user has access to
            # In production, implement proper access control
            query = select(Contract)

            # Apply filters
            if deal_id is not None:
                query = query.where(Contract.deal_id == deal_id)

            if template_id is not None:
                query = query.where(Contract.template_id == template_id)

            if status:
                query = query.where(Contract.status == status)

            # Apply ordering and pagination
            query = query.order_by(Contract.created_at.desc()).offset(offset).limit(limit)

            # Execute query
            contracts = session.exec(query).all()

            return [self._to_public_model(contract) for contract in contracts]

        except Exception as e:
            logger.error(f"List contracts failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to list contracts"
            )

    async def update_contract(
        self,
        contract_id: int,
        contract_update: ContractUpdate,
        user: User,
        session: Session
    ) -> ContractPublic:
        """
        Update contract information.

        Args:
            contract_id: Contract ID to update
            contract_update: Update data
            user: User performing update
            session: Database session

        Returns:
            ContractPublic: Updated contract information
        """
        try:
            # Get contract
            contract = session.get(Contract, contract_id)
            if not contract:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Contract not found"
                )

            # Check permissions
            if not await self._check_contract_access(contract, user, session):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied"
                )

            # Store original values for version tracking
            original_variables = contract.variables.copy() if contract.variables else {}

            # Update contract
            update_data = contract_update.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(contract, field, value)

            contract.updated_at = datetime.utcnow()
            session.add(contract)
            session.commit()
            session.refresh(contract)

            # Create version if variables changed
            if contract.variables != original_variables:
                await self._create_contract_version(
                    contract,
                    user,
                    "Variables updated",
                    session
                )

            # Log update
            audit_log = AuditLog(
                user_id=user.id,
                actor=f"user:{user.id}",
                action=AuditAction.CONTRACT_UPDATED,
                success=True,
                meta={
                    "contract_id": contract.id,
                    "updated_fields": list(update_data.keys())
                }
            )
            session.add(audit_log)
            session.commit()

            return self._to_public_model(contract)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Contract update failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update contract"
            )

    async def delete_contract(
        self,
        contract_id: int,
        user: User,
        session: Session
    ) -> bool:
        """
        Delete contract.

        Args:
            contract_id: Contract ID to delete
            user: User requesting deletion
            session: Database session

        Returns:
            bool: True if deleted successfully
        """
        try:
            # Get contract
            contract = session.get(Contract, contract_id)
            if not contract:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Contract not found"
                )

            # Check permissions (only admin or contract owner can delete)
            if user.role != "admin":
                # For now, allow deletion - implement proper ownership check
                pass

            # Delete generated files from storage
            if contract.generated_pdf_key:
                try:
                    self.storage_client.delete_file(contract.generated_pdf_key)
                except StorageError as e:
                    logger.warning(f"Failed to delete PDF file: {e}")

            if contract.generated_docx_key:
                try:
                    self.storage_client.delete_file(contract.generated_docx_key)
                except StorageError as e:
                    logger.warning(f"Failed to delete DOCX file: {e}")

            # Mark as deleted (soft delete)
            contract.status = "void"
            contract.updated_at = datetime.utcnow()
            session.add(contract)
            session.commit()

            # Log deletion
            audit_log = AuditLog(
                user_id=user.id,
                actor=f"user:{user.id}",
                action=AuditAction.CONTRACT_DELETED,
                success=True,
                meta={
                    "contract_id": contract.id,
                    "deleted_by": user.id
                }
            )
            session.add(audit_log)
            session.commit()

            return True

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Contract deletion failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete contract"
            )

    async def validate_contract_comprehensive(
        self,
        contract_id: int,
        user: User,
        session: Session
    ) -> Dict[str, Any]:
        """
        Perform comprehensive contract validation.

        Args:
            contract_id: Contract ID to validate
            user: User performing validation
            session: Database session

        Returns:
            Dict: Comprehensive validation results
        """
        try:
            # Get contract
            contract = session.get(Contract, contract_id)
            if not contract:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Contract not found"
                )

            # Check access permissions
            if not await self._check_contract_access(contract, user, session):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied"
                )

            # Get template for validation rules
            template = session.get(Template, contract.template_id)
            if not template:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Template not found"
                )

            validation_results = {
                "contract_id": contract_id,
                "is_valid": True,
                "errors": [],
                "warnings": [],
                "validation_timestamp": datetime.utcnow().isoformat(),
                "validated_by": user.id,
                "validation_details": {}
            }

            # 1. Variable validation
            if contract.variables and template.variables:
                var_validation = await self._validate_contract_variables(
                    contract.variables,
                    template,
                    session
                )
                validation_results["validation_details"]["variables"] = var_validation
                if not var_validation["is_valid"]:
                    validation_results["is_valid"] = False
                    validation_results["errors"].extend(var_validation["errors"])
                validation_results["warnings"].extend(var_validation.get("warnings", []))

            # 2. Business rules validation
            if template.business_rules:
                rules_validation = await self._validate_business_rules(
                    contract.variables or {},
                    template.business_rules,
                    session
                )
                validation_results["validation_details"]["business_rules"] = rules_validation
                if not rules_validation["is_valid"]:
                    validation_results["is_valid"] = False
                    validation_results["errors"].extend(rules_validation["errors"])
                validation_results["warnings"].extend(rules_validation.get("warnings", []))

            # 3. Data integrity validation
            integrity_validation = await self._validate_data_integrity(contract, session)
            validation_results["validation_details"]["data_integrity"] = integrity_validation
            if not integrity_validation["is_valid"]:
                validation_results["is_valid"] = False
                validation_results["errors"].extend(integrity_validation["errors"])
            validation_results["warnings"].extend(integrity_validation.get("warnings", []))

            # 4. Compliance validation
            compliance_validation = await self._validate_compliance(contract, template, session)
            validation_results["validation_details"]["compliance"] = compliance_validation
            if not compliance_validation["is_valid"]:
                validation_results["is_valid"] = False
                validation_results["errors"].extend(compliance_validation["errors"])
            validation_results["warnings"].extend(compliance_validation.get("warnings", []))

            # Log validation
            audit_log = AuditLog(
                user_id=user.id,
                actor=f"user:{user.id}",
                action=AuditAction.CONTRACT_VALIDATED,
                success=validation_results["is_valid"],
                meta={
                    "contract_id": contract_id,
                    "validation_result": validation_results["is_valid"],
                    "error_count": len(validation_results["errors"]),
                    "warning_count": len(validation_results["warnings"])
                }
            )
            session.add(audit_log)
            session.commit()

            return validation_results

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Contract validation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Contract validation failed"
            )

    async def get_contract_statistics(
        self,
        user: User,
        session: Session,
        deal_id: Optional[int] = None,
        template_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get contract statistics and analytics.

        Args:
            user: User requesting statistics
            session: Database session
            deal_id: Filter by deal ID
            template_id: Filter by template ID

        Returns:
            Dict: Contract statistics
        """
        try:
            # Build base query
            query = select(Contract)
            filters = []

            if deal_id is not None:
                filters.append(Contract.deal_id == deal_id)

            if template_id is not None:
                filters.append(Contract.template_id == template_id)

            if filters:
                query = query.where(and_(*filters))

            # Get all contracts for analysis
            contracts = session.exec(query).all()

            # Calculate statistics
            total_contracts = len(contracts)
            status_counts = {}
            template_usage = {}
            monthly_creation = {}

            for contract in contracts:
                # Status distribution
                status = contract.status or "unknown"
                status_counts[status] = status_counts.get(status, 0) + 1

                # Template usage
                template_id = contract.template_id
                template_usage[template_id] = template_usage.get(template_id, 0) + 1

                # Monthly creation trends
                month_key = contract.created_at.strftime("%Y-%m")
                monthly_creation[month_key] = monthly_creation.get(month_key, 0) + 1

            # Get template names for usage stats
            template_names = {}
            if template_usage:
                template_ids = list(template_usage.keys())
                templates = session.exec(
                    select(Template).where(Template.id.in_(template_ids))
                ).all()
                template_names = {t.id: t.name for t in templates}

            # Format template usage with names
            template_usage_formatted = [
                {
                    "template_id": tid,
                    "template_name": template_names.get(tid, f"Template {tid}"),
                    "usage_count": count
                }
                for tid, count in template_usage.items()
            ]

            # Sort by usage count
            template_usage_formatted.sort(key=lambda x: x["usage_count"], reverse=True)

            return {
                "total_contracts": total_contracts,
                "status_distribution": status_counts,
                "template_usage": template_usage_formatted,
                "monthly_creation_trend": monthly_creation,
                "generated_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Contract statistics failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get contract statistics"
            )

    async def _validate_contract_variables(
        self,
        variables: Dict[str, Any],
        template: Template,
        session: Session
    ) -> Dict[str, Any]:
        """Validate contract variables against template schema."""
        try:
            if not template.variables:
                return {'is_valid': True, 'errors': [], 'warnings': []}

            return self.template_engine.validate_variables(
                variables,
                template.variables
            )

        except Exception as e:
            logger.error(f"Variable validation failed: {e}")
            return {
                'is_valid': False,
                'errors': [f"Validation error: {str(e)}"],
                'warnings': []
            }

    async def _apply_business_rules(
        self,
        variables: Dict[str, Any],
        business_rules: Dict[str, Any],
        session: Session
    ) -> Dict[str, Any]:
        """Apply business rules to variables."""
        try:
            # Apply calculated fields
            if 'calculated_fields' in business_rules:
                for field_name, formula in business_rules['calculated_fields'].items():
                    try:
                        # Simple formula evaluation (extend as needed)
                        if isinstance(formula, str) and formula.startswith('='):
                            # Remove = and evaluate simple expressions
                            expression = formula[1:]
                            # For security, only allow basic math operations
                            if all(c in '0123456789+-*/.() ' or c.isalpha() for c in expression):
                                # Replace variable names with values
                                for var_name, var_value in variables.items():
                                    if var_name in expression:
                                        expression = expression.replace(var_name, str(var_value))

                                # Evaluate if it's a simple numeric expression
                                try:
                                    result = eval(expression, {"__builtins__": {}}, {})
                                    variables[field_name] = result
                                except:
                                    logger.warning(f"Could not evaluate formula: {formula}")
                    except Exception as e:
                        logger.warning(f"Error applying calculated field {field_name}: {e}")

            # Apply conditional logic
            if 'conditional_logic' in business_rules:
                for condition in business_rules['conditional_logic']:
                    try:
                        # Simple condition evaluation
                        if self._evaluate_condition(condition.get('if'), variables):
                            # Apply then actions
                            for action in condition.get('then', []):
                                self._apply_rule_action(action, variables)
                    except Exception as e:
                        logger.warning(f"Error applying conditional logic: {e}")

            return variables

        except Exception as e:
            logger.error(f"Business rules application failed: {e}")
            return variables

    async def _validate_business_rules(
        self,
        variables: Dict[str, Any],
        business_rules: Dict[str, Any],
        session: Session
    ) -> Dict[str, Any]:
        """Validate contract against business rules."""
        try:
            validation_result = {
                "is_valid": True,
                "errors": [],
                "warnings": []
            }

            # Check required fields
            if "required_fields" in business_rules:
                for field in business_rules["required_fields"]:
                    if field not in variables or not variables[field]:
                        validation_result["is_valid"] = False
                        validation_result["errors"].append(f"Required field '{field}' is missing or empty")

            # Check field constraints
            if "field_constraints" in business_rules:
                for field, constraints in business_rules["field_constraints"].items():
                    if field in variables:
                        value = variables[field]

                        # Min/max value constraints
                        if "min_value" in constraints and isinstance(value, (int, float)):
                            if value < constraints["min_value"]:
                                validation_result["errors"].append(
                                    f"Field '{field}' value {value} is below minimum {constraints['min_value']}"
                                )
                                validation_result["is_valid"] = False

                        if "max_value" in constraints and isinstance(value, (int, float)):
                            if value > constraints["max_value"]:
                                validation_result["errors"].append(
                                    f"Field '{field}' value {value} exceeds maximum {constraints['max_value']}"
                                )
                                validation_result["is_valid"] = False

                        # Pattern constraints
                        if "pattern" in constraints and isinstance(value, str):
                            import re
                            if not re.match(constraints["pattern"], value):
                                validation_result["errors"].append(
                                    f"Field '{field}' does not match required pattern"
                                )
                                validation_result["is_valid"] = False

            # Check conditional rules
            if "conditional_rules" in business_rules:
                for rule in business_rules["conditional_rules"]:
                    if self._evaluate_condition(rule.get("condition"), variables):
                        # Check if required fields are present
                        for required_field in rule.get("then_required", []):
                            if required_field not in variables or not variables[required_field]:
                                validation_result["is_valid"] = False
                                validation_result["errors"].append(
                                    f"Field '{required_field}' is required when condition is met"
                                )

            return validation_result

        except Exception as e:
            logger.error(f"Business rules validation failed: {e}")
            return {
                "is_valid": False,
                "errors": [f"Business rules validation error: {str(e)}"],
                "warnings": []
            }

    async def _validate_data_integrity(
        self,
        contract: Contract,
        session: Session
    ) -> Dict[str, Any]:
        """Validate contract data integrity."""
        try:
            validation_result = {
                "is_valid": True,
                "errors": [],
                "warnings": []
            }

            # Check if deal exists and is accessible
            from ..models.deal import Deal
            deal = session.get(Deal, contract.deal_id)
            if not deal:
                validation_result["is_valid"] = False
                validation_result["errors"].append("Associated deal not found")

            # Check if template exists and is active
            template = session.get(Template, contract.template_id)
            if not template:
                validation_result["is_valid"] = False
                validation_result["errors"].append("Associated template not found")
            elif template.status != TemplateStatus.ACTIVE:
                validation_result["warnings"].append("Associated template is not active")

            # Check for orphaned files
            if contract.generated_pdf_key:
                try:
                    # In production, check if file exists in storage
                    pass
                except Exception:
                    validation_result["warnings"].append("Generated PDF file may be missing")

            if contract.generated_docx_key:
                try:
                    # In production, check if file exists in storage
                    pass
                except Exception:
                    validation_result["warnings"].append("Generated DOCX file may be missing")

            # Check contract status consistency
            if contract.status == "completed" and not contract.completed_at:
                validation_result["warnings"].append("Contract marked as completed but no completion date set")

            if contract.status == "sent_for_signature" and not contract.sent_for_signature_at:
                validation_result["warnings"].append("Contract marked as sent for signature but no send date set")

            return validation_result

        except Exception as e:
            logger.error(f"Data integrity validation failed: {e}")
            return {
                "is_valid": False,
                "errors": [f"Data integrity validation error: {str(e)}"],
                "warnings": []
            }

    async def _validate_compliance(
        self,
        contract: Contract,
        template: Template,
        session: Session
    ) -> Dict[str, Any]:
        """Validate contract compliance with regulations."""
        try:
            validation_result = {
                "is_valid": True,
                "errors": [],
                "warnings": []
            }

            # Check template compliance rules
            if template.ruleset:
                compliance_rules = template.ruleset.get("compliance", {})

                # Check required disclosures
                if "required_disclosures" in compliance_rules:
                    for disclosure in compliance_rules["required_disclosures"]:
                        if disclosure not in (contract.variables or {}):
                            validation_result["warnings"].append(
                                f"Required disclosure '{disclosure}' not found in contract variables"
                            )

                # Check jurisdiction-specific rules
                if "jurisdiction_rules" in compliance_rules:
                    jurisdiction = (contract.variables or {}).get("jurisdiction", "")
                    if jurisdiction in compliance_rules["jurisdiction_rules"]:
                        jurisdiction_rules = compliance_rules["jurisdiction_rules"][jurisdiction]

                        for rule in jurisdiction_rules.get("required_fields", []):
                            if rule not in (contract.variables or {}):
                                validation_result["errors"].append(
                                    f"Jurisdiction '{jurisdiction}' requires field '{rule}'"
                                )
                                validation_result["is_valid"] = False

            # Check for sensitive data handling
            sensitive_fields = ["ssn", "tax_id", "bank_account", "credit_card"]
            for field in sensitive_fields:
                if field in (contract.variables or {}):
                    validation_result["warnings"].append(
                        f"Contract contains sensitive field '{field}' - ensure proper data protection"
                    )

            return validation_result

        except Exception as e:
            logger.error(f"Compliance validation failed: {e}")
            return {
                "is_valid": True,  # Don't fail on compliance validation errors
                "errors": [],
                "warnings": [f"Compliance validation error: {str(e)}"]
            }

    def _evaluate_condition(self, condition: Dict[str, Any], variables: Dict[str, Any]) -> bool:
        """Evaluate a simple condition."""
        if not condition:
            return False

        try:
            field = condition.get('field')
            operator = condition.get('operator')
            value = condition.get('value')

            if field not in variables:
                return False

            var_value = variables[field]

            if operator == 'equals':
                return var_value == value
            elif operator == 'not_equals':
                return var_value != value
            elif operator == 'greater_than':
                return float(var_value) > float(value)
            elif operator == 'less_than':
                return float(var_value) < float(value)
            elif operator == 'contains':
                return str(value).lower() in str(var_value).lower()
            elif operator == 'is_empty':
                return not var_value or str(var_value).strip() == ''
            elif operator == 'is_not_empty':
                return var_value and str(var_value).strip() != ''

            return False

        except Exception:
            return False

    def _apply_rule_action(self, action: Dict[str, Any], variables: Dict[str, Any]):
        """Apply a rule action to variables."""
        try:
            action_type = action.get('type')

            if action_type == 'set_value':
                field = action.get('field')
                value = action.get('value')
                if field:
                    variables[field] = value

            elif action_type == 'calculate':
                field = action.get('field')
                formula = action.get('formula')
                if field and formula:
                    # Simple calculation (extend as needed)
                    variables[field] = self._calculate_value(formula, variables)

        except Exception as e:
            logger.warning(f"Error applying rule action: {e}")

    def _calculate_value(self, formula: str, variables: Dict[str, Any]) -> Any:
        """Calculate value from formula."""
        try:
            # Replace variable names with values
            expression = formula
            for var_name, var_value in variables.items():
                if var_name in expression:
                    expression = expression.replace(var_name, str(var_value))

            # Evaluate simple numeric expressions
            if all(c in '0123456789+-*/.() ' for c in expression):
                return eval(expression, {"__builtins__": {}}, {})

            return formula

        except Exception:
            return formula

    async def _get_template_content(self, template: Template, session: Session) -> str:
        """Get template content from storage or database."""
        try:
            # Try HTML content first
            if template.html_content:
                return template.html_content

            # Try DOCX file
            if template.docx_key:
                # For now, return a placeholder - implement DOCX to HTML conversion
                return f"""
                <div class="contract-header">
                    <h1>{template.name}</h1>
                    <p>Version: {template.version}</p>
                </div>
                <div class="contract-content">
                    <p>This contract was generated from template: {template.name}</p>
                    <p>Template variables will be substituted here.</p>
                    <!-- DOCX content conversion would go here -->
                </div>
                """

            # Default template content
            return f"""
            <div class="contract-header">
                <h1>{template.name}</h1>
                <p>Version: {template.version}</p>
            </div>
            <div class="contract-content">
                <p>Contract content goes here.</p>
                <p>This contract was generated from template: {template.name}</p>
                <p>Template variables will be substituted during rendering.</p>
            </div>
            """

        except Exception as e:
            logger.error(f"Failed to get template content: {e}")
            raise ContractGenerationError(f"Could not load template content: {str(e)}")

    async def _store_generated_content(
        self,
        contract_id: int,
        content: str,
        output_format: OutputFormat,
        session: Session
    ) -> str:
        """Store generated contract content in storage."""
        try:
            # Generate storage key
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            file_extension = output_format.value.lower()
            storage_key = f"contracts/{contract_id}/generated_{timestamp}.{file_extension}"

            # Convert content to bytes
            content_bytes = content.encode('utf-8')

            # Determine MIME type
            mime_type = {
                OutputFormat.HTML: 'text/html',
                OutputFormat.PDF: 'application/pdf',
                OutputFormat.DOCX: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                OutputFormat.TXT: 'text/plain'
            }.get(output_format, 'text/plain')

            # Upload to storage
            import io
            file_obj = io.BytesIO(content_bytes)

            result = self.storage_client.upload_file(
                file_obj=file_obj,
                storage_key=storage_key,
                mime_type=mime_type
            )

            return storage_key

        except Exception as e:
            logger.error(f"Failed to store generated content: {e}")
            raise ContractGenerationError(f"Could not store generated content: {str(e)}")

    async def _create_contract_version(
        self,
        contract: Contract,
        user: User,
        change_summary: str,
        session: Session
    ):
        """Create a new contract version."""
        try:
            # Get current version count
            version_count = session.exec(
                select(func.count(Version.id)).where(Version.contract_id == contract.id)
            ).first() or 0

            # Create version
            version_data = VersionCreate(
                contract_id=contract.id,
                number=version_count + 1,
                diff=change_summary,
                created_by=user.email,
                change_summary=change_summary,
                content_hash="",  # TODO: Calculate content hash
                is_current=True
            )

            version = Version(**version_data.dict())
            session.add(version)

            # Mark other versions as not current
            other_versions = session.exec(
                select(Version).where(
                    and_(Version.contract_id == contract.id, Version.id != version.id)
                )
            ).all()

            for other_version in other_versions:
                other_version.is_current = False
                session.add(other_version)

            session.commit()

        except Exception as e:
            logger.error(f"Failed to create contract version: {e}")

    async def _check_contract_access(
        self,
        contract: Contract,
        user: User,
        session: Session
    ) -> bool:
        """Check if user has access to contract."""
        # For now, allow all access - implement proper access control
        return True

    def _to_public_model(self, contract: Contract) -> ContractPublic:
        """Convert contract to public model."""
        return ContractPublic(
            id=contract.id,
            created_at=contract.created_at,
            updated_at=contract.updated_at,
            deal_id=contract.deal_id,
            template_id=contract.template_id,
            title=contract.title,
            status=contract.status,
            sent_for_signature_at=contract.sent_for_signature_at,
            completed_at=contract.completed_at
        )

    def _to_detailed_model(self, contract: Contract, session: Session) -> ContractWithDetails:
        """Convert contract to detailed model."""
        # Get related data
        versions = session.exec(
            select(Version).where(Version.contract_id == contract.id)
        ).all()

        public_model = self._to_public_model(contract)
        return ContractWithDetails(
            **public_model.dict(),
            versions=[self._version_to_public(v) for v in versions],
            signers=[],  # TODO: Implement signers
            validations=[]  # TODO: Implement validations
        )

    def _version_to_public(self, version: Version) -> VersionPublic:
        """Convert version to public model."""
        return VersionPublic(
            id=version.id,
            created_at=version.created_at,
            contract_id=version.contract_id,
            number=version.number,
            diff=version.diff,
            created_by=version.created_by,
            change_summary=version.change_summary,
            content_hash=version.content_hash,
            is_current=version.is_current
        )


# Global contract service instance
_contract_service: Optional[ContractService] = None


def get_contract_service() -> ContractService:
    """
    Get global contract service instance.

    Returns:
        ContractService: Configured contract service
    """
    global _contract_service

    if _contract_service is None:
        _contract_service = ContractService()

    return _contract_service


# Export service
__all__ = [
    "ContractService",
    "ContractGenerationError",
    "ContractValidationError",
    "get_contract_service",
]
