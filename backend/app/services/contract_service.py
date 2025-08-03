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
