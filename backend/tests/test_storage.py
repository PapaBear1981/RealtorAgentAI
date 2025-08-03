"""
Tests for storage client functionality.

This module tests S3/MinIO storage operations including
upload, download, and file management.
"""

import pytest
import io
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError, NoCredentialsError

from app.core.storage import (
    StorageClient, StorageError,
    calculate_file_checksum, detect_file_type,
    validate_file_size, sanitize_filename
)


class TestStorageClient:
    """Test StorageClient functionality."""

    @patch('app.core.storage.boto3.client')
    def test_storage_client_initialization_success(self, mock_boto_client):
        """Test successful storage client initialization."""
        mock_client = Mock()
        mock_client.head_bucket.return_value = {}
        mock_boto_client.return_value = mock_client

        with patch('app.core.storage.settings') as mock_settings:
            mock_settings.STORAGE_BUCKET_NAME_COMPUTED = "test-bucket"
            mock_settings.AWS_REGION_COMPUTED = "us-east-1"
            mock_settings.STORAGE_ENDPOINT_URL_COMPUTED = None
            mock_settings.AWS_ACCESS_KEY_ID_COMPUTED = "test-key"
            mock_settings.AWS_SECRET_ACCESS_KEY_COMPUTED = "test-secret"

            storage_client = StorageClient()

            assert storage_client._bucket_name == "test-bucket"
            mock_client.head_bucket.assert_called_once_with(Bucket="test-bucket")

    @patch('app.core.storage.boto3.client')
    def test_storage_client_initialization_no_credentials(self, mock_boto_client):
        """Test storage client initialization without credentials."""
        mock_boto_client.side_effect = NoCredentialsError()

        with pytest.raises(StorageError, match="Storage credentials not configured"):
            StorageClient()

    @patch('app.core.storage.boto3.client')
    def test_storage_client_bucket_creation(self, mock_boto_client):
        """Test bucket creation when bucket doesn't exist."""
        mock_client = Mock()

        # First call (head_bucket) raises 404, second call (create_bucket) succeeds
        mock_client.head_bucket.side_effect = ClientError(
            {'Error': {'Code': '404'}}, 'HeadBucket'
        )
        mock_client.create_bucket.return_value = {}
        mock_client.put_bucket_versioning.return_value = {}
        mock_client.put_bucket_lifecycle_configuration.return_value = {}

        mock_boto_client.return_value = mock_client

        with patch('app.core.storage.settings') as mock_settings:
            mock_settings.STORAGE_BUCKET_NAME_COMPUTED = "test-bucket"
            mock_settings.AWS_REGION_COMPUTED = "us-west-2"
            mock_settings.STORAGE_ENDPOINT_URL_COMPUTED = None
            mock_settings.AWS_ACCESS_KEY_ID_COMPUTED = "test-key"
            mock_settings.AWS_SECRET_ACCESS_KEY_COMPUTED = "test-secret"

            storage_client = StorageClient()

            mock_client.create_bucket.assert_called_once_with(
                Bucket="test-bucket",
                CreateBucketConfiguration={'LocationConstraint': 'us-west-2'}
            )

    def test_generate_storage_key(self):
        """Test storage key generation."""
        with patch('app.core.storage.settings') as mock_settings:
            mock_settings.STORAGE_BUCKET_NAME_COMPUTED = "test-bucket"

            with patch('app.core.storage.boto3.client'):
                with patch.object(StorageClient, '_ensure_bucket_exists'):
                    storage_client = StorageClient()

                    key = storage_client.generate_storage_key(
                        user_id=123,
                        filename="test document.pdf",
                        file_type="pdf"
                    )

                    assert key.startswith("files/pdf/")
                    assert "user_123" in key
                    assert key.endswith(".pdf")
                    assert "test_document" in key  # Sanitized filename

    @patch('app.core.storage.boto3.client')
    def test_generate_presigned_upload_url(self, mock_boto_client):
        """Test presigned upload URL generation."""
        mock_client = Mock()
        mock_client.head_bucket.return_value = {}
        mock_client.generate_presigned_post.return_value = {
            'url': 'https://test-bucket.s3.amazonaws.com/',
            'fields': {'key': 'test/file.pdf'}
        }
        mock_boto_client.return_value = mock_client

        with patch('app.core.storage.settings') as mock_settings:
            mock_settings.STORAGE_BUCKET_NAME_COMPUTED = "test-bucket"
            mock_settings.AWS_REGION_COMPUTED = "us-east-1"
            mock_settings.STORAGE_ENDPOINT_URL_COMPUTED = None
            mock_settings.AWS_ACCESS_KEY_ID_COMPUTED = "test-key"
            mock_settings.AWS_SECRET_ACCESS_KEY_COMPUTED = "test-secret"

            storage_client = StorageClient()

            url, fields = storage_client.generate_presigned_upload_url(
                storage_key="test/file.pdf",
                mime_type="application/pdf",
                file_size=1024
            )

            assert url == 'https://test-bucket.s3.amazonaws.com/'
            assert 'key' in fields
            mock_client.generate_presigned_post.assert_called_once()

    @patch('app.core.storage.boto3.client')
    def test_generate_presigned_download_url(self, mock_boto_client):
        """Test presigned download URL generation."""
        mock_client = Mock()
        mock_client.head_bucket.return_value = {}
        mock_client.generate_presigned_url.return_value = 'https://test-bucket.s3.amazonaws.com/download'
        mock_boto_client.return_value = mock_client

        with patch('app.core.storage.settings') as mock_settings:
            mock_settings.STORAGE_BUCKET_NAME_COMPUTED = "test-bucket"
            mock_settings.AWS_REGION_COMPUTED = "us-east-1"
            mock_settings.STORAGE_ENDPOINT_URL_COMPUTED = None
            mock_settings.AWS_ACCESS_KEY_ID_COMPUTED = "test-key"
            mock_settings.AWS_SECRET_ACCESS_KEY_COMPUTED = "test-secret"

            storage_client = StorageClient()

            url = storage_client.generate_presigned_download_url(
                storage_key="test/file.pdf",
                filename="document.pdf"
            )

            assert url == 'https://test-bucket.s3.amazonaws.com/download'
            mock_client.generate_presigned_url.assert_called_once()

    @patch('app.core.storage.boto3.client')
    def test_upload_file(self, mock_boto_client):
        """Test direct file upload."""
        mock_client = Mock()
        mock_client.head_bucket.return_value = {}
        mock_client.upload_fileobj.return_value = None
        mock_client.head_object.return_value = {
            'ETag': '"test-etag"',
            'ContentLength': 1024,
            'LastModified': '2023-01-01T00:00:00Z',
            'Metadata': {}
        }
        mock_boto_client.return_value = mock_client

        with patch('app.core.storage.settings') as mock_settings:
            mock_settings.STORAGE_BUCKET_NAME_COMPUTED = "test-bucket"
            mock_settings.AWS_REGION_COMPUTED = "us-east-1"
            mock_settings.STORAGE_ENDPOINT_URL_COMPUTED = None
            mock_settings.AWS_ACCESS_KEY_ID_COMPUTED = "test-key"
            mock_settings.AWS_SECRET_ACCESS_KEY_COMPUTED = "test-secret"

            storage_client = StorageClient()

            file_obj = io.BytesIO(b"test content")
            result = storage_client.upload_file(
                file_obj=file_obj,
                storage_key="test/file.pdf",
                mime_type="application/pdf"
            )

            assert result['etag'] == 'test-etag'
            assert result['size'] == 1024
            mock_client.upload_fileobj.assert_called_once()

    @patch('app.core.storage.boto3.client')
    def test_download_file(self, mock_boto_client):
        """Test file download."""
        mock_client = Mock()
        mock_client.head_bucket.return_value = {}

        # Mock the response body
        mock_body = Mock()
        mock_body.read.return_value = b"test file content"
        mock_client.get_object.return_value = {'Body': mock_body}

        mock_boto_client.return_value = mock_client

        with patch('app.core.storage.settings') as mock_settings:
            mock_settings.STORAGE_BUCKET_NAME_COMPUTED = "test-bucket"
            mock_settings.AWS_REGION_COMPUTED = "us-east-1"
            mock_settings.STORAGE_ENDPOINT_URL_COMPUTED = None
            mock_settings.AWS_ACCESS_KEY_ID_COMPUTED = "test-key"
            mock_settings.AWS_SECRET_ACCESS_KEY_COMPUTED = "test-secret"

            storage_client = StorageClient()

            content = storage_client.download_file("test/file.pdf")

            assert content == b"test file content"
            mock_client.get_object.assert_called_once_with(
                Bucket="test-bucket",
                Key="test/file.pdf"
            )

    @patch('app.core.storage.boto3.client')
    def test_delete_file(self, mock_boto_client):
        """Test file deletion."""
        mock_client = Mock()
        mock_client.head_bucket.return_value = {}
        mock_client.delete_object.return_value = {}
        mock_boto_client.return_value = mock_client

        with patch('app.core.storage.settings') as mock_settings:
            mock_settings.STORAGE_BUCKET_NAME_COMPUTED = "test-bucket"
            mock_settings.AWS_REGION_COMPUTED = "us-east-1"
            mock_settings.STORAGE_ENDPOINT_URL_COMPUTED = None
            mock_settings.AWS_ACCESS_KEY_ID_COMPUTED = "test-key"
            mock_settings.AWS_SECRET_ACCESS_KEY_COMPUTED = "test-secret"

            storage_client = StorageClient()

            result = storage_client.delete_file("test/file.pdf")

            assert result is True
            mock_client.delete_object.assert_called_once_with(
                Bucket="test-bucket",
                Key="test/file.pdf"
            )

    @patch('app.core.storage.boto3.client')
    def test_file_exists_true(self, mock_boto_client):
        """Test file existence check - file exists."""
        mock_client = Mock()
        mock_client.head_bucket.return_value = {}
        mock_client.head_object.return_value = {}
        mock_boto_client.return_value = mock_client

        with patch('app.core.storage.settings') as mock_settings:
            mock_settings.STORAGE_BUCKET_NAME_COMPUTED = "test-bucket"
            mock_settings.AWS_REGION_COMPUTED = "us-east-1"
            mock_settings.STORAGE_ENDPOINT_URL_COMPUTED = None
            mock_settings.AWS_ACCESS_KEY_ID_COMPUTED = "test-key"
            mock_settings.AWS_SECRET_ACCESS_KEY_COMPUTED = "test-secret"

            storage_client = StorageClient()

            exists = storage_client.file_exists("test/file.pdf")

            assert exists is True
            mock_client.head_object.assert_called_once()

    @patch('app.core.storage.boto3.client')
    def test_file_exists_false(self, mock_boto_client):
        """Test file existence check - file doesn't exist."""
        mock_client = Mock()
        mock_client.head_bucket.return_value = {}
        mock_client.head_object.side_effect = ClientError(
            {'Error': {'Code': '404'}}, 'HeadObject'
        )
        mock_boto_client.return_value = mock_client

        with patch('app.core.storage.settings') as mock_settings:
            mock_settings.STORAGE_BUCKET_NAME_COMPUTED = "test-bucket"
            mock_settings.AWS_REGION_COMPUTED = "us-east-1"
            mock_settings.STORAGE_ENDPOINT_URL_COMPUTED = None
            mock_settings.AWS_ACCESS_KEY_ID_COMPUTED = "test-key"
            mock_settings.AWS_SECRET_ACCESS_KEY_COMPUTED = "test-secret"

            storage_client = StorageClient()

            exists = storage_client.file_exists("test/file.pdf")

            assert exists is False


class TestStorageUtilities:
    """Test storage utility functions."""

    def test_calculate_file_checksum(self):
        """Test file checksum calculation."""
        file_obj = io.BytesIO(b"test content")
        checksum = calculate_file_checksum(file_obj)

        # Verify checksum is a valid SHA-256 hex string
        assert len(checksum) == 64
        assert all(c in '0123456789abcdef' for c in checksum)

        # Verify file pointer is reset
        assert file_obj.tell() == 0

    def test_detect_file_type_pdf(self):
        """Test PDF file type detection."""
        file_type = detect_file_type("document.pdf", "application/pdf")
        assert file_type == "pdf"

    def test_detect_file_type_docx(self):
        """Test DOCX file type detection."""
        file_type = detect_file_type("document.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        assert file_type == "docx"

    def test_detect_file_type_image(self):
        """Test image file type detection."""
        file_type = detect_file_type("image.jpg", "image/jpeg")
        assert file_type == "image"

    def test_detect_file_type_text(self):
        """Test text file type detection."""
        file_type = detect_file_type("document.txt", "text/plain")
        assert file_type == "txt"

    def test_detect_file_type_other(self):
        """Test other file type detection."""
        file_type = detect_file_type("archive.zip", "application/zip")
        assert file_type == "other"

    def test_validate_file_size_valid(self):
        """Test valid file size validation."""
        assert validate_file_size(1024) is True
        assert validate_file_size(50 * 1024 * 1024) is True  # 50MB

    def test_validate_file_size_invalid(self):
        """Test invalid file size validation."""
        assert validate_file_size(0) is False  # Zero size
        assert validate_file_size(-1) is False  # Negative size
        assert validate_file_size(200 * 1024 * 1024) is False  # 200MB > 100MB default

    def test_validate_file_size_custom_limit(self):
        """Test file size validation with custom limit."""
        assert validate_file_size(5 * 1024 * 1024, max_size=10 * 1024 * 1024) is True
        assert validate_file_size(15 * 1024 * 1024, max_size=10 * 1024 * 1024) is False

    def test_sanitize_filename_normal(self):
        """Test filename sanitization with normal filename."""
        result = sanitize_filename("document.pdf")
        assert result == "document.pdf"

    def test_sanitize_filename_dangerous_chars(self):
        """Test filename sanitization with dangerous characters."""
        result = sanitize_filename("doc<script>alert('xss')</script>.pdf")
        # Check that dangerous characters are replaced with underscores
        assert "<" not in result
        assert ">" not in result
        assert result.endswith(".pdf")
        assert "doc" in result
        assert "script" in result

    def test_sanitize_filename_long(self):
        """Test filename sanitization with very long filename."""
        long_name = "a" * 300 + ".pdf"
        result = sanitize_filename(long_name)
        assert len(result) <= 255
        assert result.endswith(".pdf")

    def test_sanitize_filename_no_extension(self):
        """Test filename sanitization without extension."""
        result = sanitize_filename("document_without_extension")
        assert result == "document_without_extension"

    def test_sanitize_filename_whitespace(self):
        """Test filename sanitization with whitespace."""
        result = sanitize_filename("  document with spaces.pdf  ")
        assert result == "document with spaces.pdf"
