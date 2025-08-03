"""
File management API endpoints.

This module provides REST API endpoints for file upload, download,
processing, and management operations.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File as FastAPIFile
from sqlmodel import Session

from ..core.database import get_session
from ..core.dependencies import get_current_active_user, require_admin
from ..services.file_service import get_file_service
from ..models.user import User
from ..models.file import (
    FilePublic,
    FileWithContent,
    FileUploadInitiate,
    FileUploadResponse,
    FileUploadComplete,
    FileDownloadResponse,
    FileUpdate,
    FileStatus,
    StorageQuotaPublic,
    BatchProcessingRequest,
    BatchProcessingResponse
)

router = APIRouter()
file_service = get_file_service()


@router.post("/upload/initiate", response_model=FileUploadResponse)
async def initiate_file_upload(
    upload_request: FileUploadInitiate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Initiate file upload process.
    
    Creates a file record and returns a presigned URL for direct upload to storage.
    
    Args:
        upload_request: File upload initiation data
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        FileUploadResponse: Upload URL and metadata
    """
    return await file_service.initiate_upload(upload_request, current_user, session)


@router.post("/upload/complete", response_model=FilePublic)
async def complete_file_upload(
    completion_request: FileUploadComplete,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Complete file upload process.
    
    Verifies the uploaded file and updates the file status.
    
    Args:
        completion_request: Upload completion data
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        FilePublic: Completed file information
    """
    return await file_service.complete_upload(completion_request, current_user, session)


@router.post("/upload/direct", response_model=FilePublic)
async def direct_file_upload(
    file: UploadFile = FastAPIFile(...),
    description: Optional[str] = None,
    tags: Optional[str] = None,
    contract_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Direct file upload (for smaller files).
    
    Uploads file directly through the API without presigned URLs.
    Recommended for files smaller than 10MB.
    
    Args:
        file: Uploaded file
        description: Optional file description
        tags: Optional comma-separated tags
        contract_id: Optional associated contract ID
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        FilePublic: Uploaded file information
    """
    try:
        # Read file content
        file_content = await file.read()
        
        # Parse tags
        tag_list = [tag.strip() for tag in tags.split(',')] if tags else []
        
        # Create upload request
        upload_request = FileUploadInitiate(
            filename=file.filename,
            file_size=len(file_content),
            mime_type=file.content_type,
            checksum="",  # Will be calculated by service
            description=description,
            tags=tag_list,
            contract_id=contract_id
        )
        
        # Initiate upload
        upload_response = await file_service.initiate_upload(upload_request, current_user, session)
        
        # TODO: Implement direct upload to storage
        # For now, return the upload response
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Direct upload not yet implemented. Use initiate/complete flow."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )


@router.get("/{file_id}/download", response_model=FileDownloadResponse)
async def get_file_download_url(
    file_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Get file download URL.
    
    Generates a presigned URL for downloading the specified file.
    
    Args:
        file_id: File ID to download
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        FileDownloadResponse: Download URL and metadata
    """
    return await file_service.get_download_url(file_id, current_user, session)


@router.get("/{file_id}", response_model=FilePublic)
async def get_file(
    file_id: int,
    include_content: bool = Query(False, description="Include extracted text content"),
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Get file information.
    
    Retrieves detailed information about a specific file.
    
    Args:
        file_id: File ID
        include_content: Whether to include extracted text content
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        FilePublic or FileWithContent: File information
    """
    file_info = await file_service.get_file(file_id, current_user, session, include_content)
    
    if include_content and isinstance(file_info, FileWithContent):
        return file_info
    else:
        return file_info


@router.get("/", response_model=List[FilePublic])
async def list_files(
    contract_id: Optional[int] = Query(None, description="Filter by contract ID"),
    file_type: Optional[str] = Query(None, description="Filter by file type"),
    status: Optional[FileStatus] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results offset"),
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    List user's files.
    
    Retrieves a paginated list of files with optional filtering.
    
    Args:
        contract_id: Filter by contract ID
        file_type: Filter by file type
        status: Filter by status
        limit: Maximum results
        offset: Results offset
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        List[FilePublic]: List of files
    """
    return await file_service.list_files(
        current_user,
        session,
        contract_id=contract_id,
        file_type=file_type,
        status=status,
        limit=limit,
        offset=offset
    )


@router.put("/{file_id}", response_model=FilePublic)
async def update_file(
    file_id: int,
    file_update: FileUpdate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Update file metadata.
    
    Updates file description, tags, and other metadata.
    
    Args:
        file_id: File ID to update
        file_update: Update data
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        FilePublic: Updated file information
    """
    # TODO: Implement file update functionality
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="File update not yet implemented"
    )


@router.delete("/{file_id}")
async def delete_file(
    file_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Delete file.
    
    Removes the file from storage and marks it as deleted in the database.
    
    Args:
        file_id: File ID to delete
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        Dict: Deletion confirmation
    """
    success = await file_service.delete_file(file_id, current_user, session)
    
    if success:
        return {"message": "File deleted successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete file"
        )


@router.get("/quota/me", response_model=StorageQuotaPublic)
async def get_my_quota(
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Get current user's storage quota.
    
    Retrieves storage quota information for the authenticated user.
    
    Args:
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        StorageQuotaPublic: Quota information
    """
    return await file_service.get_user_quota(current_user.id, session)


@router.post("/batch/process", response_model=BatchProcessingResponse)
async def batch_process_files(
    batch_request: BatchProcessingRequest,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Batch process multiple files.
    
    Schedules processing jobs for multiple files at once.
    
    Args:
        batch_request: Batch processing request
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        BatchProcessingResponse: Processing job information
    """
    # TODO: Implement batch processing functionality
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Batch processing not yet implemented"
    )


# Admin endpoints
@router.get("/admin/all", response_model=List[FilePublic])
async def admin_list_all_files(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results offset"),
    current_user: User = Depends(require_admin()),
    session: Session = Depends(get_session)
):
    """
    Admin: List all files in the system.
    
    Allows administrators to view all files across all users.
    
    Args:
        user_id: Filter by user ID
        limit: Maximum results
        offset: Results offset
        current_user: Current authenticated admin user
        session: Database session
        
    Returns:
        List[FilePublic]: List of files
    """
    # TODO: Implement admin file listing
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Admin file listing not yet implemented"
    )


@router.get("/admin/quota/{user_id}", response_model=StorageQuotaPublic)
async def admin_get_user_quota(
    user_id: int,
    current_user: User = Depends(require_admin()),
    session: Session = Depends(get_session)
):
    """
    Admin: Get user's storage quota.
    
    Allows administrators to view any user's quota information.
    
    Args:
        user_id: User ID to get quota for
        current_user: Current authenticated admin user
        session: Database session
        
    Returns:
        StorageQuotaPublic: Quota information
    """
    return await file_service.get_user_quota(user_id, session)


@router.put("/admin/quota/{user_id}")
async def admin_update_user_quota(
    user_id: int,
    max_storage_bytes: int = Query(..., description="Maximum storage in bytes"),
    max_files: int = Query(..., description="Maximum number of files"),
    current_user: User = Depends(require_admin()),
    session: Session = Depends(get_session)
):
    """
    Admin: Update user's storage quota.
    
    Allows administrators to modify user quota limits.
    
    Args:
        user_id: User ID to update quota for
        max_storage_bytes: New maximum storage in bytes
        max_files: New maximum number of files
        current_user: Current authenticated admin user
        session: Database session
        
    Returns:
        Dict: Update confirmation
    """
    # TODO: Implement admin quota update
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Admin quota update not yet implemented"
    )


@router.delete("/admin/{file_id}")
async def admin_delete_file(
    file_id: int,
    current_user: User = Depends(require_admin()),
    session: Session = Depends(get_session)
):
    """
    Admin: Delete any file.
    
    Allows administrators to delete any file in the system.
    
    Args:
        file_id: File ID to delete
        current_user: Current authenticated admin user
        session: Database session
        
    Returns:
        Dict: Deletion confirmation
    """
    success = await file_service.delete_file(file_id, current_user, session)
    
    if success:
        return {"message": "File deleted successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete file"
        )


# Export router
__all__ = ["router"]
