"""
Agent Tools Package.

This package provides all specialized tools for AI agents in the real estate
contract management system. Tools are organized by category and can be
dynamically registered and discovered.
"""

from .base import (
    BaseTool,
    ToolCategory,
    ToolResult,
    ToolInput,
    ToolRegistry,
    get_tool_registry
)

# Data Extraction Tools
from .data_extraction import (
    DocumentParsingTool,
    EntityRecognitionTool,
    ConfidenceScoringTool
)

# Contract Generation Tools
from .contract_generation import (
    TemplateFillTool,
    ClauseGenerationTool,
    DocumentGenerationTool
)

# Compliance Checking Tools
from .compliance_checking import (
    ComplianceValidationTool,
    RuleEngineValidationTool,
    ComplianceReportTool
)

# Signature Tracking Tools
from .signature_tracking import (
    SignatureTrackingTool,
    WebhookReconciliationTool,
    NotificationTool,
    AuditTrailTool
)

# Summarization Tools
from .summarization import (
    DocumentSummarizationTool,
    DiffGenerationTool
)

# Help and Assistance Tools
from .help_assistance import (
    ContextualQATool,
    WorkflowGuidanceTool,
    ClauseExplanationTool
)

# Database Access Tools
from .database_access import (
    ContractDatabaseTool,
    TemplateDatabaseTool,
    FileDatabaseTool,
    UserDatabaseTool
)

# File Operation Tools
from .file_operations import (
    FileReadTool,
    FileWriteTool,
    FileProcessingTool,
    FileManagementTool
)

# Template Processing Tools
from .template_processing import (
    TemplateAnalysisTool,
    TemplateRenderingTool
)

# Performance Optimization Tools
from .performance_optimization import (
    CacheTool,
    PerformanceMonitorTool
)

# Tool registry instance
tool_registry = get_tool_registry()


def register_all_tools():
    """Register all available tools in the tool registry."""

    # Data Extraction Tools
    tool_registry.register_tool(DocumentParsingTool())
    tool_registry.register_tool(EntityRecognitionTool())
    tool_registry.register_tool(ConfidenceScoringTool())

    # Contract Generation Tools
    tool_registry.register_tool(TemplateFillTool())
    tool_registry.register_tool(ClauseGenerationTool())
    tool_registry.register_tool(DocumentGenerationTool())

    # Compliance Checking Tools
    tool_registry.register_tool(ComplianceValidationTool())
    tool_registry.register_tool(RuleEngineValidationTool())
    tool_registry.register_tool(ComplianceReportTool())

    # Signature Tracking Tools
    tool_registry.register_tool(SignatureTrackingTool())
    tool_registry.register_tool(WebhookReconciliationTool())
    tool_registry.register_tool(NotificationTool())
    tool_registry.register_tool(AuditTrailTool())

    # Summarization Tools
    tool_registry.register_tool(DocumentSummarizationTool())
    tool_registry.register_tool(DiffGenerationTool())

    # Help and Assistance Tools
    tool_registry.register_tool(ContextualQATool())
    tool_registry.register_tool(WorkflowGuidanceTool())
    tool_registry.register_tool(ClauseExplanationTool())

    # Database Access Tools
    tool_registry.register_tool(ContractDatabaseTool())
    tool_registry.register_tool(TemplateDatabaseTool())
    tool_registry.register_tool(FileDatabaseTool())
    tool_registry.register_tool(UserDatabaseTool())

    # File Operation Tools
    tool_registry.register_tool(FileReadTool())
    tool_registry.register_tool(FileWriteTool())
    tool_registry.register_tool(FileProcessingTool())
    tool_registry.register_tool(FileManagementTool())

    # Template Processing Tools
    tool_registry.register_tool(TemplateAnalysisTool())
    tool_registry.register_tool(TemplateRenderingTool())

    # Performance Optimization Tools
    tool_registry.register_tool(CacheTool())
    tool_registry.register_tool(PerformanceMonitorTool())


def get_tools_for_agent(agent_role: str) -> list:
    """Get tools appropriate for a specific agent role."""

    tool_mappings = {
        "data_extraction": [
            "document_parser",
            "entity_recognizer",
            "confidence_scorer"
        ],
        "contract_generator": [
            "template_filler",
            "clause_generator",
            "document_generator"
        ],
        "compliance_checker": [
            "compliance_validator",
            "rule_engine_validator",
            "compliance_reporter"
        ],
        "signature_tracker": [
            "signature_tracker",
            "webhook_reconciler",
            "notification_sender",
            "audit_trail_generator"
        ],
        "summary_agent": [
            "document_summarizer",
            "diff_generator"
        ],
        "help_agent": [
            "contextual_qa",
            "workflow_guide",
            "clause_explainer"
        ],
        "database_manager": [
            "contract_db_access",
            "template_db_access",
            "file_db_access",
            "user_db_access"
        ],
        "file_manager": [
            "file_reader",
            "file_writer",
            "file_processor",
            "file_manager"
        ],
        "template_processor": [
            "template_analyzer",
            "template_renderer"
        ],
        "performance_optimizer": [
            "cache_manager",
            "performance_monitor"
        ]
    }

    tool_names = tool_mappings.get(agent_role, [])
    tools = []

    for tool_name in tool_names:
        tool = tool_registry.get_tool(tool_name)
        if tool:
            tools.append(tool)

    return tools


def get_tools_by_category(category: ToolCategory) -> list:
    """Get all tools in a specific category."""
    return tool_registry.get_tools_by_category(category)


def list_all_tools() -> list:
    """List all registered tools."""
    return tool_registry.list_tools()


# Auto-register tools when module is imported
register_all_tools()

__all__ = [
    # Base classes
    'BaseTool',
    'ToolCategory',
    'ToolResult',
    'ToolInput',
    'ToolRegistry',
    'get_tool_registry',

    # Data Extraction Tools
    'DocumentParsingTool',
    'EntityRecognitionTool',
    'ConfidenceScoringTool',

    # Contract Generation Tools
    'TemplateFillTool',
    'ClauseGenerationTool',
    'DocumentGenerationTool',

    # Compliance Checking Tools
    'ComplianceValidationTool',
    'RuleEngineValidationTool',
    'ComplianceReportTool',

    # Signature Tracking Tools
    'SignatureTrackingTool',
    'WebhookReconciliationTool',
    'NotificationTool',
    'AuditTrailTool',

    # Summarization Tools
    'DocumentSummarizationTool',
    'DiffGenerationTool',

    # Help and Assistance Tools
    'ContextualQATool',
    'WorkflowGuidanceTool',
    'ClauseExplanationTool',

    # Database Access Tools
    'ContractDatabaseTool',
    'TemplateDatabaseTool',
    'FileDatabaseTool',
    'UserDatabaseTool',

    # File Operation Tools
    'FileReadTool',
    'FileWriteTool',
    'FileProcessingTool',
    'FileManagementTool',

    # Template Processing Tools
    'TemplateAnalysisTool',
    'TemplateRenderingTool',

    # Performance Optimization Tools
    'CacheTool',
    'PerformanceMonitorTool',

    # Utility functions
    'register_all_tools',
    'get_tools_for_agent',
    'get_tools_by_category',
    'list_all_tools',
    'tool_registry'
]
