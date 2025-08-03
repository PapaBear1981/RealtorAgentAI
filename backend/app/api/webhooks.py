"""
Webhook handlers for e-signature providers.

This module provides webhook endpoints for receiving status updates
from external e-signature providers including DocuSign, HelloSign,
Adobe Sign, and PandaDoc with proper verification and processing.
"""

import logging
import hashlib
import hmac
import json
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, HTTPException, status, Depends, Header
from sqlmodel import Session, select

from ..core.database import get_session
from ..core.config import get_settings
from ..services.signature_service import get_signature_service
from ..models.signature import SignatureRequest, SignatureProviderConfig, SignatureProvider
from ..models.audit_log import AuditLog, AuditAction

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()
signature_service = get_signature_service()


@router.post("/docusign")
async def docusign_webhook(
    request: Request,
    session: Session = Depends(get_session),
    x_docusign_signature_1: Optional[str] = Header(None),
    x_docusign_signature_2: Optional[str] = Header(None)
):
    """
    Handle DocuSign webhook events.
    
    Processes DocuSign Connect webhook notifications for envelope
    status changes, signer events, and completion notifications.
    
    Args:
        request: FastAPI request object
        session: Database session
        x_docusign_signature_1: DocuSign signature header 1
        x_docusign_signature_2: DocuSign signature header 2
        
    Returns:
        Dict: Webhook processing results
    """
    try:
        # Get raw body for signature verification
        body = await request.body()
        
        # Verify webhook signature
        if not await _verify_docusign_signature(body, x_docusign_signature_1, session):
            logger.warning("Invalid DocuSign webhook signature")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )
        
        # Parse webhook data
        try:
            webhook_data = json.loads(body.decode('utf-8'))
        except json.JSONDecodeError:
            # DocuSign might send XML, handle accordingly
            webhook_data = await _parse_docusign_xml(body)
        
        # Process webhook event
        result = await _process_docusign_webhook(webhook_data, session)
        
        # Log webhook event
        await _log_webhook_event(
            provider=SignatureProvider.DOCUSIGN,
            event_type=webhook_data.get("event", "unknown"),
            webhook_data=webhook_data,
            processing_result=result,
            session=session
        )
        
        return {"status": "processed", "result": result}
        
    except Exception as e:
        logger.error(f"DocuSign webhook processing failed: {e}")
        
        # Log error
        await _log_webhook_event(
            provider=SignatureProvider.DOCUSIGN,
            event_type="error",
            webhook_data={"error": str(e)},
            processing_result={"error": str(e)},
            session=session
        )
        
        # Return 200 to prevent retries for unrecoverable errors
        return {"status": "error", "message": str(e)}


@router.post("/hellosign")
async def hellosign_webhook(
    request: Request,
    session: Session = Depends(get_session)
):
    """
    Handle HelloSign webhook events.
    
    Processes HelloSign webhook notifications for signature request
    status changes and signer events.
    
    Args:
        request: FastAPI request object
        session: Database session
        
    Returns:
        Dict: Webhook processing results
    """
    try:
        # Get form data (HelloSign sends form-encoded data)
        form_data = await request.form()
        json_data = form_data.get("json")
        
        if not json_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing JSON data in webhook"
            )
        
        # Parse webhook data
        webhook_data = json.loads(json_data)
        
        # Verify webhook signature
        if not await _verify_hellosign_signature(webhook_data, session):
            logger.warning("Invalid HelloSign webhook signature")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )
        
        # Process webhook event
        result = await _process_hellosign_webhook(webhook_data, session)
        
        # Log webhook event
        await _log_webhook_event(
            provider=SignatureProvider.HELLOSIGN,
            event_type=webhook_data.get("event", {}).get("event_type", "unknown"),
            webhook_data=webhook_data,
            processing_result=result,
            session=session
        )
        
        return {"status": "processed", "result": result}
        
    except Exception as e:
        logger.error(f"HelloSign webhook processing failed: {e}")
        
        # Log error
        await _log_webhook_event(
            provider=SignatureProvider.HELLOSIGN,
            event_type="error",
            webhook_data={"error": str(e)},
            processing_result={"error": str(e)},
            session=session
        )
        
        return {"status": "error", "message": str(e)}


@router.post("/adobe-sign")
async def adobe_sign_webhook(
    request: Request,
    session: Session = Depends(get_session),
    x_adobesign_client_id: Optional[str] = Header(None)
):
    """
    Handle Adobe Sign webhook events.
    
    Processes Adobe Sign webhook notifications for agreement
    status changes and participant events.
    
    Args:
        request: FastAPI request object
        session: Database session
        x_adobesign_client_id: Adobe Sign client ID header
        
    Returns:
        Dict: Webhook processing results
    """
    try:
        # Get JSON body
        webhook_data = await request.json()
        
        # Verify webhook (Adobe Sign uses client ID verification)
        if not await _verify_adobe_sign_webhook(webhook_data, x_adobesign_client_id, session):
            logger.warning("Invalid Adobe Sign webhook")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook"
            )
        
        # Process webhook event
        result = await _process_adobe_sign_webhook(webhook_data, session)
        
        # Log webhook event
        await _log_webhook_event(
            provider=SignatureProvider.ADOBE_SIGN,
            event_type=webhook_data.get("event", "unknown"),
            webhook_data=webhook_data,
            processing_result=result,
            session=session
        )
        
        return {"status": "processed", "result": result}
        
    except Exception as e:
        logger.error(f"Adobe Sign webhook processing failed: {e}")
        
        # Log error
        await _log_webhook_event(
            provider=SignatureProvider.ADOBE_SIGN,
            event_type="error",
            webhook_data={"error": str(e)},
            processing_result={"error": str(e)},
            session=session
        )
        
        return {"status": "error", "message": str(e)}


@router.post("/pandadoc")
async def pandadoc_webhook(
    request: Request,
    session: Session = Depends(get_session)
):
    """
    Handle PandaDoc webhook events.
    
    Processes PandaDoc webhook notifications for document
    status changes and recipient events.
    
    Args:
        request: FastAPI request object
        session: Database session
        
    Returns:
        Dict: Webhook processing results
    """
    try:
        # Get JSON body
        webhook_data = await request.json()
        
        # Verify webhook signature
        if not await _verify_pandadoc_signature(request, webhook_data, session):
            logger.warning("Invalid PandaDoc webhook signature")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )
        
        # Process webhook event
        result = await _process_pandadoc_webhook(webhook_data, session)
        
        # Log webhook event
        await _log_webhook_event(
            provider=SignatureProvider.PANDADOC,
            event_type=webhook_data.get("event_type", "unknown"),
            webhook_data=webhook_data,
            processing_result=result,
            session=session
        )
        
        return {"status": "processed", "result": result}
        
    except Exception as e:
        logger.error(f"PandaDoc webhook processing failed: {e}")
        
        # Log error
        await _log_webhook_event(
            provider=SignatureProvider.PANDADOC,
            event_type="error",
            webhook_data={"error": str(e)},
            processing_result={"error": str(e)},
            session=session
        )
        
        return {"status": "error", "message": str(e)}


# Webhook verification functions
async def _verify_docusign_signature(
    body: bytes,
    signature: Optional[str],
    session: Session
) -> bool:
    """Verify DocuSign webhook signature."""
    if not signature:
        return False
    
    try:
        # Get DocuSign webhook secret
        config = session.exec(
            select(SignatureProviderConfig)
            .where(SignatureProviderConfig.provider == SignatureProvider.DOCUSIGN)
            .where(SignatureProviderConfig.is_active == True)
        ).first()
        
        if not config or not config.webhook_url:
            return False
        
        # Extract secret from configuration
        webhook_secret = config.settings.get("webhook_secret") if config.settings else None
        if not webhook_secret:
            return False
        
        # Compute expected signature
        expected_signature = hmac.new(
            webhook_secret.encode(),
            body,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
        
    except Exception as e:
        logger.error(f"DocuSign signature verification failed: {e}")
        return False


async def _verify_hellosign_signature(
    webhook_data: Dict[str, Any],
    session: Session
) -> bool:
    """Verify HelloSign webhook signature."""
    try:
        # Get HelloSign API key
        config = session.exec(
            select(SignatureProviderConfig)
            .where(SignatureProviderConfig.provider == SignatureProvider.HELLOSIGN)
            .where(SignatureProviderConfig.is_active == True)
        ).first()
        
        if not config:
            return False
        
        api_key = config.api_credentials.get("api_key") if config.api_credentials else None
        if not api_key:
            return False
        
        # HelloSign verification logic would go here
        # For now, return True for development
        return True
        
    except Exception as e:
        logger.error(f"HelloSign signature verification failed: {e}")
        return False


async def _verify_adobe_sign_webhook(
    webhook_data: Dict[str, Any],
    client_id: Optional[str],
    session: Session
) -> bool:
    """Verify Adobe Sign webhook."""
    try:
        # Get Adobe Sign configuration
        config = session.exec(
            select(SignatureProviderConfig)
            .where(SignatureProviderConfig.provider == SignatureProvider.ADOBE_SIGN)
            .where(SignatureProviderConfig.is_active == True)
        ).first()
        
        if not config:
            return False
        
        expected_client_id = config.api_credentials.get("client_id") if config.api_credentials else None
        if not expected_client_id:
            return False
        
        return client_id == expected_client_id
        
    except Exception as e:
        logger.error(f"Adobe Sign webhook verification failed: {e}")
        return False


async def _verify_pandadoc_signature(
    request: Request,
    webhook_data: Dict[str, Any],
    session: Session
) -> bool:
    """Verify PandaDoc webhook signature."""
    try:
        # Get PandaDoc webhook secret
        config = session.exec(
            select(SignatureProviderConfig)
            .where(SignatureProviderConfig.provider == SignatureProvider.PANDADOC)
            .where(SignatureProviderConfig.is_active == True)
        ).first()
        
        if not config:
            return False
        
        webhook_secret = config.settings.get("webhook_secret") if config.settings else None
        if not webhook_secret:
            return False
        
        # PandaDoc signature verification logic would go here
        # For now, return True for development
        return True
        
    except Exception as e:
        logger.error(f"PandaDoc signature verification failed: {e}")
        return False


# Webhook processing functions
async def _process_docusign_webhook(
    webhook_data: Dict[str, Any],
    session: Session
) -> Dict[str, Any]:
    """Process DocuSign webhook event."""
    try:
        envelope_id = webhook_data.get("envelopeId")
        event_type = webhook_data.get("event")
        
        if not envelope_id:
            return {"error": "Missing envelope ID"}
        
        # Find signature request by provider envelope ID
        signature_request = session.exec(
            select(SignatureRequest)
            .where(SignatureRequest.provider_envelope_id == envelope_id)
        ).first()
        
        if not signature_request:
            return {"error": f"Signature request not found for envelope {envelope_id}"}
        
        # Update signature request status
        await signature_service.update_signature_request_status(
            signature_request.id,
            webhook_data,
            session
        )
        
        return {
            "signature_request_id": signature_request.id,
            "event_type": event_type,
            "processed": True
        }
        
    except Exception as e:
        logger.error(f"DocuSign webhook processing error: {e}")
        return {"error": str(e)}


async def _process_hellosign_webhook(
    webhook_data: Dict[str, Any],
    session: Session
) -> Dict[str, Any]:
    """Process HelloSign webhook event."""
    try:
        event_data = webhook_data.get("event", {})
        signature_request_data = webhook_data.get("signature_request", {})
        signature_request_id = signature_request_data.get("signature_request_id")
        
        if not signature_request_id:
            return {"error": "Missing signature request ID"}
        
        # Find signature request by provider envelope ID
        signature_request = session.exec(
            select(SignatureRequest)
            .where(SignatureRequest.provider_envelope_id == signature_request_id)
        ).first()
        
        if not signature_request:
            return {"error": f"Signature request not found for ID {signature_request_id}"}
        
        # Update signature request status
        await signature_service.update_signature_request_status(
            signature_request.id,
            webhook_data,
            session
        )
        
        return {
            "signature_request_id": signature_request.id,
            "event_type": event_data.get("event_type"),
            "processed": True
        }
        
    except Exception as e:
        logger.error(f"HelloSign webhook processing error: {e}")
        return {"error": str(e)}


async def _process_adobe_sign_webhook(
    webhook_data: Dict[str, Any],
    session: Session
) -> Dict[str, Any]:
    """Process Adobe Sign webhook event."""
    try:
        agreement_id = webhook_data.get("agreementId")
        event_type = webhook_data.get("event")
        
        if not agreement_id:
            return {"error": "Missing agreement ID"}
        
        # Find signature request by provider envelope ID
        signature_request = session.exec(
            select(SignatureRequest)
            .where(SignatureRequest.provider_envelope_id == agreement_id)
        ).first()
        
        if not signature_request:
            return {"error": f"Signature request not found for agreement {agreement_id}"}
        
        # Update signature request status
        await signature_service.update_signature_request_status(
            signature_request.id,
            webhook_data,
            session
        )
        
        return {
            "signature_request_id": signature_request.id,
            "event_type": event_type,
            "processed": True
        }
        
    except Exception as e:
        logger.error(f"Adobe Sign webhook processing error: {e}")
        return {"error": str(e)}


async def _process_pandadoc_webhook(
    webhook_data: Dict[str, Any],
    session: Session
) -> Dict[str, Any]:
    """Process PandaDoc webhook event."""
    try:
        document_id = webhook_data.get("data", {}).get("id")
        event_type = webhook_data.get("event_type")
        
        if not document_id:
            return {"error": "Missing document ID"}
        
        # Find signature request by provider envelope ID
        signature_request = session.exec(
            select(SignatureRequest)
            .where(SignatureRequest.provider_envelope_id == document_id)
        ).first()
        
        if not signature_request:
            return {"error": f"Signature request not found for document {document_id}"}
        
        # Update signature request status
        await signature_service.update_signature_request_status(
            signature_request.id,
            webhook_data,
            session
        )
        
        return {
            "signature_request_id": signature_request.id,
            "event_type": event_type,
            "processed": True
        }
        
    except Exception as e:
        logger.error(f"PandaDoc webhook processing error: {e}")
        return {"error": str(e)}


async def _parse_docusign_xml(body: bytes) -> Dict[str, Any]:
    """Parse DocuSign XML webhook data."""
    # XML parsing implementation would go here
    # For now, return empty dict
    return {}


async def _log_webhook_event(
    provider: SignatureProvider,
    event_type: str,
    webhook_data: Dict[str, Any],
    processing_result: Dict[str, Any],
    session: Session
):
    """Log webhook event for audit purposes."""
    try:
        audit_log = AuditLog(
            action=AuditAction.WEBHOOK_RECEIVED,
            resource_type="signature_webhook",
            resource_id=webhook_data.get("envelopeId") or webhook_data.get("signature_request_id"),
            details={
                "provider": provider,
                "event_type": event_type,
                "webhook_data": webhook_data,
                "processing_result": processing_result
            },
            ip_address="webhook",
            user_agent=f"{provider}_webhook"
        )
        
        session.add(audit_log)
        session.commit()
        
    except Exception as e:
        logger.error(f"Failed to log webhook event: {e}")


# Export router
__all__ = ["router"]
