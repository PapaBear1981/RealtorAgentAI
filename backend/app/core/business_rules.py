"""
Business rules and validation engine for contracts.

This module provides comprehensive business rule processing,
data validation, compliance checking, and rule-based automation
for contract generation and management.
"""

import logging
import re
import json
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, Any, List, Optional, Union, Callable
from enum import Enum

from ..models.template import TemplateVariable, VariableType

logger = logging.getLogger(__name__)


class RuleSeverity(str, Enum):
    """Rule violation severity levels."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class RuleType(str, Enum):
    """Business rule types."""
    VALIDATION = "validation"
    CALCULATION = "calculation"
    CONDITIONAL = "conditional"
    COMPLIANCE = "compliance"
    TRANSFORMATION = "transformation"


class BusinessRuleError(Exception):
    """Exception raised during business rule processing."""
    pass


class ValidationError(Exception):
    """Exception raised during data validation."""
    pass


class BusinessRuleEngine:
    """
    Comprehensive business rule engine for contract processing.
    
    Provides rule-based validation, calculations, conditional logic,
    compliance checking, and data transformation capabilities.
    """
    
    def __init__(self):
        """Initialize business rule engine."""
        self.built_in_functions = self._register_built_in_functions()
        self.validation_rules = self._register_validation_rules()
        self.compliance_rules = self._register_compliance_rules()
    
    def _register_built_in_functions(self) -> Dict[str, Callable]:
        """Register built-in functions for rule processing."""
        return {
            # Math functions
            'add': lambda a, b: float(a) + float(b),
            'subtract': lambda a, b: float(a) - float(b),
            'multiply': lambda a, b: float(a) * float(b),
            'divide': lambda a, b: float(a) / float(b) if float(b) != 0 else 0,
            'percentage': lambda value, total: (float(value) / float(total)) * 100 if float(total) != 0 else 0,
            'round': lambda value, decimals=2: round(float(value), int(decimals)),
            'min': lambda *args: min(float(x) for x in args),
            'max': lambda *args: max(float(x) for x in args),
            'abs': lambda value: abs(float(value)),
            
            # String functions
            'upper': lambda text: str(text).upper(),
            'lower': lambda text: str(text).lower(),
            'title': lambda text: str(text).title(),
            'trim': lambda text: str(text).strip(),
            'length': lambda text: len(str(text)),
            'substring': lambda text, start, end=None: str(text)[int(start):int(end) if end else None],
            'replace': lambda text, old, new: str(text).replace(str(old), str(new)),
            'contains': lambda text, substring: str(substring) in str(text),
            'starts_with': lambda text, prefix: str(text).startswith(str(prefix)),
            'ends_with': lambda text, suffix: str(text).endswith(str(suffix)),
            
            # Date functions
            'today': lambda: date.today(),
            'now': lambda: datetime.now(),
            'date_add_days': lambda date_val, days: self._parse_date(date_val) + timedelta(days=int(days)),
            'date_diff_days': lambda date1, date2: (self._parse_date(date2) - self._parse_date(date1)).days,
            'format_date': lambda date_val, format_str='%Y-%m-%d': self._parse_date(date_val).strftime(format_str),
            
            # Validation functions
            'is_email': lambda email: re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', str(email)) is not None,
            'is_phone': lambda phone: re.match(r'^[\+]?[1-9][\d]{0,15}$', re.sub(r'[^\d\+]', '', str(phone))) is not None,
            'is_number': lambda value: self._is_number(value),
            'is_positive': lambda value: self._is_number(value) and float(value) > 0,
            'is_not_empty': lambda value: value is not None and str(value).strip() != '',
            
            # Logical functions
            'if': lambda condition, true_val, false_val: true_val if condition else false_val,
            'and': lambda *args: all(args),
            'or': lambda *args: any(args),
            'not': lambda value: not value,
        }
    
    def _register_validation_rules(self) -> Dict[str, Dict[str, Any]]:
        """Register common validation rules."""
        return {
            'required_field': {
                'type': RuleType.VALIDATION,
                'severity': RuleSeverity.ERROR,
                'description': 'Field is required',
                'validator': lambda value: value is not None and str(value).strip() != ''
            },
            'email_format': {
                'type': RuleType.VALIDATION,
                'severity': RuleSeverity.ERROR,
                'description': 'Invalid email format',
                'validator': lambda value: self.built_in_functions['is_email'](value) if value else True
            },
            'phone_format': {
                'type': RuleType.VALIDATION,
                'severity': RuleSeverity.WARNING,
                'description': 'Invalid phone format',
                'validator': lambda value: self.built_in_functions['is_phone'](value) if value else True
            },
            'positive_number': {
                'type': RuleType.VALIDATION,
                'severity': RuleSeverity.ERROR,
                'description': 'Value must be a positive number',
                'validator': lambda value: self.built_in_functions['is_positive'](value) if value else True
            },
            'future_date': {
                'type': RuleType.VALIDATION,
                'severity': RuleSeverity.WARNING,
                'description': 'Date should be in the future',
                'validator': lambda value: self._parse_date(value) > date.today() if value else True
            },
            'past_date': {
                'type': RuleType.VALIDATION,
                'severity': RuleSeverity.WARNING,
                'description': 'Date should be in the past',
                'validator': lambda value: self._parse_date(value) < date.today() if value else True
            }
        }
    
    def _register_compliance_rules(self) -> Dict[str, Dict[str, Any]]:
        """Register compliance rules for real estate contracts."""
        return {
            'disclosure_required': {
                'type': RuleType.COMPLIANCE,
                'severity': RuleSeverity.ERROR,
                'description': 'Property disclosure is required',
                'rule': 'property_type in ["residential", "commercial"] and disclosure_provided == true'
            },
            'earnest_money_limit': {
                'type': RuleType.COMPLIANCE,
                'severity': RuleSeverity.WARNING,
                'description': 'Earnest money exceeds recommended limit',
                'rule': 'earnest_money <= (purchase_price * 0.05)'
            },
            'inspection_period': {
                'type': RuleType.COMPLIANCE,
                'severity': RuleSeverity.INFO,
                'description': 'Inspection period should be reasonable',
                'rule': 'inspection_days >= 7 and inspection_days <= 30'
            },
            'financing_contingency': {
                'type': RuleType.COMPLIANCE,
                'severity': RuleSeverity.WARNING,
                'description': 'Financing contingency period may be insufficient',
                'rule': 'financing_days >= 21'
            }
        }
    
    async def process_business_rules(
        self,
        variables: Dict[str, Any],
        rules: Dict[str, Any],
        variable_definitions: Optional[List[TemplateVariable]] = None
    ) -> Dict[str, Any]:
        """
        Process business rules against variables.
        
        Args:
            variables: Variable values to process
            rules: Business rules configuration
            variable_definitions: Variable definitions for validation
            
        Returns:
            Dict: Processing results with updated variables and validation
        """
        try:
            results = {
                'variables': variables.copy(),
                'validation_results': {
                    'is_valid': True,
                    'errors': [],
                    'warnings': [],
                    'info': []
                },
                'applied_rules': [],
                'calculations_performed': [],
                'transformations_applied': []
            }
            
            # Apply validation rules
            if variable_definitions:
                validation_results = await self._apply_validation_rules(
                    results['variables'], 
                    variable_definitions
                )
                results['validation_results'] = validation_results
            
            # Apply business rules
            if rules:
                # Process calculated fields
                if 'calculated_fields' in rules:
                    calc_results = await self._apply_calculated_fields(
                        results['variables'], 
                        rules['calculated_fields']
                    )
                    results['variables'].update(calc_results['variables'])
                    results['calculations_performed'].extend(calc_results['calculations'])
                
                # Process conditional logic
                if 'conditional_logic' in rules:
                    cond_results = await self._apply_conditional_logic(
                        results['variables'], 
                        rules['conditional_logic']
                    )
                    results['variables'].update(cond_results['variables'])
                    results['applied_rules'].extend(cond_results['rules_applied'])
                
                # Process transformations
                if 'transformations' in rules:
                    trans_results = await self._apply_transformations(
                        results['variables'], 
                        rules['transformations']
                    )
                    results['variables'].update(trans_results['variables'])
                    results['transformations_applied'].extend(trans_results['transformations'])
                
                # Process compliance rules
                if 'compliance_rules' in rules:
                    compliance_results = await self._apply_compliance_rules(
                        results['variables'], 
                        rules['compliance_rules']
                    )
                    # Merge compliance results into validation results
                    for severity in ['errors', 'warnings', 'info']:
                        results['validation_results'][severity].extend(
                            compliance_results.get(severity, [])
                        )
            
            # Update overall validation status
            results['validation_results']['is_valid'] = len(results['validation_results']['errors']) == 0
            
            return results
            
        except Exception as e:
            logger.error(f"Business rule processing failed: {e}")
            raise BusinessRuleError(f"Rule processing failed: {str(e)}")
    
    async def _apply_validation_rules(
        self,
        variables: Dict[str, Any],
        variable_definitions: List[TemplateVariable]
    ) -> Dict[str, Any]:
        """Apply validation rules to variables."""
        results = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'info': []
        }
        
        for var_def in variable_definitions:
            var_name = var_def.name
            var_value = variables.get(var_name)
            
            # Check required fields
            if var_def.required and (var_value is None or str(var_value).strip() == ''):
                results['errors'].append(f"Required field '{var_def.label or var_name}' is missing")
                continue
            
            if var_value is None:
                continue
            
            # Type-specific validation
            try:
                if var_def.variable_type == VariableType.EMAIL:
                    if not self.built_in_functions['is_email'](var_value):
                        results['errors'].append(f"Invalid email format for '{var_def.label or var_name}'")
                
                elif var_def.variable_type == VariableType.PHONE:
                    if not self.built_in_functions['is_phone'](var_value):
                        results['warnings'].append(f"Invalid phone format for '{var_def.label or var_name}'")
                
                elif var_def.variable_type == VariableType.NUMBER:
                    if not self.built_in_functions['is_number'](var_value):
                        results['errors'].append(f"Invalid number format for '{var_def.label or var_name}'")
                    else:
                        num_value = float(var_value)
                        if var_def.min_value is not None and num_value < var_def.min_value:
                            results['errors'].append(f"'{var_def.label or var_name}' must be at least {var_def.min_value}")
                        if var_def.max_value is not None and num_value > var_def.max_value:
                            results['errors'].append(f"'{var_def.label or var_name}' must be at most {var_def.max_value}")
                
                elif var_def.variable_type == VariableType.CURRENCY:
                    if not self.built_in_functions['is_positive'](var_value):
                        results['errors'].append(f"'{var_def.label or var_name}' must be a positive amount")
                
                elif var_def.variable_type == VariableType.CHOICE:
                    if var_def.choices and var_value not in var_def.choices:
                        results['errors'].append(f"'{var_def.label or var_name}' must be one of: {', '.join(var_def.choices)}")
                
                # Pattern validation
                if var_def.pattern and isinstance(var_value, str):
                    if not re.match(var_def.pattern, var_value):
                        results['errors'].append(f"'{var_def.label or var_name}' does not match required format")
                
                # Length validation
                if var_def.variable_type == VariableType.STRING:
                    str_value = str(var_value)
                    if var_def.min_length and len(str_value) < var_def.min_length:
                        results['errors'].append(f"'{var_def.label or var_name}' must be at least {var_def.min_length} characters")
                    if var_def.max_length and len(str_value) > var_def.max_length:
                        results['errors'].append(f"'{var_def.label or var_name}' must be at most {var_def.max_length} characters")
                
            except Exception as e:
                results['warnings'].append(f"Validation error for '{var_def.label or var_name}': {str(e)}")
        
        results['is_valid'] = len(results['errors']) == 0
        return results
    
    async def _apply_calculated_fields(
        self,
        variables: Dict[str, Any],
        calculated_fields: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply calculated field rules."""
        results = {
            'variables': {},
            'calculations': []
        }
        
        for field_name, formula in calculated_fields.items():
            try:
                if isinstance(formula, str):
                    # Simple formula evaluation
                    calculated_value = self._evaluate_formula(formula, variables)
                    results['variables'][field_name] = calculated_value
                    results['calculations'].append({
                        'field': field_name,
                        'formula': formula,
                        'result': calculated_value
                    })
                elif isinstance(formula, dict):
                    # Complex calculation with conditions
                    if 'formula' in formula:
                        calculated_value = self._evaluate_formula(formula['formula'], variables)
                        results['variables'][field_name] = calculated_value
                        results['calculations'].append({
                            'field': field_name,
                            'formula': formula['formula'],
                            'result': calculated_value,
                            'conditions': formula.get('conditions')
                        })
                        
            except Exception as e:
                logger.warning(f"Calculation failed for field {field_name}: {e}")
        
        return results
    
    async def _apply_conditional_logic(
        self,
        variables: Dict[str, Any],
        conditional_rules: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Apply conditional logic rules."""
        results = {
            'variables': {},
            'rules_applied': []
        }
        
        for rule in conditional_rules:
            try:
                condition = rule.get('if')
                then_actions = rule.get('then', [])
                else_actions = rule.get('else', [])
                
                if self._evaluate_condition(condition, variables):
                    # Apply then actions
                    for action in then_actions:
                        self._apply_action(action, variables, results['variables'])
                    results['rules_applied'].append({
                        'condition': condition,
                        'branch': 'then',
                        'actions_applied': len(then_actions)
                    })
                else:
                    # Apply else actions
                    for action in else_actions:
                        self._apply_action(action, variables, results['variables'])
                    results['rules_applied'].append({
                        'condition': condition,
                        'branch': 'else',
                        'actions_applied': len(else_actions)
                    })
                    
            except Exception as e:
                logger.warning(f"Conditional logic error: {e}")
        
        return results
    
    async def _apply_transformations(
        self,
        variables: Dict[str, Any],
        transformations: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply data transformations."""
        results = {
            'variables': {},
            'transformations': []
        }
        
        for field_name, transformation in transformations.items():
            try:
                if field_name in variables:
                    original_value = variables[field_name]
                    transformed_value = self._apply_transformation(original_value, transformation)
                    results['variables'][field_name] = transformed_value
                    results['transformations'].append({
                        'field': field_name,
                        'transformation': transformation,
                        'original_value': original_value,
                        'transformed_value': transformed_value
                    })
                    
            except Exception as e:
                logger.warning(f"Transformation failed for field {field_name}: {e}")
        
        return results
    
    async def _apply_compliance_rules(
        self,
        variables: Dict[str, Any],
        compliance_rules: List[str]
    ) -> Dict[str, Any]:
        """Apply compliance rules."""
        results = {
            'errors': [],
            'warnings': [],
            'info': []
        }
        
        for rule_name in compliance_rules:
            if rule_name in self.compliance_rules:
                rule_config = self.compliance_rules[rule_name]
                try:
                    if not self._evaluate_condition(rule_config['rule'], variables):
                        severity = rule_config['severity']
                        message = rule_config['description']
                        
                        if severity == RuleSeverity.ERROR:
                            results['errors'].append(f"Compliance violation: {message}")
                        elif severity == RuleSeverity.WARNING:
                            results['warnings'].append(f"Compliance warning: {message}")
                        else:
                            results['info'].append(f"Compliance info: {message}")
                            
                except Exception as e:
                    logger.warning(f"Compliance rule evaluation failed for {rule_name}: {e}")
        
        return results
    
    def _evaluate_formula(self, formula: str, variables: Dict[str, Any]) -> Any:
        """Evaluate a formula expression."""
        try:
            # Simple formula evaluation with variable substitution
            expression = formula
            
            # Replace variable names with values
            for var_name, var_value in variables.items():
                if var_name in expression:
                    # Handle different value types
                    if isinstance(var_value, str):
                        expression = expression.replace(var_name, f'"{var_value}"')
                    else:
                        expression = expression.replace(var_name, str(var_value))
            
            # Replace function calls
            for func_name, func in self.built_in_functions.items():
                if func_name in expression:
                    # Simple function replacement (extend as needed)
                    pass
            
            # Evaluate simple numeric expressions
            if all(c in '0123456789+-*/.() ' for c in expression):
                return eval(expression, {"__builtins__": {}}, {})
            
            return expression
            
        except Exception as e:
            logger.warning(f"Formula evaluation failed: {e}")
            return formula
    
    def _evaluate_condition(self, condition: Union[str, Dict[str, Any]], variables: Dict[str, Any]) -> bool:
        """Evaluate a condition expression."""
        try:
            if isinstance(condition, str):
                # Simple string condition
                return self._evaluate_string_condition(condition, variables)
            elif isinstance(condition, dict):
                # Structured condition
                return self._evaluate_dict_condition(condition, variables)
            else:
                return bool(condition)
                
        except Exception as e:
            logger.warning(f"Condition evaluation failed: {e}")
            return False
    
    def _evaluate_string_condition(self, condition: str, variables: Dict[str, Any]) -> bool:
        """Evaluate string-based condition."""
        # Replace variables in condition
        expression = condition
        for var_name, var_value in variables.items():
            if var_name in expression:
                if isinstance(var_value, str):
                    expression = expression.replace(var_name, f'"{var_value}"')
                else:
                    expression = expression.replace(var_name, str(var_value))
        
        # Simple boolean expression evaluation
        try:
            # Only allow safe operations
            allowed_chars = set('0123456789+-*/.()=<>!& |"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_ ')
            if all(c in allowed_chars for c in expression):
                # Replace operators
                expression = expression.replace(' and ', ' and ')
                expression = expression.replace(' or ', ' or ')
                expression = expression.replace('==', '==')
                expression = expression.replace('!=', '!=')
                expression = expression.replace('<=', '<=')
                expression = expression.replace('>=', '>=')
                
                return eval(expression, {"__builtins__": {}}, {})
        except:
            pass
        
        return False
    
    def _evaluate_dict_condition(self, condition: Dict[str, Any], variables: Dict[str, Any]) -> bool:
        """Evaluate dictionary-based condition."""
        field = condition.get('field')
        operator = condition.get('operator')
        value = condition.get('value')
        
        if field not in variables:
            return False
        
        var_value = variables[field]
        
        if operator == 'equals':
            return var_value == value
        elif operator == 'not_equals':
            return var_value != value
        elif operator == 'greater_than':
            return float(var_value) > float(value)
        elif operator == 'less_than':
            return float(var_value) < float(value)
        elif operator == 'greater_equal':
            return float(var_value) >= float(value)
        elif operator == 'less_equal':
            return float(var_value) <= float(value)
        elif operator == 'contains':
            return str(value) in str(var_value)
        elif operator == 'starts_with':
            return str(var_value).startswith(str(value))
        elif operator == 'ends_with':
            return str(var_value).endswith(str(value))
        elif operator == 'is_empty':
            return not var_value or str(var_value).strip() == ''
        elif operator == 'is_not_empty':
            return var_value and str(var_value).strip() != ''
        
        return False
    
    def _apply_action(self, action: Dict[str, Any], variables: Dict[str, Any], results: Dict[str, Any]):
        """Apply a rule action."""
        action_type = action.get('type')
        
        if action_type == 'set_value':
            field = action.get('field')
            value = action.get('value')
            if field:
                results[field] = value
        
        elif action_type == 'calculate':
            field = action.get('field')
            formula = action.get('formula')
            if field and formula:
                results[field] = self._evaluate_formula(formula, variables)
        
        elif action_type == 'transform':
            field = action.get('field')
            transformation = action.get('transformation')
            if field and field in variables:
                results[field] = self._apply_transformation(variables[field], transformation)
    
    def _apply_transformation(self, value: Any, transformation: Union[str, Dict[str, Any]]) -> Any:
        """Apply a data transformation."""
        if isinstance(transformation, str):
            # Simple transformation
            if transformation == 'upper':
                return str(value).upper()
            elif transformation == 'lower':
                return str(value).lower()
            elif transformation == 'title':
                return str(value).title()
            elif transformation == 'trim':
                return str(value).strip()
        
        elif isinstance(transformation, dict):
            # Complex transformation
            transform_type = transformation.get('type')
            
            if transform_type == 'format':
                format_string = transformation.get('format')
                if format_string:
                    return format_string.format(value)
            
            elif transform_type == 'replace':
                old_value = transformation.get('old')
                new_value = transformation.get('new')
                if old_value is not None and new_value is not None:
                    return str(value).replace(str(old_value), str(new_value))
        
        return value
    
    def _parse_date(self, date_value: Any) -> date:
        """Parse date from various formats."""
        if isinstance(date_value, date):
            return date_value
        elif isinstance(date_value, datetime):
            return date_value.date()
        elif isinstance(date_value, str):
            try:
                return datetime.fromisoformat(date_value.replace('Z', '+00:00')).date()
            except:
                try:
                    return datetime.strptime(date_value, '%Y-%m-%d').date()
                except:
                    return date.today()
        else:
            return date.today()
    
    def _is_number(self, value: Any) -> bool:
        """Check if value is a number."""
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False


# Global business rule engine instance
_business_rule_engine: Optional[BusinessRuleEngine] = None


def get_business_rule_engine() -> BusinessRuleEngine:
    """
    Get global business rule engine instance.
    
    Returns:
        BusinessRuleEngine: Configured business rule engine
    """
    global _business_rule_engine
    
    if _business_rule_engine is None:
        _business_rule_engine = BusinessRuleEngine()
    
    return _business_rule_engine


# Export engine
__all__ = [
    "BusinessRuleEngine",
    "BusinessRuleError",
    "ValidationError",
    "RuleSeverity",
    "RuleType",
    "get_business_rule_engine",
]
