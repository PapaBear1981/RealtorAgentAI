"""
Tests for document processing functionality.

This module tests PDF processing, DOCX processing, OCR,
and document validation capabilities.
"""

import pytest
import asyncio
import io
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from PIL import Image

from app.core.document_processor import (
    DocumentProcessor, DocumentProcessingError,
    get_document_processor
)


class TestDocumentProcessor:
    """Test DocumentProcessor functionality."""
    
    def test_document_processor_initialization(self):
        """Test document processor initialization."""
        processor = DocumentProcessor()
        
        assert 'pdf' in processor.supported_formats
        assert 'docx' in processor.supported_formats
        assert 'image' in processor.supported_formats
        assert 'txt' in processor.supported_formats
    
    def test_get_supported_formats(self):
        """Test getting supported file formats."""
        processor = DocumentProcessor()
        formats = processor.get_supported_formats()
        
        expected_formats = ['pdf', 'docx', 'doc', 'txt', 'image']
        assert all(fmt in formats for fmt in expected_formats)
    
    @pytest.mark.asyncio
    async def test_process_document_unsupported_type(self):
        """Test processing unsupported file type."""
        processor = DocumentProcessor()
        
        with pytest.raises(DocumentProcessingError, match="Unsupported file type"):
            await processor.process_document(
                file_content=b"test content",
                file_type="unsupported",
                filename="test.unsupported"
            )
    
    @pytest.mark.asyncio
    async def test_process_text_document(self):
        """Test processing plain text document."""
        processor = DocumentProcessor()
        
        text_content = "This is a test document.\nWith multiple lines.\nAnd some content."
        file_content = text_content.encode('utf-8')
        
        result = await processor.process_document(
            file_content=file_content,
            file_type="txt",
            filename="test.txt"
        )
        
        assert result['processing_success'] is True
        assert result['extracted_text'] == text_content
        assert result['ocr_text'] is None
        assert result['document_stats']['line_count'] == 3
        assert result['document_stats']['word_count'] > 0
        assert 'processing_metadata' in result
    
    @pytest.mark.asyncio
    async def test_process_text_document_encoding_fallback(self):
        """Test processing text document with encoding issues."""
        processor = DocumentProcessor()
        
        # Create content with non-UTF-8 characters
        text_content = "Test with special chars: café"
        file_content = text_content.encode('latin-1')
        
        result = await processor.process_document(
            file_content=file_content,
            file_type="txt",
            filename="test.txt"
        )
        
        assert result['processing_success'] is True
        assert result['extracted_text'] is not None
        assert len(result['extracted_text']) > 0
    
    @patch('app.core.document_processor.pymupdf4llm')
    @patch('app.core.document_processor.fitz')
    @pytest.mark.asyncio
    async def test_process_pdf_document_advanced(self, mock_fitz, mock_pymupdf4llm):
        """Test processing PDF document with advanced extraction."""
        processor = DocumentProcessor()
        
        # Mock pymupdf4llm
        mock_pymupdf4llm.to_markdown.side_effect = [
            "# Test Document\n\nThis is test content.",  # First call for text
            [{"page": 1, "text": "Page 1 content", "metadata": {}}]  # Second call for chunks
        ]
        
        # Mock PyMuPDF
        mock_doc = Mock()
        mock_doc.metadata = {"title": "Test Document", "author": "Test Author"}
        mock_doc.page_count = 1
        mock_doc.needs_pass = False
        
        mock_page = Mock()
        mock_page.get_links.return_value = []
        mock_page.get_images.return_value = []
        mock_page.annots.return_value = []
        mock_doc.__getitem__.return_value = mock_page
        mock_doc.__iter__.return_value = [mock_page]
        
        mock_fitz.open.return_value = mock_doc
        
        # Create a temporary PDF file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_file.write(b"fake pdf content")
            temp_path = temp_file.name
        
        try:
            # Mock the temporary file creation
            with patch('tempfile.NamedTemporaryFile') as mock_temp:
                mock_temp_file = Mock()
                mock_temp_file.name = temp_path
                mock_temp_file.__enter__.return_value = mock_temp_file
                mock_temp_file.__exit__.return_value = None
                mock_temp.return_value = mock_temp_file
                
                result = await processor.process_document(
                    file_content=b"fake pdf content",
                    file_type="pdf",
                    filename="test.pdf",
                    processing_options={"use_advanced_extraction": True}
                )
                
                assert result['processing_success'] is True
                assert result['extracted_text'] == "# Test Document\n\nThis is test content."
                assert result['document_metadata']['title'] == "Test Document"
                assert result['document_stats']['page_count'] == 1
                assert result['document_stats']['is_encrypted'] is False
        
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    @patch('app.core.document_processor.DocxDocument')
    @pytest.mark.asyncio
    async def test_process_docx_document(self, mock_docx_document):
        """Test processing DOCX document."""
        processor = DocumentProcessor()
        
        # Mock DOCX document
        mock_doc = Mock()
        
        # Mock paragraphs
        mock_para1 = Mock()
        mock_para1.text = "First paragraph"
        mock_para1.style.name = "Normal"
        
        mock_para2 = Mock()
        mock_para2.text = "Second paragraph"
        mock_para2.style.name = "Heading 1"
        
        mock_doc.paragraphs = [mock_para1, mock_para2]
        
        # Mock tables
        mock_cell1 = Mock()
        mock_cell1.text = "Cell 1"
        mock_cell2 = Mock()
        mock_cell2.text = "Cell 2"
        
        mock_row = Mock()
        mock_row.cells = [mock_cell1, mock_cell2]
        
        mock_table = Mock()
        mock_table.rows = [mock_row]
        
        mock_doc.tables = [mock_table]
        
        # Mock core properties
        mock_props = Mock()
        mock_props.title = "Test Document"
        mock_props.author = "Test Author"
        mock_props.subject = "Test Subject"
        mock_props.keywords = "test, document"
        mock_props.created = None
        mock_props.modified = None
        mock_props.last_modified_by = None
        mock_props.revision = None
        mock_props.category = None
        mock_props.comments = None
        
        mock_doc.core_properties = mock_props
        
        mock_docx_document.return_value = mock_doc
        
        result = await processor.process_document(
            file_content=b"fake docx content",
            file_type="docx",
            filename="test.docx"
        )
        
        assert result['processing_success'] is True
        assert "First paragraph" in result['extracted_text']
        assert "Second paragraph" in result['extracted_text']
        assert "Cell 1" in result['extracted_text']
        assert result['document_metadata']['title'] == "Test Document"
        assert result['document_stats']['paragraph_count'] == 2
        assert result['document_stats']['table_count'] == 1
    
    @patch('app.core.document_processor.pytesseract')
    @patch('app.core.document_processor.Image')
    @pytest.mark.asyncio
    async def test_process_image_ocr(self, mock_image_class, mock_pytesseract):
        """Test processing image with OCR."""
        processor = DocumentProcessor()
        
        # Mock PIL Image
        mock_image = Mock()
        mock_image.format = "JPEG"
        mock_image.mode = "RGB"
        mock_image.size = (800, 600)
        mock_image.getbands.return_value = ['R', 'G', 'B']
        mock_image.info = {}
        
        mock_image_class.open.return_value = mock_image
        
        # Mock Tesseract OCR
        mock_pytesseract.image_to_string.return_value = "This is extracted text from image"
        mock_pytesseract.image_to_data.return_value = {
            'conf': [95, 90, 85, 92],
            'text': ['This', 'is', 'extracted', 'text']
        }
        
        result = await processor.process_document(
            file_content=b"fake image content",
            file_type="image",
            filename="test.jpg",
            processing_options={"detailed_ocr": True}
        )
        
        assert result['processing_success'] is True
        assert result['extracted_text'] is None  # Images don't have native text
        assert result['ocr_text'] == "This is extracted text from image"
        assert result['image_metadata']['format'] == "JPEG"
        assert result['document_stats']['width'] == 800
        assert result['document_stats']['height'] == 600
        assert result['document_stats']['ocr_confidence'] > 0
    
    @pytest.mark.asyncio
    async def test_validate_document_pdf_valid(self):
        """Test PDF document validation - valid file."""
        processor = DocumentProcessor()
        
        with patch('app.core.document_processor.fitz') as mock_fitz:
            mock_doc = Mock()
            mock_doc.needs_pass = False
            mock_fitz.open.return_value = mock_doc
            
            with patch('tempfile.NamedTemporaryFile') as mock_temp:
                mock_temp_file = Mock()
                mock_temp_file.name = "/tmp/test.pdf"
                mock_temp_file.__enter__.return_value = mock_temp_file
                mock_temp_file.__exit__.return_value = None
                mock_temp.return_value = mock_temp_file
                
                with patch('os.unlink'):
                    result = await processor.validate_document(
                        file_content=b"fake pdf content",
                        file_type="pdf",
                        filename="test.pdf"
                    )
                    
                    assert result['is_valid'] is True
                    assert result['detected_type'] == "pdf"
                    assert len(result['errors']) == 0
    
    @pytest.mark.asyncio
    async def test_validate_document_pdf_password_protected(self):
        """Test PDF document validation - password protected."""
        processor = DocumentProcessor()
        
        with patch('app.core.document_processor.fitz') as mock_fitz:
            mock_doc = Mock()
            mock_doc.needs_pass = True
            mock_fitz.open.return_value = mock_doc
            
            with patch('tempfile.NamedTemporaryFile') as mock_temp:
                mock_temp_file = Mock()
                mock_temp_file.name = "/tmp/test.pdf"
                mock_temp_file.__enter__.return_value = mock_temp_file
                mock_temp_file.__exit__.return_value = None
                mock_temp.return_value = mock_temp_file
                
                with patch('os.unlink'):
                    result = await processor.validate_document(
                        file_content=b"fake pdf content",
                        file_type="pdf",
                        filename="test.pdf"
                    )
                    
                    assert result['is_valid'] is True
                    assert result['detected_type'] == "pdf"
                    assert len(result['warnings']) > 0
                    assert "password protected" in result['warnings'][0]
    
    @pytest.mark.asyncio
    async def test_validate_document_empty_file(self):
        """Test document validation with empty file."""
        processor = DocumentProcessor()
        
        result = await processor.validate_document(
            file_content=b"",
            file_type="pdf",
            filename="empty.pdf"
        )
        
        assert result['is_valid'] is False
        assert "File is empty" in result['errors']
    
    @pytest.mark.asyncio
    async def test_validate_document_image_large(self):
        """Test image validation with very large image."""
        processor = DocumentProcessor()
        
        with patch('app.core.document_processor.Image') as mock_image_class:
            mock_image = Mock()
            mock_image.size = (10000, 10000)  # Very large image
            mock_image_class.open.return_value = mock_image
            
            result = await processor.validate_document(
                file_content=b"fake image content",
                file_type="image",
                filename="large.jpg"
            )
            
            assert result['is_valid'] is True
            assert result['detected_type'] == "image"
            assert len(result['warnings']) > 0
            assert "large image" in result['warnings'][0].lower()
    
    def test_calculate_ocr_confidence(self):
        """Test OCR confidence calculation."""
        processor = DocumentProcessor()
        
        # Test with valid confidence data
        ocr_data = {
            'conf': [95, 90, 85, 92, 88]
        }
        confidence = processor._calculate_ocr_confidence(ocr_data)
        assert confidence == 90.0  # Average of the values
        
        # Test with no confidence data
        ocr_data = {'conf': []}
        confidence = processor._calculate_ocr_confidence(ocr_data)
        assert confidence == 0.0
        
        # Test with invalid data
        confidence = processor._calculate_ocr_confidence({})
        assert confidence == 0.0
        
        # Test with negative confidence values (filtered out)
        ocr_data = {'conf': [95, -1, 90, 0, 85]}
        confidence = processor._calculate_ocr_confidence(ocr_data)
        assert confidence == 90.0  # Average of 95, 90, 85


class TestDocumentProcessorIntegration:
    """Integration tests for document processor."""
    
    def test_get_document_processor_singleton(self):
        """Test that get_document_processor returns singleton."""
        processor1 = get_document_processor()
        processor2 = get_document_processor()
        
        assert processor1 is processor2
    
    @pytest.mark.asyncio
    async def test_process_document_with_options(self):
        """Test document processing with various options."""
        processor = DocumentProcessor()
        
        # Test with custom options
        options = {
            "extract_text": True,
            "perform_ocr": False,
            "custom_setting": "test_value"
        }
        
        result = await processor.process_document(
            file_content=b"test content",
            file_type="txt",
            filename="test.txt",
            processing_options=options
        )
        
        assert result['processing_success'] is True
        assert result['processing_metadata']['processing_options'] == options
    
    @pytest.mark.asyncio
    async def test_error_handling_in_processing(self):
        """Test error handling during document processing."""
        processor = DocumentProcessor()
        
        # Mock a processing function to raise an exception
        with patch.object(processor, '_process_text', side_effect=Exception("Test error")):
            with pytest.raises(DocumentProcessingError, match="Document processing failed"):
                await processor.process_document(
                    file_content=b"test content",
                    file_type="txt",
                    filename="test.txt"
                )
