"""
Comprehensive test suite for contract management system.

Tests the core business logic implementation including CRUD operations,
template management, version control, and contract generation.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch
from sqlmodel import Session, create_engine, SQLModel
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import get_session
from app.services.contract_service import ContractService, get_contract_service
from app.services.template_service import TemplateService, get_template_service
from app.services.version_control_service import VersionControlService, get_version_control_service
from app.models.user import User
from app.models.deal import Deal, DealCreate
from app.models.contract import Contract, ContractCreate
from app.models.template import Template, TemplateCreate, TemplateStatus, TemplateType, OutputFormat
from app.models.version import Version


# Test database setup
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
def test_client(test_session):
    """Create test client with database override."""
    def get_test_session():
        return test_session
    
    app.dependency_overrides[get_session] = get_test_session
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(test_session):
    """Create test user."""
    user = User(
        email="test@example.com",
        hashed_password="hashed_password",
        full_name="Test User",
        role="user",
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
        title="Test Deal",
        status="active",
        property_address="123 Test St",
        deal_value=100000.0
    )
    deal = Deal(**deal_data.dict(), owner_id=test_user.id)
    test_session.add(deal)
    test_session.commit()
    test_session.refresh(deal)
    return deal


@pytest.fixture
def test_template(test_session, test_user):
    """Create test template."""
    template_data = TemplateCreate(
        name="Test Template",
        version="1.0",
        template_type=TemplateType.CONTRACT,
        status=TemplateStatus.ACTIVE,
        html_content="<h1>{{title}}</h1><p>{{content}}</p>",
        description="Test template for contracts"
    )
    template = Template(**template_data.dict(), created_by=test_user.id)
    test_session.add(template)
    test_session.commit()
    test_session.refresh(template)
    return template


class TestContractService:
    """Test contract service functionality."""

    @pytest.mark.asyncio
    async def test_create_contract(self, test_session, test_user, test_deal, test_template):
        """Test contract creation."""
        service = ContractService()
        
        contract_data = ContractCreate(
            deal_id=test_deal.id,
            template_id=test_template.id,
            title="Test Contract",
            status="draft",
            variables={"title": "Test Contract", "content": "Contract content"}
        )
        
        result = await service.create_contract(contract_data, test_user, test_session)
        
        assert result.id is not None
        assert result.title == "Test Contract"
        assert result.deal_id == test_deal.id
        assert result.template_id == test_template.id

    @pytest.mark.asyncio
    async def test_search_contracts(self, test_session, test_user, test_deal, test_template):
        """Test contract search functionality."""
        service = ContractService()
        
        # Create test contracts
        for i in range(3):
            contract_data = ContractCreate(
                deal_id=test_deal.id,
                template_id=test_template.id,
                title=f"Test Contract {i}",
                status="draft"
            )
            await service.create_contract(contract_data, test_user, test_session)
        
        # Test search
        result = await service.search_contracts(
            test_user,
            test_session,
            search_query="Test Contract",
            limit=10,
            offset=0
        )
        
        assert result["total_count"] == 3
        assert len(result["contracts"]) == 3
        assert not result["has_more"]

    @pytest.mark.asyncio
    async def test_validate_contract_comprehensive(self, test_session, test_user, test_deal, test_template):
        """Test comprehensive contract validation."""
        service = ContractService()
        
        # Create contract
        contract_data = ContractCreate(
            deal_id=test_deal.id,
            template_id=test_template.id,
            title="Test Contract",
            status="draft",
            variables={"title": "Test Contract", "content": "Contract content"}
        )
        contract = await service.create_contract(contract_data, test_user, test_session)
        
        # Test validation
        result = await service.validate_contract_comprehensive(
            contract.id, test_user, test_session
        )
        
        assert "is_valid" in result
        assert "errors" in result
        assert "warnings" in result
        assert "validation_details" in result

    @pytest.mark.asyncio
    async def test_get_contract_statistics(self, test_session, test_user, test_deal, test_template):
        """Test contract statistics."""
        service = ContractService()
        
        # Create test contracts with different statuses
        statuses = ["draft", "active", "completed"]
        for status in statuses:
            contract_data = ContractCreate(
                deal_id=test_deal.id,
                template_id=test_template.id,
                title=f"Contract {status}",
                status=status
            )
            await service.create_contract(contract_data, test_user, test_session)
        
        # Test statistics
        result = await service.get_contract_statistics(test_user, test_session)
        
        assert result["total_contracts"] == 3
        assert "status_distribution" in result
        assert "template_usage" in result
        assert "monthly_creation_trend" in result


class TestVersionControlService:
    """Test version control service functionality."""

    @pytest.mark.asyncio
    async def test_create_version(self, test_session, test_user, test_deal, test_template):
        """Test version creation."""
        # Create contract first
        contract_service = ContractService()
        contract_data = ContractCreate(
            deal_id=test_deal.id,
            template_id=test_template.id,
            title="Test Contract",
            status="draft"
        )
        contract = await contract_service.create_contract(contract_data, test_user, test_session)
        
        # Test version creation
        version_service = VersionControlService()
        result = await version_service.create_version(
            "contract",
            contract.id,
            "Initial version",
            test_user,
            test_session
        )
        
        assert result.id is not None
        assert result.number == 1
        assert result.change_summary == "Initial version"
        assert result.is_current is True

    @pytest.mark.asyncio
    async def test_get_version_history(self, test_session, test_user, test_deal, test_template):
        """Test version history retrieval."""
        # Create contract and versions
        contract_service = ContractService()
        contract_data = ContractCreate(
            deal_id=test_deal.id,
            template_id=test_template.id,
            title="Test Contract",
            status="draft"
        )
        contract = await contract_service.create_contract(contract_data, test_user, test_session)
        
        version_service = VersionControlService()
        
        # Create multiple versions
        for i in range(3):
            await version_service.create_version(
                "contract",
                contract.id,
                f"Version {i+1}",
                test_user,
                test_session
            )
        
        # Test history retrieval
        result = await version_service.get_version_history(
            "contract",
            contract.id,
            test_user,
            test_session
        )
        
        assert result["total_count"] == 3
        assert len(result["versions"]) == 3

    @pytest.mark.asyncio
    async def test_generate_diff(self, test_session, test_user, test_deal, test_template):
        """Test diff generation between versions."""
        # Create contract and versions
        contract_service = ContractService()
        contract_data = ContractCreate(
            deal_id=test_deal.id,
            template_id=test_template.id,
            title="Test Contract",
            status="draft"
        )
        contract = await contract_service.create_contract(contract_data, test_user, test_session)
        
        version_service = VersionControlService()
        
        # Create two versions
        version1 = await version_service.create_version(
            "contract", contract.id, "Version 1", test_user, test_session
        )
        version2 = await version_service.create_version(
            "contract", contract.id, "Version 2", test_user, test_session
        )
        
        # Test diff generation
        result = await version_service.generate_diff(
            "contract",
            contract.id,
            version1.id,
            version2.id,
            test_user,
            test_session,
            "summary"
        )
        
        assert "diff" in result
        assert "version1" in result
        assert "version2" in result
        assert result["entity_type"] == "contract"


class TestContractAPI:
    """Test contract API endpoints."""

    def test_create_contract_endpoint(self, test_client, test_user, test_deal, test_template):
        """Test contract creation endpoint."""
        # Mock authentication
        with patch('app.core.dependencies.get_current_active_user', return_value=test_user):
            response = test_client.post(
                "/api/v1/contracts/",
                json={
                    "deal_id": test_deal.id,
                    "template_id": test_template.id,
                    "title": "API Test Contract",
                    "status": "draft"
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "API Test Contract"
        assert data["deal_id"] == test_deal.id

    def test_search_contracts_endpoint(self, test_client, test_user):
        """Test contract search endpoint."""
        with patch('app.core.dependencies.get_current_active_user', return_value=test_user):
            response = test_client.get(
                "/api/v1/contracts/search",
                params={
                    "search_query": "test",
                    "limit": 10,
                    "offset": 0
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert "contracts" in data
        assert "total_count" in data
        assert "has_more" in data

    def test_get_contract_statistics_endpoint(self, test_client, test_user):
        """Test contract statistics endpoint."""
        with patch('app.core.dependencies.get_current_active_user', return_value=test_user):
            response = test_client.get("/api/v1/contracts/statistics")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_contracts" in data
        assert "status_distribution" in data
        assert "template_usage" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
