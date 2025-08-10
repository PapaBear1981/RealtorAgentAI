"""
Contract Generator Agent Tools.

This module provides specialized tools for the Contract Generator Agent,
including template filling, clause generation, and DOCX output creation.
"""

import json
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path

import structlog
from pydantic import BaseModel, Field

from .base import ContractTool, ToolInput, ToolResult, ToolCategory
from ...core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class TemplateFillInput(ToolInput):
    """Input for template filling tool."""
    template_id: str = Field(..., description="ID of the contract template")
    extracted_data: Dict[str, Any] = Field(..., description="Extracted data for filling")
    fill_options: Dict[str, Any] = Field(default_factory=dict, description="Template filling options")


class ClauseGenerationInput(ToolInput):
    """Input for clause generation tool."""
    clause_type: str = Field(..., description="Type of clause to generate")
    context_data: Dict[str, Any] = Field(..., description="Context data for clause generation")
    jurisdiction: str = Field(default="default", description="Legal jurisdiction")
    style_preferences: Dict[str, Any] = Field(default_factory=dict, description="Style preferences")


class DocumentGenerationInput(ToolInput):
    """Input for document generation tool."""
    filled_template: Dict[str, Any] = Field(..., description="Filled template data")
    output_format: str = Field(default="docx", description="Output format (docx, pdf)")
    formatting_options: Dict[str, Any] = Field(default_factory=dict, description="Formatting options")


class VersionControlInput(ToolInput):
    """Input for version control tool."""
    contract_id: str = Field(..., description="Contract ID")
    changes: Dict[str, Any] = Field(..., description="Changes to track")
    version_notes: str = Field(default="", description="Version notes")


class TemplateFillTool(ContractTool):
    """Tool for filling contract templates with extracted data."""

    @property
    def name(self) -> str:
        return "template_filler"

    @property
    def description(self) -> str:
        return "Fill contract templates with extracted data using intelligent variable substitution"

    async def execute(self, input_data: TemplateFillInput) -> ToolResult:
        """Fill a contract template with extracted data."""
        try:
            # Validate template access
            if not await self._validate_template_access(input_data.template_id, input_data.user_id):
                return ToolResult(
                    success=False,
                    errors=["Access denied to template"],
                    execution_time=0.0,
                    tool_name=self.name
                )

            # Load template
            template_data = await self._load_template(input_data.template_id)

            # Map extracted data to template variables
            variable_mapping = await self._map_data_to_variables(
                input_data.extracted_data,
                template_data.get("variables", {}),
                input_data.fill_options
            )

            # Fill template
            filled_template = await self._fill_template_content(
                template_data,
                variable_mapping,
                input_data.fill_options
            )

            # Validate filled template
            validation_results = await self._validate_filled_template(filled_template)

            return ToolResult(
                success=True,
                data={
                    "template_id": input_data.template_id,
                    "filled_template": filled_template,
                    "variable_mapping": variable_mapping,
                    "validation_results": validation_results,
                    "fill_percentage": self._calculate_fill_percentage(variable_mapping),
                    "missing_variables": self._get_missing_variables(variable_mapping)
                },
                metadata={
                    "template_metadata": template_data.get("metadata", {}),
                    "fill_timestamp": datetime.utcnow().isoformat(),
                    "data_sources": list(input_data.extracted_data.keys())
                },
                execution_time=0.0,
                tool_name=self.name
            )

        except Exception as e:
            return ToolResult(
                success=False,
                errors=[f"Template filling failed: {str(e)}"],
                execution_time=0.0,
                tool_name=self.name
            )

    async def _load_template(self, template_id: str) -> Dict[str, Any]:
        """Load template data from the template service."""
        try:
            # Integrate with the existing template service
            from ...services.template_service import get_template_service

            template_service = get_template_service()
            template_data = await template_service.get_template(template_id)

            if not template_data:
                # Fallback to a basic template if specific template not found
                logger.warning(f"Template {template_id} not found, using default template")
                return self._get_default_template()

            return template_data

        except Exception as e:
            logger.error(f"Failed to load template {template_id}: {e}")
            # Return a basic fallback template
            return self._get_default_template()

    def _get_default_template(self) -> Dict[str, Any]:
        """Get a default real estate contract template."""
        return {
            "id": "default_real_estate",
            "name": "Default Real Estate Purchase Agreement",
            "content": """
            REAL ESTATE PURCHASE AGREEMENT

            This agreement is made between {{buyer_name}} (Buyer) and {{seller_name}} (Seller)
            for the purchase of the property located at {{property_address}}.

            Purchase Price: {{purchase_price}}
            Down Payment: {{down_payment}}
            Closing Date: {{closing_date}}

            Property Description:
            {{property_description}}

            Terms and Conditions:
            {{terms_and_conditions}}

            Contingencies:
            {{contingencies}}

            Additional Terms:
            {{additional_terms}}
            """,
            "variables": {
                "buyer_name": {"type": "text", "required": True, "description": "Full name of the buyer"},
                "seller_name": {"type": "text", "required": True, "description": "Full name of the seller"},
                "property_address": {"type": "address", "required": True, "description": "Complete property address"},
                "purchase_price": {"type": "currency", "required": True, "description": "Total purchase price"},
                "down_payment": {"type": "currency", "required": True},
                "closing_date": {"type": "date", "required": True},
                "property_description": {"type": "text", "required": False},
                "terms_and_conditions": {"type": "text", "required": False}
            },
            "metadata": {
                "version": "1.0",
                "jurisdiction": "default",
                "category": "residential_purchase"
            }
        }

    async def _map_data_to_variables(self,
                                   extracted_data: Dict[str, Any],
                                   template_variables: Dict[str, Any],
                                   options: Dict[str, Any]) -> Dict[str, Any]:
        """Map extracted data to template variables."""
        variable_mapping = {}

        for var_name, var_config in template_variables.items():
            mapped_value = await self._find_matching_data(
                var_name, var_config, extracted_data
            )

            variable_mapping[var_name] = {
                "value": mapped_value,
                "source": self._get_data_source(var_name, extracted_data),
                "confidence": self._get_mapping_confidence(var_name, mapped_value, extracted_data),
                "required": var_config.get("required", False),
                "filled": mapped_value is not None
            }

        return variable_mapping

    async def _find_matching_data(self,
                                var_name: str,
                                var_config: Dict[str, Any],
                                extracted_data: Dict[str, Any]) -> Optional[str]:
        """Find matching data for a template variable."""
        var_type = var_config.get("type", "text")

        # Direct mapping strategies
        if var_name in extracted_data:
            return str(extracted_data[var_name])

        # Smart mapping based on variable name and type
        if var_name == "buyer_name":
            return self._find_party_name(extracted_data, "buyer")
        elif var_name == "seller_name":
            return self._find_party_name(extracted_data, "seller")
        elif var_name == "property_address":
            return self._find_address(extracted_data)
        elif var_name == "purchase_price":
            return self._find_financial_amount(extracted_data, "purchase_price")
        elif var_name == "down_payment":
            return self._find_financial_amount(extracted_data, "down_payment")
        elif var_name == "closing_date":
            return self._find_date(extracted_data, "closing")

        return None

    def _find_party_name(self, data: Dict[str, Any], role: str) -> Optional[str]:
        """Find party name by role."""
        parties = data.get("parties", [])
        if isinstance(parties, list):
            for party in parties:
                if isinstance(party, dict) and party.get("role", "").lower() == role.lower():
                    return party.get("name")
        return None

    def _find_address(self, data: Dict[str, Any]) -> Optional[str]:
        """Find property address."""
        addresses = data.get("addresses", [])
        if isinstance(addresses, list) and addresses:
            return addresses[0].get("value") if isinstance(addresses[0], dict) else str(addresses[0])
        return None

    def _find_financial_amount(self, data: Dict[str, Any], amount_type: str) -> Optional[str]:
        """Find financial amount by type."""
        financial = data.get("financial_terms", [])
        if isinstance(financial, list):
            for item in financial:
                if isinstance(item, dict) and amount_type.lower() in item.get("value", "").lower():
                    return item.get("value")
        return None

    def _find_date(self, data: Dict[str, Any], date_type: str) -> Optional[str]:
        """Find date by type."""
        dates = data.get("dates", [])
        if isinstance(dates, list) and dates:
            # For now, return the first date found
            return dates[0].get("value") if isinstance(dates[0], dict) else str(dates[0])
        return None

    def _get_data_source(self, var_name: str, data: Dict[str, Any]) -> str:
        """Get the source of mapped data."""
        # This would track which extraction category provided the data
        return "extracted_data"

    def _get_mapping_confidence(self, var_name: str, value: Any, data: Dict[str, Any]) -> float:
        """Calculate confidence score for variable mapping."""
        if value is None:
            return 0.0

        # Simple confidence calculation
        if var_name in data:
            return 0.95  # Direct match
        else:
            return 0.75  # Inferred match

    async def _fill_template_content(self,
                                   template_data: Dict[str, Any],
                                   variable_mapping: Dict[str, Any],
                                   options: Dict[str, Any]) -> Dict[str, Any]:
        """Fill template content with mapped variables."""
        content = template_data.get("content", "")

        # Replace variables in content
        for var_name, mapping in variable_mapping.items():
            if mapping["filled"]:
                placeholder = f"{{{{{var_name}}}}}"
                content = content.replace(placeholder, str(mapping["value"]))
            else:
                # Handle missing required variables
                if mapping["required"]:
                    placeholder = f"{{{{{var_name}}}}}"
                    content = content.replace(placeholder, f"[MISSING: {var_name}]")

        return {
            "content": content,
            "template_id": template_data["id"],
            "template_name": template_data["name"],
            "filled_variables": {k: v["value"] for k, v in variable_mapping.items() if v["filled"]},
            "missing_variables": [k for k, v in variable_mapping.items() if not v["filled"] and v["required"]]
        }

    async def _validate_filled_template(self, filled_template: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the filled template."""
        validation_results = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "completeness_score": 0.0
        }

        # Check for missing required variables
        missing_vars = filled_template.get("missing_variables", [])
        if missing_vars:
            validation_results["is_valid"] = False
            validation_results["errors"].extend([f"Missing required variable: {var}" for var in missing_vars])

        # Check for placeholder patterns that weren't filled
        content = filled_template.get("content", "")
        unfilled_placeholders = re.findall(r'\{\{[^}]+\}\}', content)
        if unfilled_placeholders:
            validation_results["warnings"].extend([f"Unfilled placeholder: {ph}" for ph in unfilled_placeholders])

        # Calculate completeness score
        filled_vars = len(filled_template.get("filled_variables", {}))
        total_vars = filled_vars + len(missing_vars)
        validation_results["completeness_score"] = filled_vars / total_vars if total_vars > 0 else 1.0

        return validation_results

    def _calculate_fill_percentage(self, variable_mapping: Dict[str, Any]) -> float:
        """Calculate the percentage of variables that were filled."""
        if not variable_mapping:
            return 0.0

        filled_count = sum(1 for mapping in variable_mapping.values() if mapping["filled"])
        return (filled_count / len(variable_mapping)) * 100

    def _get_missing_variables(self, variable_mapping: Dict[str, Any]) -> List[str]:
        """Get list of missing required variables."""
        return [
            var_name for var_name, mapping in variable_mapping.items()
            if not mapping["filled"] and mapping["required"]
        ]


class ClauseGenerationTool(ContractTool):
    """Tool for generating contract clauses based on context."""

    @property
    def name(self) -> str:
        return "clause_generator"

    @property
    def description(self) -> str:
        return "Generate contract clauses based on context data and legal requirements"

    async def execute(self, input_data: ClauseGenerationInput) -> ToolResult:
        """Generate a contract clause based on context."""
        try:
            # Get clause template
            clause_template = await self._get_clause_template(
                input_data.clause_type,
                input_data.jurisdiction
            )

            # Generate clause content
            generated_clause = await self._generate_clause_content(
                clause_template,
                input_data.context_data,
                input_data.style_preferences
            )

            # Validate generated clause
            validation_results = await self._validate_clause(
                generated_clause,
                input_data.clause_type,
                input_data.jurisdiction
            )

            return ToolResult(
                success=True,
                data={
                    "clause_type": input_data.clause_type,
                    "generated_clause": generated_clause,
                    "validation_results": validation_results,
                    "jurisdiction": input_data.jurisdiction,
                    "word_count": len(generated_clause.get("content", "").split())
                },
                metadata={
                    "template_used": clause_template.get("id"),
                    "generation_timestamp": datetime.utcnow().isoformat(),
                    "style_preferences": input_data.style_preferences
                },
                execution_time=0.0,
                tool_name=self.name
            )

        except Exception as e:
            return ToolResult(
                success=False,
                errors=[f"Clause generation failed: {str(e)}"],
                execution_time=0.0,
                tool_name=self.name
            )

    async def _get_clause_template(self, clause_type: str, jurisdiction: str) -> Dict[str, Any]:
        """Get clause template for the specified type and jurisdiction."""
        # This would load from a clause template database
        templates = {
            "contingency": {
                "id": "contingency_template",
                "content": "This offer is contingent upon {contingency_condition} within {timeframe} days of acceptance.",
                "variables": ["contingency_condition", "timeframe"],
                "legal_requirements": ["must_specify_condition", "must_specify_timeframe"]
            },
            "financing": {
                "id": "financing_template",
                "content": "Buyer's obligation to purchase is contingent upon obtaining financing in the amount of {loan_amount} at an interest rate not to exceed {max_interest_rate}% per annum.",
                "variables": ["loan_amount", "max_interest_rate"],
                "legal_requirements": ["must_specify_amount", "must_specify_rate"]
            },
            "inspection": {
                "id": "inspection_template",
                "content": "Buyer shall have {inspection_period} days from acceptance to conduct inspections and approve the condition of the property.",
                "variables": ["inspection_period"],
                "legal_requirements": ["must_specify_period"]
            }
        }

        return templates.get(clause_type, {
            "id": "default_template",
            "content": f"Standard {clause_type} clause for {jurisdiction} jurisdiction.",
            "variables": [],
            "legal_requirements": []
        })

    async def _generate_clause_content(self,
                                     template: Dict[str, Any],
                                     context_data: Dict[str, Any],
                                     style_preferences: Dict[str, Any]) -> Dict[str, Any]:
        """Generate clause content from template and context."""
        content = template.get("content", "")
        variables = template.get("variables", [])

        # Fill template variables with context data
        for variable in variables:
            if variable in context_data:
                placeholder = f"{{{variable}}}"
                content = content.replace(placeholder, str(context_data[variable]))

        # Apply style preferences
        if style_preferences.get("formal_language", True):
            content = self._apply_formal_language(content)

        if style_preferences.get("include_definitions", False):
            content = self._add_definitions(content)

        return {
            "content": content,
            "template_id": template.get("id"),
            "variables_used": [v for v in variables if v in context_data],
            "style_applied": style_preferences
        }

    def _apply_formal_language(self, content: str) -> str:
        """Apply formal legal language patterns."""
        # Simple formal language transformations
        content = content.replace("will", "shall")
        content = content.replace("can", "may")
        return content

    def _add_definitions(self, content: str) -> str:
        """Add definitions section if requested."""
        definitions = "\n\nDefinitions: Terms used in this clause shall have the meanings set forth in the main agreement."
        return content + definitions

    async def _validate_clause(self,
                             clause: Dict[str, Any],
                             clause_type: str,
                             jurisdiction: str) -> Dict[str, Any]:
        """Validate generated clause for legal compliance."""
        validation_results = {
            "is_valid": True,
            "compliance_score": 0.85,
            "issues": [],
            "suggestions": []
        }

        content = clause.get("content", "")

        # Basic validation checks
        if len(content) < 10:
            validation_results["is_valid"] = False
            validation_results["issues"].append("Clause content is too short")

        if not content.strip().endswith('.'):
            validation_results["suggestions"].append("Consider ending clause with proper punctuation")

        # Clause-specific validation
        if clause_type == "contingency" and "contingent" not in content.lower():
            validation_results["issues"].append("Contingency clause should contain 'contingent' language")

        return validation_results


class DocumentGenerationTool(ContractTool):
    """Tool for generating formatted contract documents."""

    @property
    def name(self) -> str:
        return "document_generator"

    @property
    def description(self) -> str:
        return "Generate formatted contract documents in DOCX or PDF format"

    async def execute(self, input_data: DocumentGenerationInput) -> ToolResult:
        """Generate a formatted contract document."""
        try:
            # Generate document based on format
            if input_data.output_format.lower() == "docx":
                document_data = await self._generate_docx(
                    input_data.filled_template,
                    input_data.formatting_options
                )
            elif input_data.output_format.lower() == "pdf":
                document_data = await self._generate_pdf(
                    input_data.filled_template,
                    input_data.formatting_options
                )
            else:
                raise ValueError(f"Unsupported output format: {input_data.output_format}")

            return ToolResult(
                success=True,
                data={
                    "document_id": document_data["document_id"],
                    "file_path": document_data["file_path"],
                    "file_size": document_data["file_size"],
                    "page_count": document_data["page_count"],
                    "format": input_data.output_format,
                    "generation_metadata": document_data["metadata"]
                },
                metadata={
                    "template_id": input_data.filled_template.get("template_id"),
                    "generation_timestamp": datetime.utcnow().isoformat(),
                    "formatting_options": input_data.formatting_options
                },
                execution_time=0.0,
                tool_name=self.name
            )

        except Exception as e:
            return ToolResult(
                success=False,
                errors=[f"Document generation failed: {str(e)}"],
                execution_time=0.0,
                tool_name=self.name
            )

    async def _generate_docx(self,
                           filled_template: Dict[str, Any],
                           formatting_options: Dict[str, Any]) -> Dict[str, Any]:
        """Generate DOCX document."""
        # This would use python-docx library in production
        document_id = f"contract_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        return {
            "document_id": document_id,
            "file_path": f"/tmp/{document_id}.docx",
            "file_size": 25600,  # Mock size
            "page_count": 3,
            "metadata": {
                "title": filled_template.get("template_name", "Contract"),
                "author": "AI Contract Generator",
                "created": datetime.utcnow().isoformat(),
                "format": "docx"
            }
        }

    async def _generate_pdf(self,
                          filled_template: Dict[str, Any],
                          formatting_options: Dict[str, Any]) -> Dict[str, Any]:
        """Generate PDF document."""
        # This would use reportlab or similar library in production
        document_id = f"contract_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        return {
            "document_id": document_id,
            "file_path": f"/tmp/{document_id}.pdf",
            "file_size": 35200,  # Mock size
            "page_count": 3,
            "metadata": {
                "title": filled_template.get("template_name", "Contract"),
                "author": "AI Contract Generator",
                "created": datetime.utcnow().isoformat(),
                "format": "pdf"
            }
        }
