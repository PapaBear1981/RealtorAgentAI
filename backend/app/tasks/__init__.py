"""
Background task modules for the RealtorAgentAI platform.

This package contains Celery tasks organized by functionality:
- ingest_tasks: File upload and validation tasks
- ocr_tasks: Document text extraction tasks
- llm_tasks: AI model interaction tasks
- export_tasks: Document generation and delivery tasks
- system_tasks: Maintenance and monitoring tasks

All tasks are configured with proper retry logic, error handling,
and monitoring capabilities.
"""

from .ingest_tasks import *
# from .ocr_tasks import *  # Temporarily disabled due to pytesseract dependency
from .llm_tasks import *
from .export_tasks import *
from .system_tasks import *

__all__ = [
    # Ingest tasks
    "process_file_upload",
    "validate_document",
    "extract_metadata",
    "virus_scan_file",

    # OCR tasks (temporarily disabled due to pytesseract dependency)
    # "extract_text_from_pdf",
    # "extract_text_from_image",
    # "process_document_ocr",
    # "enhance_text_quality",

    # LLM tasks
    "analyze_contract_content",
    "generate_contract_summary",
    "extract_contract_entities",
    "validate_contract_compliance",
    "generate_contract_from_template",

    # Export tasks
    "generate_pdf_document",
    "generate_docx_document",
    "prepare_document_delivery",
    "send_document_notification",

    # System tasks
    "cleanup_expired_results",
    "health_check",
    "update_task_metrics",
    "backup_database",
    "optimize_storage",
]
