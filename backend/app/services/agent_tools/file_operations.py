"""
File Operation Tools for AI Agents.

This module provides specialized tools for agents to interact with the file system
and storage service for document management and processing operations.
"""

import os
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, BinaryIO
from datetime import datetime
import mimetypes
import hashlib

import structlog
from pydantic import BaseModel, Field

from .base import BaseTool, ToolInput, ToolResult, ToolCategory
# from ...services.file_service import FileService  # Commented out due to dependencies
from ...core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class FileReadInput(ToolInput):
    """Input for file reading operations."""
    file_path: str = Field(..., description="Path to the file to read")
    file_id: Optional[str] = Field(None, description="File ID from database")
    read_mode: str = Field(default="text", description="Read mode: text, binary, or metadata")
    encoding: str = Field(default="utf-8", description="Text encoding for text mode")


class FileWriteInput(ToolInput):
    """Input for file writing operations."""
    file_path: str = Field(..., description="Path where to write the file")
    content: Union[str, bytes] = Field(..., description="Content to write")
    write_mode: str = Field(default="text", description="Write mode: text or binary")
    encoding: str = Field(default="utf-8", description="Text encoding for text mode")
    create_dirs: bool = Field(default=True, description="Create directories if they don't exist")


class FileProcessingInput(ToolInput):
    """Input for file processing operations."""
    file_path: str = Field(..., description="Path to the file to process")
    operation: str = Field(..., description="Processing operation: extract_text, convert, analyze")
    options: Dict[str, Any] = Field(default_factory=dict, description="Processing options")


class FileManagementInput(ToolInput):
    """Input for file management operations."""
    operation: str = Field(..., description="Management operation: copy, move, delete, list")
    source_path: Optional[str] = Field(None, description="Source file/directory path")
    target_path: Optional[str] = Field(None, description="Target file/directory path")
    options: Dict[str, Any] = Field(default_factory=dict, description="Operation options")


class FileReadTool(BaseTool):
    """Tool for reading files from storage."""

    @property
    def name(self) -> str:
        return "file_reader"

    @property
    def description(self) -> str:
        return "Read files from storage with support for text, binary, and metadata operations"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.DOCUMENT_PROCESSING

    async def execute(self, input_data: FileReadInput) -> ToolResult:
        """Execute file reading operation."""
        try:
            if input_data.read_mode == "metadata":
                result = await self._read_file_metadata(input_data.file_path)
            elif input_data.read_mode == "binary":
                result = await self._read_file_binary(input_data)
            else:
                result = await self._read_file_text(input_data)

            return ToolResult(
                success=True,
                data=result,
                metadata={
                    "file_path": input_data.file_path,
                    "read_mode": input_data.read_mode,
                    "timestamp": datetime.utcnow().isoformat(),
                    "user_id": input_data.user_id
                },
                execution_time=0.0,
                tool_name=self.name
            )

        except Exception as e:
            return ToolResult(
                success=False,
                errors=[f"File reading failed: {str(e)}"],
                execution_time=0.0,
                tool_name=self.name
            )

    async def _read_file_text(self, input_data: FileReadInput) -> Dict[str, Any]:
        """Read file as text."""
        try:
            # Try to read from file service first
            with open(input_data.file_path, 'r', encoding=input_data.encoding) as f:
                content = f.read()
        except Exception:
            # Fallback to direct file reading
            with open(input_data.file_path, 'r', encoding=input_data.encoding) as f:
                content = f.read()

        return {
            "content": content,
            "content_type": "text",
            "encoding": input_data.encoding,
            "size": len(content),
            "lines": len(content.splitlines()) if content else 0
        }

    async def _read_file_binary(self, input_data: FileReadInput) -> Dict[str, Any]:
        """Read file as binary."""
        try:
            # Direct file reading for binary content
            with open(input_data.file_path, 'rb') as f:
                content = f.read()
        except Exception:
            # Fallback to direct file reading
            with open(input_data.file_path, 'rb') as f:
                content = f.read()

        # Convert to base64 for JSON serialization
        import base64
        content_b64 = base64.b64encode(content).decode('ascii')

        return {
            "content": content_b64,
            "content_type": "binary",
            "encoding": "base64",
            "size": len(content)
        }

    async def _read_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """Read file metadata."""
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        stat = path.stat()

        return {
            "file_path": str(path.absolute()),
            "filename": path.name,
            "file_extension": path.suffix,
            "file_size": stat.st_size,
            "mime_type": mimetypes.guess_type(str(path))[0],
            "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "is_file": path.is_file(),
            "is_directory": path.is_dir(),
            "permissions": oct(stat.st_mode)[-3:]
        }


class FileWriteTool(BaseTool):
    """Tool for writing files to storage."""

    @property
    def name(self) -> str:
        return "file_writer"

    @property
    def description(self) -> str:
        return "Write files to storage with support for text and binary content"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.DOCUMENT_PROCESSING

    async def execute(self, input_data: FileWriteInput) -> ToolResult:
        """Execute file writing operation."""
        try:
            if input_data.write_mode == "binary":
                result = await self._write_file_binary(input_data)
            else:
                result = await self._write_file_text(input_data)

            return ToolResult(
                success=True,
                data=result,
                metadata={
                    "file_path": input_data.file_path,
                    "write_mode": input_data.write_mode,
                    "timestamp": datetime.utcnow().isoformat(),
                    "user_id": input_data.user_id
                },
                execution_time=0.0,
                tool_name=self.name
            )

        except Exception as e:
            return ToolResult(
                success=False,
                errors=[f"File writing failed: {str(e)}"],
                execution_time=0.0,
                tool_name=self.name
            )

    async def _write_file_text(self, input_data: FileWriteInput) -> Dict[str, Any]:
        """Write text content to file."""
        # Create directories if needed
        if input_data.create_dirs:
            Path(input_data.file_path).parent.mkdir(parents=True, exist_ok=True)

        try:
            # Direct file writing for text content
            with open(input_data.file_path, 'w', encoding=input_data.encoding) as f:
                f.write(input_data.content)
        except Exception:
            # Fallback to direct file writing
            with open(input_data.file_path, 'w', encoding=input_data.encoding) as f:
                f.write(input_data.content)

        return {
            "file_path": input_data.file_path,
            "content_type": "text",
            "encoding": input_data.encoding,
            "size": len(input_data.content),
            "operation": "written"
        }

    async def _write_file_binary(self, input_data: FileWriteInput) -> Dict[str, Any]:
        """Write binary content to file."""
        # Create directories if needed
        if input_data.create_dirs:
            Path(input_data.file_path).parent.mkdir(parents=True, exist_ok=True)

        content = input_data.content
        if isinstance(content, str):
            # Assume base64 encoded
            import base64
            content = base64.b64decode(content)

        try:
            # Direct file writing for binary content
            with open(input_data.file_path, 'wb') as f:
                f.write(content)
        except Exception:
            # Fallback to direct file writing
            with open(input_data.file_path, 'wb') as f:
                f.write(content)

        return {
            "file_path": input_data.file_path,
            "content_type": "binary",
            "size": len(content),
            "operation": "written"
        }


class FileProcessingTool(BaseTool):
    """Tool for processing files (text extraction, conversion, analysis)."""

    @property
    def name(self) -> str:
        return "file_processor"

    @property
    def description(self) -> str:
        return "Process files for text extraction, format conversion, and content analysis"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.DOCUMENT_PROCESSING

    async def execute(self, input_data: FileProcessingInput) -> ToolResult:
        """Execute file processing operation."""
        try:
            if input_data.operation == "extract_text":
                result = await self._extract_text(input_data)
            elif input_data.operation == "convert":
                result = await self._convert_file(input_data)
            elif input_data.operation == "analyze":
                result = await self._analyze_file(input_data)
            else:
                raise ValueError(f"Unknown processing operation: {input_data.operation}")

            return ToolResult(
                success=True,
                data=result,
                metadata={
                    "file_path": input_data.file_path,
                    "operation": input_data.operation,
                    "timestamp": datetime.utcnow().isoformat(),
                    "user_id": input_data.user_id
                },
                execution_time=0.0,
                tool_name=self.name
            )

        except Exception as e:
            return ToolResult(
                success=False,
                errors=[f"File processing failed: {str(e)}"],
                execution_time=0.0,
                tool_name=self.name
            )

    async def _extract_text(self, input_data: FileProcessingInput) -> Dict[str, Any]:
        """Extract text from various file formats."""
        file_path = Path(input_data.file_path)
        file_extension = file_path.suffix.lower()

        if file_extension == '.txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        elif file_extension == '.pdf':
            text = await self._extract_text_from_pdf(file_path)
        elif file_extension in ['.docx', '.doc']:
            text = await self._extract_text_from_docx(file_path)
        else:
            # Try to read as text
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
            except UnicodeDecodeError:
                text = f"Binary file - text extraction not supported for {file_extension}"

        return {
            "extracted_text": text,
            "file_type": file_extension,
            "text_length": len(text),
            "word_count": len(text.split()) if text else 0,
            "line_count": len(text.splitlines()) if text else 0
        }

    async def _extract_text_from_pdf(self, file_path: Path) -> str:
        """Extract text from PDF file."""
        try:
            import PyPDF2
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            return text
        except ImportError:
            return "PDF text extraction requires PyPDF2 library"
        except Exception as e:
            return f"PDF text extraction failed: {str(e)}"

    async def _extract_text_from_docx(self, file_path: Path) -> str:
        """Extract text from DOCX file."""
        try:
            import docx
            doc = docx.Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except ImportError:
            return "DOCX text extraction requires python-docx library"
        except Exception as e:
            return f"DOCX text extraction failed: {str(e)}"

    async def _convert_file(self, input_data: FileProcessingInput) -> Dict[str, Any]:
        """Convert file to different format."""
        target_format = input_data.options.get("target_format", "txt")
        output_path = input_data.options.get("output_path")

        if not output_path:
            file_path = Path(input_data.file_path)
            output_path = file_path.with_suffix(f".{target_format}")

        # Simple conversion example (text to different formats)
        if target_format == "txt":
            # Extract text and save as .txt
            text_result = await self._extract_text(input_data)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(text_result["extracted_text"])
        else:
            raise ValueError(f"Conversion to {target_format} not supported")

        return {
            "original_file": input_data.file_path,
            "converted_file": str(output_path),
            "target_format": target_format,
            "operation": "converted"
        }

    async def _analyze_file(self, input_data: FileProcessingInput) -> Dict[str, Any]:
        """Analyze file content and structure."""
        file_path = Path(input_data.file_path)

        # Basic file analysis
        stat = file_path.stat()

        # Content analysis
        content_analysis = {}
        if file_path.suffix.lower() in ['.txt', '.md', '.py', '.js', '.html', '.css']:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                content_analysis = {
                    "character_count": len(content),
                    "word_count": len(content.split()),
                    "line_count": len(content.splitlines()),
                    "paragraph_count": len([p for p in content.split('\n\n') if p.strip()]),
                    "has_code": any(keyword in content for keyword in ['def ', 'function ', 'class ', 'import ', 'from ']),
                    "language_hints": self._detect_language_hints(content, file_path.suffix)
                }
            except Exception:
                content_analysis = {"error": "Could not analyze content"}

        return {
            "file_path": str(file_path),
            "file_size": stat.st_size,
            "file_type": file_path.suffix,
            "mime_type": mimetypes.guess_type(str(file_path))[0],
            "content_analysis": content_analysis,
            "checksum": await self._calculate_checksum(file_path),
            "analysis_timestamp": datetime.utcnow().isoformat()
        }

    def _detect_language_hints(self, content: str, extension: str) -> List[str]:
        """Detect programming language hints from content."""
        hints = []

        if extension == '.py':
            hints.append('python')
        elif extension == '.js':
            hints.append('javascript')
        elif extension == '.html':
            hints.append('html')

        # Content-based detection
        if 'import ' in content or 'from ' in content:
            hints.append('python')
        if 'function(' in content or 'const ' in content:
            hints.append('javascript')
        if '<html' in content or '<!DOCTYPE' in content:
            hints.append('html')

        return list(set(hints))

    async def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate MD5 checksum of file."""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()


class FileManagementTool(BaseTool):
    """Tool for file management operations (copy, move, delete, list)."""

    @property
    def name(self) -> str:
        return "file_manager"

    @property
    def description(self) -> str:
        return "Manage files and directories with copy, move, delete, and list operations"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.DOCUMENT_PROCESSING

    async def execute(self, input_data: FileManagementInput) -> ToolResult:
        """Execute file management operation."""
        try:
            if input_data.operation == "copy":
                result = await self._copy_file(input_data)
            elif input_data.operation == "move":
                result = await self._move_file(input_data)
            elif input_data.operation == "delete":
                result = await self._delete_file(input_data)
            elif input_data.operation == "list":
                result = await self._list_files(input_data)
            else:
                raise ValueError(f"Unknown management operation: {input_data.operation}")

            return ToolResult(
                success=True,
                data=result,
                metadata={
                    "operation": input_data.operation,
                    "timestamp": datetime.utcnow().isoformat(),
                    "user_id": input_data.user_id
                },
                execution_time=0.0,
                tool_name=self.name
            )

        except Exception as e:
            return ToolResult(
                success=False,
                errors=[f"File management operation failed: {str(e)}"],
                execution_time=0.0,
                tool_name=self.name
            )

    async def _copy_file(self, input_data: FileManagementInput) -> Dict[str, Any]:
        """Copy file or directory."""
        source = Path(input_data.source_path)
        target = Path(input_data.target_path)

        if not source.exists():
            raise FileNotFoundError(f"Source not found: {source}")

        # Create target directory if needed
        target.parent.mkdir(parents=True, exist_ok=True)

        if source.is_file():
            shutil.copy2(source, target)
        else:
            shutil.copytree(source, target, dirs_exist_ok=True)

        return {
            "operation": "copy",
            "source": str(source),
            "target": str(target),
            "type": "file" if source.is_file() else "directory"
        }

    async def _move_file(self, input_data: FileManagementInput) -> Dict[str, Any]:
        """Move file or directory."""
        source = Path(input_data.source_path)
        target = Path(input_data.target_path)

        if not source.exists():
            raise FileNotFoundError(f"Source not found: {source}")

        # Create target directory if needed
        target.parent.mkdir(parents=True, exist_ok=True)

        shutil.move(str(source), str(target))

        return {
            "operation": "move",
            "source": str(source),
            "target": str(target),
            "type": "file" if target.is_file() else "directory"
        }

    async def _delete_file(self, input_data: FileManagementInput) -> Dict[str, Any]:
        """Delete file or directory."""
        target = Path(input_data.source_path)

        if not target.exists():
            raise FileNotFoundError(f"Target not found: {target}")

        if target.is_file():
            target.unlink()
            file_type = "file"
        else:
            shutil.rmtree(target)
            file_type = "directory"

        return {
            "operation": "delete",
            "target": str(target),
            "type": file_type
        }

    async def _list_files(self, input_data: FileManagementInput) -> Dict[str, Any]:
        """List files in directory."""
        directory = Path(input_data.source_path or ".")

        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

        if not directory.is_dir():
            raise ValueError(f"Path is not a directory: {directory}")

        files = []
        for item in directory.iterdir():
            stat = item.stat()
            files.append({
                "name": item.name,
                "path": str(item),
                "type": "file" if item.is_file() else "directory",
                "size": stat.st_size if item.is_file() else None,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "extension": item.suffix if item.is_file() else None
            })

        # Sort by name
        files.sort(key=lambda x: x["name"])

        return {
            "operation": "list",
            "directory": str(directory),
            "files": files,
            "count": len(files)
        }
