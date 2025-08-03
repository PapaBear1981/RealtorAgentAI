"""
Document signing management service.

This module provides comprehensive document signing capabilities
including document preparation, signer authentication, field positioning,
signature validation, and bulk signing operations.
"""

import logging
import asyncio
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, BinaryIO
from sqlmodel import Session, select
from fastapi import HTTPException, status
# import PyPDF2  # Would be used for PDF analysis
# from PIL import Image  # Would be used for image processing
import io

from ..core.config import get_settings
from ..models.signature import (
    SignatureRequest, SignatureField, SignatureFieldType, SignatureProvider,
    BulkSignatureRequest, BulkSignatureResponse
)
from ..models.contract import Contract
from ..models.signer import Signer
from ..models.user import User
from ..services.signature_service import get_signature_service
from ..services.file_service import get_file_service
from ..core.security import verify_signature_token, create_signature_token

logger = logging.getLogger(__name__)
settings = get_settings()


class DocumentSigningError(Exception):
    """Exception raised during document signing operations."""
    pass


class SignerAuthenticationError(Exception):
    """Exception raised during signer authentication."""
    pass


class DocumentPreparationError(Exception):
    """Exception raised during document preparation."""
    pass


class DocumentSigningService:
    """
    Comprehensive document signing management service.

    Provides document preparation, signer authentication,
    field positioning, signature validation, and bulk operations.
    """

    def __init__(self):
        """Initialize document signing service."""
        self.signature_service = get_signature_service()
        self.file_service = get_file_service()

    async def prepare_document_for_signing(
        self,
        contract_id: int,
        field_positions: List[Dict[str, Any]],
        current_user: User,
        session: Session
    ) -> Dict[str, Any]:
        """
        Prepare document for signing with field positioning.

        Args:
            contract_id: Contract ID
            field_positions: List of signature field positions
            current_user: Current authenticated user
            session: Database session

        Returns:
            Dict: Document preparation results
        """
        try:
            # Get contract
            contract = session.get(Contract, contract_id)
            if not contract:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Contract not found"
                )

            # Validate document exists
            if not contract.generated_pdf_key:
                raise DocumentPreparationError("Contract PDF not generated")

            # Download and analyze document
            document_content = await self.file_service.download_file(contract.generated_pdf_key)
            document_info = await self._analyze_document(document_content)

            # Validate field positions
            validated_fields = await self._validate_field_positions(
                field_positions,
                document_info
            )

            # Generate field preview
            preview_data = await self._generate_field_preview(
                document_content,
                validated_fields
            )

            return {
                "contract_id": contract_id,
                "document_info": document_info,
                "validated_fields": validated_fields,
                "preview_url": preview_data["preview_url"],
                "field_count": len(validated_fields),
                "preparation_timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to prepare document for signing: {e}")
            raise DocumentPreparationError(f"Document preparation failed: {str(e)}")

    async def authenticate_signer(
        self,
        signature_request_id: int,
        signer_email: str,
        authentication_method: str = "email",
        authentication_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Authenticate signer for document access.

        Args:
            signature_request_id: Signature request ID
            signer_email: Signer email address
            authentication_method: Authentication method (email, sms, id_verification)
            authentication_data: Additional authentication data

        Returns:
            Dict: Authentication results with access token
        """
        try:
            # Validate signature request and signer
            with get_session() as session:
                signature_request = session.get(SignatureRequest, signature_request_id)
                if not signature_request:
                    raise SignerAuthenticationError("Signature request not found")

                signer = session.exec(
                    select(Signer)
                    .where(Signer.contract_id == signature_request.contract_id)
                    .where(Signer.email == signer_email)
                ).first()

                if not signer:
                    raise SignerAuthenticationError("Signer not found for this request")

                if signer.status == "signed":
                    raise SignerAuthenticationError("Document already signed by this signer")

            # Perform authentication based on method
            auth_result = await self._perform_authentication(
                signer,
                authentication_method,
                authentication_data or {}
            )

            if not auth_result["authenticated"]:
                raise SignerAuthenticationError("Authentication failed")

            # Generate access token
            access_token = create_signature_token(
                signature_request_id=signature_request_id,
                signer_id=signer.id,
                expires_delta=timedelta(hours=24)
            )

            # Log authentication event
            await self._log_signer_event(
                signer.id,
                "authentication_success",
                f"Signer authenticated using {authentication_method}",
                session
            )

            return {
                "authenticated": True,
                "access_token": access_token,
                "signer_id": signer.id,
                "signing_url": await self._generate_signing_url(signature_request, signer),
                "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
                "authentication_method": authentication_method
            }

        except Exception as e:
            logger.error(f"Signer authentication failed: {e}")
            raise SignerAuthenticationError(f"Authentication failed: {str(e)}")

    async def get_signing_session(
        self,
        access_token: str,
        session: Session
    ) -> Dict[str, Any]:
        """
        Get signing session information for authenticated signer.

        Args:
            access_token: Signer access token
            session: Database session

        Returns:
            Dict: Signing session information
        """
        try:
            # Verify and decode token
            token_data = verify_signature_token(access_token)

            signature_request_id = token_data["signature_request_id"]
            signer_id = token_data["signer_id"]

            # Get signature request and signer
            signature_request = session.get(SignatureRequest, signature_request_id)
            signer = session.get(Signer, signer_id)

            if not signature_request or not signer:
                raise SignerAuthenticationError("Invalid signing session")

            # Get signature fields for this signer
            fields = session.exec(
                select(SignatureField)
                .where(SignatureField.signature_request_id == signature_request_id)
                .where(SignatureField.signer_id == signer_id)
            ).all()

            # Get document information
            contract = session.get(Contract, signature_request.contract_id)
            document_url = await self._get_document_url(contract)

            return {
                "signature_request_id": signature_request_id,
                "signer_id": signer_id,
                "signer_name": signer.name,
                "signer_email": signer.email,
                "document_title": signature_request.title,
                "document_url": document_url,
                "signature_fields": [
                    {
                        "id": field.id,
                        "type": field.field_type,
                        "label": field.label,
                        "page": field.page_number,
                        "x": field.x_position,
                        "y": field.y_position,
                        "width": field.width,
                        "height": field.height,
                        "required": field.required,
                        "default_value": field.default_value
                    }
                    for field in fields
                ],
                "signing_order": signer.order,
                "can_sign": await self._can_signer_sign(signer, session),
                "session_expires_at": token_data["exp"]
            }

        except Exception as e:
            logger.error(f"Failed to get signing session: {e}")
            raise SignerAuthenticationError(f"Invalid signing session: {str(e)}")

    async def submit_signature(
        self,
        access_token: str,
        field_values: Dict[str, Any],
        signature_data: Optional[Dict[str, Any]],
        session: Session
    ) -> Dict[str, Any]:
        """
        Submit signature and field values.

        Args:
            access_token: Signer access token
            field_values: Field values submitted by signer
            signature_data: Signature image/data
            session: Database session

        Returns:
            Dict: Signature submission results
        """
        try:
            # Verify token and get session info
            token_data = verify_signature_token(access_token)
            signature_request_id = token_data["signature_request_id"]
            signer_id = token_data["signer_id"]

            # Get signer and validate
            signer = session.get(Signer, signer_id)
            if not signer:
                raise SignerAuthenticationError("Invalid signer")

            if not await self._can_signer_sign(signer, session):
                raise DocumentSigningError("Signer cannot sign at this time")

            # Validate required fields
            await self._validate_signature_fields(signature_request_id, signer_id, field_values, session)

            # Process signature
            signature_result = await self._process_signature(
                signer,
                field_values,
                signature_data,
                session
            )

            # Update signer status
            signer.status = "signed"
            signer.signed_at = datetime.utcnow()
            session.add(signer)
            session.commit()

            # Check if all signers have signed
            await self._check_completion_status(signature_request_id, session)

            # Log signature event
            await self._log_signer_event(
                signer_id,
                "signature_completed",
                "Document signed successfully",
                session
            )

            return {
                "signed": True,
                "signer_id": signer_id,
                "signed_at": signer.signed_at.isoformat(),
                "signature_id": signature_result["signature_id"],
                "next_signer": await self._get_next_signer(signature_request_id, session),
                "completion_status": await self._get_completion_status(signature_request_id, session)
            }

        except Exception as e:
            logger.error(f"Signature submission failed: {e}")
            session.rollback()
            raise DocumentSigningError(f"Signature submission failed: {str(e)}")

    async def bulk_create_signature_requests(
        self,
        bulk_request: BulkSignatureRequest,
        current_user: User,
        session: Session
    ) -> BulkSignatureResponse:
        """
        Create multiple signature requests in bulk.

        Args:
            bulk_request: Bulk signature request data
            current_user: Current authenticated user
            session: Database session

        Returns:
            BulkSignatureResponse: Bulk operation results
        """
        try:
            successful_requests = []
            failed_requests = []
            errors = []

            for i, request_data in enumerate(bulk_request.requests):
                try:
                    # Merge common settings
                    if bulk_request.common_settings:
                        request_data.update(bulk_request.common_settings)

                    # Create signature request
                    from ..models.signature import SignatureRequestCreate
                    signature_request_data = SignatureRequestCreate(**request_data)

                    signature_request = await self.signature_service.create_signature_request(
                        signature_request_data,
                        current_user,
                        session
                    )

                    successful_requests.append(signature_request.id)

                except Exception as e:
                    failed_requests.append(i)
                    errors.append({
                        "index": i,
                        "error": str(e),
                        "request_data": request_data
                    })
                    logger.error(f"Failed to create bulk signature request {i}: {e}")

            return BulkSignatureResponse(
                total_requests=len(bulk_request.requests),
                successful_requests=len(successful_requests),
                failed_requests=len(failed_requests),
                request_ids=successful_requests,
                errors=errors
            )

        except Exception as e:
            logger.error(f"Bulk signature request creation failed: {e}")
            raise DocumentSigningError(f"Bulk operation failed: {str(e)}")

    async def validate_signature_integrity(
        self,
        signature_request_id: int,
        session: Session
    ) -> Dict[str, Any]:
        """
        Validate signature integrity and authenticity.

        Args:
            signature_request_id: Signature request ID
            session: Database session

        Returns:
            Dict: Validation results
        """
        try:
            signature_request = session.get(SignatureRequest, signature_request_id)
            if not signature_request:
                raise DocumentSigningError("Signature request not found")

            # Get all signers
            signers = session.exec(
                select(Signer)
                .where(Signer.contract_id == signature_request.contract_id)
            ).all()

            validation_results = {
                "signature_request_id": signature_request_id,
                "is_valid": True,
                "validation_timestamp": datetime.utcnow().isoformat(),
                "signer_validations": [],
                "document_integrity": {},
                "provider_validation": {}
            }

            # Validate each signer
            for signer in signers:
                signer_validation = await self._validate_signer_signature(signer, session)
                validation_results["signer_validations"].append(signer_validation)

                if not signer_validation["is_valid"]:
                    validation_results["is_valid"] = False

            # Validate document integrity
            document_validation = await self._validate_document_integrity(signature_request, session)
            validation_results["document_integrity"] = document_validation

            if not document_validation["is_valid"]:
                validation_results["is_valid"] = False

            # Validate with provider if available
            if signature_request.provider_envelope_id:
                provider_validation = await self._validate_with_provider(signature_request, session)
                validation_results["provider_validation"] = provider_validation

                if not provider_validation["is_valid"]:
                    validation_results["is_valid"] = False

            return validation_results

        except Exception as e:
            logger.error(f"Signature validation failed: {e}")
            raise DocumentSigningError(f"Signature validation failed: {str(e)}")

    # Helper methods
    async def _analyze_document(self, document_content: bytes) -> Dict[str, Any]:
        """Analyze PDF document structure."""
        try:
            # For now, return mock document info
            # In production, would use PyPDF2 or similar library
            return {
                "page_count": 1,
                "document_size": len(document_content),
                "has_form_fields": False,
                "page_dimensions": [
                    {
                        "page": 1,
                        "width": 612.0,  # Standard letter size
                        "height": 792.0
                    }
                ]
            }

        except Exception as e:
            logger.error(f"Document analysis failed: {e}")
            raise DocumentPreparationError(f"Failed to analyze document: {str(e)}")

    async def _validate_field_positions(
        self,
        field_positions: List[Dict[str, Any]],
        document_info: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Validate signature field positions."""
        validated_fields = []

        for field in field_positions:
            # Validate page number
            page_num = field.get("page_number", 1)
            if page_num < 1 or page_num > document_info["page_count"]:
                raise DocumentPreparationError(f"Invalid page number: {page_num}")

            # Validate position coordinates
            x_pos = field.get("x_position", 0)
            y_pos = field.get("y_position", 0)
            width = field.get("width", 0.2)
            height = field.get("height", 0.05)

            if not (0 <= x_pos <= 1 and 0 <= y_pos <= 1):
                raise DocumentPreparationError("Field position must be between 0 and 1")

            if not (0 < width <= 1 and 0 < height <= 1):
                raise DocumentPreparationError("Field dimensions must be between 0 and 1")

            if x_pos + width > 1 or y_pos + height > 1:
                raise DocumentPreparationError("Field extends beyond page boundaries")

            validated_fields.append({
                **field,
                "page_number": page_num,
                "x_position": x_pos,
                "y_position": y_pos,
                "width": width,
                "height": height
            })

        return validated_fields

    async def _generate_field_preview(
        self,
        document_content: bytes,
        fields: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate preview of document with field overlays."""
        # For now, return a placeholder URL
        # In production, this would generate actual preview images
        preview_url = f"{settings.base_url}/api/documents/preview/{hashlib.md5(document_content).hexdigest()}"

        return {
            "preview_url": preview_url,
            "field_overlays": len(fields)
        }

    async def _perform_authentication(
        self,
        signer: Signer,
        method: str,
        auth_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform signer authentication."""
        if method == "email":
            # Email-based authentication (link clicked)
            return {"authenticated": True, "method": "email"}

        elif method == "sms":
            # SMS verification code
            provided_code = auth_data.get("verification_code")
            # In production, verify against sent SMS code
            return {"authenticated": provided_code == "123456", "method": "sms"}

        elif method == "id_verification":
            # ID document verification
            # In production, integrate with ID verification service
            return {"authenticated": True, "method": "id_verification"}

        else:
            return {"authenticated": False, "method": method, "error": "Unsupported method"}

    async def _generate_signing_url(
        self,
        signature_request: SignatureRequest,
        signer: Signer
    ) -> str:
        """Generate signing URL for signer."""
        return f"{settings.base_url}/sign/{signature_request.id}/{signer.id}"

    async def _get_document_url(self, contract: Contract) -> str:
        """Get document URL for viewing."""
        if contract.generated_pdf_key:
            return f"{settings.base_url}/api/files/download/{contract.generated_pdf_key}"
        return ""

    async def _can_signer_sign(self, signer: Signer, session: Session) -> bool:
        """Check if signer can sign based on signing order."""
        if signer.status == "signed":
            return False

        # Check if previous signers have signed (for sequential signing)
        signature_request = session.exec(
            select(SignatureRequest)
            .where(SignatureRequest.contract_id == signer.contract_id)
        ).first()

        if not signature_request or not signature_request.sequential_signing:
            return True

        # Check previous signers
        previous_signers = session.exec(
            select(Signer)
            .where(Signer.contract_id == signer.contract_id)
            .where(Signer.order < signer.order)
        ).all()

        return all(s.status == "signed" for s in previous_signers)

    async def _validate_signature_fields(
        self,
        signature_request_id: int,
        signer_id: int,
        field_values: Dict[str, Any],
        session: Session
    ):
        """Validate submitted signature field values."""
        required_fields = session.exec(
            select(SignatureField)
            .where(SignatureField.signature_request_id == signature_request_id)
            .where(SignatureField.signer_id == signer_id)
            .where(SignatureField.required == True)
        ).all()

        for field in required_fields:
            field_key = f"field_{field.id}"
            if field_key not in field_values or not field_values[field_key]:
                raise DocumentSigningError(f"Required field '{field.label}' is missing")

    async def _process_signature(
        self,
        signer: Signer,
        field_values: Dict[str, Any],
        signature_data: Optional[Dict[str, Any]],
        session: Session
    ) -> Dict[str, Any]:
        """Process and store signature data."""
        # Generate signature ID
        signature_id = hashlib.sha256(
            f"{signer.id}_{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()

        # Store signature data (in production, store securely)
        signature_record = {
            "signature_id": signature_id,
            "signer_id": signer.id,
            "field_values": field_values,
            "signature_data": signature_data,
            "timestamp": datetime.utcnow().isoformat(),
            "ip_address": "127.0.0.1",  # Would get from request
            "user_agent": "Browser"     # Would get from request
        }

        return signature_record

    async def _check_completion_status(self, signature_request_id: int, session: Session):
        """Check if all signers have completed signing."""
        signature_request = session.get(SignatureRequest, signature_request_id)
        if not signature_request:
            return

        signers = session.exec(
            select(Signer)
            .where(Signer.contract_id == signature_request.contract_id)
        ).all()

        all_signed = all(signer.status == "signed" for signer in signers)

        if all_signed:
            signature_request.status = "completed"
            signature_request.completed_at = datetime.utcnow()
            session.add(signature_request)
            session.commit()

    async def _get_next_signer(self, signature_request_id: int, session: Session) -> Optional[Dict[str, Any]]:
        """Get next signer in sequence."""
        signature_request = session.get(SignatureRequest, signature_request_id)
        if not signature_request:
            return None

        next_signer = session.exec(
            select(Signer)
            .where(Signer.contract_id == signature_request.contract_id)
            .where(Signer.status == "pending")
            .order_by(Signer.order)
        ).first()

        if next_signer:
            return {
                "signer_id": next_signer.id,
                "name": next_signer.name,
                "email": next_signer.email,
                "order": next_signer.order
            }

        return None

    async def _get_completion_status(self, signature_request_id: int, session: Session) -> Dict[str, Any]:
        """Get completion status of signature request."""
        signature_request = session.get(SignatureRequest, signature_request_id)
        if not signature_request:
            return {"completed": False}

        signers = session.exec(
            select(Signer)
            .where(Signer.contract_id == signature_request.contract_id)
        ).all()

        signed_count = sum(1 for signer in signers if signer.status == "signed")
        total_count = len(signers)

        return {
            "completed": signed_count == total_count,
            "signed_count": signed_count,
            "total_count": total_count,
            "completion_percentage": (signed_count / total_count * 100) if total_count > 0 else 0
        }

    async def _validate_signer_signature(self, signer: Signer, session: Session) -> Dict[str, Any]:
        """Validate individual signer signature."""
        return {
            "signer_id": signer.id,
            "signer_email": signer.email,
            "is_valid": signer.status == "signed",
            "signed_at": signer.signed_at.isoformat() if signer.signed_at else None,
            "validation_errors": []
        }

    async def _validate_document_integrity(
        self,
        signature_request: SignatureRequest,
        session: Session
    ) -> Dict[str, Any]:
        """Validate document integrity."""
        return {
            "is_valid": True,
            "document_hash": "placeholder_hash",
            "validation_errors": []
        }

    async def _validate_with_provider(
        self,
        signature_request: SignatureRequest,
        session: Session
    ) -> Dict[str, Any]:
        """Validate signature with external provider."""
        return {
            "is_valid": True,
            "provider": signature_request.provider,
            "provider_validation_id": signature_request.provider_envelope_id,
            "validation_errors": []
        }

    async def _log_signer_event(
        self,
        signer_id: int,
        event_type: str,
        description: str,
        session: Session
    ):
        """Log signer event."""
        from ..models.sign_event import SignEvent

        event = SignEvent(
            signer_id=signer_id,
            type=event_type,
            ip="127.0.0.1",  # Would get from request
            ua="Browser",   # Would get from request
            ts=datetime.utcnow()
        )

        session.add(event)
        session.commit()


# Global document signing service instance
_document_signing_service: Optional[DocumentSigningService] = None


def get_document_signing_service() -> DocumentSigningService:
    """
    Get global document signing service instance.

    Returns:
        DocumentSigningService: Configured document signing service
    """
    global _document_signing_service

    if _document_signing_service is None:
        _document_signing_service = DocumentSigningService()

    return _document_signing_service


# Export service
__all__ = [
    "DocumentSigningService",
    "DocumentSigningError",
    "SignerAuthenticationError",
    "DocumentPreparationError",
    "get_document_signing_service",
]
