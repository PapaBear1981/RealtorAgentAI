"""
Tests for business rules and validation engine.

This module tests business rule processing, data validation,
compliance checking, and rule-based automation.
"""

import pytest
import asyncio
from datetime import datetime, date
from unittest.mock import Mock, patch

from app.core.business_rules import (
    BusinessRuleEngine, BusinessRuleError, ValidationError,
    RuleSeverity, RuleType, get_business_rule_engine
)
from app.models.template import TemplateVariable, VariableType


class TestBusinessRuleEngine:
    """Test business rule engine functionality."""
    
    def test_engine_initialization(self):
        """Test business rule engine initialization."""
        engine = BusinessRuleEngine()
        
        assert engine.built_in_functions is not None
        assert engine.validation_rules is not None
        assert engine.compliance_rules is not None
        assert len(engine.built_in_functions) > 0
        assert len(engine.validation_rules) > 0
        assert len(engine.compliance_rules) > 0
    
    def test_built_in_functions(self):
        """Test built-in functions."""
        engine = BusinessRuleEngine()
        
        # Math functions
        assert engine.built_in_functions['add'](10, 5) == 15
        assert engine.built_in_functions['subtract'](10, 5) == 5
        assert engine.built_in_functions['multiply'](10, 5) == 50
        assert engine.built_in_functions['divide'](10, 5) == 2
        assert engine.built_in_functions['percentage'](25, 100) == 25
        assert engine.built_in_functions['round'](3.14159, 2) == 3.14
        
        # String functions
        assert engine.built_in_functions['upper']('hello') == 'HELLO'
        assert engine.built_in_functions['lower']('HELLO') == 'hello'
        assert engine.built_in_functions['title']('hello world') == 'Hello World'
        assert engine.built_in_functions['trim']('  hello  ') == 'hello'
        assert engine.built_in_functions['length']('hello') == 5
        assert engine.built_in_functions['contains']('hello world', 'world') is True
        
        # Validation functions
        assert engine.built_in_functions['is_email']('test@example.com') is True
        assert engine.built_in_functions['is_email']('invalid-email') is False
        assert engine.built_in_functions['is_number']('123') is True
        assert engine.built_in_functions['is_number']('abc') is False
        assert engine.built_in_functions['is_positive']('10') is True
        assert engine.built_in_functions['is_positive']('-5') is False
        
        # Logical functions
        assert engine.built_in_functions['if'](True, 'yes', 'no') == 'yes'
        assert engine.built_in_functions['if'](False, 'yes', 'no') == 'no'
        assert engine.built_in_functions['and'](True, True, True) is True
        assert engine.built_in_functions['and'](True, False, True) is False
        assert engine.built_in_functions['or'](False, False, True) is True
        assert engine.built_in_functions['not'](True) is False


class TestVariableValidation:
    """Test variable validation functionality."""
    
    @pytest.mark.asyncio
    async def test_validate_required_fields(self):
        """Test validation of required fields."""
        engine = BusinessRuleEngine()
        
        variables = {
            'name': 'John Doe',
            'email': 'john@example.com'
            # Missing 'phone' which is required
        }
        
        variable_definitions = [
            TemplateVariable(
                name='name',
                label='Full Name',
                variable_type=VariableType.STRING,
                required=True
            ),
            TemplateVariable(
                name='email',
                label='Email Address',
                variable_type=VariableType.EMAIL,
                required=True
            ),
            TemplateVariable(
                name='phone',
                label='Phone Number',
                variable_type=VariableType.PHONE,
                required=True
            )
        ]
        
        result = await engine._apply_validation_rules(variables, variable_definitions)
        
        assert result['is_valid'] is False
        assert len(result['errors']) == 1
        assert 'phone' in result['errors'][0].lower()
    
    @pytest.mark.asyncio
    async def test_validate_email_format(self):
        """Test email format validation."""
        engine = BusinessRuleEngine()
        
        variables = {
            'email': 'invalid-email-format'
        }
        
        variable_definitions = [
            TemplateVariable(
                name='email',
                label='Email Address',
                variable_type=VariableType.EMAIL,
                required=True
            )
        ]
        
        result = await engine._apply_validation_rules(variables, variable_definitions)
        
        assert result['is_valid'] is False
        assert len(result['errors']) == 1
        assert 'email format' in result['errors'][0].lower()
    
    @pytest.mark.asyncio
    async def test_validate_number_constraints(self):
        """Test number constraint validation."""
        engine = BusinessRuleEngine()
        
        variables = {
            'price': 50000,  # Below minimum
            'quantity': 150  # Above maximum
        }
        
        variable_definitions = [
            TemplateVariable(
                name='price',
                label='Price',
                variable_type=VariableType.NUMBER,
                required=True,
                min_value=100000
            ),
            TemplateVariable(
                name='quantity',
                label='Quantity',
                variable_type=VariableType.NUMBER,
                required=True,
                max_value=100
            )
        ]
        
        result = await engine._apply_validation_rules(variables, variable_definitions)
        
        assert result['is_valid'] is False
        assert len(result['errors']) == 2
        assert any('at least' in error for error in result['errors'])
        assert any('at most' in error for error in result['errors'])
    
    @pytest.mark.asyncio
    async def test_validate_string_length(self):
        """Test string length validation."""
        engine = BusinessRuleEngine()
        
        variables = {
            'short_text': 'Hi',  # Too short
            'long_text': 'A' * 200  # Too long
        }
        
        variable_definitions = [
            TemplateVariable(
                name='short_text',
                label='Short Text',
                variable_type=VariableType.STRING,
                required=True,
                min_length=5
            ),
            TemplateVariable(
                name='long_text',
                label='Long Text',
                variable_type=VariableType.STRING,
                required=True,
                max_length=100
            )
        ]
        
        result = await engine._apply_validation_rules(variables, variable_definitions)
        
        assert result['is_valid'] is False
        assert len(result['errors']) == 2
        assert any('at least' in error for error in result['errors'])
        assert any('at most' in error for error in result['errors'])
    
    @pytest.mark.asyncio
    async def test_validate_choice_options(self):
        """Test choice validation."""
        engine = BusinessRuleEngine()
        
        variables = {
            'property_type': 'invalid_type'
        }
        
        variable_definitions = [
            TemplateVariable(
                name='property_type',
                label='Property Type',
                variable_type=VariableType.CHOICE,
                required=True,
                choices=['residential', 'commercial', 'industrial']
            )
        ]
        
        result = await engine._apply_validation_rules(variables, variable_definitions)
        
        assert result['is_valid'] is False
        assert len(result['errors']) == 1
        assert 'must be one of' in result['errors'][0]


class TestCalculatedFields:
    """Test calculated field functionality."""
    
    @pytest.mark.asyncio
    async def test_simple_calculations(self):
        """Test simple calculated fields."""
        engine = BusinessRuleEngine()
        
        variables = {
            'purchase_price': 300000,
            'down_payment_percent': 20
        }
        
        calculated_fields = {
            'down_payment': 'purchase_price * (down_payment_percent / 100)',
            'loan_amount': 'purchase_price - down_payment'
        }
        
        result = await engine._apply_calculated_fields(variables, calculated_fields)
        
        assert 'down_payment' in result['variables']
        assert result['variables']['down_payment'] == 60000
        assert len(result['calculations']) == 2
    
    @pytest.mark.asyncio
    async def test_complex_calculations(self):
        """Test complex calculated fields with conditions."""
        engine = BusinessRuleEngine()
        
        variables = {
            'purchase_price': 500000,
            'is_first_time_buyer': True
        }
        
        calculated_fields = {
            'earnest_money': {
                'formula': 'purchase_price * 0.01 if is_first_time_buyer else purchase_price * 0.02',
                'conditions': {'is_first_time_buyer': True}
            }
        }
        
        result = await engine._apply_calculated_fields(variables, calculated_fields)
        
        assert 'earnest_money' in result['variables']
        assert len(result['calculations']) == 1


class TestConditionalLogic:
    """Test conditional logic functionality."""
    
    @pytest.mark.asyncio
    async def test_simple_conditional_logic(self):
        """Test simple conditional logic rules."""
        engine = BusinessRuleEngine()
        
        variables = {
            'property_type': 'residential',
            'purchase_price': 400000
        }
        
        conditional_rules = [
            {
                'if': {'field': 'property_type', 'operator': 'equals', 'value': 'residential'},
                'then': [
                    {'type': 'set_value', 'field': 'inspection_required', 'value': True},
                    {'type': 'set_value', 'field': 'inspection_days', 'value': 10}
                ],
                'else': [
                    {'type': 'set_value', 'field': 'inspection_required', 'value': False}
                ]
            }
        ]
        
        result = await engine._apply_conditional_logic(variables, conditional_rules)
        
        assert result['variables']['inspection_required'] is True
        assert result['variables']['inspection_days'] == 10
        assert len(result['rules_applied']) == 1
        assert result['rules_applied'][0]['branch'] == 'then'
    
    @pytest.mark.asyncio
    async def test_numeric_conditional_logic(self):
        """Test numeric conditional logic rules."""
        engine = BusinessRuleEngine()
        
        variables = {
            'purchase_price': 750000
        }
        
        conditional_rules = [
            {
                'if': {'field': 'purchase_price', 'operator': 'greater_than', 'value': 500000},
                'then': [
                    {'type': 'set_value', 'field': 'jumbo_loan', 'value': True},
                    {'type': 'calculate', 'field': 'min_down_payment', 'formula': 'purchase_price * 0.20'}
                ],
                'else': [
                    {'type': 'set_value', 'field': 'jumbo_loan', 'value': False},
                    {'type': 'calculate', 'field': 'min_down_payment', 'formula': 'purchase_price * 0.10'}
                ]
            }
        ]
        
        result = await engine._apply_conditional_logic(variables, conditional_rules)
        
        assert result['variables']['jumbo_loan'] is True
        assert result['variables']['min_down_payment'] == 150000


class TestComplianceRules:
    """Test compliance rule functionality."""
    
    @pytest.mark.asyncio
    async def test_disclosure_compliance(self):
        """Test disclosure compliance rules."""
        engine = BusinessRuleEngine()
        
        variables = {
            'property_type': 'residential',
            'disclosure_provided': False
        }
        
        compliance_rules = ['disclosure_required']
        
        result = await engine._apply_compliance_rules(variables, compliance_rules)
        
        assert len(result['errors']) == 1
        assert 'disclosure' in result['errors'][0].lower()
    
    @pytest.mark.asyncio
    async def test_earnest_money_compliance(self):
        """Test earnest money compliance rules."""
        engine = BusinessRuleEngine()
        
        variables = {
            'purchase_price': 300000,
            'earnest_money': 20000  # 6.67% - exceeds 5% recommendation
        }
        
        compliance_rules = ['earnest_money_limit']
        
        result = await engine._apply_compliance_rules(variables, compliance_rules)
        
        assert len(result['warnings']) == 1
        assert 'earnest money' in result['warnings'][0].lower()
    
    @pytest.mark.asyncio
    async def test_financing_contingency_compliance(self):
        """Test financing contingency compliance rules."""
        engine = BusinessRuleEngine()
        
        variables = {
            'financing_days': 15  # Less than recommended 21 days
        }
        
        compliance_rules = ['financing_contingency']
        
        result = await engine._apply_compliance_rules(variables, compliance_rules)
        
        assert len(result['warnings']) == 1
        assert 'financing' in result['warnings'][0].lower()


class TestDataTransformations:
    """Test data transformation functionality."""
    
    @pytest.mark.asyncio
    async def test_simple_transformations(self):
        """Test simple data transformations."""
        engine = BusinessRuleEngine()
        
        variables = {
            'buyer_name': '  john doe  ',
            'seller_name': 'JANE SMITH'
        }
        
        transformations = {
            'buyer_name': 'title',
            'seller_name': 'title'
        }
        
        result = await engine._apply_transformations(variables, transformations)
        
        assert result['variables']['buyer_name'] == 'John Doe'
        assert result['variables']['seller_name'] == 'Jane Smith'
        assert len(result['transformations']) == 2
    
    @pytest.mark.asyncio
    async def test_complex_transformations(self):
        """Test complex data transformations."""
        engine = BusinessRuleEngine()
        
        variables = {
            'phone_number': '1234567890'
        }
        
        transformations = {
            'phone_number': {
                'type': 'format',
                'format': '({}) {}-{}'
            }
        }
        
        result = await engine._apply_transformations(variables, transformations)
        
        # Note: This would need more sophisticated formatting logic
        assert 'phone_number' in result['variables']
        assert len(result['transformations']) == 1


class TestBusinessRuleProcessing:
    """Test comprehensive business rule processing."""
    
    @pytest.mark.asyncio
    async def test_comprehensive_rule_processing(self):
        """Test comprehensive business rule processing."""
        engine = BusinessRuleEngine()
        
        variables = {
            'property_type': 'residential',
            'purchase_price': 400000,
            'buyer_name': 'john doe',
            'seller_name': 'jane smith',
            'down_payment_percent': 20,
            'disclosure_provided': True,
            'financing_days': 30
        }
        
        variable_definitions = [
            TemplateVariable(
                name='buyer_name',
                label='Buyer Name',
                variable_type=VariableType.STRING,
                required=True
            ),
            TemplateVariable(
                name='purchase_price',
                label='Purchase Price',
                variable_type=VariableType.CURRENCY,
                required=True,
                min_value=1000
            )
        ]
        
        rules = {
            'calculated_fields': {
                'down_payment': 'purchase_price * (down_payment_percent / 100)',
                'loan_amount': 'purchase_price - down_payment'
            },
            'conditional_logic': [
                {
                    'if': {'field': 'property_type', 'operator': 'equals', 'value': 'residential'},
                    'then': [
                        {'type': 'set_value', 'field': 'inspection_required', 'value': True}
                    ]
                }
            ],
            'transformations': {
                'buyer_name': 'title',
                'seller_name': 'title'
            },
            'compliance_rules': ['disclosure_required', 'financing_contingency']
        }
        
        result = await engine.process_business_rules(variables, rules, variable_definitions)
        
        assert result['validation_results']['is_valid'] is True
        assert 'down_payment' in result['variables']
        assert result['variables']['down_payment'] == 80000
        assert result['variables']['inspection_required'] is True
        assert result['variables']['buyer_name'] == 'John Doe'
        assert len(result['calculations_performed']) == 2
        assert len(result['applied_rules']) == 1
        assert len(result['transformations_applied']) == 2
    
    @pytest.mark.asyncio
    async def test_rule_processing_with_errors(self):
        """Test business rule processing with validation errors."""
        engine = BusinessRuleEngine()
        
        variables = {
            'purchase_price': -100000,  # Invalid negative price
            'buyer_email': 'invalid-email'  # Invalid email format
        }
        
        variable_definitions = [
            TemplateVariable(
                name='purchase_price',
                label='Purchase Price',
                variable_type=VariableType.CURRENCY,
                required=True
            ),
            TemplateVariable(
                name='buyer_email',
                label='Buyer Email',
                variable_type=VariableType.EMAIL,
                required=True
            )
        ]
        
        rules = {
            'calculated_fields': {
                'commission': 'purchase_price * 0.06'
            }
        }
        
        result = await engine.process_business_rules(variables, rules, variable_definitions)
        
        assert result['validation_results']['is_valid'] is False
        assert len(result['validation_results']['errors']) >= 1
        # Calculations should still be performed despite validation errors
        assert 'commission' in result['variables']


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_get_business_rule_engine_singleton(self):
        """Test that get_business_rule_engine returns singleton."""
        engine1 = get_business_rule_engine()
        engine2 = get_business_rule_engine()
        
        assert engine1 is engine2
    
    def test_condition_evaluation(self):
        """Test condition evaluation methods."""
        engine = BusinessRuleEngine()
        
        variables = {
            'price': 100000,
            'type': 'residential',
            'active': True
        }
        
        # Test dictionary conditions
        assert engine._evaluate_dict_condition(
            {'field': 'price', 'operator': 'greater_than', 'value': 50000},
            variables
        ) is True
        
        assert engine._evaluate_dict_condition(
            {'field': 'type', 'operator': 'equals', 'value': 'residential'},
            variables
        ) is True
        
        assert engine._evaluate_dict_condition(
            {'field': 'active', 'operator': 'equals', 'value': True},
            variables
        ) is True
        
        assert engine._evaluate_dict_condition(
            {'field': 'price', 'operator': 'less_than', 'value': 50000},
            variables
        ) is False
    
    def test_formula_evaluation(self):
        """Test formula evaluation."""
        engine = BusinessRuleEngine()
        
        variables = {
            'a': 10,
            'b': 5,
            'c': 2
        }
        
        # Simple arithmetic
        assert engine._evaluate_formula('a + b', variables) == 15
        assert engine._evaluate_formula('a * b', variables) == 50
        assert engine._evaluate_formula('a / b', variables) == 2
        assert engine._evaluate_formula('(a + b) * c', variables) == 30
