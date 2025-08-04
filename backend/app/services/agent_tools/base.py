"""
Base classes for AI Agent Tools.

This module provides the foundation for all agent tools, including
common functionality, error handling, and integration patterns.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

import structlog
from pydantic import BaseModel, Field

from ...core.config import get_settings
from ...services.agent_memory import AgentMemoryManager, MemoryType, MemoryScope

logger = structlog.get_logger(__name__)
settings = get_settings()


class ToolCategory(Enum):
    """Categories of agent tools."""
    DOCUMENT_PROCESSING = "document_processing"
    DATA_EXTRACTION = "data_extraction"
    CONTRACT_GENERATION = "contract_generation"
    COMPLIANCE_CHECKING = "compliance_checking"
    SIGNATURE_TRACKING = "signature_tracking"
    SUMMARIZATION = "summarization"
    KNOWLEDGE_BASE = "knowledge_base"
    WORKFLOW_MANAGEMENT = "workflow_management"


class ToolResult(BaseModel):
    """Standard result format for all agent tools."""
    success: bool = Field(..., description="Whether the tool execution was successful")
    data: Dict[str, Any] = Field(default_factory=dict, description="Tool output data")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    errors: List[str] = Field(default_factory=list, description="Error messages if any")
    execution_time: float = Field(..., description="Execution time in seconds")
    tool_name: str = Field(..., description="Name of the tool that was executed")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Execution timestamp")


class ToolInput(BaseModel):
    """Base input model for agent tools."""
    agent_id: Optional[str] = Field(None, description="ID of the agent using the tool")
    workflow_id: Optional[str] = Field(None, description="ID of the current workflow")
    user_id: Optional[str] = Field(None, description="ID of the user initiating the action")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context data")


class BaseTool(ABC):
    """
    Abstract base class for all agent tools.
    
    Provides common functionality including error handling, logging,
    memory integration, and standardized result formatting.
    """
    
    def __init__(self, memory_manager: Optional[AgentMemoryManager] = None):
        self.memory_manager = memory_manager or AgentMemoryManager()
        self.settings = get_settings()
        self.logger = structlog.get_logger(self.__class__.__name__)
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name for identification."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description for agent understanding."""
        pass
    
    @property
    @abstractmethod
    def category(self) -> ToolCategory:
        """Tool category for organization."""
        pass
    
    @abstractmethod
    async def execute(self, input_data: ToolInput) -> ToolResult:
        """
        Execute the tool with the given input.
        
        Args:
            input_data: Tool input data
            
        Returns:
            Tool execution result
        """
        pass
    
    async def _store_execution_memory(self, 
                                    input_data: ToolInput, 
                                    result: ToolResult) -> None:
        """Store tool execution in memory for context sharing."""
        try:
            memory_content = {
                "tool_name": self.name,
                "tool_category": self.category.value,
                "input_summary": self._summarize_input(input_data),
                "result_summary": self._summarize_result(result),
                "success": result.success,
                "execution_time": result.execution_time,
                "timestamp": result.timestamp.isoformat()
            }
            
            await self.memory_manager.store_memory(
                content=memory_content,
                memory_type=MemoryType.WORKFLOW,
                scope=MemoryScope.WORKFLOW,
                identifier=f"tool_execution_{self.name}_{datetime.utcnow().timestamp()}",
                agent_id=input_data.agent_id,
                workflow_id=input_data.workflow_id,
                user_id=input_data.user_id,
                tags={self.category.value, "tool_execution", self.name}
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to store tool execution memory: {e}")
    
    def _summarize_input(self, input_data: ToolInput) -> Dict[str, Any]:
        """Create a summary of input data for memory storage."""
        return {
            "agent_id": input_data.agent_id,
            "workflow_id": input_data.workflow_id,
            "user_id": input_data.user_id,
            "context_keys": list(input_data.context.keys()) if input_data.context else []
        }
    
    def _summarize_result(self, result: ToolResult) -> Dict[str, Any]:
        """Create a summary of result data for memory storage."""
        return {
            "success": result.success,
            "data_keys": list(result.data.keys()) if result.data else [],
            "metadata_keys": list(result.metadata.keys()) if result.metadata else [],
            "error_count": len(result.errors),
            "execution_time": result.execution_time
        }
    
    async def safe_execute(self, input_data: ToolInput) -> ToolResult:
        """
        Execute the tool with comprehensive error handling and logging.
        
        Args:
            input_data: Tool input data
            
        Returns:
            Tool execution result with error handling
        """
        start_time = datetime.utcnow()
        
        try:
            self.logger.info(
                "Tool execution started",
                tool_name=self.name,
                agent_id=input_data.agent_id,
                workflow_id=input_data.workflow_id
            )
            
            # Execute the tool
            result = await self.execute(input_data)
            
            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            result.execution_time = execution_time
            result.tool_name = self.name
            
            # Store execution in memory
            await self._store_execution_memory(input_data, result)
            
            self.logger.info(
                "Tool execution completed",
                tool_name=self.name,
                success=result.success,
                execution_time=execution_time,
                agent_id=input_data.agent_id,
                workflow_id=input_data.workflow_id
            )
            
            return result
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            error_result = ToolResult(
                success=False,
                data={},
                metadata={"error_type": type(e).__name__},
                errors=[str(e)],
                execution_time=execution_time,
                tool_name=self.name,
                timestamp=datetime.utcnow()
            )
            
            # Store failed execution in memory
            await self._store_execution_memory(input_data, error_result)
            
            self.logger.error(
                "Tool execution failed",
                tool_name=self.name,
                error=str(e),
                execution_time=execution_time,
                agent_id=input_data.agent_id,
                workflow_id=input_data.workflow_id
            )
            
            return error_result
    
    def get_tool_info(self) -> Dict[str, Any]:
        """Get tool information for agent registration."""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "class": self.__class__.__name__
        }


class DocumentTool(BaseTool):
    """Base class for document processing tools."""
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.DOCUMENT_PROCESSING
    
    async def _validate_document_access(self, document_id: str, user_id: Optional[str]) -> bool:
        """Validate that the user has access to the document."""
        try:
            # This would integrate with the existing file service
            # For now, we'll assume access is granted
            return True
        except Exception as e:
            self.logger.error(f"Document access validation failed: {e}")
            return False
    
    async def _get_document_metadata(self, document_id: str) -> Dict[str, Any]:
        """Get document metadata from the file service."""
        try:
            # This would integrate with the existing file service
            # For now, return basic metadata
            return {
                "document_id": document_id,
                "type": "unknown",
                "size": 0,
                "created_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Failed to get document metadata: {e}")
            return {}


class DataExtractionTool(BaseTool):
    """Base class for data extraction tools."""
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.DATA_EXTRACTION
    
    def _calculate_confidence_score(self, 
                                  extracted_data: Dict[str, Any], 
                                  validation_results: Dict[str, Any]) -> float:
        """Calculate confidence score for extracted data."""
        try:
            # Basic confidence calculation based on validation results
            total_fields = len(extracted_data)
            if total_fields == 0:
                return 0.0
            
            valid_fields = sum(1 for field, result in validation_results.items() 
                             if result.get("valid", False))
            
            base_confidence = valid_fields / total_fields
            
            # Adjust based on field importance and data quality
            # This is a simplified implementation
            return min(max(base_confidence, 0.0), 1.0)
            
        except Exception as e:
            self.logger.error(f"Confidence score calculation failed: {e}")
            return 0.0


class ContractTool(BaseTool):
    """Base class for contract-related tools."""
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.CONTRACT_GENERATION
    
    async def _validate_template_access(self, template_id: str, user_id: Optional[str]) -> bool:
        """Validate that the user has access to the template."""
        try:
            # This would integrate with the existing template service
            return True
        except Exception as e:
            self.logger.error(f"Template access validation failed: {e}")
            return False


class ComplianceTool(BaseTool):
    """Base class for compliance checking tools."""
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.COMPLIANCE_CHECKING
    
    def _get_jurisdiction_rules(self, jurisdiction: str) -> Dict[str, Any]:
        """Get compliance rules for a specific jurisdiction."""
        try:
            # This would load jurisdiction-specific rules
            # For now, return basic rules
            return {
                "jurisdiction": jurisdiction,
                "rules": [],
                "severity_levels": ["blocker", "warning", "info"]
            }
        except Exception as e:
            self.logger.error(f"Failed to get jurisdiction rules: {e}")
            return {}


class ToolRegistry:
    """Registry for managing agent tools."""
    
    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
        self.tools_by_category: Dict[ToolCategory, List[BaseTool]] = {}
    
    def register_tool(self, tool: BaseTool) -> None:
        """Register a tool in the registry."""
        self.tools[tool.name] = tool
        
        if tool.category not in self.tools_by_category:
            self.tools_by_category[tool.category] = []
        self.tools_by_category[tool.category].append(tool)
        
        logger.info(f"Tool registered: {tool.name} ({tool.category.value})")
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self.tools.get(name)
    
    def get_tools_by_category(self, category: ToolCategory) -> List[BaseTool]:
        """Get all tools in a category."""
        return self.tools_by_category.get(category, [])
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """List all registered tools."""
        return [tool.get_tool_info() for tool in self.tools.values()]


# Global tool registry
tool_registry = ToolRegistry()


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry."""
    return tool_registry
