"""
Background worker for document processing.

This module provides asynchronous document processing capabilities
for extracting text, performing OCR, and updating file records.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from sqlmodel import Session, select

from ..core.database import get_session_context
from ..core.storage import get_storage_client, StorageError
from ..core.document_processor import get_document_processor, DocumentProcessingError
from ..models.file import File, FileProcessingJob, ProcessingStatus, FileStatus
from ..models.audit_log import AuditLog

logger = logging.getLogger(__name__)


class DocumentWorker:
    """
    Background worker for processing documents.
    
    Handles queued document processing jobs including text extraction,
    OCR, and metadata extraction with proper error handling and logging.
    """
    
    def __init__(self):
        """Initialize document worker."""
        self.storage_client = get_storage_client()
        self.document_processor = get_document_processor()
        self.is_running = False
        self.max_concurrent_jobs = 3
        self.processing_semaphore = asyncio.Semaphore(self.max_concurrent_jobs)
    
    async def start(self):
        """Start the document processing worker."""
        if self.is_running:
            logger.warning("Document worker is already running")
            return
        
        self.is_running = True
        logger.info("Starting document processing worker")
        
        try:
            while self.is_running:
                await self._process_pending_jobs()
                await asyncio.sleep(10)  # Check for new jobs every 10 seconds
                
        except Exception as e:
            logger.error(f"Document worker error: {e}")
        finally:
            self.is_running = False
            logger.info("Document processing worker stopped")
    
    async def stop(self):
        """Stop the document processing worker."""
        logger.info("Stopping document processing worker")
        self.is_running = False
    
    async def _process_pending_jobs(self):
        """Process all pending document processing jobs."""
        try:
            with get_session_context() as session:
                # Get pending jobs ordered by priority and creation time
                pending_jobs = session.exec(
                    select(FileProcessingJob)
                    .where(FileProcessingJob.status == ProcessingStatus.PENDING)
                    .order_by(FileProcessingJob.priority.asc(), FileProcessingJob.created_at.asc())
                    .limit(self.max_concurrent_jobs * 2)  # Get more jobs than we can process concurrently
                ).all()
                
                if not pending_jobs:
                    return
                
                logger.info(f"Found {len(pending_jobs)} pending processing jobs")
                
                # Process jobs concurrently
                tasks = []
                for job in pending_jobs[:self.max_concurrent_jobs]:
                    task = asyncio.create_task(self._process_job(job.id))
                    tasks.append(task)
                
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                    
        except Exception as e:
            logger.error(f"Error processing pending jobs: {e}")
    
    async def _process_job(self, job_id: int):
        """
        Process a single document processing job.
        
        Args:
            job_id: ID of the processing job
        """
        async with self.processing_semaphore:
            try:
                with get_session_context() as session:
                    # Get job and file
                    job = session.get(FileProcessingJob, job_id)
                    if not job:
                        logger.warning(f"Processing job {job_id} not found")
                        return
                    
                    # Check if job is still pending
                    if job.status != ProcessingStatus.PENDING:
                        logger.info(f"Job {job_id} is no longer pending (status: {job.status})")
                        return
                    
                    # Get associated file
                    file_record = session.get(File, job.file_id)
                    if not file_record:
                        logger.error(f"File {job.file_id} not found for job {job_id}")
                        await self._mark_job_failed(job, "Associated file not found", session)
                        return
                    
                    # Update job status to in progress
                    job.status = ProcessingStatus.IN_PROGRESS
                    job.started_at = datetime.utcnow()
                    session.add(job)
                    session.commit()
                    
                    logger.info(f"Processing job {job_id} for file {file_record.filename}")
                    
                    # Process the document
                    await self._process_document(job, file_record, session)
                    
            except Exception as e:
                logger.error(f"Error processing job {job_id}: {e}")
                try:
                    with get_session_context() as session:
                        job = session.get(FileProcessingJob, job_id)
                        if job:
                            await self._mark_job_failed(job, str(e), session)
                except Exception as cleanup_error:
                    logger.error(f"Error during job cleanup: {cleanup_error}")
    
    async def _process_document(
        self,
        job: FileProcessingJob,
        file_record: File,
        session: Session
    ):
        """
        Process a document file.
        
        Args:
            job: Processing job
            file_record: File record
            session: Database session
        """
        try:
            # Update file processing status
            file_record.processing_status = ProcessingStatus.IN_PROGRESS
            session.add(file_record)
            session.commit()
            
            # Download file from storage
            try:
                file_content = self.storage_client.download_file(file_record.storage_key)
            except StorageError as e:
                raise DocumentProcessingError(f"Failed to download file: {e}")
            
            # Process document
            processing_options = job.parameters or {}
            processing_result = await self.document_processor.process_document(
                file_content,
                file_record.file_type,
                file_record.filename,
                processing_options
            )
            
            # Update file record with processing results
            if processing_result.get('processing_success'):
                file_record.extracted_text = processing_result.get('extracted_text')
                file_record.ocr_text = processing_result.get('ocr_text')
                file_record.processing_status = ProcessingStatus.COMPLETED
                file_record.processed_at = datetime.utcnow()
                
                # Update metadata
                if file_record.metadata is None:
                    file_record.metadata = {}
                
                file_record.metadata.update({
                    'document_stats': processing_result.get('document_stats', {}),
                    'processing_metadata': processing_result.get('processing_metadata', {})
                })
                
                # Store detailed results in job
                job.result = {
                    'processing_success': True,
                    'extracted_text_length': len(processing_result.get('extracted_text', '')),
                    'ocr_text_length': len(processing_result.get('ocr_text', '') or ''),
                    'document_stats': processing_result.get('document_stats', {}),
                    'pages_processed': len(processing_result.get('pages_data', [])),
                }
                
                logger.info(f"Successfully processed document {file_record.filename}")
                
            else:
                raise DocumentProcessingError("Document processing failed")
            
            # Mark job as completed
            job.status = ProcessingStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            
            # Update file status if it was just uploaded
            if file_record.status == FileStatus.UPLOADED:
                file_record.status = FileStatus.PROCESSED
            
            session.add(job)
            session.add(file_record)
            session.commit()
            
            # Log successful processing
            audit_log = AuditLog(
                actor=f"system:document_worker",
                action="file.processing_completed",
                success=True,
                meta={
                    "file_id": file_record.id,
                    "job_id": job.id,
                    "filename": file_record.filename,
                    "processing_time_seconds": (
                        job.completed_at - job.started_at
                    ).total_seconds() if job.started_at else None
                }
            )
            session.add(audit_log)
            session.commit()
            
        except Exception as e:
            logger.error(f"Document processing failed for file {file_record.id}: {e}")
            await self._mark_job_failed(job, str(e), session)
            
            # Update file processing status
            file_record.processing_status = ProcessingStatus.FAILED
            file_record.processing_error = str(e)
            session.add(file_record)
            session.commit()
    
    async def _mark_job_failed(
        self,
        job: FileProcessingJob,
        error_message: str,
        session: Session
    ):
        """
        Mark a processing job as failed.
        
        Args:
            job: Processing job
            error_message: Error message
            session: Database session
        """
        try:
            job.status = ProcessingStatus.FAILED
            job.error_message = error_message
            job.completed_at = datetime.utcnow()
            
            session.add(job)
            session.commit()
            
            # Log failed processing
            audit_log = AuditLog(
                actor=f"system:document_worker",
                action="file.processing_failed",
                success=False,
                error_message=error_message,
                meta={
                    "file_id": job.file_id,
                    "job_id": job.id,
                    "error": error_message
                }
            )
            session.add(audit_log)
            session.commit()
            
            logger.error(f"Marked job {job.id} as failed: {error_message}")
            
        except Exception as e:
            logger.error(f"Error marking job {job.id} as failed: {e}")
    
    async def process_file_immediately(
        self,
        file_id: int,
        processing_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a file immediately (for testing or priority processing).
        
        Args:
            file_id: File ID to process
            processing_options: Optional processing parameters
            
        Returns:
            Dict: Processing results
        """
        try:
            with get_session_context() as session:
                # Get file record
                file_record = session.get(File, file_id)
                if not file_record:
                    raise ValueError(f"File {file_id} not found")
                
                # Create processing job
                job = FileProcessingJob(
                    file_id=file_id,
                    job_type="immediate_processing",
                    status=ProcessingStatus.PENDING,
                    priority=1,  # High priority
                    parameters=processing_options or {}
                )
                
                session.add(job)
                session.commit()
                session.refresh(job)
                
                # Process immediately
                await self._process_document(job, file_record, session)
                
                # Return results
                session.refresh(job)
                return {
                    "job_id": job.id,
                    "status": job.status.value,
                    "result": job.result,
                    "error_message": job.error_message
                }
                
        except Exception as e:
            logger.error(f"Immediate processing failed for file {file_id}: {e}")
            return {
                "job_id": None,
                "status": "failed",
                "result": None,
                "error_message": str(e)
            }
    
    async def get_job_status(self, job_id: int) -> Optional[Dict[str, Any]]:
        """
        Get processing job status.
        
        Args:
            job_id: Processing job ID
            
        Returns:
            Dict: Job status information
        """
        try:
            with get_session_context() as session:
                job = session.get(FileProcessingJob, job_id)
                if not job:
                    return None
                
                return {
                    "job_id": job.id,
                    "file_id": job.file_id,
                    "job_type": job.job_type,
                    "status": job.status.value,
                    "priority": job.priority,
                    "created_at": job.created_at.isoformat(),
                    "started_at": job.started_at.isoformat() if job.started_at else None,
                    "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                    "result": job.result,
                    "error_message": job.error_message
                }
                
        except Exception as e:
            logger.error(f"Error getting job status for {job_id}: {e}")
            return None
    
    async def cleanup_old_jobs(self, days_old: int = 30):
        """
        Clean up old completed/failed processing jobs.
        
        Args:
            days_old: Remove jobs older than this many days
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            with get_session_context() as session:
                # Delete old completed/failed jobs
                old_jobs = session.exec(
                    select(FileProcessingJob)
                    .where(
                        and_(
                            FileProcessingJob.status.in_([
                                ProcessingStatus.COMPLETED,
                                ProcessingStatus.FAILED
                            ]),
                            FileProcessingJob.completed_at < cutoff_date
                        )
                    )
                ).all()
                
                for job in old_jobs:
                    session.delete(job)
                
                session.commit()
                
                logger.info(f"Cleaned up {len(old_jobs)} old processing jobs")
                
        except Exception as e:
            logger.error(f"Error cleaning up old jobs: {e}")


# Global document worker instance
_document_worker: Optional[DocumentWorker] = None


def get_document_worker() -> DocumentWorker:
    """
    Get global document worker instance.
    
    Returns:
        DocumentWorker: Document processing worker
    """
    global _document_worker
    
    if _document_worker is None:
        _document_worker = DocumentWorker()
    
    return _document_worker


# Export worker
__all__ = [
    "DocumentWorker",
    "get_document_worker",
]
