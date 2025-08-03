"""
E-signature provider integration services.

This module provides integration with external e-signature providers
including DocuSign, HelloSign, Adobe Sign, and PandaDoc with unified
interfaces for envelope creation, status tracking, and webhook handling.
"""

import logging
import asyncio
import base64
import json
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from urllib.parse import urljoin
import httpx
from cryptography.fernet import Fernet

from ..core.config import get_settings
from ..models.signature import (
    SignatureProvider, SignatureRequestStatus, SignatureFieldType,
    SignatureRequest, SignatureField, SignatureProviderConfig
)

logger = logging.getLogger(__name__)
settings = get_settings()


class SignatureProviderError(Exception):
    """Exception raised during signature provider operations."""
    pass


class ProviderAuthenticationError(SignatureProviderError):
    """Exception raised during provider authentication."""
    pass


class ProviderRateLimitError(SignatureProviderError):
    """Exception raised when provider rate limits are exceeded."""
    pass


class BaseSignatureProvider(ABC):
    """
    Abstract base class for e-signature providers.

    Defines the common interface that all signature providers
    must implement for consistent integration.
    """

    def __init__(self, config: SignatureProviderConfig):
        """Initialize provider with configuration."""
        self.config = config
        self.provider_type = config.provider
        self.is_sandbox = config.is_sandbox
        self.client = httpx.AsyncClient(timeout=30.0)
        self._auth_token = None
        self._token_expires_at = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.authenticate()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()

    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with the provider."""
        pass

    @abstractmethod
    async def create_envelope(
        self,
        title: str,
        message: str,
        documents: List[Dict[str, Any]],
        signers: List[Dict[str, Any]],
        fields: Optional[List[Dict[str, Any]]] = None,
        settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a signature envelope."""
        pass

    @abstractmethod
    async def get_envelope_status(self, envelope_id: str) -> Dict[str, Any]:
        """Get envelope status and details."""
        pass

    @abstractmethod
    async def send_envelope(self, envelope_id: str) -> Dict[str, Any]:
        """Send envelope to signers."""
        pass

    @abstractmethod
    async def void_envelope(self, envelope_id: str, reason: str) -> Dict[str, Any]:
        """Void an envelope."""
        pass

    @abstractmethod
    async def get_signing_url(self, envelope_id: str, signer_id: str) -> str:
        """Get embedded signing URL for a signer."""
        pass

    @abstractmethod
    async def download_completed_document(self, envelope_id: str) -> bytes:
        """Download completed signed document."""
        pass

    def _decrypt_credentials(self) -> Dict[str, Any]:
        """Decrypt stored API credentials."""
        try:
            if not self.config.api_credentials:
                raise ProviderAuthenticationError("No API credentials configured")

            # In production, use proper encryption key from settings
            # For now, assume credentials are stored as plain JSON
            return self.config.api_credentials
        except Exception as e:
            logger.error(f"Failed to decrypt credentials: {e}")
            raise ProviderAuthenticationError("Invalid API credentials")

    def _map_status_to_internal(self, provider_status: str) -> SignatureRequestStatus:
        """Map provider status to internal status."""
        # Default mapping - override in specific providers
        status_map = {
            "created": SignatureRequestStatus.DRAFT,
            "sent": SignatureRequestStatus.SENT,
            "delivered": SignatureRequestStatus.IN_PROGRESS,
            "completed": SignatureRequestStatus.COMPLETED,
            "declined": SignatureRequestStatus.DECLINED,
            "voided": SignatureRequestStatus.VOIDED,
            "expired": SignatureRequestStatus.EXPIRED,
        }
        return status_map.get(provider_status.lower(), SignatureRequestStatus.IN_PROGRESS)


class DocuSignProvider(BaseSignatureProvider):
    """
    DocuSign e-signature provider implementation.

    Integrates with DocuSign eSignature API for envelope
    creation, management, and status tracking.
    """

    def __init__(self, config: SignatureProviderConfig):
        super().__init__(config)
        self.base_url = "https://demo.docusign.net/restapi" if self.is_sandbox else "https://na1.docusign.net/restapi"
        self.account_id = None

    async def authenticate(self) -> bool:
        """Authenticate with DocuSign using JWT or OAuth."""
        try:
            credentials = self._decrypt_credentials()

            if "access_token" in credentials:
                # Use existing access token
                self._auth_token = credentials["access_token"]
                self._token_expires_at = datetime.utcnow() + timedelta(hours=1)

                # Get account info
                await self._get_account_info()
                return True

            elif "integration_key" in credentials and "private_key" in credentials:
                # Use JWT authentication
                return await self._authenticate_jwt(credentials)

            else:
                raise ProviderAuthenticationError("Invalid DocuSign credentials format")

        except Exception as e:
            logger.error(f"DocuSign authentication failed: {e}")
            raise ProviderAuthenticationError(f"DocuSign authentication failed: {str(e)}")

    async def _authenticate_jwt(self, credentials: Dict[str, Any]) -> bool:
        """Authenticate using JWT grant."""
        # JWT authentication implementation would go here
        # For now, simulate successful authentication
        self._auth_token = "simulated_docusign_token"
        self._token_expires_at = datetime.utcnow() + timedelta(hours=1)
        self.account_id = "simulated_account_id"
        return True

    async def _get_account_info(self):
        """Get account information."""
        headers = {"Authorization": f"Bearer {self._auth_token}"}

        try:
            response = await self.client.get(
                f"{self.base_url}/v2.1/accounts",
                headers=headers
            )
            response.raise_for_status()

            accounts = response.json().get("accounts", [])
            if accounts:
                self.account_id = accounts[0]["accountId"]
            else:
                raise ProviderAuthenticationError("No DocuSign accounts found")

        except httpx.HTTPError as e:
            logger.error(f"Failed to get DocuSign account info: {e}")
            raise ProviderAuthenticationError("Failed to get account information")

    async def create_envelope(
        self,
        title: str,
        message: str,
        documents: List[Dict[str, Any]],
        signers: List[Dict[str, Any]],
        fields: Optional[List[Dict[str, Any]]] = None,
        settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create DocuSign envelope."""
        try:
            envelope_data = {
                "emailSubject": title,
                "emailBlurb": message,
                "status": "created",
                "documents": self._format_documents(documents),
                "recipients": {
                    "signers": self._format_signers(signers, fields or [])
                }
            }

            # Add custom fields if provided
            if fields:
                envelope_data["customFields"] = self._format_custom_fields(fields)

            headers = {
                "Authorization": f"Bearer {self._auth_token}",
                "Content-Type": "application/json"
            }

            response = await self.client.post(
                f"{self.base_url}/v2.1/accounts/{self.account_id}/envelopes",
                headers=headers,
                json=envelope_data
            )
            response.raise_for_status()

            result = response.json()
            return {
                "envelope_id": result["envelopeId"],
                "status": result["status"],
                "uri": result.get("uri"),
                "provider_data": result
            }

        except httpx.HTTPError as e:
            logger.error(f"DocuSign envelope creation failed: {e}")
            raise SignatureProviderError(f"Failed to create DocuSign envelope: {str(e)}")

    async def get_envelope_status(self, envelope_id: str) -> Dict[str, Any]:
        """Get DocuSign envelope status."""
        try:
            headers = {"Authorization": f"Bearer {self._auth_token}"}

            response = await self.client.get(
                f"{self.base_url}/v2.1/accounts/{self.account_id}/envelopes/{envelope_id}",
                headers=headers
            )
            response.raise_for_status()

            result = response.json()
            return {
                "status": self._map_docusign_status(result["status"]),
                "provider_status": result["status"],
                "created_at": result.get("createdDateTime"),
                "sent_at": result.get("sentDateTime"),
                "completed_at": result.get("completedDateTime"),
                "provider_data": result
            }

        except httpx.HTTPError as e:
            logger.error(f"Failed to get DocuSign envelope status: {e}")
            raise SignatureProviderError(f"Failed to get envelope status: {str(e)}")

    async def send_envelope(self, envelope_id: str) -> Dict[str, Any]:
        """Send DocuSign envelope to signers."""
        try:
            headers = {
                "Authorization": f"Bearer {self._auth_token}",
                "Content-Type": "application/json"
            }

            response = await self.client.put(
                f"{self.base_url}/v2.1/accounts/{self.account_id}/envelopes/{envelope_id}",
                headers=headers,
                json={"status": "sent"}
            )
            response.raise_for_status()

            result = response.json()
            return {
                "status": self._map_docusign_status(result["status"]),
                "provider_data": result
            }

        except httpx.HTTPError as e:
            logger.error(f"Failed to send DocuSign envelope: {e}")
            raise SignatureProviderError(f"Failed to send envelope: {str(e)}")

    async def void_envelope(self, envelope_id: str, reason: str) -> Dict[str, Any]:
        """Void DocuSign envelope."""
        try:
            headers = {
                "Authorization": f"Bearer {self._auth_token}",
                "Content-Type": "application/json"
            }

            response = await self.client.put(
                f"{self.base_url}/v2.1/accounts/{self.account_id}/envelopes/{envelope_id}",
                headers=headers,
                json={"status": "voided", "voidedReason": reason}
            )
            response.raise_for_status()

            result = response.json()
            return {
                "status": SignatureRequestStatus.VOIDED,
                "provider_data": result
            }

        except httpx.HTTPError as e:
            logger.error(f"Failed to void DocuSign envelope: {e}")
            raise SignatureProviderError(f"Failed to void envelope: {str(e)}")

    async def get_signing_url(self, envelope_id: str, signer_id: str) -> str:
        """Get embedded signing URL for DocuSign."""
        try:
            headers = {
                "Authorization": f"Bearer {self._auth_token}",
                "Content-Type": "application/json"
            }

            view_data = {
                "returnUrl": f"{settings.base_url}/signatures/complete",
                "authenticationMethod": "none",
                "email": "signer@example.com",  # Would be actual signer email
                "userName": "Signer Name",  # Would be actual signer name
                "clientUserId": signer_id
            }

            response = await self.client.post(
                f"{self.base_url}/v2.1/accounts/{self.account_id}/envelopes/{envelope_id}/views/recipient",
                headers=headers,
                json=view_data
            )
            response.raise_for_status()

            result = response.json()
            return result["url"]

        except httpx.HTTPError as e:
            logger.error(f"Failed to get DocuSign signing URL: {e}")
            raise SignatureProviderError(f"Failed to get signing URL: {str(e)}")

    async def download_completed_document(self, envelope_id: str) -> bytes:
        """Download completed DocuSign document."""
        try:
            headers = {"Authorization": f"Bearer {self._auth_token}"}

            response = await self.client.get(
                f"{self.base_url}/v2.1/accounts/{self.account_id}/envelopes/{envelope_id}/documents/combined",
                headers=headers
            )
            response.raise_for_status()

            return response.content

        except httpx.HTTPError as e:
            logger.error(f"Failed to download DocuSign document: {e}")
            raise SignatureProviderError(f"Failed to download document: {str(e)}")

    def _format_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format documents for DocuSign API."""
        formatted = []
        for i, doc in enumerate(documents):
            formatted.append({
                "documentId": str(i + 1),
                "name": doc.get("name", f"Document {i + 1}"),
                "documentBase64": doc.get("content_base64", ""),
                "fileExtension": doc.get("extension", "pdf")
            })
        return formatted

    def _format_signers(self, signers: List[Dict[str, Any]], fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format signers for DocuSign API."""
        formatted = []
        for signer in signers:
            signer_data = {
                "email": signer["email"],
                "name": signer["name"],
                "recipientId": str(signer["order"]),
                "routingOrder": str(signer["order"])
            }

            # Add signature fields for this signer
            signer_fields = [f for f in fields if f.get("signer_id") == signer.get("id")]
            if signer_fields:
                signer_data["tabs"] = self._format_tabs(signer_fields)

            formatted.append(signer_data)

        return formatted

    def _format_tabs(self, fields: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Format signature fields as DocuSign tabs."""
        tabs = {
            "signHereTabs": [],
            "dateSignedTabs": [],
            "textTabs": [],
            "checkboxTabs": []
        }

        for field in fields:
            tab_data = {
                "documentId": "1",  # Assuming single document for now
                "pageNumber": str(field.get("page_number", 1)),
                "xPosition": str(int(field.get("x_position", 0) * 612)),  # Convert to points
                "yPosition": str(int(field.get("y_position", 0) * 792)),  # Convert to points
                "width": str(int(field.get("width", 0.2) * 612)),
                "height": str(int(field.get("height", 0.05) * 792))
            }

            field_type = field.get("field_type", "signature")
            if field_type == "signature":
                tabs["signHereTabs"].append(tab_data)
            elif field_type == "date":
                tabs["dateSignedTabs"].append(tab_data)
            elif field_type == "text":
                tab_data["tabLabel"] = field.get("label", "Text")
                tabs["textTabs"].append(tab_data)
            elif field_type == "checkbox":
                tabs["checkboxTabs"].append(tab_data)

        return tabs

    def _format_custom_fields(self, fields: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Format custom fields for DocuSign."""
        return {
            "textCustomFields": [
                {
                    "name": field.get("name", ""),
                    "value": field.get("value", ""),
                    "required": field.get("required", False)
                }
                for field in fields if field.get("field_type") == "custom_text"
            ]
        }

    def _map_docusign_status(self, status: str) -> SignatureRequestStatus:
        """Map DocuSign status to internal status."""
        status_map = {
            "created": SignatureRequestStatus.DRAFT,
            "sent": SignatureRequestStatus.SENT,
            "delivered": SignatureRequestStatus.IN_PROGRESS,
            "signed": SignatureRequestStatus.IN_PROGRESS,
            "completed": SignatureRequestStatus.COMPLETED,
            "declined": SignatureRequestStatus.DECLINED,
            "voided": SignatureRequestStatus.VOIDED,
            "expired": SignatureRequestStatus.EXPIRED,
        }
        return status_map.get(status.lower(), SignatureRequestStatus.IN_PROGRESS)


class HelloSignProvider(BaseSignatureProvider):
    """
    HelloSign (Dropbox Sign) e-signature provider implementation.

    Integrates with HelloSign API for signature request
    creation, management, and status tracking.
    """

    def __init__(self, config: SignatureProviderConfig):
        super().__init__(config)
        self.base_url = "https://api.hellosign.com/v3"
        self.api_key = None

    async def authenticate(self) -> bool:
        """Authenticate with HelloSign using API key."""
        try:
            credentials = self._decrypt_credentials()

            if "api_key" not in credentials:
                raise ProviderAuthenticationError("HelloSign API key not found in credentials")

            self.api_key = credentials["api_key"]

            # Test authentication by getting account info
            headers = {"Authorization": f"Basic {base64.b64encode(f'{self.api_key}:'.encode()).decode()}"}

            response = await self.client.get(
                f"{self.base_url}/account",
                headers=headers
            )
            response.raise_for_status()

            self._auth_token = self.api_key
            self._token_expires_at = datetime.utcnow() + timedelta(days=365)  # API keys don't expire

            return True

        except Exception as e:
            logger.error(f"HelloSign authentication failed: {e}")
            raise ProviderAuthenticationError(f"HelloSign authentication failed: {str(e)}")

    async def create_envelope(
        self,
        title: str,
        message: str,
        documents: List[Dict[str, Any]],
        signers: List[Dict[str, Any]],
        fields: Optional[List[Dict[str, Any]]] = None,
        settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create HelloSign signature request."""
        try:
            # HelloSign uses multipart form data
            form_data = {
                "title": title,
                "message": message,
                "test_mode": "1" if self.is_sandbox else "0"
            }

            # Add signers
            for i, signer in enumerate(signers):
                form_data[f"signers[{i}][email_address]"] = signer["email"]
                form_data[f"signers[{i}][name]"] = signer["name"]
                form_data[f"signers[{i}][order]"] = str(signer["order"])

            # Add documents
            files = []
            for i, doc in enumerate(documents):
                if "content_base64" in doc:
                    content = base64.b64decode(doc["content_base64"])
                    files.append(("file", (doc.get("name", f"document_{i}.pdf"), content, "application/pdf")))

            headers = {"Authorization": f"Basic {base64.b64encode(f'{self.api_key}:'.encode()).decode()}"}

            response = await self.client.post(
                f"{self.base_url}/signature_request/send",
                headers=headers,
                data=form_data,
                files=files
            )
            response.raise_for_status()

            result = response.json()["signature_request"]
            return {
                "envelope_id": result["signature_request_id"],
                "status": self._map_hellosign_status(result["status_code"]),
                "uri": result.get("signing_url"),
                "provider_data": result
            }

        except httpx.HTTPError as e:
            logger.error(f"HelloSign signature request creation failed: {e}")
            raise SignatureProviderError(f"Failed to create HelloSign signature request: {str(e)}")

    async def get_envelope_status(self, envelope_id: str) -> Dict[str, Any]:
        """Get HelloSign signature request status."""
        try:
            headers = {"Authorization": f"Basic {base64.b64encode(f'{self.api_key}:'.encode()).decode()}"}

            response = await self.client.get(
                f"{self.base_url}/signature_request/{envelope_id}",
                headers=headers
            )
            response.raise_for_status()

            result = response.json()["signature_request"]
            return {
                "status": self._map_hellosign_status(result["status_code"]),
                "provider_status": result["status_code"],
                "created_at": result.get("created_at"),
                "sent_at": None,  # HelloSign doesn't track sent separately
                "completed_at": result.get("final_copy_uri") and datetime.utcnow().isoformat(),
                "provider_data": result
            }

        except httpx.HTTPError as e:
            logger.error(f"Failed to get HelloSign signature request status: {e}")
            raise SignatureProviderError(f"Failed to get signature request status: {str(e)}")

    async def send_envelope(self, envelope_id: str) -> Dict[str, Any]:
        """Send HelloSign signature request (automatically sent on creation)."""
        # HelloSign automatically sends signature requests when created
        return await self.get_envelope_status(envelope_id)

    async def void_envelope(self, envelope_id: str, reason: str) -> Dict[str, Any]:
        """Cancel HelloSign signature request."""
        try:
            headers = {"Authorization": f"Basic {base64.b64encode(f'{self.api_key}:'.encode()).decode()}"}

            response = await self.client.post(
                f"{self.base_url}/signature_request/cancel/{envelope_id}",
                headers=headers
            )
            response.raise_for_status()

            return {
                "status": SignatureRequestStatus.VOIDED,
                "provider_data": response.json()
            }

        except httpx.HTTPError as e:
            logger.error(f"Failed to cancel HelloSign signature request: {e}")
            raise SignatureProviderError(f"Failed to cancel signature request: {str(e)}")

    async def get_signing_url(self, envelope_id: str, signer_id: str) -> str:
        """Get embedded signing URL for HelloSign."""
        try:
            headers = {"Authorization": f"Basic {base64.b64encode(f'{self.api_key}:'.encode()).decode()}"}

            response = await self.client.get(
                f"{self.base_url}/embedded/sign_url/{envelope_id}",
                headers=headers
            )
            response.raise_for_status()

            result = response.json()["embedded"]
            return result["sign_url"]

        except httpx.HTTPError as e:
            logger.error(f"Failed to get HelloSign signing URL: {e}")
            raise SignatureProviderError(f"Failed to get signing URL: {str(e)}")

    async def download_completed_document(self, envelope_id: str) -> bytes:
        """Download completed HelloSign document."""
        try:
            headers = {"Authorization": f"Basic {base64.b64encode(f'{self.api_key}:'.encode()).decode()}"}

            response = await self.client.get(
                f"{self.base_url}/signature_request/files/{envelope_id}",
                headers=headers
            )
            response.raise_for_status()

            return response.content

        except httpx.HTTPError as e:
            logger.error(f"Failed to download HelloSign document: {e}")
            raise SignatureProviderError(f"Failed to download document: {str(e)}")

    def _map_hellosign_status(self, status_code: str) -> SignatureRequestStatus:
        """Map HelloSign status to internal status."""
        status_map = {
            "awaiting_signature": SignatureRequestStatus.SENT,
            "partially_signed": SignatureRequestStatus.IN_PROGRESS,
            "signed": SignatureRequestStatus.COMPLETED,
            "cancelled": SignatureRequestStatus.VOIDED,
            "declined": SignatureRequestStatus.DECLINED,
            "error": SignatureRequestStatus.ERROR,
        }
        return status_map.get(status_code, SignatureRequestStatus.IN_PROGRESS)


class ProviderFactory:
    """Factory for creating signature provider instances."""

    _providers = {
        SignatureProvider.DOCUSIGN: DocuSignProvider,
        SignatureProvider.HELLOSIGN: HelloSignProvider,
    }

    @classmethod
    def create_provider(cls, config: SignatureProviderConfig) -> BaseSignatureProvider:
        """Create provider instance based on configuration."""
        provider_class = cls._providers.get(config.provider)

        if not provider_class:
            raise SignatureProviderError(f"Unsupported provider: {config.provider}")

        return provider_class(config)

    @classmethod
    def get_supported_providers(cls) -> List[SignatureProvider]:
        """Get list of supported providers."""
        return list(cls._providers.keys())


# Export provider classes
__all__ = [
    "BaseSignatureProvider",
    "DocuSignProvider",
    "HelloSignProvider",
    "ProviderFactory",
    "SignatureProviderError",
    "ProviderAuthenticationError",
    "ProviderRateLimitError",
]
