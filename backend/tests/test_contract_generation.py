"""
Comprehensive tests for contract generation system.

This module tests contract generation, template rendering,
business rules processing, and multi-format output.
"""

import pytest
import tempfile
import os
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import get_session
from app.core.security import auth_rate_limiter, general_rate_limiter
from app.models.template import (
    Template, TemplateCreate, TemplateStatus, TemplateType, OutputFormat,
    TemplateVariable, VariableType, TemplateGenerationRequest
)
from app.models.contract import Contract
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
def sample_template(client, test_user):
    """Create a sample template for testing."""
    template_data = {
        "name": "Test Contract Template",
        "version": "1.0",
        "template_type": "contract",
        "status": "active",
        "html_content": """
        <div class="contract-header">
            <h1>{{ contract_title }}</h1>
            <p>Date: {{ contract_date }}</p>
        </div>
        <div class="contract-content">
            <p>This contract is between {{ buyer_name }} and {{ seller_name }}.</p>
            <p>Property Address: {{ property_address }}</p>
            <p>Purchase Price: ${{ purchase_price }}</p>
            {% if earnest_money %}
            <p>Earnest Money: ${{ earnest_money }}</p>
            {% endif %}
        </div>
        """,
        "description": "Test contract template",
        "category": "residential",
        "variables": [
            {
                "name": "contract_title",
                "label": "Contract Title",
                "variable_type": "string",
                "required": True,
                "default_value": "Purchase Agreement"
            },
            {
                "name": "contract_date",
                "label": "Contract Date",
                "variable_type": "date",
                "required": True
            },
            {
                "name": "buyer_name",
                "label": "Buyer Name",
                "variable_type": "string",
                "required": True
            },
            {
                "name": "seller_name",
                "label": "Seller Name",
                "variable_type": "string",
                "required": True
            },
            {
                "name": "property_address",
                "label": "Property Address",
                "variable_type": "address",
                "required": True
            },
            {
                "name": "purchase_price",
                "label": "Purchase Price",
                "variable_type": "currency",
                "required": True,
                "min_value": 1000
            },
            {
                "name": "earnest_money",
                "label": "Earnest Money",
                "variable_type": "currency",
                "required": False
            }
        ]
    }
    
    headers = {"Authorization": f"Bearer {test_user}"}
    response = client.post("/templates/", json=template_data, headers=headers)
    assert response.status_code == 200
    return response.json()


class TestContractGeneration:
    """Test contract generation functionality."""
    
    def test_generate_contract_success(self, client, test_user, sample_template):
        """Test successful contract generation."""
        generation_request = {
            "template_id": sample_template["id"],
            "variables": {
                "contract_title": "Residential Purchase Agreement",
                "contract_date": "2024-01-15",
                "buyer_name": "John Doe",
                "seller_name": "Jane Smith",
                "property_address": "123 Main St, Anytown, ST 12345",
                "purchase_price": 350000,
                "earnest_money": 5000
            },
            "output_format": "html",
            "deal_id": 1,
            "custom_title": "Test Contract",
            "apply_business_rules": True,
            "validate_before_generation": True
        }
        
        headers = {"Authorization": f"Bearer {test_user}"}
        response = client.post("/contracts/generate", json=generation_request, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "contract_id" in data
        assert "generated_file_key" in data
        assert data["output_format"] == "html"
        assert "generation_time_ms" in data
    
    def test_generate_contract_missing_required_variable(self, client, test_user, sample_template):
        """Test contract generation with missing required variable."""
        generation_request = {
            "template_id": sample_template["id"],
            "variables": {
                "contract_title": "Residential Purchase Agreement",
                "buyer_name": "John Doe",
                "seller_name": "Jane Smith",
                # Missing required property_address and purchase_price
            },
            "output_format": "html",
            "validate_before_generation": True
        }
        
        headers = {"Authorization": f"Bearer {test_user}"}
        response = client.post("/contracts/generate", json=generation_request, headers=headers)
        
        assert response.status_code == 400
        assert "validation failed" in response.json()["detail"].lower()
    
    def test_generate_contract_invalid_template(self, client, test_user):
        """Test contract generation with invalid template ID."""
        generation_request = {
            "template_id": 99999,
            "variables": {"test": "value"},
            "output_format": "html"
        }
        
        headers = {"Authorization": f"Bearer {test_user}"}
        response = client.post("/contracts/generate", json=generation_request, headers=headers)
        
        assert response.status_code == 404
        assert "Template not found" in response.json()["detail"]
    
    def test_preview_contract_success(self, client, test_user, sample_template):
        """Test successful contract preview."""
        preview_request = {
            "template_id": sample_template["id"],
            "variables": {
                "contract_title": "Preview Contract",
                "contract_date": "2024-01-15",
                "buyer_name": "John Doe",
                "seller_name": "Jane Smith",
                "property_address": "123 Main St, Anytown, ST 12345",
                "purchase_price": 350000
            },
            "output_format": "html",
            "include_placeholders": True
        }
        
        headers = {"Authorization": f"Bearer {test_user}"}
        response = client.post("/contracts/preview", json=preview_request, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "preview_content" in data
        assert data["output_format"] == "html"
        assert "missing_variables" in data
        assert "earnest_money" in data["missing_variables"]  # Optional variable should be in missing list
    
    def test_preview_contract_with_placeholders(self, client, test_user, sample_template):
        """Test contract preview with placeholder variables."""
        preview_request = {
            "template_id": sample_template["id"],
            "variables": {
                "contract_title": "Preview Contract",
                "buyer_name": "John Doe"
                # Missing other required variables
            },
            "output_format": "html",
            "include_placeholders": True
        }
        
        headers = {"Authorization": f"Bearer {test_user}"}
        response = client.post("/contracts/preview", json=preview_request, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "preview_content" in data
        assert len(data["missing_variables"]) > 0
        # Check that placeholders are included in content
        assert "[" in data["preview_content"] and "]" in data["preview_content"]


class TestContractManagement:
    """Test contract management operations."""
    
    def test_get_contract_info(self, client, test_user, sample_template):
        """Test getting contract information."""
        # First generate a contract
        generation_request = {
            "template_id": sample_template["id"],
            "variables": {
                "contract_title": "Test Contract",
                "contract_date": "2024-01-15",
                "buyer_name": "John Doe",
                "seller_name": "Jane Smith",
                "property_address": "123 Main St, Anytown, ST 12345",
                "purchase_price": 350000
            },
            "output_format": "html"
        }
        
        headers = {"Authorization": f"Bearer {test_user}"}
        gen_response = client.post("/contracts/generate", json=generation_request, headers=headers)
        contract_id = gen_response.json()["contract_id"]
        
        # Get contract info
        response = client.get(f"/contracts/{contract_id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == contract_id
        assert data["title"] == "Test Contract"
        assert data["template_id"] == sample_template["id"]
    
    def test_get_contract_with_details(self, client, test_user, sample_template):
        """Test getting contract with detailed information."""
        # First generate a contract
        generation_request = {
            "template_id": sample_template["id"],
            "variables": {
                "contract_title": "Detailed Contract",
                "contract_date": "2024-01-15",
                "buyer_name": "John Doe",
                "seller_name": "Jane Smith",
                "property_address": "123 Main St, Anytown, ST 12345",
                "purchase_price": 350000
            },
            "output_format": "html"
        }
        
        headers = {"Authorization": f"Bearer {test_user}"}
        gen_response = client.post("/contracts/generate", json=generation_request, headers=headers)
        contract_id = gen_response.json()["contract_id"]
        
        # Get contract with details
        response = client.get(f"/contracts/{contract_id}?include_details=true", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == contract_id
        assert "versions" in data
        assert "signers" in data
        assert "validations" in data
    
    def test_list_contracts(self, client, test_user, sample_template):
        """Test listing user contracts."""
        # Generate multiple contracts
        for i in range(3):
            generation_request = {
                "template_id": sample_template["id"],
                "variables": {
                    "contract_title": f"Contract {i+1}",
                    "contract_date": "2024-01-15",
                    "buyer_name": f"Buyer {i+1}",
                    "seller_name": f"Seller {i+1}",
                    "property_address": f"{i+1}23 Main St, Anytown, ST 12345",
                    "purchase_price": 300000 + (i * 10000)
                },
                "output_format": "html"
            }
            
            headers = {"Authorization": f"Bearer {test_user}"}
            client.post("/contracts/generate", json=generation_request, headers=headers)
        
        # List contracts
        response = client.get("/contracts/", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert all("id" in contract for contract in data)
        assert all("title" in contract for contract in data)
    
    def test_update_contract(self, client, test_user, sample_template):
        """Test updating contract information."""
        # First generate a contract
        generation_request = {
            "template_id": sample_template["id"],
            "variables": {
                "contract_title": "Original Contract",
                "contract_date": "2024-01-15",
                "buyer_name": "John Doe",
                "seller_name": "Jane Smith",
                "property_address": "123 Main St, Anytown, ST 12345",
                "purchase_price": 350000
            },
            "output_format": "html"
        }
        
        headers = {"Authorization": f"Bearer {test_user}"}
        gen_response = client.post("/contracts/generate", json=generation_request, headers=headers)
        contract_id = gen_response.json()["contract_id"]
        
        # Update contract
        update_data = {
            "title": "Updated Contract Title",
            "status": "review"
        }
        
        response = client.put(f"/contracts/{contract_id}", json=update_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Contract Title"
        assert data["status"] == "review"
    
    def test_delete_contract(self, client, test_user, sample_template):
        """Test deleting contract."""
        # First generate a contract
        generation_request = {
            "template_id": sample_template["id"],
            "variables": {
                "contract_title": "Contract to Delete",
                "contract_date": "2024-01-15",
                "buyer_name": "John Doe",
                "seller_name": "Jane Smith",
                "property_address": "123 Main St, Anytown, ST 12345",
                "purchase_price": 350000
            },
            "output_format": "html"
        }
        
        headers = {"Authorization": f"Bearer {test_user}"}
        gen_response = client.post("/contracts/generate", json=generation_request, headers=headers)
        contract_id = gen_response.json()["contract_id"]
        
        # Delete contract
        response = client.delete(f"/contracts/{contract_id}", headers=headers)
        
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]
    
    def test_regenerate_contract(self, client, test_user, sample_template):
        """Test regenerating contract with updated variables."""
        # First generate a contract
        generation_request = {
            "template_id": sample_template["id"],
            "variables": {
                "contract_title": "Original Contract",
                "contract_date": "2024-01-15",
                "buyer_name": "John Doe",
                "seller_name": "Jane Smith",
                "property_address": "123 Main St, Anytown, ST 12345",
                "purchase_price": 350000
            },
            "output_format": "html"
        }
        
        headers = {"Authorization": f"Bearer {test_user}"}
        gen_response = client.post("/contracts/generate", json=generation_request, headers=headers)
        contract_id = gen_response.json()["contract_id"]
        
        # Regenerate with updated variables
        regenerate_data = {
            "variables": {
                "contract_title": "Regenerated Contract",
                "contract_date": "2024-01-20",
                "buyer_name": "John Doe",
                "seller_name": "Jane Smith",
                "property_address": "123 Main St, Anytown, ST 12345",
                "purchase_price": 375000,
                "earnest_money": 7500
            },
            "output_format": "pdf"
        }
        
        response = client.post(f"/contracts/{contract_id}/regenerate", json=regenerate_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "contract_id" in data
        assert data["output_format"] == "pdf"


class TestAuthentication:
    """Test authentication for contract operations."""
    
    def test_generate_contract_without_auth(self, client, sample_template):
        """Test contract generation without authentication."""
        generation_request = {
            "template_id": sample_template["id"],
            "variables": {"test": "value"},
            "output_format": "html"
        }
        
        response = client.post("/contracts/generate", json=generation_request)
        
        assert response.status_code == 401
    
    def test_get_contract_without_auth(self, client):
        """Test getting contract without authentication."""
        response = client.get("/contracts/1")
        
        assert response.status_code == 401
    
    def test_list_contracts_without_auth(self, client):
        """Test listing contracts without authentication."""
        response = client.get("/contracts/")
        
        assert response.status_code == 401
