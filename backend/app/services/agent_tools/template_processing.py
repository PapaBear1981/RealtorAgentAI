"""
Template Processing Tools for AI Agents.

This module provides specialized tools for agents to interact with the template
engine for advanced template operations, variable processing, and content generation.
"""

import re
import json
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from jinja2 import Template as Jinja2Template, Environment, meta

import structlog
from pydantic import BaseModel, Field

from .base import BaseTool, ToolInput, ToolResult, ToolCategory
from ...services.template_service import TemplateService
from ...core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class TemplateAnalysisInput(ToolInput):
    """Input for template analysis operations."""
    template_content: str = Field(..., description="Template content to analyze")
    template_id: Optional[str] = Field(None, description="Template ID from database")
    analysis_type: str = Field(default="comprehensive", description="Type of analysis to perform")


class TemplateRenderingInput(ToolInput):
    """Input for template rendering operations."""
    template_content: str = Field(..., description="Template content to render")
    variables: Dict[str, Any] = Field(default_factory=dict, description="Variables for template rendering")
    rendering_options: Dict[str, Any] = Field(default_factory=dict, description="Rendering options")


class TemplateValidationInput(ToolInput):
    """Input for template validation operations."""
    template_content: str = Field(..., description="Template content to validate")
    validation_rules: Dict[str, Any] = Field(default_factory=dict, description="Validation rules")
    strict_mode: bool = Field(default=False, description="Enable strict validation mode")


class TemplateOptimizationInput(ToolInput):
    """Input for template optimization operations."""
    template_content: str = Field(..., description="Template content to optimize")
    optimization_goals: List[str] = Field(default_factory=list, description="Optimization goals")
    constraints: Dict[str, Any] = Field(default_factory=dict, description="Optimization constraints")


class TemplateAnalysisTool(BaseTool):
    """Tool for analyzing template structure, variables, and complexity."""

    @property
    def name(self) -> str:
        return "template_analyzer"

    @property
    def description(self) -> str:
        return "Analyze template structure, extract variables, and assess complexity"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.CONTRACT_GENERATION

    async def execute(self, input_data: TemplateAnalysisInput) -> ToolResult:
        """Execute template analysis."""
        try:
            if input_data.analysis_type == "variables":
                result = await self._analyze_variables(input_data.template_content)
            elif input_data.analysis_type == "structure":
                result = await self._analyze_structure(input_data.template_content)
            elif input_data.analysis_type == "complexity":
                result = await self._analyze_complexity(input_data.template_content)
            else:
                result = await self._comprehensive_analysis(input_data.template_content)

            return ToolResult(
                success=True,
                data=result,
                metadata={
                    "template_id": input_data.template_id,
                    "analysis_type": input_data.analysis_type,
                    "timestamp": datetime.utcnow().isoformat(),
                    "user_id": input_data.user_id
                },
                execution_time=0.0,
                tool_name=self.name
            )

        except Exception as e:
            return ToolResult(
                success=False,
                errors=[f"Template analysis failed: {str(e)}"],
                execution_time=0.0,
                tool_name=self.name
            )

    async def _analyze_variables(self, template_content: str) -> Dict[str, Any]:
        """Analyze template variables and their usage."""
        # Use Jinja2 to extract variables
        env = Environment()
        ast = env.parse(template_content)
        variables = meta.find_undeclared_variables(ast)

        # Analyze variable patterns
        variable_patterns = {
            "simple": [],
            "conditional": [],
            "loops": [],
            "filters": []
        }

        # Find different types of variable usage
        simple_vars = re.findall(r'\{\{\s*(\w+)\s*\}\}', template_content)
        conditional_vars = re.findall(r'\{\%\s*if\s+(\w+)', template_content)
        loop_vars = re.findall(r'\{\%\s*for\s+\w+\s+in\s+(\w+)', template_content)
        filter_vars = re.findall(r'\{\{\s*(\w+)\s*\|', template_content)

        variable_patterns["simple"] = list(set(simple_vars))
        variable_patterns["conditional"] = list(set(conditional_vars))
        variable_patterns["loops"] = list(set(loop_vars))
        variable_patterns["filters"] = list(set(filter_vars))

        # Variable statistics
        variable_stats = {
            "total_variables": len(variables),
            "unique_variables": len(set(variables)),
            "most_used": self._get_most_used_variables(template_content, variables),
            "required_variables": list(variables),
            "optional_variables": self._find_optional_variables(template_content)
        }

        return {
            "variables": list(variables),
            "variable_patterns": variable_patterns,
            "variable_stats": variable_stats,
            "variable_types": self._classify_variable_types(variables)
        }

    async def _analyze_structure(self, template_content: str) -> Dict[str, Any]:
        """Analyze template structure and organization."""
        # Count different template elements
        blocks = len(re.findall(r'\{\%\s*block\s+\w+\s*\%\}', template_content))
        includes = len(re.findall(r'\{\%\s*include\s+', template_content))
        extends = len(re.findall(r'\{\%\s*extends\s+', template_content))
        macros = len(re.findall(r'\{\%\s*macro\s+\w+', template_content))

        # Analyze control structures
        if_statements = len(re.findall(r'\{\%\s*if\s+', template_content))
        for_loops = len(re.findall(r'\{\%\s*for\s+', template_content))

        # Content analysis
        lines = template_content.splitlines()
        non_empty_lines = [line for line in lines if line.strip()]

        return {
            "template_elements": {
                "blocks": blocks,
                "includes": includes,
                "extends": extends,
                "macros": macros
            },
            "control_structures": {
                "if_statements": if_statements,
                "for_loops": for_loops
            },
            "content_stats": {
                "total_lines": len(lines),
                "non_empty_lines": len(non_empty_lines),
                "character_count": len(template_content),
                "word_count": len(template_content.split())
            },
            "template_type": self._classify_template_type(template_content)
        }

    async def _analyze_complexity(self, template_content: str) -> Dict[str, Any]:
        """Analyze template complexity metrics."""
        # Cyclomatic complexity (simplified)
        if_count = len(re.findall(r'\{\%\s*if\s+', template_content))
        elif_count = len(re.findall(r'\{\%\s*elif\s+', template_content))
        for_count = len(re.findall(r'\{\%\s*for\s+', template_content))

        cyclomatic_complexity = 1 + if_count + elif_count + for_count

        # Nesting depth
        nesting_depth = self._calculate_nesting_depth(template_content)

        # Variable complexity
        env = Environment()
        ast = env.parse(template_content)
        variables = meta.find_undeclared_variables(ast)
        variable_complexity = len(variables)

        # Overall complexity score
        complexity_score = (
            cyclomatic_complexity * 0.4 +
            nesting_depth * 0.3 +
            variable_complexity * 0.3
        )

        return {
            "cyclomatic_complexity": cyclomatic_complexity,
            "nesting_depth": nesting_depth,
            "variable_complexity": variable_complexity,
            "complexity_score": round(complexity_score, 2),
            "complexity_level": self._classify_complexity_level(complexity_score),
            "recommendations": self._generate_complexity_recommendations(complexity_score)
        }

    async def _comprehensive_analysis(self, template_content: str) -> Dict[str, Any]:
        """Perform comprehensive template analysis."""
        variables_analysis = await self._analyze_variables(template_content)
        structure_analysis = await self._analyze_structure(template_content)
        complexity_analysis = await self._analyze_complexity(template_content)

        return {
            "variables": variables_analysis,
            "structure": structure_analysis,
            "complexity": complexity_analysis,
            "summary": {
                "total_variables": variables_analysis["variable_stats"]["total_variables"],
                "complexity_level": complexity_analysis["complexity_level"],
                "template_type": structure_analysis["template_type"],
                "maintainability": self._assess_maintainability(complexity_analysis, structure_analysis)
            }
        }

    def _get_most_used_variables(self, content: str, variables: set) -> List[Dict[str, Any]]:
        """Find most frequently used variables."""
        usage_counts = {}
        for var in variables:
            count = len(re.findall(rf'\b{var}\b', content))
            usage_counts[var] = count

        sorted_vars = sorted(usage_counts.items(), key=lambda x: x[1], reverse=True)
        return [{"variable": var, "count": count} for var, count in sorted_vars[:5]]

    def _find_optional_variables(self, content: str) -> List[str]:
        """Find variables that appear to be optional (in if statements)."""
        optional_vars = re.findall(r'\{\%\s*if\s+(\w+)\s*\%\}', content)
        return list(set(optional_vars))

    def _classify_variable_types(self, variables: set) -> Dict[str, List[str]]:
        """Classify variables by their likely types based on naming conventions."""
        types = {
            "text": [],
            "numeric": [],
            "date": [],
            "boolean": [],
            "list": [],
            "object": []
        }

        for var in variables:
            var_lower = var.lower()
            if any(keyword in var_lower for keyword in ['name', 'title', 'description', 'address']):
                types["text"].append(var)
            elif any(keyword in var_lower for keyword in ['price', 'amount', 'count', 'number']):
                types["numeric"].append(var)
            elif any(keyword in var_lower for keyword in ['date', 'time', 'created', 'updated']):
                types["date"].append(var)
            elif any(keyword in var_lower for keyword in ['is_', 'has_', 'can_', 'should_']):
                types["boolean"].append(var)
            elif any(keyword in var_lower for keyword in ['list', 'items', 'array']):
                types["list"].append(var)
            else:
                types["object"].append(var)

        return types

    def _classify_template_type(self, content: str) -> str:
        """Classify the type of template based on content."""
        if 'contract' in content.lower() or 'agreement' in content.lower():
            return "contract"
        elif 'email' in content.lower() or 'subject' in content.lower():
            return "email"
        elif 'report' in content.lower() or 'summary' in content.lower():
            return "report"
        elif 'form' in content.lower() or 'input' in content.lower():
            return "form"
        else:
            return "document"

    def _calculate_nesting_depth(self, content: str) -> int:
        """Calculate maximum nesting depth of template structures."""
        depth = 0
        max_depth = 0

        for line in content.splitlines():
            if re.search(r'\{\%\s*(if|for|block)', line):
                depth += 1
                max_depth = max(max_depth, depth)
            elif re.search(r'\{\%\s*(endif|endfor|endblock)', line):
                depth = max(0, depth - 1)

        return max_depth

    def _classify_complexity_level(self, score: float) -> str:
        """Classify complexity level based on score."""
        if score < 5:
            return "low"
        elif score < 15:
            return "medium"
        elif score < 30:
            return "high"
        else:
            return "very_high"

    def _generate_complexity_recommendations(self, score: float) -> List[str]:
        """Generate recommendations based on complexity score."""
        recommendations = []

        if score > 20:
            recommendations.append("Consider breaking down into smaller templates")
            recommendations.append("Extract reusable components into macros")

        if score > 15:
            recommendations.append("Review variable naming for clarity")
            recommendations.append("Add comments for complex logic")

        if score > 10:
            recommendations.append("Consider using template inheritance")

        return recommendations

    def _assess_maintainability(self, complexity: Dict[str, Any], structure: Dict[str, Any]) -> str:
        """Assess template maintainability."""
        complexity_score = complexity["complexity_score"]
        nesting_depth = complexity["nesting_depth"]
        line_count = structure["content_stats"]["non_empty_lines"]

        if complexity_score < 10 and nesting_depth < 3 and line_count < 100:
            return "high"
        elif complexity_score < 20 and nesting_depth < 5 and line_count < 200:
            return "medium"
        else:
            return "low"


class TemplateRenderingTool(BaseTool):
    """Tool for rendering templates with variables and advanced features."""

    @property
    def name(self) -> str:
        return "template_renderer"

    @property
    def description(self) -> str:
        return "Render templates with variables, filters, and advanced Jinja2 features"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.CONTRACT_GENERATION

    async def execute(self, input_data: TemplateRenderingInput) -> ToolResult:
        """Execute template rendering."""
        try:
            # Get template service
            template_service = TemplateService()

            # Render template
            rendered_content = await self._render_template(
                input_data.template_content,
                input_data.variables,
                input_data.rendering_options
            )

            # Validate rendered content
            validation_result = await self._validate_rendered_content(rendered_content)

            # Generate rendering statistics
            stats = await self._generate_rendering_stats(
                input_data.template_content,
                rendered_content,
                input_data.variables
            )

            return ToolResult(
                success=True,
                data={
                    "rendered_content": rendered_content,
                    "validation_result": validation_result,
                    "rendering_stats": stats,
                    "variables_used": list(input_data.variables.keys())
                },
                metadata={
                    "template_length": len(input_data.template_content),
                    "rendered_length": len(rendered_content),
                    "variables_count": len(input_data.variables),
                    "timestamp": datetime.utcnow().isoformat(),
                    "user_id": input_data.user_id
                },
                execution_time=0.0,
                tool_name=self.name
            )

        except Exception as e:
            return ToolResult(
                success=False,
                errors=[f"Template rendering failed: {str(e)}"],
                execution_time=0.0,
                tool_name=self.name
            )

    async def _render_template(self,
                             template_content: str,
                             variables: Dict[str, Any],
                             options: Dict[str, Any]) -> str:
        """Render template with variables."""
        # Create Jinja2 environment with custom filters
        env = Environment()

        # Add custom filters for real estate templates
        env.filters['currency'] = self._currency_filter
        env.filters['date_format'] = self._date_format_filter
        env.filters['title_case'] = self._title_case_filter
        env.filters['legal_format'] = self._legal_format_filter

        # Create template
        template = env.from_string(template_content)

        # Render with variables
        rendered = template.render(**variables)

        # Apply post-processing if specified
        if options.get("post_process"):
            rendered = await self._post_process_content(rendered, options)

        return rendered

    async def _validate_rendered_content(self, content: str) -> Dict[str, Any]:
        """Validate rendered template content."""
        validation_result = {
            "is_valid": True,
            "warnings": [],
            "errors": []
        }

        # Check for unrendered variables
        unrendered_vars = re.findall(r'\{\{[^}]+\}\}', content)
        if unrendered_vars:
            validation_result["warnings"].append(f"Unrendered variables found: {unrendered_vars}")

        # Check for unrendered blocks
        unrendered_blocks = re.findall(r'\{\%[^%]+\%\}', content)
        if unrendered_blocks:
            validation_result["errors"].append(f"Unrendered template blocks found: {unrendered_blocks}")
            validation_result["is_valid"] = False

        # Check for empty content
        if not content.strip():
            validation_result["errors"].append("Rendered content is empty")
            validation_result["is_valid"] = False

        return validation_result

    async def _generate_rendering_stats(self,
                                      template_content: str,
                                      rendered_content: str,
                                      variables: Dict[str, Any]) -> Dict[str, Any]:
        """Generate statistics about the rendering process."""
        return {
            "template_size": len(template_content),
            "rendered_size": len(rendered_content),
            "size_change": len(rendered_content) - len(template_content),
            "compression_ratio": len(rendered_content) / len(template_content) if template_content else 0,
            "variables_provided": len(variables),
            "variables_used": len(re.findall(r'\{\{[^}]+\}\}', template_content)),
            "rendering_efficiency": self._calculate_rendering_efficiency(template_content, rendered_content)
        }

    async def _post_process_content(self, content: str, options: Dict[str, Any]) -> str:
        """Apply post-processing to rendered content."""
        if options.get("remove_extra_whitespace"):
            content = re.sub(r'\n\s*\n', '\n\n', content)  # Remove extra blank lines
            content = re.sub(r' +', ' ', content)  # Remove extra spaces

        if options.get("capitalize_sentences"):
            sentences = content.split('. ')
            sentences = [s.capitalize() if s else s for s in sentences]
            content = '. '.join(sentences)

        return content

    def _currency_filter(self, value: Union[str, int, float]) -> str:
        """Format value as currency."""
        try:
            amount = float(value)
            return f"${amount:,.2f}"
        except (ValueError, TypeError):
            return str(value)

    def _date_format_filter(self, value: str, format_str: str = "%B %d, %Y") -> str:
        """Format date string."""
        try:
            if isinstance(value, str):
                # Try to parse common date formats
                from datetime import datetime
                for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"]:
                    try:
                        date_obj = datetime.strptime(value, fmt)
                        return date_obj.strftime(format_str)
                    except ValueError:
                        continue
            return str(value)
        except Exception:
            return str(value)

    def _title_case_filter(self, value: str) -> str:
        """Convert to title case."""
        return str(value).title()

    def _legal_format_filter(self, value: str) -> str:
        """Apply legal document formatting."""
        # Capitalize legal terms
        legal_terms = ['whereas', 'therefore', 'hereby', 'herein', 'hereof', 'hereunder']
        for term in legal_terms:
            value = re.sub(rf'\b{term}\b', term.upper(), value, flags=re.IGNORECASE)
        return value

    def _calculate_rendering_efficiency(self, template: str, rendered: str) -> float:
        """Calculate rendering efficiency score."""
        template_vars = len(re.findall(r'\{\{[^}]+\}\}', template))
        if template_vars == 0:
            return 1.0

        unrendered_vars = len(re.findall(r'\{\{[^}]+\}\}', rendered))
        return (template_vars - unrendered_vars) / template_vars
