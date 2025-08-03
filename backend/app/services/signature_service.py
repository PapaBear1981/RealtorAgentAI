"""
Comprehensive signature workflow management service.

This module provides the main signature service for managing
signature requests, workflows, multi-party coordination,
and integration with external e-signature providers.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from sqlmodel import Session, select
from fastapi import HTTPException, status

from ..core.database import get_session
from ..core.config import get_settings
from ..models.signature import (
    SignatureRequest, SignatureRequestCreate, SignatureRequestUpdate, SignatureRequestPublic,
    SignatureRequestWithDetails, SignatureWorkflow, SignatureField, SignatureProviderConfig,
    SignatureAudit, SignatureProvider, SignatureRequestStatus, WorkflowType
)
from ..models.contract import Contract
from ..models.signer import Signer, SignerCreate
from ..models.user import User
from ..models.audit_log import AuditLog, AuditAction
from ..services.signature_providers import ProviderFactory, SignatureProviderError
from ..services.file_service import get_file_service
from ..core.notifications import get_notification_service

logger = logging.getLogger(__name__)
settings = get_settings()


class SignatureServiceError(Exception):
    """Exception raised during signature service operations."""
    pass


class SignatureWorkflowError(Exception):
    """Exception raised during workflow processing."""
    pass


class SignatureService:
    """
    Comprehensive signature workflow management service.
    
    Provides signature request creation, workflow management,
    multi-party coordination, and provider integration.
    """
    
    def __init__(self):
        """Initialize signature service."""
        self.file_service = get_file_service()
        self.notification_service = get_notification_service()
    
    async def create_signature_request(
        self,
        request_data: SignatureRequestCreate,
        current_user: User,
        session: Session
    ) -> SignatureRequestPublic:
        """
        Create a new signature request with workflow processing.
        
        Args:
            request_data: Signature request creation data
            current_user: Current authenticated user
            session: Database session
            
        Returns:
            SignatureRequestPublic: Created signature request
        """
        try:
            # Validate contract exists and user has access
            contract = session.get(Contract, request_data.contract_id)
            if not contract:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Contract not found"
                )
            
            # Create signature request
            signature_request = SignatureRequest(
                title=request_data.title,
                message=request_data.message,
                provider=request_data.provider,
                status=SignatureRequestStatus.DRAFT,
                expires_at=request_data.expires_at,
                reminder_frequency=request_data.reminder_frequency,
                allow_decline=request_data.allow_decline,
                require_authentication=request_data.require_authentication,
                sequential_signing=request_data.sequential_signing,
                contract_id=request_data.contract_id,
                created_by=current_user.id,
                workflow_id=request_data.workflow_id,
                settings=request_data.settings or {}
            )
            
            session.add(signature_request)
            session.commit()
            session.refresh(signature_request)
            
            # Create signers
            await self._create_signers(signature_request, request_data.signers, session)
            
            # Create signature fields if provided
            if request_data.fields:
                await self._create_signature_fields(signature_request, request_data.fields, session)
            
            # Apply workflow if specified
            if request_data.workflow_id:
                await self._apply_workflow(signature_request, session)
            
            # Log audit event
            await self._log_audit_event(
                signature_request.id,
                "signature_request_created",
                f"Signature request '{signature_request.title}' created",
                current_user.id,
                session
            )
            
            return SignatureRequestPublic.model_validate(signature_request)
            
        except Exception as e:
            logger.error(f"Failed to create signature request: {e}")
            session.rollback()
            raise SignatureServiceError(f"Failed to create signature request: {str(e)}")
    
    async def send_signature_request(
        self,
        request_id: int,
        current_user: User,
        session: Session
    ) -> SignatureRequestPublic:
        """
        Send signature request to signers via provider.
        
        Args:
            request_id: Signature request ID
            current_user: Current authenticated user
            session: Database session
            
        Returns:
            SignatureRequestPublic: Updated signature request
        """
        try:
            # Get signature request with details
            signature_request = await self._get_signature_request_with_details(request_id, session)
            
            if signature_request.status != SignatureRequestStatus.DRAFT:
                raise SignatureServiceError("Signature request has already been sent")
            
            # Get provider configuration
            provider_config = await self._get_provider_config(signature_request.provider, session)
            
            # Prepare documents
            documents = await self._prepare_documents(signature_request, session)
            
            # Prepare signers
            signers = await self._prepare_signers(signature_request, session)
            
            # Prepare fields
            fields = await self._prepare_fields(signature_request, session)
            
            # Create envelope with provider
            async with ProviderFactory.create_provider(provider_config) as provider:
                envelope_result = await provider.create_envelope(
                    title=signature_request.title,
                    message=signature_request.message or "",
                    documents=documents,
                    signers=signers,
                    fields=fields,
                    settings=signature_request.settings
                )
                
                # Send envelope
                send_result = await provider.send_envelope(envelope_result["envelope_id"])
            
            # Update signature request
            signature_request.provider_envelope_id = envelope_result["envelope_id"]
            signature_request.provider_status = send_result.get("provider_status")
            signature_request.provider_uri = envelope_result.get("uri")
            signature_request.status = SignatureRequestStatus.SENT
            signature_request.sent_at = datetime.utcnow()
            signature_request.updated_at = datetime.utcnow()
            
            session.add(signature_request)
            session.commit()
            
            # Update contract status
            contract = session.get(Contract, signature_request.contract_id)
            if contract:
                contract.status = "sent"
                contract.sent_for_signature_at = datetime.utcnow()
                session.add(contract)
                session.commit()
            
            # Send notifications to signers
            await self._send_signer_notifications(signature_request, session)
            
            # Log audit event
            await self._log_audit_event(
                signature_request.id,
                "signature_request_sent",
                f"Signature request sent to {len(signers)} signers",
                current_user.id,
                session
            )
            
            return SignatureRequestPublic.model_validate(signature_request)
            
        except Exception as e:
            logger.error(f"Failed to send signature request: {e}")
            session.rollback()
            raise SignatureServiceError(f"Failed to send signature request: {str(e)}")
    
    async def get_signature_request(
        self,
        request_id: int,
        current_user: User,
        session: Session,
        include_details: bool = False
    ) -> SignatureRequestPublic:
        """
        Get signature request information.
        
        Args:
            request_id: Signature request ID
            current_user: Current authenticated user
            session: Database session
            include_details: Whether to include detailed information
            
        Returns:
            SignatureRequestPublic: Signature request information
        """
        try:
            signature_request = session.get(SignatureRequest, request_id)
            
            if not signature_request:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Signature request not found"
                )
            
            # Check access permissions
            if not await self._check_access_permission(signature_request, current_user, session):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to signature request"
                )
            
            if include_details:
                return SignatureRequestWithDetails.model_validate(signature_request)
            else:
                return SignatureRequestPublic.model_validate(signature_request)
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get signature request: {e}")
            raise SignatureServiceError(f"Failed to get signature request: {str(e)}")
    
    async def update_signature_request_status(
        self,
        request_id: int,
        provider_data: Dict[str, Any],
        session: Session
    ) -> SignatureRequestPublic:
        """
        Update signature request status from provider webhook.
        
        Args:
            request_id: Signature request ID
            provider_data: Provider webhook data
            session: Database session
            
        Returns:
            SignatureRequestPublic: Updated signature request
        """
        try:
            signature_request = session.get(SignatureRequest, request_id)
            
            if not signature_request:
                raise SignatureServiceError("Signature request not found")
            
            # Get provider configuration
            provider_config = await self._get_provider_config(signature_request.provider, session)
            
            # Update status from provider
            async with ProviderFactory.create_provider(provider_config) as provider:
                status_result = await provider.get_envelope_status(signature_request.provider_envelope_id)
            
            # Update signature request
            old_status = signature_request.status
            signature_request.status = status_result["status"]
            signature_request.provider_status = status_result.get("provider_status")
            signature_request.updated_at = datetime.utcnow()
            
            if status_result["status"] == SignatureRequestStatus.COMPLETED:
                signature_request.completed_at = datetime.utcnow()
                
                # Update contract status
                contract = session.get(Contract, signature_request.contract_id)
                if contract:
                    contract.status = "signed"
                    contract.completed_at = datetime.utcnow()
                    session.add(contract)
            
            session.add(signature_request)
            session.commit()
            
            # Process status change
            await self._process_status_change(signature_request, old_status, session)
            
            # Log audit event
            await self._log_audit_event(
                signature_request.id,
                "status_updated",
                f"Status changed from {old_status} to {signature_request.status}",
                None,
                session,
                provider_data=provider_data
            )
            
            return SignatureRequestPublic.model_validate(signature_request)
            
        except Exception as e:
            logger.error(f"Failed to update signature request status: {e}")
            session.rollback()
            raise SignatureServiceError(f"Failed to update status: {str(e)}")
    
    async def void_signature_request(
        self,
        request_id: int,
        reason: str,
        current_user: User,
        session: Session
    ) -> SignatureRequestPublic:
        """
        Void a signature request.
        
        Args:
            request_id: Signature request ID
            reason: Reason for voiding
            current_user: Current authenticated user
            session: Database session
            
        Returns:
            SignatureRequestPublic: Voided signature request
        """
        try:
            signature_request = await self._get_signature_request_with_details(request_id, session)
            
            if signature_request.status in [SignatureRequestStatus.COMPLETED, SignatureRequestStatus.VOIDED]:
                raise SignatureServiceError("Cannot void completed or already voided signature request")
            
            # Void with provider if envelope exists
            if signature_request.provider_envelope_id:
                provider_config = await self._get_provider_config(signature_request.provider, session)
                
                async with ProviderFactory.create_provider(provider_config) as provider:
                    await provider.void_envelope(signature_request.provider_envelope_id, reason)
            
            # Update signature request
            signature_request.status = SignatureRequestStatus.VOIDED
            signature_request.voided_at = datetime.utcnow()
            signature_request.updated_at = datetime.utcnow()
            
            session.add(signature_request)
            session.commit()
            
            # Update contract status
            contract = session.get(Contract, signature_request.contract_id)
            if contract:
                contract.status = "void"
                session.add(contract)
                session.commit()
            
            # Log audit event
            await self._log_audit_event(
                signature_request.id,
                "signature_request_voided",
                f"Signature request voided: {reason}",
                current_user.id,
                session
            )
            
            return SignatureRequestPublic.model_validate(signature_request)
            
        except Exception as e:
            logger.error(f"Failed to void signature request: {e}")
            session.rollback()
            raise SignatureServiceError(f"Failed to void signature request: {str(e)}")
    
    async def list_signature_requests(
        self,
        current_user: User,
        session: Session,
        contract_id: Optional[int] = None,
        status: Optional[SignatureRequestStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[SignatureRequestPublic]:
        """
        List signature requests with filtering.
        
        Args:
            current_user: Current authenticated user
            session: Database session
            contract_id: Filter by contract ID
            status: Filter by status
            limit: Maximum results
            offset: Results offset
            
        Returns:
            List[SignatureRequestPublic]: List of signature requests
        """
        try:
            query = select(SignatureRequest)
            
            # Apply filters
            if contract_id:
                query = query.where(SignatureRequest.contract_id == contract_id)
            
            if status:
                query = query.where(SignatureRequest.status == status)
            
            # Apply user access control
            if current_user.role != "admin":
                query = query.where(SignatureRequest.created_by == current_user.id)
            
            # Apply pagination
            query = query.offset(offset).limit(limit).order_by(SignatureRequest.created_at.desc())
            
            signature_requests = session.exec(query).all()
            
            return [SignatureRequestPublic.model_validate(req) for req in signature_requests]
            
        except Exception as e:
            logger.error(f"Failed to list signature requests: {e}")
            raise SignatureServiceError(f"Failed to list signature requests: {str(e)}")
    
    # Helper methods
    async def _create_signers(
        self,
        signature_request: SignatureRequest,
        signer_data: List[Dict[str, Any]],
        session: Session
    ):
        """Create signers for signature request."""
        for signer_info in signer_data:
            signer = Signer(
                contract_id=signature_request.contract_id,
                party_role=signer_info["party_role"],
                name=signer_info["name"],
                email=signer_info["email"],
                phone=signer_info.get("phone"),
                order=signer_info["order"],
                status="pending"
            )
            session.add(signer)
        
        session.commit()
    
    async def _create_signature_fields(
        self,
        signature_request: SignatureRequest,
        field_data: List[Dict[str, Any]],
        session: Session
    ):
        """Create signature fields for signature request."""
        for field_info in field_data:
            field = SignatureField(
                signature_request_id=signature_request.id,
                signer_id=field_info.get("signer_id"),
                field_type=field_info["field_type"],
                label=field_info["label"],
                page_number=field_info["page_number"],
                x_position=field_info["x_position"],
                y_position=field_info["y_position"],
                width=field_info["width"],
                height=field_info["height"],
                required=field_info.get("required", True),
                default_value=field_info.get("default_value")
            )
            session.add(field)
        
        session.commit()
    
    async def _apply_workflow(
        self,
        signature_request: SignatureRequest,
        session: Session
    ):
        """Apply workflow template to signature request."""
        if not signature_request.workflow_id:
            return
        
        workflow = session.get(SignatureWorkflow, signature_request.workflow_id)
        if not workflow:
            return
        
        # Apply workflow settings
        if workflow.field_templates:
            await self._apply_field_templates(signature_request, workflow.field_templates, session)
        
        if workflow.notification_settings:
            signature_request.settings.update(workflow.notification_settings)
        
        # Update workflow usage
        workflow.usage_count += 1
        workflow.last_used_at = datetime.utcnow()
        session.add(workflow)
        session.commit()
    
    async def _get_signature_request_with_details(
        self,
        request_id: int,
        session: Session
    ) -> SignatureRequest:
        """Get signature request with all related data."""
        signature_request = session.get(SignatureRequest, request_id)
        
        if not signature_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Signature request not found"
            )
        
        return signature_request
    
    async def _get_provider_config(
        self,
        provider: SignatureProvider,
        session: Session
    ) -> SignatureProviderConfig:
        """Get active provider configuration."""
        config = session.exec(
            select(SignatureProviderConfig)
            .where(SignatureProviderConfig.provider == provider)
            .where(SignatureProviderConfig.is_active == True)
        ).first()
        
        if not config:
            raise SignatureServiceError(f"No active configuration found for provider {provider}")
        
        return config
    
    async def _prepare_documents(
        self,
        signature_request: SignatureRequest,
        session: Session
    ) -> List[Dict[str, Any]]:
        """Prepare documents for provider."""
        # Get contract files
        contract = session.get(Contract, signature_request.contract_id)
        if not contract:
            raise SignatureServiceError("Contract not found")
        
        documents = []
        
        # Add generated contract document
        if contract.generated_pdf_key:
            file_content = await self.file_service.download_file(contract.generated_pdf_key)
            documents.append({
                "name": f"{contract.title or 'Contract'}.pdf",
                "content_base64": file_content,
                "extension": "pdf"
            })
        
        return documents
    
    async def _prepare_signers(
        self,
        signature_request: SignatureRequest,
        session: Session
    ) -> List[Dict[str, Any]]:
        """Prepare signers for provider."""
        signers = session.exec(
            select(Signer)
            .where(Signer.contract_id == signature_request.contract_id)
            .order_by(Signer.order)
        ).all()
        
        return [
            {
                "id": signer.id,
                "name": signer.name,
                "email": signer.email,
                "order": signer.order,
                "role": signer.party_role
            }
            for signer in signers
        ]
    
    async def _prepare_fields(
        self,
        signature_request: SignatureRequest,
        session: Session
    ) -> List[Dict[str, Any]]:
        """Prepare signature fields for provider."""
        fields = session.exec(
            select(SignatureField)
            .where(SignatureField.signature_request_id == signature_request.id)
        ).all()
        
        return [
            {
                "signer_id": field.signer_id,
                "field_type": field.field_type,
                "label": field.label,
                "page_number": field.page_number,
                "x_position": field.x_position,
                "y_position": field.y_position,
                "width": field.width,
                "height": field.height,
                "required": field.required,
                "default_value": field.default_value
            }
            for field in fields
        ]
    
    async def _check_access_permission(
        self,
        signature_request: SignatureRequest,
        current_user: User,
        session: Session
    ) -> bool:
        """Check if user has access to signature request."""
        if current_user.role == "admin":
            return True
        
        if signature_request.created_by == current_user.id:
            return True
        
        # Check if user is associated with the contract
        contract = session.get(Contract, signature_request.contract_id)
        if contract and contract.deal.agent_id == current_user.id:
            return True
        
        return False
    
    async def _send_signer_notifications(
        self,
        signature_request: SignatureRequest,
        session: Session
    ):
        """Send notifications to signers."""
        signers = session.exec(
            select(Signer)
            .where(Signer.contract_id == signature_request.contract_id)
        ).all()
        
        for signer in signers:
            await self.notification_service.send_signature_notification(
                signer.email,
                signer.name,
                signature_request.title,
                signature_request.provider_uri or ""
            )
    
    async def _process_status_change(
        self,
        signature_request: SignatureRequest,
        old_status: SignatureRequestStatus,
        session: Session
    ):
        """Process signature request status changes."""
        if signature_request.status == SignatureRequestStatus.COMPLETED:
            # Download completed document
            await self._download_completed_document(signature_request, session)
            
            # Send completion notifications
            await self._send_completion_notifications(signature_request, session)
    
    async def _download_completed_document(
        self,
        signature_request: SignatureRequest,
        session: Session
    ):
        """Download and store completed signed document."""
        try:
            provider_config = await self._get_provider_config(signature_request.provider, session)
            
            async with ProviderFactory.create_provider(provider_config) as provider:
                document_content = await provider.download_completed_document(
                    signature_request.provider_envelope_id
                )
            
            # Store completed document
            file_key = f"signed_contracts/{signature_request.contract_id}_{signature_request.id}.pdf"
            await self.file_service.upload_file(
                file_key,
                document_content,
                "application/pdf"
            )
            
            # Update contract with signed document
            contract = session.get(Contract, signature_request.contract_id)
            if contract:
                contract.generated_pdf_key = file_key
                session.add(contract)
                session.commit()
                
        except Exception as e:
            logger.error(f"Failed to download completed document: {e}")
    
    async def _send_completion_notifications(
        self,
        signature_request: SignatureRequest,
        session: Session
    ):
        """Send completion notifications."""
        # Notify contract creator
        creator = session.get(User, signature_request.created_by)
        if creator:
            await self.notification_service.send_completion_notification(
                creator.email,
                creator.name,
                signature_request.title
            )
    
    async def _log_audit_event(
        self,
        signature_request_id: int,
        event_type: str,
        description: str,
        user_id: Optional[int],
        session: Session,
        signer_id: Optional[int] = None,
        provider_data: Optional[Dict[str, Any]] = None
    ):
        """Log signature audit event."""
        audit_log = SignatureAudit(
            signature_request_id=signature_request_id,
            user_id=user_id,
            signer_id=signer_id,
            event_type=event_type,
            event_description=description,
            provider_data=provider_data
        )
        
        session.add(audit_log)
        session.commit()


# Global signature service instance
_signature_service: Optional[SignatureService] = None


def get_signature_service() -> SignatureService:
    """
    Get global signature service instance.
    
    Returns:
        SignatureService: Configured signature service
    """
    global _signature_service
    
    if _signature_service is None:
        _signature_service = SignatureService()
    
    return _signature_service


# Export service
__all__ = [
    "SignatureService",
    "SignatureServiceError",
    "SignatureWorkflowError",
    "get_signature_service",
]
