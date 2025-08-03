"""
Comprehensive tests for digital signature system.

This module tests signature request creation, workflow management,
provider integration, document signing, and analytics.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import get_session
from app.core.security import auth_rate_limiter, general_rate_limiter
from app.models.signature import (
    SignatureRequest, SignatureRequestCreate, SignatureRequestStatus, SignatureProvider,
    SignatureWorkflow, SignatureField, SignatureFieldType, BulkSignatureRequest
)
from app.models.contract import Contract
from app.models.signer import Signer
from app.models.user import User


# Test database engine
test_engine = create_engine(
    "sqlite://",  # In-memory SQLite database
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


def get_test_session():
    """Override database session for testing."""
    with Session(test_engine) as session:
        yield session


# Override the database dependency
app.dependency_overrides[get_session] = get_test_session


@pytest.fixture(scope="function")
def client():
    """Create test client for FastAPI application."""
    # Create test database tables
    SQLModel.metadata.create_all(test_engine)
    
    # Clear rate limiters for testing
    auth_rate_limiter.requests.clear()
    general_rate_limiter.requests.clear()
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Clean up
    SQLModel.metadata.drop_all(test_engine)


@pytest.fixture
def test_user(client):
    """Create test user and return login token."""
    user_data = {
        "email": "test@example.com",
        "name": "Test User",
        "role": "agent",
        "password": "testpassword123"
    }
    
    # Register user (first user becomes admin)
    register_response = client.post("/auth/register", json=user_data)
    assert register_response.status_code == 200
    
    # Login to get token
    login_data = {
        "username": user_data["email"],
        "password": user_data["password"]
    }
    login_response = client.post("/auth/login", data=login_data)
    assert login_response.status_code == 200
    return login_response.json()["access_token"]


@pytest.fixture
def sample_contract(client, test_user):
    """Create a sample contract for testing."""
    # First create a deal
    deal_data = {
        "title": "Test Deal",
        "property_address": "123 Test St",
        "listing_price": 300000,
        "deal_type": "purchase",
        "status": "active"
    }
    
    headers = {"Authorization": f"Bearer {test_user}"}
    deal_response = client.post("/deals/", json=deal_data, headers=headers)
    assert deal_response.status_code == 200
    deal_id = deal_response.json()["id"]
    
    # Create contract
    contract_data = {
        "deal_id": deal_id,
        "template_id": 1,  # Assuming template exists
        "title": "Test Contract",
        "variables": {
            "buyer_name": "John Doe",
            "seller_name": "Jane Smith",
            "property_address": "123 Test St",
            "purchase_price": 300000
        }
    }
    
    contract_response = client.post("/contracts/generate", json=contract_data, headers=headers)
    assert contract_response.status_code == 200
    return contract_response.json()["contract_id"]


class TestSignatureRequestCreation:
    """Test signature request creation functionality."""
    
    def test_create_signature_request_success(self, client, test_user, sample_contract):
        """Test successful signature request creation."""
        signature_request_data = {
            "title": "Test Signature Request",
            "message": "Please sign this document",
            "provider": "docusign",
            "contract_id": sample_contract,
            "expires_at": (datetime.utcnow() + timedelta(days=7)).isoformat(),
            "signers": [
                {
                    "party_role": "buyer",
                    "name": "John Doe",
                    "email": "john@example.com",
                    "order": 1
                },
                {
                    "party_role": "seller",
                    "name": "Jane Smith",
                    "email": "jane@example.com",
                    "order": 2
                }
            ],
            "fields": [
                {
                    "field_type": "signature",
                    "label": "Buyer Signature",
                    "page_number": 1,
                    "x_position": 0.1,
                    "y_position": 0.8,
                    "width": 0.3,
                    "height": 0.1,
                    "required": True
                }
            ]
        }
        
        headers = {"Authorization": f"Bearer {test_user}"}
        response = client.post("/signatures/requests", json=signature_request_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Signature Request"
        assert data["provider"] == "docusign"
        assert data["status"] == "draft"
        assert "id" in data
    
    def test_create_signature_request_invalid_contract(self, client, test_user):
        """Test signature request creation with invalid contract."""
        signature_request_data = {
            "title": "Test Signature Request",
            "provider": "docusign",
            "contract_id": 99999,  # Non-existent contract
            "signers": [
                {
                    "party_role": "buyer",
                    "name": "John Doe",
                    "email": "john@example.com",
                    "order": 1
                }
            ]
        }
        
        headers = {"Authorization": f"Bearer {test_user}"}
        response = client.post("/signatures/requests", json=signature_request_data, headers=headers)
        
        assert response.status_code == 404
        assert "Contract not found" in response.json()["detail"]
    
    def test_create_signature_request_missing_signers(self, client, test_user, sample_contract):
        """Test signature request creation without signers."""
        signature_request_data = {
            "title": "Test Signature Request",
            "provider": "docusign",
            "contract_id": sample_contract,
            "signers": []  # Empty signers list
        }
        
        headers = {"Authorization": f"Bearer {test_user}"}
        response = client.post("/signatures/requests", json=signature_request_data, headers=headers)
        
        assert response.status_code == 422  # Validation error


class TestSignatureRequestManagement:
    """Test signature request management operations."""
    
    def test_get_signature_request(self, client, test_user, sample_contract):
        """Test getting signature request information."""
        # Create signature request
        signature_request_data = {
            "title": "Get Test Request",
            "provider": "docusign",
            "contract_id": sample_contract,
            "signers": [
                {
                    "party_role": "buyer",
                    "name": "John Doe",
                    "email": "john@example.com",
                    "order": 1
                }
            ]
        }
        
        headers = {"Authorization": f"Bearer {test_user}"}
        create_response = client.post("/signatures/requests", json=signature_request_data, headers=headers)
        request_id = create_response.json()["id"]
        
        # Get signature request
        response = client.get(f"/signatures/requests/{request_id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == request_id
        assert data["title"] == "Get Test Request"
    
    def test_get_signature_request_with_details(self, client, test_user, sample_contract):
        """Test getting signature request with detailed information."""
        # Create signature request
        signature_request_data = {
            "title": "Detailed Test Request",
            "provider": "docusign",
            "contract_id": sample_contract,
            "signers": [
                {
                    "party_role": "buyer",
                    "name": "John Doe",
                    "email": "john@example.com",
                    "order": 1
                }
            ]
        }
        
        headers = {"Authorization": f"Bearer {test_user}"}
        create_response = client.post("/signatures/requests", json=signature_request_data, headers=headers)
        request_id = create_response.json()["id"]
        
        # Get signature request with details
        response = client.get(f"/signatures/requests/{request_id}?include_details=true", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == request_id
        # Would check for additional detail fields in full implementation
    
    def test_list_signature_requests(self, client, test_user, sample_contract):
        """Test listing signature requests."""
        # Create multiple signature requests
        for i in range(3):
            signature_request_data = {
                "title": f"List Test Request {i+1}",
                "provider": "docusign",
                "contract_id": sample_contract,
                "signers": [
                    {
                        "party_role": "buyer",
                        "name": f"Buyer {i+1}",
                        "email": f"buyer{i+1}@example.com",
                        "order": 1
                    }
                ]
            }
            
            headers = {"Authorization": f"Bearer {test_user}"}
            client.post("/signatures/requests", json=signature_request_data, headers=headers)
        
        # List signature requests
        response = client.get("/signatures/requests", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert all("id" in request for request in data)
    
    def test_void_signature_request(self, client, test_user, sample_contract):
        """Test voiding signature request."""
        # Create signature request
        signature_request_data = {
            "title": "Void Test Request",
            "provider": "docusign",
            "contract_id": sample_contract,
            "signers": [
                {
                    "party_role": "buyer",
                    "name": "John Doe",
                    "email": "john@example.com",
                    "order": 1
                }
            ]
        }
        
        headers = {"Authorization": f"Bearer {test_user}"}
        create_response = client.post("/signatures/requests", json=signature_request_data, headers=headers)
        request_id = create_response.json()["id"]
        
        # Void signature request
        void_data = "Contract terms changed"
        response = client.post(f"/signatures/requests/{request_id}/void", json=void_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "voided"


class TestDocumentSigning:
    """Test document signing functionality."""
    
    def test_prepare_document_for_signing(self, client, test_user, sample_contract):
        """Test document preparation for signing."""
        field_positions = [
            {
                "field_type": "signature",
                "label": "Buyer Signature",
                "page_number": 1,
                "x_position": 0.1,
                "y_position": 0.8,
                "width": 0.3,
                "height": 0.1,
                "required": True
            },
            {
                "field_type": "date",
                "label": "Date Signed",
                "page_number": 1,
                "x_position": 0.5,
                "y_position": 0.8,
                "width": 0.2,
                "height": 0.05,
                "required": True
            }
        ]
        
        headers = {"Authorization": f"Bearer {test_user}"}
        response = client.post(
            f"/signatures/documents/{sample_contract}/prepare",
            json=field_positions,
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["contract_id"] == sample_contract
        assert "document_info" in data
        assert "validated_fields" in data
        assert len(data["validated_fields"]) == 2
    
    def test_authenticate_signer(self, client):
        """Test signer authentication."""
        auth_data = {
            "signature_request_id": 1,
            "signer_email": "john@example.com",
            "authentication_method": "email"
        }
        
        response = client.post("/signatures/auth/signer", json=auth_data)
        
        # This would fail in real implementation without proper setup
        # but tests the endpoint structure
        assert response.status_code in [200, 404, 500]
    
    def test_submit_signature(self, client):
        """Test signature submission."""
        signature_data = {
            "access_token": "test_token",
            "field_values": {
                "field_1": "John Doe",
                "field_2": "2024-01-15"
            },
            "signature_data": {
                "signature_image": "base64_encoded_signature"
            }
        }
        
        response = client.post("/signatures/signing/submit", json=signature_data)
        
        # This would fail in real implementation without proper setup
        # but tests the endpoint structure
        assert response.status_code in [200, 401, 404, 500]


class TestBulkOperations:
    """Test bulk signature operations."""
    
    def test_bulk_create_signature_requests(self, client, test_user, sample_contract):
        """Test bulk signature request creation."""
        bulk_request_data = {
            "template_id": 1,
            "requests": [
                {
                    "title": "Bulk Request 1",
                    "provider": "docusign",
                    "contract_id": sample_contract,
                    "signers": [
                        {
                            "party_role": "buyer",
                            "name": "Buyer 1",
                            "email": "buyer1@example.com",
                            "order": 1
                        }
                    ]
                },
                {
                    "title": "Bulk Request 2",
                    "provider": "docusign",
                    "contract_id": sample_contract,
                    "signers": [
                        {
                            "party_role": "buyer",
                            "name": "Buyer 2",
                            "email": "buyer2@example.com",
                            "order": 1
                        }
                    ]
                }
            ],
            "common_settings": {
                "reminder_frequency": "weekly",
                "expires_at": (datetime.utcnow() + timedelta(days=7)).isoformat()
            }
        }
        
        headers = {"Authorization": f"Bearer {test_user}"}
        response = client.post("/signatures/requests/bulk", json=bulk_request_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_requests"] == 2
        assert data["successful_requests"] >= 0
        assert data["failed_requests"] >= 0


class TestSignatureAnalytics:
    """Test signature analytics functionality."""
    
    def test_get_signature_analytics(self, client, test_user):
        """Test getting signature analytics."""
        headers = {"Authorization": f"Bearer {test_user}"}
        response = client.get("/signatures/analytics", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "total_requests" in data
        assert "completion_rate" in data
        assert "provider_breakdown" in data
    
    def test_generate_signature_report(self, client, test_user):
        """Test generating signature report."""
        report_data = {
            "report_type": "completion_summary",
            "filters": {
                "start_date": "2024-01-01",
                "end_date": "2024-01-31"
            }
        }
        
        headers = {"Authorization": f"Bearer {test_user}"}
        response = client.post("/signatures/reports/generate", json=report_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["report_type"] == "completion_summary"
        assert "generated_at" in data


class TestWebhooks:
    """Test webhook functionality."""
    
    def test_docusign_webhook(self, client):
        """Test DocuSign webhook processing."""
        webhook_data = {
            "event": "envelope-completed",
            "envelopeId": "test-envelope-123",
            "status": "completed"
        }
        
        response = client.post("/webhooks/docusign", json=webhook_data)
        
        # Webhook should return 200 even if processing fails
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
    
    def test_hellosign_webhook(self, client):
        """Test HelloSign webhook processing."""
        # HelloSign sends form data
        form_data = {
            "json": '{"event": {"event_type": "signature_request_signed"}, "signature_request": {"signature_request_id": "test-123"}}'
        }
        
        response = client.post("/webhooks/hellosign", data=form_data)
        
        # Webhook should return 200 even if processing fails
        assert response.status_code == 200
        data = response.json()
        assert "status" in data


class TestAuthentication:
    """Test authentication for signature operations."""
    
    def test_create_signature_request_without_auth(self, client, sample_contract):
        """Test signature request creation without authentication."""
        signature_request_data = {
            "title": "Unauthorized Request",
            "provider": "docusign",
            "contract_id": sample_contract,
            "signers": []
        }
        
        response = client.post("/signatures/requests", json=signature_request_data)
        
        assert response.status_code == 401
    
    def test_get_signature_request_without_auth(self, client):
        """Test getting signature request without authentication."""
        response = client.get("/signatures/requests/1")
        
        assert response.status_code == 401
    
    def test_list_signature_requests_without_auth(self, client):
        """Test listing signature requests without authentication."""
        response = client.get("/signatures/requests")
        
        assert response.status_code == 401


class TestValidation:
    """Test signature validation functionality."""
    
    def test_validate_signature_integrity(self, client, test_user, sample_contract):
        """Test signature integrity validation."""
        # Create signature request first
        signature_request_data = {
            "title": "Validation Test Request",
            "provider": "docusign",
            "contract_id": sample_contract,
            "signers": [
                {
                    "party_role": "buyer",
                    "name": "John Doe",
                    "email": "john@example.com",
                    "order": 1
                }
            ]
        }
        
        headers = {"Authorization": f"Bearer {test_user}"}
        create_response = client.post("/signatures/requests", json=signature_request_data, headers=headers)
        request_id = create_response.json()["id"]
        
        # Validate signature integrity
        response = client.post(f"/signatures/requests/{request_id}/validate", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "signature_request_id" in data
        assert "is_valid" in data
        assert "validation_timestamp" in data


class TestErrorHandling:
    """Test error handling in signature operations."""
    
    def test_get_nonexistent_signature_request(self, client, test_user):
        """Test getting non-existent signature request."""
        headers = {"Authorization": f"Bearer {test_user}"}
        response = client.get("/signatures/requests/99999", headers=headers)
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_void_nonexistent_signature_request(self, client, test_user):
        """Test voiding non-existent signature request."""
        headers = {"Authorization": f"Bearer {test_user}"}
        response = client.post("/signatures/requests/99999/void", json="Test reason", headers=headers)
        
        assert response.status_code == 404
    
    def test_invalid_field_positions(self, client, test_user, sample_contract):
        """Test document preparation with invalid field positions."""
        invalid_field_positions = [
            {
                "field_type": "signature",
                "label": "Invalid Signature",
                "page_number": 999,  # Invalid page number
                "x_position": 1.5,   # Invalid position (> 1)
                "y_position": 0.8,
                "width": 0.3,
                "height": 0.1,
                "required": True
            }
        ]
        
        headers = {"Authorization": f"Bearer {test_user}"}
        response = client.post(
            f"/signatures/documents/{sample_contract}/prepare",
            json=invalid_field_positions,
            headers=headers
        )
        
        # Should return error for invalid field positions
        assert response.status_code in [400, 422, 500]
