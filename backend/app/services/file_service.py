"""
File management service layer.

This module provides high-level file management operations including
upload, download, processing, and quota management.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, BinaryIO, Tuple
from sqlmodel import Session, select, and_, or_, func
from fastapi import HTTPException, status

from ..core.storage import get_storage_client, StorageError, detect_file_type, validate_file_size
from ..core.document_processor import get_document_processor, DocumentProcessingError
from ..models.file import (
    File, FileCreate, FileUpdate, FilePublic, FileWithContent,
    FileUploadInitiate, FileUploadResponse, FileUploadComplete,
    FileDownloadResponse, FileStatus, ProcessingStatus,
    FileProcessingJob, FileProcessingJobCreate, FileProcessingJobPublic,
    StorageQuota, StorageQuotaPublic,
    BatchProcessingRequest, BatchProcessingResponse
)
from ..models.user import User
from ..models.audit_log import AuditLog, AuditAction

logger = logging.getLogger(__name__)


class FileService:
    """
    High-level file management service.

    Provides comprehensive file operations including upload/download,
    processing, quota management, and access control.
    """

    def __init__(self):
        """Initialize file service."""
        self.storage_client = get_storage_client()
        self.document_processor = get_document_processor()

    async def initiate_upload(
        self,
        upload_request: FileUploadInitiate,
        user: User,
        session: Session
    ) -> FileUploadResponse:
        """
        Initiate file upload process.

        Args:
            upload_request: Upload initiation request
            user: User performing the upload
            session: Database session

        Returns:
            FileUploadResponse: Upload URL and metadata
        """
        try:
            # Validate file size
            if not validate_file_size(upload_request.file_size):
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="File size exceeds maximum allowed size"
                )

            # Check user quota
            await self._check_user_quota(user.id, upload_request.file_size, session)

            # Detect file type
            file_type = detect_file_type(upload_request.filename, upload_request.mime_type)

            # Generate storage key
            storage_key = self.storage_client.generate_storage_key(
                user.id,
                upload_request.filename,
                file_type
            )

            # Create file record
            file_data = FileCreate(
                filename=upload_request.filename,
                file_type=file_type,
                mime_type=upload_request.mime_type,
                file_size=upload_request.file_size,
                checksum=upload_request.checksum,
                description=upload_request.description,
                tags=upload_request.tags or [],
                contract_id=upload_request.contract_id
            )

            file_record = File(
                **file_data.dict(),
                storage_path=f"s3://{self.storage_client._bucket_name}/{storage_key}",
                storage_bucket=self.storage_client._bucket_name,
                storage_key=storage_key,
                uploaded_by=user.id,
                status=FileStatus.UPLOADING
            )

            session.add(file_record)
            session.commit()
            session.refresh(file_record)

            # Generate presigned upload URL
            upload_url, upload_fields = self.storage_client.generate_presigned_upload_url(
                storage_key,
                upload_request.mime_type,
                upload_request.file_size,
                expires_in=3600  # 1 hour
            )

            # Log upload initiation
            audit_log = AuditLog(
                user_id=user.id,
                actor=f"user:{user.id}",
                action=AuditAction.FILE_UPLOAD_INITIATED,
                success=True,
                meta={
                    "file_id": file_record.id,
                    "filename": upload_request.filename,
                    "file_size": upload_request.file_size,
                    "file_type": file_type
                }
            )
            session.add(audit_log)
            session.commit()

            return FileUploadResponse(
                file_id=file_record.id,
                upload_url=upload_url,
                upload_fields=upload_fields,
                expires_at=datetime.utcnow() + timedelta(hours=1)
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Upload initiation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to initiate upload"
            )

    async def complete_upload(
        self,
        completion_request: FileUploadComplete,
        user: User,
        session: Session
    ) -> FilePublic:
        """
        Complete file upload process.

        Args:
            completion_request: Upload completion request
            user: User performing the upload
            session: Database session

        Returns:
            FilePublic: Completed file information
        """
        try:
            # Get file record
            file_record = session.get(File, completion_request.file_id)
            if not file_record:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="File not found"
                )

            # Verify ownership
            if file_record.uploaded_by != user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied"
                )

            # Verify file is in uploading state
            if file_record.status != FileStatus.UPLOADING:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File is not in uploading state"
                )

            # Verify file exists in storage
            if not self.storage_client.file_exists(file_record.storage_key):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File not found in storage"
                )

            # Get file metadata from storage
            storage_metadata = self.storage_client.get_file_metadata(file_record.storage_key)

            # Verify file size matches
            if storage_metadata['size'] != file_record.file_size:
                logger.warning(f"File size mismatch for file {file_record.id}")

            # Update file status
            file_record.status = FileStatus.UPLOADED
            file_record.updated_at = datetime.utcnow()

            # Update user quota
            await self._update_user_quota(user.id, file_record.file_size, 1, session)

            session.add(file_record)
            session.commit()
            session.refresh(file_record)

            # Schedule processing if supported
            if file_record.file_type in ['pdf', 'docx', 'image']:
                await self._schedule_processing(file_record, session)

            # Log upload completion
            audit_log = AuditLog(
                user_id=user.id,
                actor=f"user:{user.id}",
                action=AuditAction.FILE_UPLOAD_COMPLETED,
                success=True,
                meta={
                    "file_id": file_record.id,
                    "filename": file_record.filename,
                    "storage_key": file_record.storage_key
                }
            )
            session.add(audit_log)
            session.commit()

            return self._to_public_model(file_record)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Upload completion failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to complete upload"
            )

    async def get_download_url(
        self,
        file_id: int,
        user: User,
        session: Session
    ) -> FileDownloadResponse:
        """
        Generate download URL for file.

        Args:
            file_id: File ID to download
            user: User requesting download
            session: Database session

        Returns:
            FileDownloadResponse: Download URL and metadata
        """
        try:
            # Get file record
            file_record = session.get(File, file_id)
            if not file_record:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="File not found"
                )

            # Check access permissions
            if not await self._check_file_access(file_record, user, session):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied"
                )

            # Verify file is available
            if file_record.status not in [FileStatus.UPLOADED, FileStatus.PROCESSED]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File is not available for download"
                )

            # Generate download URL
            download_url = self.storage_client.generate_presigned_download_url(
                file_record.storage_key,
                expires_in=3600,  # 1 hour
                filename=file_record.filename
            )

            # Log download access
            audit_log = AuditLog(
                user_id=user.id,
                actor=f"user:{user.id}",
                action=AuditAction.FILE_DOWNLOAD,
                success=True,
                meta={
                    "file_id": file_record.id,
                    "filename": file_record.filename
                }
            )
            session.add(audit_log)
            session.commit()

            return FileDownloadResponse(
                download_url=download_url,
                expires_at=datetime.utcnow() + timedelta(hours=1),
                filename=file_record.filename,
                file_size=file_record.file_size,
                mime_type=file_record.mime_type
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Download URL generation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate download URL"
            )

    async def get_file(
        self,
        file_id: int,
        user: User,
        session: Session,
        include_content: bool = False
    ) -> FilePublic:
        """
        Get file information.

        Args:
            file_id: File ID
            user: User requesting file info
            session: Database session
            include_content: Whether to include extracted content

        Returns:
            FilePublic: File information
        """
        try:
            # Get file record
            file_record = session.get(File, file_id)
            if not file_record:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="File not found"
                )

            # Check access permissions
            if not await self._check_file_access(file_record, user, session):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied"
                )

            if include_content:
                return self._to_content_model(file_record)
            else:
                return self._to_public_model(file_record)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Get file failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get file information"
            )

    async def list_files(
        self,
        user: User,
        session: Session,
        contract_id: Optional[int] = None,
        file_type: Optional[str] = None,
        status: Optional[FileStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[FilePublic]:
        """
        List user's files with filtering.

        Args:
            user: User requesting files
            session: Database session
            contract_id: Filter by contract ID
            file_type: Filter by file type
            status: Filter by status
            limit: Maximum results
            offset: Results offset

        Returns:
            List[FilePublic]: List of files
        """
        try:
            # Build query
            query = select(File).where(File.uploaded_by == user.id)

            # Apply filters
            if contract_id is not None:
                query = query.where(File.contract_id == contract_id)

            if file_type:
                query = query.where(File.file_type == file_type)

            if status:
                query = query.where(File.status == status)

            # Apply ordering and pagination
            query = query.order_by(File.created_at.desc()).offset(offset).limit(limit)

            # Execute query
            files = session.exec(query).all()

            return [self._to_public_model(file) for file in files]

        except Exception as e:
            logger.error(f"List files failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to list files"
            )

    async def delete_file(
        self,
        file_id: int,
        user: User,
        session: Session
    ) -> bool:
        """
        Delete file.

        Args:
            file_id: File ID to delete
            user: User requesting deletion
            session: Database session

        Returns:
            bool: True if deleted successfully
        """
        try:
            # Get file record
            file_record = session.get(File, file_id)
            if not file_record:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="File not found"
                )

            # Check permissions (only owner or admin can delete)
            if file_record.uploaded_by != user.id and user.role != "admin":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied"
                )

            # Delete from storage
            try:
                self.storage_client.delete_file(file_record.storage_key)
            except StorageError as e:
                logger.warning(f"Storage deletion failed for file {file_id}: {e}")
                # Continue with database deletion even if storage fails

            # Update user quota
            await self._update_user_quota(
                file_record.uploaded_by,
                -file_record.file_size,
                -1,
                session
            )

            # Mark as deleted in database
            file_record.status = FileStatus.DELETED
            file_record.updated_at = datetime.utcnow()
            session.add(file_record)

            # Log deletion
            audit_log = AuditLog(
                user_id=user.id,
                actor=f"user:{user.id}",
                action=AuditAction.FILE_DELETE,
                success=True,
                meta={
                    "file_id": file_record.id,
                    "filename": file_record.filename,
                    "deleted_by": user.id
                }
            )
            session.add(audit_log)
            session.commit()

            return True

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"File deletion failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete file"
            )

    async def get_user_quota(
        self,
        user_id: int,
        session: Session
    ) -> StorageQuotaPublic:
        """
        Get user storage quota information.

        Args:
            user_id: User ID
            session: Database session

        Returns:
            StorageQuotaPublic: Quota information
        """
        try:
            # Get or create quota record
            quota = session.exec(
                select(StorageQuota).where(StorageQuota.user_id == user_id)
            ).first()

            if not quota:
                quota = StorageQuota(user_id=user_id)
                session.add(quota)
                session.commit()
                session.refresh(quota)

            return StorageQuotaPublic(
                user_id=quota.user_id,
                max_storage_bytes=quota.max_storage_bytes,
                max_files=quota.max_files,
                used_storage_bytes=quota.used_storage_bytes,
                used_files=quota.used_files
            )

        except Exception as e:
            logger.error(f"Get user quota failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get quota information"
            )

    async def _check_user_quota(
        self,
        user_id: int,
        additional_bytes: int,
        session: Session
    ):
        """Check if user has sufficient quota for upload."""
        quota = await self.get_user_quota(user_id, session)

        if quota.used_storage_bytes + additional_bytes > quota.max_storage_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Storage quota exceeded"
            )

        if quota.used_files + 1 > quota.max_files:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File count quota exceeded"
            )

    async def _update_user_quota(
        self,
        user_id: int,
        bytes_delta: int,
        files_delta: int,
        session: Session
    ):
        """Update user quota usage."""
        quota = session.exec(
            select(StorageQuota).where(StorageQuota.user_id == user_id)
        ).first()

        if not quota:
            quota = StorageQuota(user_id=user_id)
            session.add(quota)

        quota.used_storage_bytes = max(0, quota.used_storage_bytes + bytes_delta)
        quota.used_files = max(0, quota.used_files + files_delta)
        quota.updated_at = datetime.utcnow()

        session.add(quota)
        session.commit()

    async def _check_file_access(
        self,
        file_record: File,
        user: User,
        session: Session
    ) -> bool:
        """Check if user has access to file."""
        # Owner has access
        if file_record.uploaded_by == user.id:
            return True

        # Admin has access
        if user.role == "admin":
            return True

        # Contract-based access (if file is associated with a contract)
        if file_record.contract_id:
            # TODO: Implement contract-based access control
            # For now, allow access if user has access to the contract
            pass

        return False

    async def _schedule_processing(
        self,
        file_record: File,
        session: Session
    ):
        """Schedule document processing job."""
        try:
            processing_job = FileProcessingJob(
                file_id=file_record.id,
                job_type="document_extraction",
                status=ProcessingStatus.PENDING,
                priority=5,
                parameters={
                    "extract_text": True,
                    "perform_ocr": file_record.file_type == "image",
                    "use_advanced_extraction": file_record.file_type == "pdf"
                }
            )

            session.add(processing_job)
            session.commit()

            # Update file processing status
            file_record.processing_status = ProcessingStatus.PENDING
            session.add(file_record)
            session.commit()

            logger.info(f"Scheduled processing for file {file_record.id}")

        except Exception as e:
            logger.error(f"Failed to schedule processing for file {file_record.id}: {e}")

    def _to_public_model(self, file_record: File) -> FilePublic:
        """Convert file record to public model."""
        return FilePublic(
            id=file_record.id,
            filename=file_record.filename,
            file_type=file_record.file_type,
            mime_type=file_record.mime_type,
            file_size=file_record.file_size,
            checksum=file_record.checksum,
            description=file_record.description,
            tags=file_record.tags or [],
            file_metadata=file_record.file_metadata or {},
            storage_path=file_record.storage_path,
            status=file_record.status,
            processing_status=file_record.processing_status,
            uploaded_by=file_record.uploaded_by,
            contract_id=file_record.contract_id,
            created_at=file_record.created_at,
            updated_at=file_record.updated_at,
            processed_at=file_record.processed_at,
            expires_at=file_record.expires_at,
            has_extracted_text=bool(file_record.extracted_text),
            has_ocr_text=bool(file_record.ocr_text),
            processing_error=file_record.processing_error
        )

    def _to_content_model(self, file_record: File) -> FileWithContent:
        """Convert file record to content model."""
        public_model = self._to_public_model(file_record)
        return FileWithContent(
            **public_model.dict(),
            extracted_text=file_record.extracted_text,
            ocr_text=file_record.ocr_text
        )


# Global file service instance
_file_service: Optional[FileService] = None


def get_file_service() -> FileService:
    """
    Get global file service instance.

    Returns:
        FileService: Configured file service
    """
    global _file_service

    if _file_service is None:
        _file_service = FileService()

    return _file_service


# Export service
__all__ = [
    "FileService",
    "get_file_service",
]
