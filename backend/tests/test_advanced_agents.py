"""
Integration Tests for Advanced AI Agents.

This module contains comprehensive integration tests for advanced agent capabilities
including multi-agent workflows, real estate domain specialization, and enterprise features.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from typing import Dict, Any

from fastapi.testclient import TestClient
from fastapi import status

from app.main import app
from app.services.advanced_workflow_orchestrator import (
    AdvancedWorkflowOrchestrator, WorkflowDefinition, WorkflowTask, TaskPriority, WorkflowStatus
)
from app.services.real_estate_knowledge_base import (
    RealEstateKnowledgeBase, PropertyType, TransactionType, Jurisdiction
)
from app.services.enterprise_integration import (
    EnterpriseIntegrationService, ComplianceFramework, AuditEventType
)
from app.services.agent_orchestrator import AgentRole
from app.models.user import User


class TestAdvancedWorkflowOrchestrator:
    """Test cases for advanced workflow orchestrator."""
    
    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance for testing."""
        return AdvancedWorkflowOrchestrator()
    
    @pytest.fixture
    def sample_workflow(self):
        """Create sample workflow definition."""
        return WorkflowDefinition(
            workflow_id="test_workflow",
            name="Test Workflow",
            description="Test workflow for unit testing",
            tasks=[
                WorkflowTask(
                    task_id="task1",
                    agent_role=AgentRole.DATA_EXTRACTION,
                    task_type="data_extraction",
                    description="Extract data from document",
                    input_data={"document_id": "test_doc"},
                    priority=TaskPriority.HIGH
                ),
                WorkflowTask(
                    task_id="task2",
                    agent_role=AgentRole.CONTRACT_GENERATOR,
                    task_type="contract_generation",
                    description="Generate contract",
                    input_data={},
                    dependencies=["task1"],
                    priority=TaskPriority.NORMAL
                )
            ]
        )
    
    @pytest.mark.asyncio
    async def test_workflow_registration(self, orchestrator, sample_workflow):
        """Test workflow template registration."""
        orchestrator.register_workflow_template(sample_workflow)
        
        assert sample_workflow.workflow_id in orchestrator.workflow_definitions
        assert orchestrator.workflow_definitions[sample_workflow.workflow_id] == sample_workflow
    
    @pytest.mark.asyncio
    async def test_workflow_execution_creation(self, orchestrator, sample_workflow):
        """Test workflow execution creation."""
        orchestrator.register_workflow_template(sample_workflow)
        
        execution = await orchestrator.create_workflow_execution(
            template_id=sample_workflow.workflow_id,
            input_data={"test_input": "value"},
            user_id="test_user"
        )
        
        assert execution.workflow_definition.workflow_id == sample_workflow.workflow_id
        assert execution.context["input_data"]["test_input"] == "value"
        assert execution.context["user_id"] == "test_user"
        assert execution.execution_id in orchestrator.active_workflows
    
    @pytest.mark.asyncio
    async def test_workflow_status_tracking(self, orchestrator, sample_workflow):
        """Test workflow status tracking."""
        orchestrator.register_workflow_template(sample_workflow)
        
        execution = await orchestrator.create_workflow_execution(
            template_id=sample_workflow.workflow_id,
            input_data={},
            user_id="test_user"
        )
        
        status = await orchestrator.get_workflow_status(execution.execution_id)
        
        assert status is not None
        assert status["execution_id"] == execution.execution_id
        assert "status" in status
        assert "progress" in status
        assert "total_tasks" in status
        assert status["total_tasks"] == 2
    
    @pytest.mark.asyncio
    async def test_workflow_pause_resume(self, orchestrator, sample_workflow):
        """Test workflow pause and resume functionality."""
        orchestrator.register_workflow_template(sample_workflow)
        
        execution = await orchestrator.create_workflow_execution(
            template_id=sample_workflow.workflow_id,
            input_data={},
            user_id="test_user"
        )
        
        # Start workflow
        await orchestrator.start_workflow_execution(execution.execution_id)
        assert execution.status == WorkflowStatus.RUNNING
        
        # Pause workflow
        success = await orchestrator.pause_workflow_execution(execution.execution_id)
        assert success
        assert execution.status == WorkflowStatus.PAUSED
        
        # Resume workflow
        success = await orchestrator.resume_workflow_execution(execution.execution_id)
        assert success
        assert execution.status == WorkflowStatus.RUNNING
    
    @pytest.mark.asyncio
    async def test_workflow_cancellation(self, orchestrator, sample_workflow):
        """Test workflow cancellation."""
        orchestrator.register_workflow_template(sample_workflow)
        
        execution = await orchestrator.create_workflow_execution(
            template_id=sample_workflow.workflow_id,
            input_data={},
            user_id="test_user"
        )
        
        success = await orchestrator.cancel_workflow_execution(execution.execution_id)
        assert success
        assert execution.status == WorkflowStatus.CANCELLED
        assert execution.completed_at is not None


class TestRealEstateKnowledgeBase:
    """Test cases for real estate knowledge base."""
    
    @pytest.fixture
    def knowledge_base(self):
        """Create knowledge base instance for testing."""
        return RealEstateKnowledgeBase()
    
    def test_legal_requirements_retrieval(self, knowledge_base):
        """Test legal requirements retrieval."""
        requirements = knowledge_base.get_legal_requirements(
            jurisdiction=Jurisdiction.US_CALIFORNIA,
            property_type=PropertyType.RESIDENTIAL_SINGLE_FAMILY,
            transaction_type=TransactionType.PURCHASE
        )
        
        assert len(requirements) > 0
        assert all(req.jurisdiction == Jurisdiction.US_CALIFORNIA for req in requirements)
        assert all(req.property_type == PropertyType.RESIDENTIAL_SINGLE_FAMILY for req in requirements)
        assert all(req.transaction_type == TransactionType.PURCHASE for req in requirements)
    
    def test_compliance_validation(self, knowledge_base):
        """Test compliance validation."""
        transaction_data = {
            "purchase_price": 500000,
            "financing_type": "conventional",
            "earnest_money": 10000,
            "earnest_money_percentage": 2.0
        }
        
        violations = knowledge_base.validate_compliance(
            jurisdiction=Jurisdiction.US_FEDERAL,
            transaction_data=transaction_data
        )
        
        # Should have no violations for valid data
        assert isinstance(violations, list)
    
    def test_compliance_validation_with_violations(self, knowledge_base):
        """Test compliance validation with violations."""
        transaction_data = {
            "purchase_price": 100,  # Too low
            "financing_type": "invalid_type",  # Invalid
            "earnest_money": 100
        }
        
        violations = knowledge_base.validate_compliance(
            jurisdiction=Jurisdiction.US_FEDERAL,
            transaction_data=transaction_data
        )
        
        assert len(violations) > 0
        assert all("rule_id" in violation for violation in violations)
        assert all("severity" in violation for violation in violations)
    
    def test_document_templates_retrieval(self, knowledge_base):
        """Test document templates retrieval."""
        templates = knowledge_base.get_document_templates(
            property_type=PropertyType.RESIDENTIAL_SINGLE_FAMILY,
            transaction_type=TransactionType.PURCHASE,
            jurisdiction=Jurisdiction.US_CALIFORNIA
        )
        
        assert len(templates) > 0
        for template in templates:
            assert PropertyType.RESIDENTIAL_SINGLE_FAMILY in template.property_types
            assert TransactionType.PURCHASE in template.transaction_types
            assert Jurisdiction.US_CALIFORNIA in template.jurisdictions
    
    def test_market_analysis(self, knowledge_base):
        """Test market analysis functionality."""
        analysis = knowledge_base.get_market_analysis(
            location="Los Angeles, CA",
            property_type=PropertyType.RESIDENTIAL_SINGLE_FAMILY
        )
        
        assert analysis is not None
        assert "median_price" in analysis
        assert "price_per_sqft" in analysis
        assert "days_on_market" in analysis
        assert "market_score" in analysis
        assert analysis["location"] == "Los Angeles, CA"
    
    def test_property_valuation(self, knowledge_base):
        """Test property valuation."""
        valuation = knowledge_base.estimate_property_value(
            location="Los Angeles, CA",
            property_type=PropertyType.RESIDENTIAL_SINGLE_FAMILY,
            square_footage=2000,
            bedrooms=3,
            bathrooms=2.5,
            year_built=2010,
            additional_features=["pool", "garage"]
        )
        
        assert "estimated_value" in valuation
        assert "base_value" in valuation
        assert "adjustment_factor" in valuation
        assert "adjustments" in valuation
        assert "confidence_level" in valuation
        assert valuation["estimated_value"] > 0
    
    def test_suggested_clauses(self, knowledge_base):
        """Test suggested clauses functionality."""
        clauses = knowledge_base.get_suggested_clauses(
            property_type=PropertyType.RESIDENTIAL_SINGLE_FAMILY,
            transaction_type=TransactionType.PURCHASE,
            jurisdiction=Jurisdiction.US_CALIFORNIA,
            risk_factors=["flood"]
        )
        
        assert len(clauses) > 0
        assert all("clause_id" in clause for clause in clauses)
        assert all("title" in clause for clause in clauses)
        assert all("content" in clause for clause in clauses)
        assert all("priority" in clause for clause in clauses)
        
        # Should include flood-related clauses
        flood_clauses = [c for c in clauses if "flood" in c.get("category", "").lower()]
        assert len(flood_clauses) > 0


class TestEnterpriseIntegration:
    """Test cases for enterprise integration features."""
    
    @pytest.fixture
    def enterprise_service(self):
        """Create enterprise service instance for testing."""
        return EnterpriseIntegrationService()
    
    def test_audit_event_logging(self, enterprise_service):
        """Test audit event logging."""
        initial_count = len(enterprise_service.audit_events)
        
        enterprise_service.log_agent_execution(
            user_id="test_user",
            user_email="test@example.com",
            agent_role="data_extraction",
            execution_id="test_execution",
            result="success",
            details={"duration": 2.5}
        )
        
        assert len(enterprise_service.audit_events) == initial_count + 1
        
        latest_event = enterprise_service.audit_events[-1]
        assert latest_event.event_type == AuditEventType.AGENT_EXECUTION
        assert latest_event.user_id == "test_user"
        assert latest_event.result == "success"
    
    def test_audit_events_retrieval(self, enterprise_service):
        """Test audit events retrieval with filtering."""
        # Add some test events
        enterprise_service.log_agent_execution(
            user_id="user1",
            user_email="user1@example.com",
            agent_role="data_extraction",
            execution_id="exec1",
            result="success",
            details={}
        )
        
        enterprise_service.log_data_access(
            user_id="user2",
            user_email="user2@example.com",
            resource_type="contracts",
            resource_id="contract1",
            action="read",
            result="success"
        )
        
        # Test filtering by user
        user1_events = enterprise_service.get_audit_events(user_id="user1")
        assert len(user1_events) >= 1
        assert all(event.user_id == "user1" for event in user1_events)
        
        # Test filtering by event type
        agent_events = enterprise_service.get_audit_events(event_type=AuditEventType.AGENT_EXECUTION)
        assert len(agent_events) >= 1
        assert all(event.event_type == AuditEventType.AGENT_EXECUTION for event in agent_events)
    
    def test_compliance_report_generation(self, enterprise_service):
        """Test compliance report generation."""
        # Add some test events
        enterprise_service.log_data_access(
            user_id="test_user",
            user_email="test@example.com",
            resource_type="financial_data",
            resource_id="financial1",
            action="read",
            result="success"
        )
        
        start_date = datetime.utcnow() - timedelta(days=30)
        end_date = datetime.utcnow()
        
        report = enterprise_service.generate_compliance_report(
            framework=ComplianceFramework.SOX,
            start_date=start_date,
            end_date=end_date
        )
        
        assert "report_id" in report
        assert "framework" in report
        assert report["framework"] == "sox"
        assert "metrics" in report
        assert "violations" in report
        assert "recommendations" in report
    
    def test_data_privacy_policy_application(self, enterprise_service):
        """Test data privacy policy application."""
        test_data = {
            "user_id": "123",
            "email": "test@example.com",
            "phone": "555-1234",
            "contract_value": 500000
        }
        
        user_context = {
            "user_id": "requesting_user",
            "user_email": "requester@example.com",
            "location": "US"
        }
        
        # Apply general data policy (no anonymization)
        processed_data = enterprise_service.apply_data_privacy_policy(
            data=test_data,
            policy_id="general_data",
            user_context=user_context
        )
        
        assert processed_data == test_data  # Should be unchanged
        
        # Apply sensitive data policy (with anonymization)
        processed_data = enterprise_service.apply_data_privacy_policy(
            data=test_data,
            policy_id="sensitive_data",
            user_context=user_context
        )
        
        # Email should be anonymized
        assert processed_data["email"] != test_data["email"]
        assert len(processed_data["email"]) == 8  # Hash length


class TestAdvancedAgentsAPI:
    """Test cases for advanced agents API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_user(self):
        """Create mock user for testing."""
        user = Mock(spec=User)
        user.id = "test_user_123"
        user.email = "test@example.com"
        user.role = "agent_manager"
        return user
    
    @pytest.fixture
    def auth_headers(self):
        """Create authentication headers."""
        return {"Authorization": "Bearer test_token"}
    
    def test_get_workflow_templates(self, client, mock_user, auth_headers):
        """Test getting workflow templates."""
        with patch('app.core.auth.get_current_user', return_value=mock_user):
            response = client.get("/api/v1/advanced-agents/workflows/templates", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert "templates" in data
            assert "total_count" in data
            assert isinstance(data["templates"], list)
    
    def test_property_analysis(self, client, mock_user, auth_headers):
        """Test property analysis endpoint."""
        with patch('app.core.auth.get_current_user', return_value=mock_user):
            request_data = {
                "location": "Los Angeles, CA",
                "property_type": "residential_single_family",
                "square_footage": 2000,
                "bedrooms": 3,
                "bathrooms": 2.5,
                "year_built": 2010,
                "additional_features": ["pool", "garage"]
            }
            
            response = client.post(
                "/api/v1/advanced-agents/real-estate/property-analysis",
                json=request_data,
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert "property_analysis" in data
            assert "market_analysis" in data
            assert "valuation" in data
            assert "analysis_timestamp" in data
    
    def test_compliance_check(self, client, mock_user, auth_headers):
        """Test compliance check endpoint."""
        with patch('app.core.auth.get_current_user', return_value=mock_user):
            request_data = {
                "jurisdiction": "us_california",
                "property_type": "residential_single_family",
                "transaction_type": "purchase",
                "transaction_data": {
                    "purchase_price": 500000,
                    "financing_type": "conventional",
                    "earnest_money": 10000
                }
            }
            
            response = client.post(
                "/api/v1/advanced-agents/real-estate/compliance-check",
                json=request_data,
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert "compliance_check" in data
            assert "legal_requirements" in data
            assert "violations" in data
            assert "compliance_status" in data
    
    def test_suggested_clauses(self, client, mock_user, auth_headers):
        """Test suggested clauses endpoint."""
        with patch('app.core.auth.get_current_user', return_value=mock_user):
            params = {
                "property_type": "residential_single_family",
                "transaction_type": "purchase",
                "jurisdiction": "us_california",
                "risk_factors": ["flood"]
            }
            
            response = client.get(
                "/api/v1/advanced-agents/real-estate/suggested-clauses",
                params=params,
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert "transaction_info" in data
            assert "suggested_clauses" in data
            assert "total_clauses" in data
            assert isinstance(data["suggested_clauses"], list)
    
    def test_create_shared_context(self, client, mock_user, auth_headers):
        """Test creating shared context."""
        with patch('app.core.auth.get_current_user', return_value=mock_user):
            request_data = {
                "context_id": "test_context",
                "context_data": {"key": "value", "number": 42},
                "access_agents": ["agent1", "agent2"]
            }
            
            response = client.post(
                "/api/v1/advanced-agents/memory/shared-context",
                json=request_data,
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert "message" in data
            assert data["context_id"] == "test_context"
            assert data["access_agents"] == ["agent1", "agent2"]
    
    def test_unauthorized_access(self, client):
        """Test unauthorized access to advanced endpoints."""
        # Test without authentication headers
        response = client.get("/api/v1/advanced-agents/workflows/templates")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        
        response = client.post("/api/v1/advanced-agents/real-estate/property-analysis", json={})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
