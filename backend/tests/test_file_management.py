"""
Comprehensive tests for file management system.

This module tests file upload, download, processing, storage,
and all file management operations.
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
from app.core.storage import StorageClient, StorageError
from app.core.document_processor import DocumentProcessor, DocumentProcessingError
from app.core.security import auth_rate_limiter, general_rate_limiter
from app.models.file import (
    File, FileStatus, ProcessingStatus, FileType,
    FileUploadInitiate, StorageQuota
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


@pytest.fixture
def mock_storage_client():
    """Mock storage client for testing."""
    with patch('app.core.storage.get_storage_client') as mock_get_client:
        mock_client = Mock(spec=StorageClient)
        mock_client._bucket_name = "test-bucket"
        
        # Mock methods
        mock_client.generate_storage_key.return_value = "test/path/file.pdf"
        mock_client.generate_presigned_upload_url.return_value = (
            "https://test-bucket.s3.amazonaws.com/upload",
            {"key": "test/path/file.pdf"}
        )
        mock_client.generate_presigned_download_url.return_value = "https://test-bucket.s3.amazonaws.com/download"
        mock_client.file_exists.return_value = True
        mock_client.get_file_metadata.return_value = {
            "size": 1024,
            "last_modified": datetime.utcnow(),
            "etag": "test-etag",
            "content_type": "application/pdf"
        }
        mock_client.delete_file.return_value = True
        
        mock_get_client.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_document_processor():
    """Mock document processor for testing."""
    with patch('app.core.document_processor.get_document_processor') as mock_get_processor:
        mock_processor = Mock(spec=DocumentProcessor)
        
        # Mock processing result
        mock_processor.process_document.return_value = {
            "extracted_text": "Test document content",
            "ocr_text": None,
            "document_metadata": {"pages": 1},
            "document_stats": {"page_count": 1, "file_size": 1024},
            "processing_success": True,
            "processing_metadata": {
                "processed_at": datetime.utcnow().isoformat(),
                "processor_version": "1.0.0"
            }
        }
        
        mock_processor.validate_document.return_value = {
            "is_valid": True,
            "file_type": "pdf",
            "detected_type": "pdf",
            "errors": [],
            "warnings": []
        }
        
        mock_get_processor.return_value = mock_processor
        yield mock_processor


class TestFileUpload:
    """Test file upload functionality."""
    
    def test_initiate_upload_success(self, client, test_user, mock_storage_client):
        """Test successful upload initiation."""
        upload_data = {
            "filename": "test.pdf",
            "file_size": 1024,
            "mime_type": "application/pdf",
            "checksum": "abc123",
            "description": "Test file"
        }
        
        headers = {"Authorization": f"Bearer {test_user}"}
        response = client.post("/files/upload/initiate", json=upload_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "file_id" in data
        assert "upload_url" in data
        assert "upload_fields" in data
        assert "expires_at" in data
    
    def test_initiate_upload_file_too_large(self, client, test_user, mock_storage_client):
        """Test upload initiation with file too large."""
        upload_data = {
            "filename": "large.pdf",
            "file_size": 200 * 1024 * 1024,  # 200MB
            "mime_type": "application/pdf",
            "checksum": "abc123"
        }
        
        headers = {"Authorization": f"Bearer {test_user}"}
        response = client.post("/files/upload/initiate", json=upload_data, headers=headers)
        
        assert response.status_code == 413
        assert "exceeds maximum" in response.json()["detail"]
    
    def test_initiate_upload_invalid_mime_type(self, client, test_user, mock_storage_client):
        """Test upload initiation with invalid MIME type."""
        upload_data = {
            "filename": "test.exe",
            "file_size": 1024,
            "mime_type": "application/x-executable",
            "checksum": "abc123"
        }
        
        headers = {"Authorization": f"Bearer {test_user}"}
        response = client.post("/files/upload/initiate", json=upload_data, headers=headers)
        
        assert response.status_code == 422
        assert "Unsupported MIME type" in str(response.json())
    
    def test_complete_upload_success(self, client, test_user, mock_storage_client):
        """Test successful upload completion."""
        # First initiate upload
        upload_data = {
            "filename": "test.pdf",
            "file_size": 1024,
            "mime_type": "application/pdf",
            "checksum": "abc123"
        }
        
        headers = {"Authorization": f"Bearer {test_user}"}
        init_response = client.post("/files/upload/initiate", json=upload_data, headers=headers)
        file_id = init_response.json()["file_id"]
        
        # Complete upload
        complete_data = {
            "file_id": file_id,
            "etag": "test-etag"
        }
        
        response = client.post("/files/upload/complete", json=complete_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == file_id
        assert data["status"] == "uploaded"
        assert data["filename"] == "test.pdf"
    
    def test_complete_upload_file_not_found(self, client, test_user, mock_storage_client):
        """Test upload completion with non-existent file."""
        complete_data = {
            "file_id": 99999,
            "etag": "test-etag"
        }
        
        headers = {"Authorization": f"Bearer {test_user}"}
        response = client.post("/files/upload/complete", json=complete_data, headers=headers)
        
        assert response.status_code == 404
        assert "File not found" in response.json()["detail"]


class TestFileDownload:
    """Test file download functionality."""
    
    def test_get_download_url_success(self, client, test_user, mock_storage_client):
        """Test successful download URL generation."""
        # Create and upload a file first
        upload_data = {
            "filename": "test.pdf",
            "file_size": 1024,
            "mime_type": "application/pdf",
            "checksum": "abc123"
        }
        
        headers = {"Authorization": f"Bearer {test_user}"}
        init_response = client.post("/files/upload/initiate", json=upload_data, headers=headers)
        file_id = init_response.json()["file_id"]
        
        # Complete upload
        complete_data = {"file_id": file_id}
        client.post("/files/upload/complete", json=complete_data, headers=headers)
        
        # Get download URL
        response = client.get(f"/files/{file_id}/download", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "download_url" in data
        assert "expires_at" in data
        assert data["filename"] == "test.pdf"
        assert data["file_size"] == 1024
    
    def test_get_download_url_file_not_found(self, client, test_user, mock_storage_client):
        """Test download URL generation for non-existent file."""
        headers = {"Authorization": f"Bearer {test_user}"}
        response = client.get("/files/99999/download", headers=headers)
        
        assert response.status_code == 404
        assert "File not found" in response.json()["detail"]


class TestFileManagement:
    """Test file management operations."""
    
    def test_get_file_info(self, client, test_user, mock_storage_client):
        """Test getting file information."""
        # Create and upload a file first
        upload_data = {
            "filename": "test.pdf",
            "file_size": 1024,
            "mime_type": "application/pdf",
            "checksum": "abc123",
            "description": "Test document"
        }
        
        headers = {"Authorization": f"Bearer {test_user}"}
        init_response = client.post("/files/upload/initiate", json=upload_data, headers=headers)
        file_id = init_response.json()["file_id"]
        
        # Get file info
        response = client.get(f"/files/{file_id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == file_id
        assert data["filename"] == "test.pdf"
        assert data["description"] == "Test document"
        assert data["file_size"] == 1024
    
    def test_list_files(self, client, test_user, mock_storage_client):
        """Test listing user files."""
        # Create multiple files
        for i in range(3):
            upload_data = {
                "filename": f"test{i}.pdf",
                "file_size": 1024 * (i + 1),
                "mime_type": "application/pdf",
                "checksum": f"abc{i}"
            }
            
            headers = {"Authorization": f"Bearer {test_user}"}
            client.post("/files/upload/initiate", json=upload_data, headers=headers)
        
        # List files
        response = client.get("/files/", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert all(file["filename"].startswith("test") for file in data)
    
    def test_delete_file_success(self, client, test_user, mock_storage_client):
        """Test successful file deletion."""
        # Create and upload a file first
        upload_data = {
            "filename": "test.pdf",
            "file_size": 1024,
            "mime_type": "application/pdf",
            "checksum": "abc123"
        }
        
        headers = {"Authorization": f"Bearer {test_user}"}
        init_response = client.post("/files/upload/initiate", json=upload_data, headers=headers)
        file_id = init_response.json()["file_id"]
        
        # Complete upload
        complete_data = {"file_id": file_id}
        client.post("/files/upload/complete", json=complete_data, headers=headers)
        
        # Delete file
        response = client.delete(f"/files/{file_id}", headers=headers)
        
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]
    
    def test_delete_file_not_found(self, client, test_user, mock_storage_client):
        """Test deletion of non-existent file."""
        headers = {"Authorization": f"Bearer {test_user}"}
        response = client.delete("/files/99999", headers=headers)
        
        assert response.status_code == 404
        assert "File not found" in response.json()["detail"]


class TestStorageQuota:
    """Test storage quota functionality."""
    
    def test_get_user_quota(self, client, test_user, mock_storage_client):
        """Test getting user storage quota."""
        headers = {"Authorization": f"Bearer {test_user}"}
        response = client.get("/files/quota/me", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "max_storage_bytes" in data
        assert "max_files" in data
        assert "used_storage_bytes" in data
        assert "used_files" in data
        assert "storage_percentage" in data
        assert "files_percentage" in data
    
    def test_quota_enforcement_storage(self, client, test_user, mock_storage_client):
        """Test storage quota enforcement."""
        # Set a very small quota for testing
        with Session(test_engine) as session:
            # Get user
            from sqlmodel import select
            user = session.exec(select(User).where(User.email == "test@example.com")).first()
            
            # Create quota with small limits
            quota = StorageQuota(
                user_id=user.id,
                max_storage_bytes=500,  # 500 bytes
                max_files=10,
                used_storage_bytes=0,
                used_files=0
            )
            session.add(quota)
            session.commit()
        
        # Try to upload file larger than quota
        upload_data = {
            "filename": "large.pdf",
            "file_size": 1024,  # 1KB > 500 bytes quota
            "mime_type": "application/pdf",
            "checksum": "abc123"
        }
        
        headers = {"Authorization": f"Bearer {test_user}"}
        response = client.post("/files/upload/initiate", json=upload_data, headers=headers)
        
        assert response.status_code == 413
        assert "quota exceeded" in response.json()["detail"]


class TestFileValidation:
    """Test file validation functionality."""
    
    def test_filename_validation(self, client, test_user, mock_storage_client):
        """Test filename validation."""
        # Test invalid filename with dangerous characters
        upload_data = {
            "filename": "test<script>.pdf",
            "file_size": 1024,
            "mime_type": "application/pdf",
            "checksum": "abc123"
        }
        
        headers = {"Authorization": f"Bearer {test_user}"}
        response = client.post("/files/upload/initiate", json=upload_data, headers=headers)
        
        assert response.status_code == 422
        assert "invalid characters" in str(response.json())
    
    def test_empty_filename_validation(self, client, test_user, mock_storage_client):
        """Test empty filename validation."""
        upload_data = {
            "filename": "",
            "file_size": 1024,
            "mime_type": "application/pdf",
            "checksum": "abc123"
        }
        
        headers = {"Authorization": f"Bearer {test_user}"}
        response = client.post("/files/upload/initiate", json=upload_data, headers=headers)
        
        assert response.status_code == 422
        assert "cannot be empty" in str(response.json())


class TestFileProcessing:
    """Test file processing functionality."""
    
    def test_file_processing_scheduling(self, client, test_user, mock_storage_client):
        """Test that file processing is scheduled after upload."""
        upload_data = {
            "filename": "test.pdf",
            "file_size": 1024,
            "mime_type": "application/pdf",
            "checksum": "abc123"
        }
        
        headers = {"Authorization": f"Bearer {test_user}"}
        init_response = client.post("/files/upload/initiate", json=upload_data, headers=headers)
        file_id = init_response.json()["file_id"]
        
        # Complete upload
        complete_data = {"file_id": file_id}
        response = client.post("/files/upload/complete", json=complete_data, headers=headers)
        
        assert response.status_code == 200
        
        # Check that processing status is set
        file_info = client.get(f"/files/{file_id}", headers=headers)
        assert file_info.json()["processing_status"] == "pending"


class TestAuthentication:
    """Test authentication for file operations."""
    
    def test_upload_without_auth(self, client, mock_storage_client):
        """Test upload without authentication."""
        upload_data = {
            "filename": "test.pdf",
            "file_size": 1024,
            "mime_type": "application/pdf",
            "checksum": "abc123"
        }
        
        response = client.post("/files/upload/initiate", json=upload_data)
        
        assert response.status_code == 401
    
    def test_download_without_auth(self, client, mock_storage_client):
        """Test download without authentication."""
        response = client.get("/files/1/download")
        
        assert response.status_code == 401
    
    def test_list_files_without_auth(self, client, mock_storage_client):
        """Test listing files without authentication."""
        response = client.get("/files/")
        
        assert response.status_code == 401
