"""
Template rendering engine for contract generation.

This module provides comprehensive template rendering capabilities using Jinja2
with support for variable substitution, conditional logic, business rules,
and multi-format output generation.
"""

import logging
import re
import json
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, Any, List, Optional, Union, Callable
from pathlib import Path

from jinja2 import (
    Environment,
    FileSystemLoader,
    DictLoader,
    BaseLoader,
    Template as Jinja2Template,
    TemplateError,
    TemplateSyntaxError,
    UndefinedError,
    select_autoescape
)
from jinja2.sandbox import SandboxedEnvironment
from markupsafe import Markup

from ..core.config import get_settings
from ..models.template import TemplateVariable, VariableType, OutputFormat

logger = logging.getLogger(__name__)
settings = get_settings()


class TemplateRenderingError(Exception):
    """Exception raised during template rendering."""
    pass


class VariableValidationError(Exception):
    """Exception raised during variable validation."""
    pass


class CustomTemplateLoader(BaseLoader):
    """Custom template loader for database-stored templates."""

    def __init__(self, template_content: str):
        self.template_content = template_content

    def get_source(self, environment, template):
        return self.template_content, None, lambda: True


class TemplateEngine:
    """
    Advanced template rendering engine with Jinja2.

    Provides comprehensive template rendering with variable validation,
    conditional logic, business rules, and multi-format output support.
    """

    def __init__(self):
        """Initialize template engine."""
        self._setup_jinja_environment()
        self._register_custom_filters()
        self._register_custom_functions()

    def _setup_jinja_environment(self):
        """Setup Jinja2 environment with security and features."""
        # Use sandboxed environment for security
        self.env = SandboxedEnvironment(
            loader=DictLoader({}),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
            enable_async=False
        )

        # Configure environment settings
        self.env.globals.update({
            'now': datetime.now,
            'today': date.today,
            'len': len,
            'str': str,
            'int': int,
            'float': float,
            'bool': bool,
            'list': list,
            'dict': dict,
        })

    def _register_custom_filters(self):
        """Register custom Jinja2 filters for contract templates."""

        def currency_filter(value, currency_code='USD', locale='en_US'):
            """Format value as currency."""
            try:
                if value is None:
                    return '$0.00'

                amount = float(value)
                if currency_code == 'USD':
                    return f'${amount:,.2f}'
                else:
                    return f'{amount:,.2f} {currency_code}'
            except (ValueError, TypeError):
                return str(value)

        def date_format_filter(value, format_string='%B %d, %Y'):
            """Format date with custom format."""
            try:
                if isinstance(value, str):
                    # Try to parse string date
                    value = datetime.fromisoformat(value.replace('Z', '+00:00'))
                elif isinstance(value, date) and not isinstance(value, datetime):
                    value = datetime.combine(value, datetime.min.time())

                if isinstance(value, datetime):
                    return value.strftime(format_string)
                return str(value)
            except (ValueError, TypeError):
                return str(value)

        def phone_format_filter(value, format_type='us'):
            """Format phone number."""
            try:
                # Remove all non-digit characters
                digits = re.sub(r'\D', '', str(value))

                if format_type == 'us' and len(digits) == 10:
                    return f'({digits[:3]}) {digits[3:6]}-{digits[6:]}'
                elif format_type == 'us' and len(digits) == 11 and digits[0] == '1':
                    return f'+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}'
                else:
                    return str(value)
            except (ValueError, TypeError):
                return str(value)

        def title_case_filter(value):
            """Convert to title case with proper handling."""
            try:
                return str(value).title()
            except (ValueError, TypeError):
                return str(value)

        def upper_case_filter(value):
            """Convert to uppercase."""
            try:
                return str(value).upper()
            except (ValueError, TypeError):
                return str(value)

        def lower_case_filter(value):
            """Convert to lowercase."""
            try:
                return str(value).lower()
            except (ValueError, TypeError):
                return str(value)

        def word_count_filter(value):
            """Count words in text."""
            try:
                return len(str(value).split())
            except (ValueError, TypeError):
                return 0

        def truncate_words_filter(value, length=50, suffix='...'):
            """Truncate text to specified word count."""
            try:
                words = str(value).split()
                if len(words) <= length:
                    return str(value)
                return ' '.join(words[:length]) + suffix
            except (ValueError, TypeError):
                return str(value)

        # Register all filters
        self.env.filters['currency'] = currency_filter
        self.env.filters['date_format'] = date_format_filter
        self.env.filters['phone_format'] = phone_format_filter
        self.env.filters['title_case'] = title_case_filter
        self.env.filters['upper_case'] = upper_case_filter
        self.env.filters['lower_case'] = lower_case_filter
        self.env.filters['word_count'] = word_count_filter
        self.env.filters['truncate_words'] = truncate_words_filter

    def _register_custom_functions(self):
        """Register custom functions for templates."""

        def calculate_percentage(value, total):
            """Calculate percentage."""
            try:
                if total == 0:
                    return 0
                return (float(value) / float(total)) * 100
            except (ValueError, TypeError, ZeroDivisionError):
                return 0

        def format_address(street, city, state, zip_code, country='USA'):
            """Format address components."""
            parts = [street, city, f"{state} {zip_code}"]
            if country and country != 'USA':
                parts.append(country)
            return ', '.join(filter(None, parts))

        def days_between(start_date, end_date):
            """Calculate days between two dates."""
            try:
                if isinstance(start_date, str):
                    start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                if isinstance(end_date, str):
                    end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))

                delta = end_date - start_date
                return delta.days
            except (ValueError, TypeError):
                return 0

        def conditional_text(condition, true_text, false_text=''):
            """Return text based on condition."""
            return true_text if condition else false_text

        # Register functions as globals
        self.env.globals.update({
            'calculate_percentage': calculate_percentage,
            'format_address': format_address,
            'days_between': days_between,
            'conditional_text': conditional_text,
        })

    def validate_variables(
        self,
        variables: Dict[str, Any],
        variable_definitions: List[TemplateVariable]
    ) -> Dict[str, List[str]]:
        """
        Validate template variables against their definitions.

        Args:
            variables: Variable values to validate
            variable_definitions: Variable definition schemas

        Returns:
            Dict with validation results (errors, warnings)
        """
        errors = []
        warnings = []

        # Create lookup for variable definitions
        var_defs = {var.name: var for var in variable_definitions}

        # Check required variables
        for var_def in variable_definitions:
            if var_def.required and var_def.name not in variables:
                errors.append(f"Required variable '{var_def.name}' is missing")
                continue

            if var_def.name not in variables:
                continue

            value = variables[var_def.name]

            # Type validation
            try:
                self._validate_variable_type(value, var_def)
            except VariableValidationError as e:
                errors.append(f"Variable '{var_def.name}': {str(e)}")

            # Value constraints validation
            try:
                self._validate_variable_constraints(value, var_def)
            except VariableValidationError as e:
                warnings.append(f"Variable '{var_def.name}': {str(e)}")

        # Check for undefined variables
        for var_name in variables:
            if var_name not in var_defs:
                warnings.append(f"Variable '{var_name}' is not defined in template schema")

        return {
            'errors': errors,
            'warnings': warnings,
            'is_valid': len(errors) == 0
        }

    def _validate_variable_type(self, value: Any, var_def: TemplateVariable):
        """Validate variable type."""
        if value is None and not var_def.required:
            return

        if var_def.variable_type == VariableType.STRING:
            if not isinstance(value, str):
                raise VariableValidationError(f"Expected string, got {type(value).__name__}")

        elif var_def.variable_type == VariableType.NUMBER:
            if not isinstance(value, (int, float, Decimal)):
                try:
                    float(value)
                except (ValueError, TypeError):
                    raise VariableValidationError(f"Expected number, got {type(value).__name__}")

        elif var_def.variable_type == VariableType.DATE:
            if not isinstance(value, (date, datetime)):
                try:
                    datetime.fromisoformat(str(value).replace('Z', '+00:00'))
                except ValueError:
                    raise VariableValidationError(f"Expected date, got invalid date format")

        elif var_def.variable_type == VariableType.BOOLEAN:
            if not isinstance(value, bool):
                if str(value).lower() not in ['true', 'false', '1', '0', 'yes', 'no']:
                    raise VariableValidationError(f"Expected boolean, got {type(value).__name__}")

        elif var_def.variable_type == VariableType.EMAIL:
            if not isinstance(value, str) or '@' not in value:
                raise VariableValidationError("Expected valid email address")

        elif var_def.variable_type == VariableType.PHONE:
            if not isinstance(value, str) or not re.match(r'[\d\s\-\(\)\+\.]+', value):
                raise VariableValidationError("Expected valid phone number")

        elif var_def.variable_type == VariableType.CHOICE:
            if var_def.choices and value not in var_def.choices:
                raise VariableValidationError(f"Value must be one of: {var_def.choices}")

    def _validate_variable_constraints(self, value: Any, var_def: TemplateVariable):
        """Validate variable constraints."""
        if value is None:
            return

        # String length constraints
        if var_def.variable_type == VariableType.STRING:
            if var_def.min_length and len(str(value)) < var_def.min_length:
                raise VariableValidationError(f"Minimum length is {var_def.min_length}")
            if var_def.max_length and len(str(value)) > var_def.max_length:
                raise VariableValidationError(f"Maximum length is {var_def.max_length}")

        # Numeric constraints
        if var_def.variable_type == VariableType.NUMBER:
            num_value = float(value)
            if var_def.min_value is not None and num_value < var_def.min_value:
                raise VariableValidationError(f"Minimum value is {var_def.min_value}")
            if var_def.max_value is not None and num_value > var_def.max_value:
                raise VariableValidationError(f"Maximum value is {var_def.max_value}")

        # Pattern validation
        if var_def.pattern and isinstance(value, str):
            if not re.match(var_def.pattern, value):
                raise VariableValidationError(f"Value does not match required pattern")

    async def render_template_advanced(
        self,
        template_content: str,
        variables: Dict[str, Any],
        variable_definitions: Optional[List[TemplateVariable]] = None,
        validate_variables: bool = True,
        output_format: OutputFormat = OutputFormat.HTML,
        enable_preview_mode: bool = False,
        apply_business_rules: bool = True,
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        Advanced template rendering with enhanced features.

        Args:
            template_content: Template content to render
            variables: Variables for substitution
            variable_definitions: Variable definitions for validation
            validate_variables: Whether to validate variables
            output_format: Output format
            enable_preview_mode: Enable preview mode with placeholders
            apply_business_rules: Apply business rules during rendering
            include_metadata: Include rendering metadata

        Returns:
            Dict: Rendering results with metadata
        """
        try:
            start_time = datetime.now()

            # Prepare variables with business rules if enabled
            processed_variables = variables.copy()
            if apply_business_rules and variable_definitions:
                processed_variables = await self._apply_rendering_rules(
                    processed_variables, variable_definitions
                )

            # Handle preview mode
            if enable_preview_mode:
                processed_variables = self._add_preview_placeholders(
                    processed_variables, variable_definitions
                )

            # Validate variables if requested
            validation_results = None
            if validate_variables and variable_definitions:
                validation_results = self.validate_variables(
                    processed_variables, variable_definitions
                )
                if not validation_results['is_valid']:
                    logger.warning(f"Variable validation failed: {validation_results['errors']}")

            # Render template
            rendered_content = self._render_with_jinja(template_content, processed_variables)

            # Post-process content based on output format
            final_content = await self._post_process_content(
                rendered_content, output_format, processed_variables
            )

            # Calculate rendering time
            end_time = datetime.now()
            render_time_ms = int((end_time - start_time).total_seconds() * 1000)

            result = {
                'content': final_content,
                'output_format': output_format,
                'render_time_ms': render_time_ms,
                'success': True
            }

            # Add metadata if requested
            if include_metadata:
                result.update({
                    'metadata': {
                        'variables_used': list(processed_variables.keys()),
                        'template_size': len(template_content),
                        'output_size': len(final_content),
                        'preview_mode': enable_preview_mode,
                        'business_rules_applied': apply_business_rules,
                        'validation_performed': validate_variables
                    }
                })

            # Add validation results if available
            if validation_results:
                result['validation_results'] = validation_results

            return result

        except Exception as e:
            logger.error(f"Advanced template rendering failed: {e}")
            return {
                'content': '',
                'output_format': output_format,
                'render_time_ms': 0,
                'success': False,
                'error': str(e),
                'validation_results': {'is_valid': False, 'errors': [str(e)], 'warnings': []}
            }

    def render_template(
        self,
        template_content: str,
        variables: Dict[str, Any],
        variable_definitions: Optional[List[TemplateVariable]] = None,
        validate_variables: bool = True,
        output_format: OutputFormat = OutputFormat.HTML
    ) -> Dict[str, Any]:
        """
        Render template with variables.

        Args:
            template_content: Template content to render
            variables: Variables to substitute
            variable_definitions: Variable definitions for validation
            validate_variables: Whether to validate variables
            output_format: Output format for rendering

        Returns:
            Dict with rendered content and metadata
        """
        try:
            start_time = datetime.now()

            # Validate variables if definitions provided
            validation_results = None
            if validate_variables and variable_definitions:
                validation_results = self.validate_variables(variables, variable_definitions)
                if not validation_results['is_valid']:
                    raise TemplateRenderingError(
                        f"Variable validation failed: {validation_results['errors']}"
                    )

            # Create template from content
            template = self.env.from_string(template_content)

            # Render template
            rendered_content = template.render(**variables)

            # Post-process based on output format
            if output_format == OutputFormat.HTML:
                rendered_content = self._post_process_html(rendered_content)
            elif output_format == OutputFormat.TXT:
                rendered_content = self._post_process_text(rendered_content)

            end_time = datetime.now()
            render_time = (end_time - start_time).total_seconds() * 1000

            return {
                'content': rendered_content,
                'output_format': output_format,
                'render_time_ms': render_time,
                'validation_results': validation_results,
                'variables_used': list(variables.keys()),
                'success': True
            }

        except (TemplateError, TemplateSyntaxError, UndefinedError) as e:
            logger.error(f"Template rendering error: {e}")
            raise TemplateRenderingError(f"Template rendering failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during template rendering: {e}")
            raise TemplateRenderingError(f"Unexpected error: {str(e)}")

    def _post_process_html(self, content: str) -> str:
        """Post-process HTML content."""
        # Add basic HTML structure if not present
        if not content.strip().startswith('<!DOCTYPE') and not content.strip().startswith('<html'):
            content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Generated Contract</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 40px; }}
        .contract-header {{ text-align: center; margin-bottom: 30px; }}
        .contract-section {{ margin-bottom: 20px; }}
        .signature-line {{ border-bottom: 1px solid #000; width: 200px; display: inline-block; }}
    </style>
</head>
<body>
{content}
</body>
</html>"""
        return content

    def _post_process_text(self, content: str) -> str:
        """Post-process plain text content."""
        # Remove HTML tags if present
        content = re.sub(r'<[^>]+>', '', content)
        # Normalize whitespace
        content = re.sub(r'\n\s*\n', '\n\n', content)
        return content.strip()

    async def _apply_rendering_rules(
        self,
        variables: Dict[str, Any],
        variable_definitions: List[TemplateVariable]
    ) -> Dict[str, Any]:
        """Apply business rules during rendering."""
        try:
            processed_variables = variables.copy()

            # Apply default values for missing variables
            for var_def in variable_definitions:
                if var_def.name not in processed_variables and var_def.default_value is not None:
                    processed_variables[var_def.name] = var_def.default_value

            # Apply calculated fields
            for var_def in variable_definitions:
                if hasattr(var_def, 'calculation_rule') and getattr(var_def, 'calculation_rule', None):
                    try:
                        calculated_value = self._calculate_field_value(
                            var_def.calculation_rule, processed_variables
                        )
                        processed_variables[var_def.name] = calculated_value
                    except Exception as e:
                        logger.warning(f"Failed to calculate field {var_def.name}: {e}")

            return processed_variables

        except Exception as e:
            logger.error(f"Failed to apply rendering rules: {e}")
            return variables

    def _add_preview_placeholders(
        self,
        variables: Dict[str, Any],
        variable_definitions: Optional[List[TemplateVariable]]
    ) -> Dict[str, Any]:
        """Add preview placeholders for missing variables."""
        try:
            preview_variables = variables.copy()

            if variable_definitions:
                for var_def in variable_definitions:
                    if var_def.name not in preview_variables:
                        placeholder = self._generate_placeholder(var_def)
                        preview_variables[var_def.name] = placeholder

            return preview_variables

        except Exception as e:
            logger.error(f"Failed to add preview placeholders: {e}")
            return variables

    def _generate_placeholder(self, var_def: TemplateVariable) -> str:
        """Generate appropriate placeholder for variable type."""
        try:
            if var_def.variable_type == VariableType.TEXT:
                return f"[{var_def.label or var_def.name}]"
            elif var_def.variable_type == VariableType.NUMBER:
                return "0.00"
            elif var_def.variable_type == VariableType.DATE:
                return datetime.now().strftime("%Y-%m-%d")
            elif var_def.variable_type == VariableType.BOOLEAN:
                return "false"
            elif var_def.variable_type == VariableType.EMAIL:
                return "example@email.com"
            elif var_def.variable_type == VariableType.PHONE:
                return "(555) 123-4567"
            elif var_def.variable_type == VariableType.ADDRESS:
                return "123 Main St, City, State 12345"
            elif var_def.variable_type == VariableType.CURRENCY:
                return "$0.00"
            else:
                return f"[{var_def.label or var_def.name}]"

        except Exception as e:
            logger.warning(f"Failed to generate placeholder for {var_def.name}: {e}")
            return f"[{var_def.name}]"

    def _calculate_field_value(
        self,
        calculation_rule: str,
        variables: Dict[str, Any]
    ) -> Any:
        """Calculate field value based on rule."""
        try:
            # Simple calculation rules (extend as needed)
            if calculation_rule.startswith('='):
                expression = calculation_rule[1:]

                # Replace variable names with values
                for var_name, var_value in variables.items():
                    if var_name in expression and isinstance(var_value, (int, float)):
                        expression = expression.replace(var_name, str(var_value))

                # Evaluate simple mathematical expressions
                if all(c in '0123456789+-*/.() ' for c in expression):
                    return eval(expression, {"__builtins__": {}}, {})

            return calculation_rule

        except Exception as e:
            logger.warning(f"Failed to calculate field value: {e}")
            return calculation_rule

    async def _post_process_content(
        self,
        content: str,
        output_format: OutputFormat,
        variables: Dict[str, Any]
    ) -> str:
        """Post-process rendered content based on output format."""
        try:
            if output_format == OutputFormat.HTML:
                # Add HTML document structure if not present
                if not content.strip().startswith('<!DOCTYPE') and not content.strip().startswith('<html'):
                    content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Generated Contract</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 40px; }}
        .contract-header {{ text-align: center; margin-bottom: 30px; }}
        .contract-content {{ margin: 20px 0; }}
        .signature-section {{ margin-top: 50px; }}
    </style>
</head>
<body>
    <div class="contract-document">
        {content}
    </div>
</body>
</html>"""

            elif output_format == OutputFormat.PDF:
                # For PDF, ensure proper HTML structure for conversion
                if not content.strip().startswith('<!DOCTYPE'):
                    content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        @page {{ margin: 1in; }}
        body {{ font-family: 'Times New Roman', serif; font-size: 12pt; line-height: 1.5; }}
        .page-break {{ page-break-before: always; }}
    </style>
</head>
<body>
    {content}
</body>
</html>"""

            elif output_format == OutputFormat.TXT:
                # Convert HTML to plain text (basic implementation)
                import re
                # Remove HTML tags
                content = re.sub(r'<[^>]+>', '', content)
                # Clean up whitespace
                content = re.sub(r'\n\s*\n', '\n\n', content)
                content = content.strip()

            return content

        except Exception as e:
            logger.error(f"Post-processing failed: {e}")
            return content


# Global template engine instance
_template_engine: Optional[TemplateEngine] = None


def get_template_engine() -> TemplateEngine:
    """
    Get global template engine instance.

    Returns:
        TemplateEngine: Configured template engine
    """
    global _template_engine

    if _template_engine is None:
        _template_engine = TemplateEngine()

    return _template_engine


# Export engine
__all__ = [
    "TemplateEngine",
    "TemplateRenderingError",
    "VariableValidationError",
    "get_template_engine",
]
