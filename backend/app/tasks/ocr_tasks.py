"""
OCR tasks for document text extraction and processing.

This module contains Celery tasks for optical character recognition,
text extraction from PDFs and images, and text quality enhancement.
"""

import logging
import tempfile
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
from io import BytesIO

from celery import current_task
import structlog
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import pymupdf4llm

from ..core.celery_app import celery_app, DatabaseTask
from ..core.document_processor import get_document_processor, DocumentProcessingError
from ..models.file import File, ProcessingStatus
from ..models.audit_log import AuditLog, AuditAction

logger = structlog.get_logger(__name__)


@celery_app.task(bind=True, base=DatabaseTask, name="app.tasks.ocr_tasks.extract_text_from_pdf")
def extract_text_from_pdf(
    self,
    file_content: bytes,
    filename: str,
    use_ocr: bool = False,
    enhance_quality: bool = True
) -> Dict[str, Any]:
    """
    Extract text from PDF document using PyMuPDF and OCR fallback.
    
    Args:
        file_content: PDF file content bytes
        filename: Original filename
        use_ocr: Force OCR even if text is extractable
        enhance_quality: Apply text quality enhancement
        
    Returns:
        Dict: Extracted text and metadata
    """
    try:
        logger.info(
            "Starting PDF text extraction",
            filename=filename,
            size=len(file_content),
            use_ocr=use_ocr,
            enhance_quality=enhance_quality
        )
        
        # Create temporary file for processing
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_file.write(file_content)
            temp_path = temp_file.name
        
        try:
            # Open PDF document
            doc = fitz.open(temp_path)
            
            extraction_results = {
                "text": "",
                "pages": [],
                "metadata": {
                    "page_count": len(doc),
                    "has_extractable_text": False,
                    "extraction_method": "direct",
                    "processing_time": 0,
                    "filename": filename
                },
                "success": True
            }
            
            start_time = datetime.utcnow()
            
            # Try direct text extraction first
            if not use_ocr:
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    page_text = page.get_text()
                    
                    if page_text.strip():
                        extraction_results["metadata"]["has_extractable_text"] = True
                        extraction_results["text"] += page_text + "\n"
                        extraction_results["pages"].append({
                            "page_number": page_num + 1,
                            "text": page_text,
                            "method": "direct"
                        })
            
            # Use OCR if no extractable text or forced
            if not extraction_results["metadata"]["has_extractable_text"] or use_ocr:
                logger.info("Using OCR for text extraction", filename=filename)
                extraction_results["metadata"]["extraction_method"] = "ocr"
                
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    
                    # Convert page to image
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better OCR
                    img_data = pix.tobytes("png")
                    
                    # Perform OCR
                    ocr_result = extract_text_from_image.delay(img_data, f"{filename}_page_{page_num + 1}")
                    page_text = ocr_result.get(timeout=300)  # 5 minute timeout
                    
                    if page_text and page_text.get("text", "").strip():
                        extraction_results["text"] += page_text["text"] + "\n"
                        extraction_results["pages"].append({
                            "page_number": page_num + 1,
                            "text": page_text["text"],
                            "method": "ocr",
                            "confidence": page_text.get("confidence", 0)
                        })
            
            # Use advanced extraction with pymupdf4llm for better formatting
            if extraction_results["metadata"]["has_extractable_text"]:
                try:
                    markdown_text = pymupdf4llm.to_markdown(temp_path)
                    if markdown_text and len(markdown_text) > len(extraction_results["text"]):
                        extraction_results["text"] = markdown_text
                        extraction_results["metadata"]["extraction_method"] = "advanced"
                        logger.info("Used advanced extraction method", filename=filename)
                except Exception as e:
                    logger.warning("Advanced extraction failed, using basic method", error=str(e))
            
            # Enhance text quality if requested
            if enhance_quality and extraction_results["text"]:
                enhanced_result = enhance_text_quality.delay(extraction_results["text"], filename)
                enhanced_text = enhanced_result.get(timeout=120)  # 2 minute timeout
                if enhanced_text and enhanced_text.get("enhanced_text"):
                    extraction_results["text"] = enhanced_text["enhanced_text"]
                    extraction_results["metadata"]["text_enhanced"] = True
            
            doc.close()
            
            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            extraction_results["metadata"]["processing_time"] = processing_time
            
            logger.info(
                "PDF text extraction completed",
                filename=filename,
                text_length=len(extraction_results["text"]),
                pages_processed=len(extraction_results["pages"]),
                processing_time=processing_time,
                method=extraction_results["metadata"]["extraction_method"]
            )
            
            return extraction_results
            
        finally:
            # Clean up temporary file
            Path(temp_path).unlink(missing_ok=True)
            
    except Exception as exc:
        logger.error("PDF text extraction failed", filename=filename, error=str(exc), exc_info=True)
        
        return {
            "text": "",
            "pages": [],
            "metadata": {
                "filename": filename,
                "extraction_error": str(exc),
                "processing_time": 0
            },
            "success": False,
            "error": str(exc)
        }


@celery_app.task(bind=True, name="app.tasks.ocr_tasks.extract_text_from_image")
def extract_text_from_image(
    self,
    image_content: bytes,
    filename: str,
    language: str = "eng",
    psm: int = 6
) -> Dict[str, Any]:
    """
    Extract text from image using Tesseract OCR.
    
    Args:
        image_content: Image file content bytes
        filename: Original filename
        language: OCR language (default: English)
        psm: Page segmentation mode for Tesseract
        
    Returns:
        Dict: Extracted text and confidence scores
    """
    try:
        logger.info(
            "Starting image OCR",
            filename=filename,
            size=len(image_content),
            language=language,
            psm=psm
        )
        
        # Open image
        image = Image.open(BytesIO(image_content))
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        start_time = datetime.utcnow()
        
        # Configure Tesseract
        custom_config = f'--oem 3 --psm {psm} -l {language}'
        
        # Extract text
        extracted_text = pytesseract.image_to_string(image, config=custom_config)
        
        # Get confidence scores
        try:
            data = pytesseract.image_to_data(image, config=custom_config, output_type=pytesseract.Output.DICT)
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        except Exception:
            avg_confidence = 0
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        results = {
            "text": extracted_text,
            "confidence": avg_confidence,
            "metadata": {
                "filename": filename,
                "image_size": image.size,
                "image_mode": image.mode,
                "language": language,
                "psm": psm,
                "processing_time": processing_time,
                "word_count": len(extracted_text.split()) if extracted_text else 0
            },
            "success": True
        }
        
        logger.info(
            "Image OCR completed",
            filename=filename,
            text_length=len(extracted_text),
            confidence=avg_confidence,
            processing_time=processing_time
        )
        
        return results
        
    except Exception as exc:
        logger.error("Image OCR failed", filename=filename, error=str(exc), exc_info=True)
        
        return {
            "text": "",
            "confidence": 0,
            "metadata": {
                "filename": filename,
                "extraction_error": str(exc),
                "processing_time": 0
            },
            "success": False,
            "error": str(exc)
        }


@celery_app.task(bind=True, base=DatabaseTask, name="app.tasks.ocr_tasks.process_document_ocr")
def process_document_ocr(
    self,
    file_id: int,
    user_id: int,
    force_ocr: bool = False,
    enhance_quality: bool = True
) -> Dict[str, Any]:
    """
    Process document OCR and update database record.
    
    Args:
        file_id: Database file record ID
        user_id: User requesting the processing
        force_ocr: Force OCR even if text is extractable
        enhance_quality: Apply text quality enhancement
        
    Returns:
        Dict: Processing results
    """
    try:
        logger.info(
            "Starting document OCR processing",
            file_id=file_id,
            user_id=user_id,
            force_ocr=force_ocr
        )
        
        # Get file record
        file_record = self.session.get(File, file_id)
        if not file_record:
            raise ValueError(f"File record not found: {file_id}")
        
        # Update processing status
        file_record.processing_status = ProcessingStatus.PROCESSING
        file_record.processing_started_at = datetime.utcnow()
        self.session.add(file_record)
        self.session.commit()
        
        # Get file content from storage
        from ..core.storage import get_storage_client
        storage_client = get_storage_client()
        file_content = storage_client.download_file(file_record.storage_key)
        
        # Process based on file type
        if file_record.mime_type == "application/pdf":
            ocr_result = extract_text_from_pdf.delay(
                file_content, file_record.original_filename, force_ocr, enhance_quality
            )
        elif file_record.mime_type.startswith("image/"):
            ocr_result = extract_text_from_image.delay(
                file_content, file_record.original_filename
            )
        else:
            raise ValueError(f"Unsupported file type for OCR: {file_record.mime_type}")
        
        # Get OCR results
        extraction_results = ocr_result.get(timeout=600)  # 10 minute timeout
        
        # Update file record with OCR results
        if extraction_results.get("success"):
            file_record.extracted_text = extraction_results["text"]
            file_record.processing_status = ProcessingStatus.COMPLETED
            
            # Update metadata
            current_metadata = file_record.metadata or {}
            current_metadata.update({
                "ocr_results": extraction_results["metadata"],
                "text_extracted": True,
                "text_length": len(extraction_results["text"]),
                "ocr_task_id": self.request.id
            })
            file_record.metadata = current_metadata
        else:
            file_record.processing_status = ProcessingStatus.FAILED
            file_record.processing_error = extraction_results.get("error", "OCR processing failed")
        
        file_record.processing_completed_at = datetime.utcnow()
        self.session.add(file_record)
        
        # Create audit log
        audit_log = AuditLog(
            user_id=user_id,
            actor=f"system:ocr_task:{self.request.id}",
            action=AuditAction.FILE_PROCESS,
            resource_type="file",
            resource_id=str(file_id),
            success=extraction_results.get("success", False),
            meta={
                "file_id": file_id,
                "ocr_method": extraction_results.get("metadata", {}).get("extraction_method"),
                "text_length": len(extraction_results.get("text", "")),
                "processing_duration": (
                    datetime.utcnow() - file_record.processing_started_at
                ).total_seconds()
            }
        )
        self.session.add(audit_log)
        self.session.commit()
        
        logger.info(
            "Document OCR processing completed",
            file_id=file_id,
            success=extraction_results.get("success"),
            text_length=len(extraction_results.get("text", ""))
        )
        
        return {
            "status": "completed" if extraction_results.get("success") else "failed",
            "file_id": file_id,
            "text_length": len(extraction_results.get("text", "")),
            "extraction_results": extraction_results
        }
        
    except Exception as exc:
        logger.error("Document OCR processing failed", file_id=file_id, error=str(exc), exc_info=True)
        
        # Update file record with error
        if 'file_record' in locals():
            file_record.processing_status = ProcessingStatus.FAILED
            file_record.processing_error = str(exc)
            file_record.processing_completed_at = datetime.utcnow()
            self.session.add(file_record)
            self.session.commit()
        
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@celery_app.task(bind=True, name="app.tasks.ocr_tasks.enhance_text_quality")
def enhance_text_quality(self, text: str, filename: str) -> Dict[str, Any]:
    """
    Enhance extracted text quality using post-processing techniques.
    
    Args:
        text: Raw extracted text
        filename: Original filename for context
        
    Returns:
        Dict: Enhanced text and improvement metrics
    """
    try:
        logger.info("Starting text quality enhancement", filename=filename, text_length=len(text))
        
        enhanced_text = text
        improvements = []
        
        # Basic text cleaning
        # Remove excessive whitespace
        import re
        enhanced_text = re.sub(r'\s+', ' ', enhanced_text)
        enhanced_text = re.sub(r'\n\s*\n', '\n\n', enhanced_text)
        
        # Fix common OCR errors
        ocr_corrections = {
            r'\b0\b': 'O',  # Zero to O
            r'\bl\b': 'I',  # lowercase l to I
            r'\brn\b': 'm',  # rn to m
            r'\bvv\b': 'w',  # vv to w
        }
        
        for pattern, replacement in ocr_corrections.items():
            if re.search(pattern, enhanced_text):
                enhanced_text = re.sub(pattern, replacement, enhanced_text)
                improvements.append(f"Fixed OCR pattern: {pattern} -> {replacement}")
        
        # Calculate improvement metrics
        original_length = len(text)
        enhanced_length = len(enhanced_text)
        
        results = {
            "enhanced_text": enhanced_text,
            "improvements": improvements,
            "metrics": {
                "original_length": original_length,
                "enhanced_length": enhanced_length,
                "improvement_count": len(improvements),
                "filename": filename
            },
            "success": True
        }
        
        logger.info(
            "Text quality enhancement completed",
            filename=filename,
            improvements=len(improvements),
            length_change=enhanced_length - original_length
        )
        
        return results
        
    except Exception as exc:
        logger.error("Text quality enhancement failed", filename=filename, error=str(exc))
        
        return {
            "enhanced_text": text,  # Return original text on failure
            "improvements": [],
            "metrics": {
                "original_length": len(text),
                "enhanced_length": len(text),
                "improvement_count": 0,
                "filename": filename,
                "enhancement_error": str(exc)
            },
            "success": False,
            "error": str(exc)
        }
