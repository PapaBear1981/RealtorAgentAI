"""
Storage client and utilities for S3/MinIO integration.

This module provides a unified interface for file storage operations
using AWS S3 or MinIO-compatible storage systems.
"""

import hashlib
import mimetypes
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, BinaryIO, Tuple
from urllib.parse import urlparse
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from botocore.config import Config
import logging

from .config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class StorageError(Exception):
    """Base exception for storage operations."""
    pass


class StorageClient:
    """
    Unified storage client for S3/MinIO operations.

    Provides a consistent interface for file upload, download,
    and management operations across different storage backends.
    """

    def __init__(self):
        """Initialize storage client with configuration."""
        self._client = None
        self._bucket_name = settings.STORAGE_BUCKET_NAME_COMPUTED
        self._setup_client()

    def _setup_client(self):
        """Setup S3/MinIO client with proper configuration."""
        try:
            # Configure client with custom endpoint for MinIO
            config = Config(
                region_name=settings.AWS_REGION_COMPUTED,
                retries={'max_attempts': 3, 'mode': 'adaptive'},
                max_pool_connections=50
            )

            # Create S3 client
            if settings.STORAGE_ENDPOINT_URL_COMPUTED:
                # MinIO or custom S3-compatible endpoint
                self._client = boto3.client(
                    's3',
                    endpoint_url=settings.STORAGE_ENDPOINT_URL_COMPUTED,
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID_COMPUTED,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY_COMPUTED,
                    config=config
                )
            else:
                # Standard AWS S3
                self._client = boto3.client(
                    's3',
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID_COMPUTED,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY_COMPUTED,
                    config=config
                )

            # Test connection and create bucket if needed
            self._ensure_bucket_exists()

            logger.info(f"Storage client initialized successfully with bucket: {self._bucket_name}")

        except NoCredentialsError:
            logger.error("AWS credentials not found")
            raise StorageError("Storage credentials not configured")
        except Exception as e:
            logger.error(f"Failed to initialize storage client: {e}")
            raise StorageError(f"Storage initialization failed: {e}")

    def _ensure_bucket_exists(self):
        """Ensure the storage bucket exists, create if necessary."""
        try:
            self._client.head_bucket(Bucket=self._bucket_name)
            logger.debug(f"Bucket {self._bucket_name} exists")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                # Bucket doesn't exist, create it
                try:
                    if settings.AWS_REGION_COMPUTED == 'us-east-1':
                        # us-east-1 doesn't need LocationConstraint
                        self._client.create_bucket(Bucket=self._bucket_name)
                    else:
                        self._client.create_bucket(
                            Bucket=self._bucket_name,
                            CreateBucketConfiguration={'LocationConstraint': settings.AWS_REGION_COMPUTED}
                        )

                    # Set bucket policy for private access
                    self._setup_bucket_policy()

                    logger.info(f"Created bucket: {self._bucket_name}")
                except ClientError as create_error:
                    error_code = create_error.response['Error']['Code']
                    if error_code in ['BucketAlreadyExists', 'BucketAlreadyOwnedByYou']:
                        # Bucket already exists, which is fine
                        logger.info(f"Bucket {self._bucket_name} already exists")
                    else:
                        logger.error(f"Failed to create bucket: {create_error}")
                        raise StorageError(f"Cannot create storage bucket: {create_error}")
            else:
                logger.error(f"Cannot access bucket: {e}")
                raise StorageError(f"Storage bucket access error: {e}")

    def _setup_bucket_policy(self):
        """Setup bucket policy for security."""
        try:
            # Enable versioning
            self._client.put_bucket_versioning(
                Bucket=self._bucket_name,
                VersioningConfiguration={'Status': 'Enabled'}
            )

            # Set lifecycle policy for cleanup
            lifecycle_config = {
                'Rules': [
                    {
                        'ID': 'DeleteIncompleteMultipartUploads',
                        'Status': 'Enabled',
                        'Filter': {'Prefix': ''},
                        'AbortIncompleteMultipartUpload': {
                            'DaysAfterInitiation': 1
                        }
                    },
                    {
                        'ID': 'DeleteOldVersions',
                        'Status': 'Enabled',
                        'Filter': {'Prefix': ''},
                        'NoncurrentVersionExpiration': {
                            'NoncurrentDays': 30
                        }
                    }
                ]
            }

            self._client.put_bucket_lifecycle_configuration(
                Bucket=self._bucket_name,
                LifecycleConfiguration=lifecycle_config
            )

            logger.debug("Bucket policy configured successfully")

        except ClientError as e:
            logger.warning(f"Could not set bucket policy: {e}")
            # Don't raise error as this is not critical

    def generate_storage_key(self, user_id: int, filename: str, file_type: str) -> str:
        """
        Generate a unique storage key for a file.

        Args:
            user_id: ID of the user uploading the file
            filename: Original filename
            file_type: File type classification

        Returns:
            str: Unique storage key
        """
        # Create timestamp-based path
        now = datetime.utcnow()
        date_path = now.strftime("%Y/%m/%d")

        # Generate unique filename with timestamp
        timestamp = now.strftime("%H%M%S")
        name_part, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')

        # Sanitize filename
        safe_name = "".join(c for c in name_part if c.isalnum() or c in ('-', '_')).strip()
        safe_name = safe_name[:50]  # Limit length

        if ext:
            unique_filename = f"{safe_name}_{timestamp}.{ext}"
        else:
            unique_filename = f"{safe_name}_{timestamp}"

        # Construct full key
        storage_key = f"files/{file_type}/{date_path}/user_{user_id}/{unique_filename}"

        return storage_key

    def generate_presigned_upload_url(
        self,
        storage_key: str,
        mime_type: str,
        file_size: int,
        expires_in: int = 3600
    ) -> Tuple[str, Dict[str, str]]:
        """
        Generate presigned URL for file upload.

        Args:
            storage_key: Storage key for the file
            mime_type: MIME type of the file
            file_size: Size of the file in bytes
            expires_in: URL expiration time in seconds

        Returns:
            Tuple[str, Dict]: Upload URL and form fields
        """
        try:
            # Generate presigned POST for secure upload
            conditions = [
                {"Content-Type": mime_type},
                ["content-length-range", 1, file_size + 1000]  # Allow small buffer
            ]

            fields = {
                "Content-Type": mime_type,
                "x-amz-meta-uploaded-at": datetime.utcnow().isoformat(),
            }

            response = self._client.generate_presigned_post(
                Bucket=self._bucket_name,
                Key=storage_key,
                Fields=fields,
                Conditions=conditions,
                ExpiresIn=expires_in
            )

            return response['url'], response['fields']

        except ClientError as e:
            logger.error(f"Failed to generate presigned upload URL: {e}")
            raise StorageError(f"Cannot generate upload URL: {e}")

    def generate_presigned_download_url(
        self,
        storage_key: str,
        expires_in: int = 3600,
        filename: Optional[str] = None
    ) -> str:
        """
        Generate presigned URL for file download.

        Args:
            storage_key: Storage key for the file
            expires_in: URL expiration time in seconds
            filename: Optional filename for download

        Returns:
            str: Download URL
        """
        try:
            params = {
                'Bucket': self._bucket_name,
                'Key': storage_key
            }

            # Set content disposition for download
            if filename:
                params['ResponseContentDisposition'] = f'attachment; filename="{filename}"'

            url = self._client.generate_presigned_url(
                'get_object',
                Params=params,
                ExpiresIn=expires_in
            )

            return url

        except ClientError as e:
            logger.error(f"Failed to generate presigned download URL: {e}")
            raise StorageError(f"Cannot generate download URL: {e}")

    def upload_file(
        self,
        file_obj: BinaryIO,
        storage_key: str,
        mime_type: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Upload file directly to storage.

        Args:
            file_obj: File object to upload
            storage_key: Storage key for the file
            mime_type: MIME type of the file
            metadata: Optional metadata to store with file

        Returns:
            Dict: Upload result with ETag and metadata
        """
        try:
            extra_args = {
                'ContentType': mime_type,
                'Metadata': metadata or {}
            }

            # Add server-side encryption
            if hasattr(settings, 'STORAGE_ENCRYPT_FILES') and settings.STORAGE_ENCRYPT_FILES:
                extra_args['ServerSideEncryption'] = 'AES256'

            response = self._client.upload_fileobj(
                file_obj,
                self._bucket_name,
                storage_key,
                ExtraArgs=extra_args
            )

            # Get object metadata
            head_response = self._client.head_object(
                Bucket=self._bucket_name,
                Key=storage_key
            )

            return {
                'etag': head_response['ETag'].strip('"'),
                'size': head_response['ContentLength'],
                'last_modified': head_response['LastModified'],
                'metadata': head_response.get('Metadata', {})
            }

        except ClientError as e:
            logger.error(f"Failed to upload file: {e}")
            raise StorageError(f"File upload failed: {e}")

    def download_file(self, storage_key: str) -> bytes:
        """
        Download file from storage.

        Args:
            storage_key: Storage key for the file

        Returns:
            bytes: File content
        """
        try:
            response = self._client.get_object(
                Bucket=self._bucket_name,
                Key=storage_key
            )

            return response['Body'].read()

        except ClientError as e:
            logger.error(f"Failed to download file: {e}")
            raise StorageError(f"File download failed: {e}")

    def delete_file(self, storage_key: str) -> bool:
        """
        Delete file from storage.

        Args:
            storage_key: Storage key for the file

        Returns:
            bool: True if deleted successfully
        """
        try:
            self._client.delete_object(
                Bucket=self._bucket_name,
                Key=storage_key
            )

            logger.info(f"Deleted file: {storage_key}")
            return True

        except ClientError as e:
            logger.error(f"Failed to delete file: {e}")
            raise StorageError(f"File deletion failed: {e}")

    def file_exists(self, storage_key: str) -> bool:
        """
        Check if file exists in storage.

        Args:
            storage_key: Storage key for the file

        Returns:
            bool: True if file exists
        """
        try:
            self._client.head_object(
                Bucket=self._bucket_name,
                Key=storage_key
            )
            return True

        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            else:
                logger.error(f"Error checking file existence: {e}")
                raise StorageError(f"Cannot check file existence: {e}")

    def get_file_metadata(self, storage_key: str) -> Dict[str, Any]:
        """
        Get file metadata from storage.

        Args:
            storage_key: Storage key for the file

        Returns:
            Dict: File metadata
        """
        try:
            response = self._client.head_object(
                Bucket=self._bucket_name,
                Key=storage_key
            )

            return {
                'size': response['ContentLength'],
                'last_modified': response['LastModified'],
                'etag': response['ETag'].strip('"'),
                'content_type': response.get('ContentType'),
                'metadata': response.get('Metadata', {})
            }

        except ClientError as e:
            logger.error(f"Failed to get file metadata: {e}")
            raise StorageError(f"Cannot get file metadata: {e}")


# Utility functions
def calculate_file_checksum(file_obj: BinaryIO) -> str:
    """
    Calculate SHA-256 checksum of a file.

    Args:
        file_obj: File object to checksum

    Returns:
        str: Hexadecimal checksum
    """
    sha256_hash = hashlib.sha256()

    # Read file in chunks to handle large files
    for chunk in iter(lambda: file_obj.read(8192), b""):
        sha256_hash.update(chunk)

    # Reset file pointer
    file_obj.seek(0)

    return sha256_hash.hexdigest()


def detect_file_type(filename: str, mime_type: str) -> str:
    """
    Detect file type from filename and MIME type.

    Args:
        filename: Original filename
        mime_type: MIME type

    Returns:
        str: File type classification
    """
    # Get file extension
    ext = filename.lower().split('.')[-1] if '.' in filename else ''

    # Map extensions and MIME types to file types
    if ext == 'pdf' or mime_type == 'application/pdf':
        return 'pdf'
    elif ext in ['docx', 'doc'] or 'word' in mime_type:
        return 'docx'
    elif ext == 'txt' or mime_type == 'text/plain':
        return 'txt'
    elif ext in ['jpg', 'jpeg', 'png', 'tiff', 'bmp'] or mime_type.startswith('image/'):
        return 'image'
    else:
        return 'other'


def validate_file_size(file_size: int, max_size: int = 100 * 1024 * 1024) -> bool:
    """
    Validate file size against limits.

    Args:
        file_size: File size in bytes
        max_size: Maximum allowed size in bytes

    Returns:
        bool: True if size is valid
    """
    return 0 < file_size <= max_size


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe storage.

    Args:
        filename: Original filename

    Returns:
        str: Sanitized filename
    """
    # Remove dangerous characters
    dangerous_chars = ['<', '>', ':', '"', '|', '?', '*', '\\', '/']
    safe_name = filename

    for char in dangerous_chars:
        safe_name = safe_name.replace(char, '_')

    # Limit length
    if len(safe_name) > 255:
        name_part, ext = safe_name.rsplit('.', 1) if '.' in safe_name else (safe_name, '')
        max_name_len = 255 - len(ext) - 1 if ext else 255
        safe_name = name_part[:max_name_len] + ('.' + ext if ext else '')

    return safe_name.strip()


# Global storage client instance
_storage_client: Optional[StorageClient] = None


def get_storage_client() -> StorageClient:
    """
    Get global storage client instance.

    Returns:
        StorageClient: Configured storage client
    """
    global _storage_client

    if _storage_client is None:
        _storage_client = StorageClient()

    return _storage_client


# Export functions and classes
__all__ = [
    "StorageError",
    "StorageClient",
    "get_storage_client",
    "calculate_file_checksum",
    "detect_file_type",
    "validate_file_size",
    "sanitize_filename",
]
