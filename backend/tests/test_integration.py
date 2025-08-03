"""
Integration tests for Phase 6: Core Business Logic implementation.

Tests the complete workflow from contract creation through template management,
version control, and business rules processing.
"""

import pytest
import asyncio
from datetime import datetime
from sqlmodel import Session, create_engine, SQLModel
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import get_session
from app.services.contract_service import ContractService
from app.services.template_service import TemplateService
from app.services.version_control_service import VersionControlService
from app.core.template_engine import TemplateEngine
from app.core.business_rules import BusinessRuleEngine
from app.models.user import User
from app.models.deal import Deal, DealCreate
from app.models.contract import Contract, ContractCreate
from app.models.template import (
    Template, TemplateCreate, TemplateStatus, TemplateType, 
    OutputFormat, TemplateVariable, VariableType
)


@pytest.fixture
def test_engine():
    """Create test database engine."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def test_session(test_engine):
    """Create test database session."""
    with Session(test_engine) as session:
        yield session


@pytest.fixture
def test_user(test_session):
    """Create test user."""
    user = User(
        email="integration@example.com",
        hashed_password="hashed_password",
        full_name="Integration Test User",
        role="admin",
        is_active=True
    )
    test_session.add(user)
    test_session.commit()
    test_session.refresh(user)
    return user


@pytest.fixture
def test_deal(test_session, test_user):
    """Create test deal."""
    deal_data = DealCreate(
        title="Integration Test Deal",
        status="active",
        property_address="456 Integration Ave",
        deal_value=250000.0
    )
    deal = Deal(**deal_data.dict(), owner_id=test_user.id)
    test_session.add(deal)
    test_session.commit()
    test_session.refresh(deal)
    return deal


class TestCompleteWorkflow:
    """Test complete contract management workflow."""

    @pytest.mark.asyncio
    async def test_end_to_end_contract_workflow(self, test_session, test_user, test_deal):
        """Test complete end-to-end contract workflow."""
        
        # Step 1: Create template with advanced features
        template_service = TemplateService()
        
        template_variables = [
            TemplateVariable(
                name="buyer_name",
                label="Buyer Name",
                variable_type=VariableType.TEXT,
                required=True,
                description="Name of the property buyer"
            ),
            TemplateVariable(
                name="seller_name",
                label="Seller Name", 
                variable_type=VariableType.TEXT,
                required=True,
                description="Name of the property seller"
            ),
            TemplateVariable(
                name="property_price",
                label="Property Price",
                variable_type=VariableType.CURRENCY,
                required=True,
                description="Purchase price of the property"
            ),
            TemplateVariable(
                name="closing_date",
                label="Closing Date",
                variable_type=VariableType.DATE,
                required=True,
                description="Date of property closing"
            )
        ]
        
        template_content = """
        <div class="contract-header">
            <h1>Real Estate Purchase Agreement</h1>
            <p>Date: {{ now().strftime('%Y-%m-%d') }}</p>
        </div>
        
        <div class="contract-body">
            <p>This agreement is between:</p>
            <ul>
                <li><strong>Buyer:</strong> {{ buyer_name }}</li>
                <li><strong>Seller:</strong> {{ seller_name }}</li>
            </ul>
            
            <p>Property Details:</p>
            <ul>
                <li><strong>Address:</strong> {{ property_address }}</li>
                <li><strong>Purchase Price:</strong> {{ property_price | currency }}</li>
                <li><strong>Closing Date:</strong> {{ closing_date | date_format }}</li>
            </ul>
            
            {% if property_price|float > 200000 %}
            <div class="high-value-notice">
                <p><strong>Notice:</strong> This is a high-value transaction requiring additional documentation.</p>
            </div>
            {% endif %}
        </div>
        
        <div class="signature-section">
            <p>Buyer Signature: ___________________________ Date: ___________</p>
            <p>Seller Signature: ___________________________ Date: ___________</p>
        </div>
        """
        
        business_rules = {
            "validation": [
                {
                    "id": "required_fields",
                    "condition": {"operator": "is_not_empty", "field": "buyer_name"},
                    "action": {"type": "validate", "message": "Buyer name is required"}
                }
            ],
            "calculation": [
                {
                    "id": "calculate_fees",
                    "condition": {"operator": "greater_than", "field": "property_price", "value": 100000},
                    "action": {
                        "type": "calculate",
                        "field": "closing_costs",
                        "formula": "property_price * 0.03"
                    }
                }
            ],
            "conditional": [
                {
                    "id": "high_value_requirements",
                    "condition": {"operator": "greater_than", "field": "property_price", "value": 200000},
                    "action": {
                        "type": "set_value",
                        "field": "requires_attorney_review",
                        "value": True
                    }
                }
            ]
        }
        
        template_data = TemplateCreate(
            name="Real Estate Purchase Agreement",
            version="1.0",
            template_type=TemplateType.CONTRACT,
            status=TemplateStatus.ACTIVE,
            html_content=template_content,
            variables=template_variables,
            business_rules=business_rules,
            description="Standard real estate purchase agreement template"
        )
        
        template = await template_service.create_template_with_inheritance(
            template_data, test_user, test_session
        )
        
        assert template.id is not None
        assert template.name == "Real Estate Purchase Agreement"
        
        # Step 2: Create contract with comprehensive validation
        contract_service = ContractService()
        
        contract_variables = {
            "buyer_name": "John Smith",
            "seller_name": "Jane Doe", 
            "property_price": 275000.0,
            "closing_date": "2024-03-15",
            "property_address": test_deal.property_address
        }
        
        contract_data = ContractCreate(
            deal_id=test_deal.id,
            template_id=template.id,
            title="Smith-Doe Purchase Agreement",
            status="draft",
            variables=contract_variables
        )
        
        contract = await contract_service.create_contract(contract_data, test_user, test_session)
        
        assert contract.id is not None
        assert contract.title == "Smith-Doe Purchase Agreement"
        
        # Step 3: Validate contract comprehensively
        validation_result = await contract_service.validate_contract_comprehensive(
            contract.id, test_user, test_session
        )
        
        assert validation_result["is_valid"] is True
        assert "validation_details" in validation_result
        
        # Step 4: Test version control
        version_service = VersionControlService()
        
        # Create initial version
        version1 = await version_service.create_version(
            "contract", contract.id, "Initial contract creation", test_user, test_session
        )
        
        assert version1.number == 1
        assert version1.is_current is True
        
        # Update contract and create new version
        updated_variables = contract_variables.copy()
        updated_variables["property_price"] = 280000.0
        
        contract_update = await contract_service.update_contract(
            contract.id,
            {"variables": updated_variables},
            test_user,
            test_session
        )
        
        version2 = await version_service.create_version(
            "contract", contract.id, "Updated property price", test_user, test_session
        )
        
        assert version2.number == 2
        
        # Test diff generation
        diff_result = await version_service.generate_diff(
            "contract", contract.id, version1.id, version2.id,
            test_user, test_session, "summary"
        )
        
        assert "diff" in diff_result
        assert diff_result["entity_type"] == "contract"
        
        # Step 5: Test advanced template rendering
        template_engine = TemplateEngine()
        
        render_result = await template_engine.render_template_advanced(
            template_content,
            updated_variables,
            template_variables,
            validate_variables=True,
            output_format=OutputFormat.HTML,
            enable_preview_mode=False,
            apply_business_rules=True,
            include_metadata=True
        )
        
        assert render_result["success"] is True
        assert "metadata" in render_result
        assert render_result["metadata"]["business_rules_applied"] is True
        
        # Step 6: Test business rules processing
        business_rule_engine = BusinessRuleEngine()
        
        rules_result = await business_rule_engine.process_business_rules(
            business_rules,
            updated_variables
        )
        
        assert rules_result["validation_results"]["is_valid"] is True
        assert len(rules_result["applied_rules"]) > 0
        
        # Verify high-value transaction rule was applied
        processed_variables = rules_result["variables"]
        assert processed_variables.get("requires_attorney_review") is True
        assert "closing_costs" in processed_variables
        
        # Step 7: Test contract statistics
        stats_result = await contract_service.get_contract_statistics(
            test_user, test_session
        )
        
        assert stats_result["total_contracts"] >= 1
        assert "status_distribution" in stats_result
        assert "template_usage" in stats_result
        
        # Step 8: Test version history and comparison
        history_result = await version_service.get_version_history(
            "contract", contract.id, test_user, test_session
        )
        
        assert history_result["total_count"] == 2
        assert len(history_result["versions"]) == 2
        
        # Test version comparison
        comparison_result = await version_service.compare_versions(
            "contract", contract.id, [version1.id, version2.id],
            test_user, test_session
        )
        
        assert len(comparison_result["versions"]) == 2
        assert len(comparison_result["comparison_matrix"]) == 1
        
        # Step 9: Test rollback functionality
        rollback_result = await version_service.rollback_to_version(
            "contract", contract.id, version1.id, test_user, test_session, True
        )
        
        assert rollback_result["target_version"]["id"] == version1.id
        assert rollback_result["backup_version_id"] is not None
        
        print("✅ Complete end-to-end workflow test passed!")
        print(f"   - Template created: {template.name}")
        print(f"   - Contract created: {contract.title}")
        print(f"   - Versions created: {history_result['total_count']}")
        print(f"   - Validation passed: {validation_result['is_valid']}")
        print(f"   - Business rules applied: {len(rules_result['applied_rules'])}")
        print(f"   - Rollback completed: {rollback_result['target_version']['number']}")

    @pytest.mark.asyncio
    async def test_template_inheritance_workflow(self, test_session, test_user):
        """Test template inheritance and composition workflow."""
        
        template_service = TemplateService()
        
        # Create base template
        base_template_data = TemplateCreate(
            name="Base Contract Template",
            version="1.0",
            template_type=TemplateType.CONTRACT,
            status=TemplateStatus.ACTIVE,
            html_content="<div class='base'>{{content}}</div>",
            description="Base template for all contracts"
        )
        
        base_template = await template_service.create_template_with_inheritance(
            base_template_data, test_user, test_session
        )
        
        # Create child template with inheritance
        child_template_data = TemplateCreate(
            name="Purchase Agreement Template",
            version="1.0",
            template_type=TemplateType.CONTRACT,
            status=TemplateStatus.ACTIVE,
            html_content="<div class='purchase'>{{buyer_name}} purchases from {{seller_name}}</div>",
            parent_template_id=base_template.id,
            description="Purchase agreement inheriting from base"
        )
        
        child_template = await template_service.create_template_with_inheritance(
            child_template_data, test_user, test_session,
            inherit_variables=True,
            inherit_rules=True,
            inherit_content=False
        )
        
        assert child_template.parent_template_id == base_template.id
        
        # Test template composition
        component_templates = [base_template]
        composition_rules = {
            "name": "Composed Contract Template",
            "composition_strategy": "append",
            "variable_merge_strategy": "merge",
            "rules_merge_strategy": "merge"
        }
        
        composed_template = await template_service.compose_template(
            base_template.id,
            [child_template.id],
            composition_rules,
            test_user,
            test_session
        )
        
        assert composed_template.name == "Composed Contract Template"
        
        print("✅ Template inheritance and composition workflow test passed!")
        print(f"   - Base template: {base_template.name}")
        print(f"   - Child template: {child_template.name}")
        print(f"   - Composed template: {composed_template.name}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
