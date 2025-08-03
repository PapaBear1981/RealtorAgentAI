"""
Comprehensive tests for template management system.

This module tests template CRUD operations, versioning,
inheritance, validation, and template library management.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import get_session
from app.core.security import auth_rate_limiter, general_rate_limiter
from app.models.template import (
    Template, TemplateCreate, TemplateStatus, TemplateType, OutputFormat,
    TemplateVariable, VariableType
)
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


class TestTemplateCreation:
    """Test template creation functionality."""
    
    def test_create_template_success(self, client, test_user):
        """Test successful template creation."""
        template_data = {
            "name": "Test Template",
            "version": "1.0",
            "template_type": "contract",
            "status": "draft",
            "html_content": "<h1>{{ title }}</h1><p>{{ content }}</p>",
            "description": "Test template for contracts",
            "category": "residential",
            "tags": ["test", "residential"],
            "supported_formats": ["html", "pdf"],
            "variables": [
                {
                    "name": "title",
                    "label": "Document Title",
                    "variable_type": "string",
                    "required": True,
                    "default_value": "Contract"
                },
                {
                    "name": "content",
                    "label": "Content",
                    "variable_type": "string",
                    "required": False,
                    "placeholder": "Enter content here"
                }
            ],
            "is_public": False,
            "access_level": "private"
        }
        
        headers = {"Authorization": f"Bearer {test_user}"}
        response = client.post("/templates/", json=template_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Template"
        assert data["version"] == "1.0"
        assert data["template_type"] == "contract"
        assert data["status"] == "draft"
        assert "id" in data
        assert "created_at" in data
    
    def test_create_template_with_inheritance(self, client, test_user):
        """Test creating template with parent template."""
        # First create parent template
        parent_data = {
            "name": "Parent Template",
            "version": "1.0",
            "template_type": "contract",
            "html_content": "<div>{{ base_content }}</div>",
            "description": "Parent template",
            "category": "base",
            "variables": [
                {
                    "name": "base_content",
                    "label": "Base Content",
                    "variable_type": "string",
                    "required": True
                }
            ]
        }
        
        headers = {"Authorization": f"Bearer {test_user}"}
        parent_response = client.post("/templates/", json=parent_data, headers=headers)
        parent_id = parent_response.json()["id"]
        
        # Create child template
        child_data = {
            "name": "Child Template",
            "version": "1.0",
            "template_type": "contract",
            "parent_template_id": parent_id,
            "html_content": "<div>{{ base_content }}<p>{{ additional_content }}</p></div>",
            "variables": [
                {
                    "name": "additional_content",
                    "label": "Additional Content",
                    "variable_type": "string",
                    "required": False
                }
            ]
        }
        
        response = client.post("/templates/", json=child_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Child Template"
        assert data["parent_template_id"] == parent_id
    
    def test_create_template_invalid_version(self, client, test_user):
        """Test creating template with invalid version format."""
        template_data = {
            "name": "Invalid Version Template",
            "version": "invalid-version",
            "template_type": "contract",
            "html_content": "<h1>Test</h1>"
        }
        
        headers = {"Authorization": f"Bearer {test_user}"}
        response = client.post("/templates/", json=template_data, headers=headers)
        
        assert response.status_code == 422
        assert "version" in str(response.json())
    
    def test_create_template_duplicate_name(self, client, test_user):
        """Test creating template with duplicate name in same category."""
        template_data = {
            "name": "Duplicate Template",
            "version": "1.0",
            "template_type": "contract",
            "html_content": "<h1>Test</h1>",
            "category": "test"
        }
        
        headers = {"Authorization": f"Bearer {test_user}"}
        
        # Create first template
        response1 = client.post("/templates/", json=template_data, headers=headers)
        assert response1.status_code == 200
        
        # Try to create duplicate
        response2 = client.post("/templates/", json=template_data, headers=headers)
        assert response2.status_code == 400
        assert "already exists" in response2.json()["detail"]


class TestTemplateRetrieval:
    """Test template retrieval functionality."""
    
    def test_get_template_success(self, client, test_user):
        """Test successful template retrieval."""
        # Create template first
        template_data = {
            "name": "Get Test Template",
            "version": "1.0",
            "template_type": "contract",
            "html_content": "<h1>{{ title }}</h1>",
            "description": "Template for testing get operation"
        }
        
        headers = {"Authorization": f"Bearer {test_user}"}
        create_response = client.post("/templates/", json=template_data, headers=headers)
        template_id = create_response.json()["id"]
        
        # Get template
        response = client.get(f"/templates/{template_id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == template_id
        assert data["name"] == "Get Test Template"
        assert data["description"] == "Template for testing get operation"
    
    def test_get_template_with_details(self, client, test_user):
        """Test getting template with detailed information."""
        # Create template with variables
        template_data = {
            "name": "Detailed Template",
            "version": "1.0",
            "template_type": "contract",
            "html_content": "<h1>{{ title }}</h1>",
            "variables": [
                {
                    "name": "title",
                    "label": "Title",
                    "variable_type": "string",
                    "required": True
                }
            ],
            "schema": {"type": "object"},
            "business_rules": {"test": "rule"}
        }
        
        headers = {"Authorization": f"Bearer {test_user}"}
        create_response = client.post("/templates/", json=template_data, headers=headers)
        template_id = create_response.json()["id"]
        
        # Get template with details
        response = client.get(f"/templates/{template_id}?include_details=true", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "variables" in data
        assert "schema" in data
        assert "business_rules" in data
        assert len(data["variables"]) == 1
    
    def test_get_template_not_found(self, client, test_user):
        """Test getting non-existent template."""
        headers = {"Authorization": f"Bearer {test_user}"}
        response = client.get("/templates/99999", headers=headers)
        
        assert response.status_code == 404
        assert "Template not found" in response.json()["detail"]
    
    def test_list_templates(self, client, test_user):
        """Test listing templates."""
        # Create multiple templates
        for i in range(3):
            template_data = {
                "name": f"List Template {i+1}",
                "version": "1.0",
                "template_type": "contract",
                "html_content": f"<h1>Template {i+1}</h1>",
                "category": "test"
            }
            
            headers = {"Authorization": f"Bearer {test_user}"}
            client.post("/templates/", json=template_data, headers=headers)
        
        # List templates
        response = client.get("/templates/", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert all("id" in template for template in data)
        assert all("name" in template for template in data)
    
    def test_list_templates_with_filters(self, client, test_user):
        """Test listing templates with filters."""
        # Create templates with different types and categories
        templates = [
            {"name": "Contract Template", "template_type": "contract", "category": "residential"},
            {"name": "Form Template", "template_type": "form", "category": "commercial"},
            {"name": "Letter Template", "template_type": "letter", "category": "residential"}
        ]
        
        headers = {"Authorization": f"Bearer {test_user}"}
        for template_data in templates:
            template_data.update({
                "version": "1.0",
                "html_content": "<h1>Test</h1>"
            })
            client.post("/templates/", json=template_data, headers=headers)
        
        # Filter by template type
        response = client.get("/templates/?template_type=contract", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["template_type"] == "contract"
        
        # Filter by category
        response = client.get("/templates/?category=residential", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(t["category"] == "residential" for t in data)
    
    def test_search_templates(self, client, test_user):
        """Test searching templates."""
        # Create templates with searchable content
        templates = [
            {"name": "Purchase Agreement", "description": "Real estate purchase contract"},
            {"name": "Lease Agreement", "description": "Property rental contract"},
            {"name": "Disclosure Form", "description": "Property disclosure document"}
        ]
        
        headers = {"Authorization": f"Bearer {test_user}"}
        for template_data in templates:
            template_data.update({
                "version": "1.0",
                "template_type": "contract",
                "html_content": "<h1>Test</h1>"
            })
            client.post("/templates/", json=template_data, headers=headers)
        
        # Search by name
        response = client.get("/templates/?search=Agreement", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all("Agreement" in t["name"] for t in data)
        
        # Search by description
        response = client.get("/templates/?search=disclosure", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert "Disclosure" in data[0]["name"]


class TestTemplateUpdate:
    """Test template update functionality."""
    
    def test_update_template_success(self, client, test_user):
        """Test successful template update."""
        # Create template first
        template_data = {
            "name": "Update Test Template",
            "version": "1.0",
            "template_type": "contract",
            "html_content": "<h1>Original</h1>",
            "description": "Original description"
        }
        
        headers = {"Authorization": f"Bearer {test_user}"}
        create_response = client.post("/templates/", json=template_data, headers=headers)
        template_id = create_response.json()["id"]
        
        # Update template
        update_data = {
            "name": "Updated Template Name",
            "description": "Updated description",
            "html_content": "<h1>Updated Content</h1>",
            "version_notes": "Updated content and description"
        }
        
        response = client.put(f"/templates/{template_id}", json=update_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Template Name"
        assert data["description"] == "Updated description"
    
    def test_update_template_create_version(self, client, test_user):
        """Test template update with version creation."""
        # Create template first
        template_data = {
            "name": "Version Test Template",
            "version": "1.0",
            "template_type": "contract",
            "html_content": "<h1>Original</h1>"
        }
        
        headers = {"Authorization": f"Bearer {test_user}"}
        create_response = client.post("/templates/", json=template_data, headers=headers)
        template_id = create_response.json()["id"]
        
        # Update with version creation
        update_data = {
            "html_content": "<h1>Updated Content</h1>",
            "version_notes": "Major content update"
        }
        
        response = client.put(f"/templates/{template_id}?create_version=true", json=update_data, headers=headers)
        
        assert response.status_code == 200
        
        # Check versions were created
        versions_response = client.get(f"/templates/{template_id}/versions", headers=headers)
        assert versions_response.status_code == 200
        versions = versions_response.json()
        assert len(versions) >= 1  # Should have at least initial version
    
    def test_update_template_not_found(self, client, test_user):
        """Test updating non-existent template."""
        update_data = {
            "name": "Updated Name"
        }
        
        headers = {"Authorization": f"Bearer {test_user}"}
        response = client.put("/templates/99999", json=update_data, headers=headers)
        
        assert response.status_code == 404
        assert "Template not found" in response.json()["detail"]


class TestTemplateDeletion:
    """Test template deletion functionality."""
    
    def test_delete_template_soft_delete(self, client, test_user):
        """Test soft delete (archive) template."""
        # Create template first
        template_data = {
            "name": "Delete Test Template",
            "version": "1.0",
            "template_type": "contract",
            "html_content": "<h1>Test</h1>"
        }
        
        headers = {"Authorization": f"Bearer {test_user}"}
        create_response = client.post("/templates/", json=template_data, headers=headers)
        template_id = create_response.json()["id"]
        
        # Soft delete template
        response = client.delete(f"/templates/{template_id}?soft_delete=true", headers=headers)
        
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]
        
        # Verify template is archived
        get_response = client.get(f"/templates/{template_id}", headers=headers)
        assert get_response.status_code == 200
        assert get_response.json()["status"] == "archived"
    
    def test_delete_template_not_found(self, client, test_user):
        """Test deleting non-existent template."""
        headers = {"Authorization": f"Bearer {test_user}"}
        response = client.delete("/templates/99999", headers=headers)
        
        assert response.status_code == 404
        assert "Template not found" in response.json()["detail"]


class TestTemplateOperations:
    """Test additional template operations."""
    
    def test_duplicate_template(self, client, test_user):
        """Test duplicating template."""
        # Create original template
        template_data = {
            "name": "Original Template",
            "version": "1.0",
            "template_type": "contract",
            "html_content": "<h1>{{ title }}</h1>",
            "description": "Original template",
            "variables": [
                {
                    "name": "title",
                    "label": "Title",
                    "variable_type": "string",
                    "required": True
                }
            ]
        }
        
        headers = {"Authorization": f"Bearer {test_user}"}
        create_response = client.post("/templates/", json=template_data, headers=headers)
        template_id = create_response.json()["id"]
        
        # Duplicate template
        response = client.post(
            f"/templates/{template_id}/duplicate?new_name=Duplicated Template&new_version=2.0",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Duplicated Template"
        assert data["version"] == "2.0"
        assert data["id"] != template_id  # Should be different ID
        assert "Copy of" in data["description"]
    
    def test_get_template_categories(self, client, test_user):
        """Test getting template categories."""
        # Create templates with different categories
        categories = ["residential", "commercial", "rental"]
        
        headers = {"Authorization": f"Bearer {test_user}"}
        for i, category in enumerate(categories):
            template_data = {
                "name": f"Template {i+1}",
                "version": "1.0",
                "template_type": "contract",
                "html_content": "<h1>Test</h1>",
                "category": category
            }
            client.post("/templates/", json=template_data, headers=headers)
        
        # Get categories
        response = client.get("/templates/categories/list", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        category_names = [cat["name"] for cat in data]
        assert all(cat in category_names for cat in categories)


class TestAuthentication:
    """Test authentication for template operations."""
    
    def test_create_template_without_auth(self, client):
        """Test creating template without authentication."""
        template_data = {
            "name": "Unauthorized Template",
            "version": "1.0",
            "template_type": "contract",
            "html_content": "<h1>Test</h1>"
        }
        
        response = client.post("/templates/", json=template_data)
        
        assert response.status_code == 401
    
    def test_get_template_without_auth(self, client):
        """Test getting template without authentication."""
        response = client.get("/templates/1")
        
        assert response.status_code == 401
    
    def test_list_templates_without_auth(self, client):
        """Test listing templates without authentication."""
        response = client.get("/templates/")
        
        assert response.status_code == 401
