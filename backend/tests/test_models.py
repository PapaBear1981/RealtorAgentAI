"""
Comprehensive tests for all SQLModel database models.

This module tests all database models according to the specification,
including field validation, relationships, and constraints.
"""

import pytest
from datetime import datetime
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.pool import StaticPool

from app.models import (
    User, UserCreate, UserUpdate,
    Deal, DealCreate, DealUpdate,
    Upload, UploadCreate, UploadUpdate,
    Template, TemplateCreate, TemplateUpdate,
    Contract, ContractCreate, ContractUpdate,
    Version, VersionCreate, VersionUpdate,
    Signer, SignerCreate, SignerUpdate,
    SignEvent, SignEventCreate, SignEventUpdate,
    Validation, ValidationCreate, ValidationUpdate,
    AuditLog, AuditLogCreate, AuditLogUpdate,
)


# Test database engine
test_engine = create_engine(
    "sqlite://",  # In-memory SQLite database
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@pytest.fixture(scope="function")
def session():
    """Create a fresh database session for each test."""
    SQLModel.metadata.create_all(test_engine)
    with Session(test_engine) as session:
        yield session
    SQLModel.metadata.drop_all(test_engine)


@pytest.fixture
def sample_user(session):
    """Create a sample user for testing."""
    user = User(
        email="test@example.com",
        name="Test User",
        role="agent",
        password_hash="hashed_password"
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def sample_deal(session, sample_user):
    """Create a sample deal for testing."""
    deal = Deal(
        title="Test Deal",
        status="active",
        owner_id=sample_user.id,
        property_address="123 Test St"
    )
    session.add(deal)
    session.commit()
    session.refresh(deal)
    return deal


@pytest.fixture
def sample_template(session):
    """Create a sample template for testing."""
    template = Template(
        name="Test Template",
        version="1.0",
        docx_key="templates/test.docx",
        schema={"fields": ["buyer_name", "seller_name"]},
        ruleset={"required": ["buyer_name"]}
    )
    session.add(template)
    session.commit()
    session.refresh(template)
    return template


class TestUserModel:
    """Test User model functionality."""

    def test_create_user(self, session):
        """Test creating a user."""
        user = User(
            email="user@example.com",
            name="John Doe",
            role="admin",
            password_hash="hashed_password"
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        assert user.id is not None
        assert user.email == "user@example.com"
        assert user.name == "John Doe"
        assert user.role == "admin"
        assert user.disabled is False
        assert user.created_at is not None

    def test_user_role_validation(self):
        """Test user role validation."""
        with pytest.raises(ValueError):
            User(
                email="user@example.com",
                name="John Doe",
                role="invalid_role",
                password_hash="hashed_password"
            )

    def test_user_create_model(self):
        """Test UserCreate model validation."""
        user_create = UserCreate(
            email="user@example.com",
            name="John Doe",
            role="agent",
            password="password123"
        )
        assert user_create.email == "user@example.com"
        assert user_create.password == "password123"

    def test_user_update_model(self):
        """Test UserUpdate model validation."""
        user_update = UserUpdate(name="Updated Name", role="admin")
        assert user_update.name == "Updated Name"
        assert user_update.role == "admin"


class TestDealModel:
    """Test Deal model functionality."""

    def test_create_deal(self, session, sample_user):
        """Test creating a deal."""
        deal = Deal(
            title="Real Estate Deal",
            status="active",
            owner_id=sample_user.id,
            property_address="456 Main St",
            deal_value=500000.0
        )
        session.add(deal)
        session.commit()
        session.refresh(deal)

        assert deal.id is not None
        assert deal.title == "Real Estate Deal"
        assert deal.status == "active"
        assert deal.owner_id == sample_user.id
        assert deal.property_address == "456 Main St"
        assert deal.deal_value == 500000.0
        assert deal.created_at is not None

    def test_deal_status_validation(self):
        """Test deal status validation."""
        with pytest.raises(ValueError):
            Deal(
                title="Test Deal",
                status="invalid_status",
                owner_id=1
            )

    def test_deal_user_relationship(self, session, sample_user):
        """Test deal-user relationship."""
        deal = Deal(
            title="Test Deal",
            status="active",
            owner_id=sample_user.id
        )
        session.add(deal)
        session.commit()
        session.refresh(deal)

        # Test relationship
        assert deal.owner.id == sample_user.id
        assert deal in sample_user.deals


class TestUploadModel:
    """Test Upload model functionality."""

    def test_create_upload(self, session, sample_deal):
        """Test creating an upload."""
        upload = Upload(
            deal_id=sample_deal.id,
            filename="document.pdf",
            s3_key="uploads/document.pdf",
            content_type="application/pdf",
            pages=5,
            ocr=True,
            file_size=1024000
        )
        session.add(upload)
        session.commit()
        session.refresh(upload)

        assert upload.id is not None
        assert upload.deal_id == sample_deal.id
        assert upload.filename == "document.pdf"
        assert upload.content_type == "application/pdf"
        assert upload.pages == 5
        assert upload.ocr is True
        assert upload.processing_status == "pending"

    def test_upload_content_type_validation(self):
        """Test upload content type validation."""
        with pytest.raises(ValueError):
            Upload(
                deal_id=1,
                filename="test.txt",
                s3_key="uploads/test.txt",
                content_type="invalid/type"
            )

    def test_upload_deal_relationship(self, session, sample_deal):
        """Test upload-deal relationship."""
        upload = Upload(
            deal_id=sample_deal.id,
            filename="test.pdf",
            s3_key="uploads/test.pdf",
            content_type="application/pdf"
        )
        session.add(upload)
        session.commit()
        session.refresh(upload)

        # Test relationship
        assert upload.deal.id == sample_deal.id
        assert upload in sample_deal.uploads


class TestTemplateModel:
    """Test Template model functionality."""

    def test_create_template(self, session):
        """Test creating a template."""
        template = Template(
            name="Purchase Agreement",
            version="2.0",
            docx_key="templates/purchase_agreement.docx",
            schema={"buyer": "string", "seller": "string"},
            ruleset={"required": ["buyer", "seller"]},
            description="Standard purchase agreement template"
        )
        session.add(template)
        session.commit()
        session.refresh(template)

        assert template.id is not None
        assert template.name == "Purchase Agreement"
        assert template.version == "2.0"
        assert template.schema["buyer"] == "string"
        assert template.is_active is True
        assert template.usage_count == 0


class TestContractModel:
    """Test Contract model functionality."""

    def test_create_contract(self, session, sample_deal, sample_template):
        """Test creating a contract."""
        contract = Contract(
            deal_id=sample_deal.id,
            template_id=sample_template.id,
            status="draft",
            variables={"buyer_name": "John Doe", "seller_name": "Jane Smith"},
            title="Purchase Agreement Contract"
        )
        session.add(contract)
        session.commit()
        session.refresh(contract)

        assert contract.id is not None
        assert contract.deal_id == sample_deal.id
        assert contract.template_id == sample_template.id
        assert contract.status == "draft"
        assert contract.variables["buyer_name"] == "John Doe"
        assert contract.title == "Purchase Agreement Contract"

    def test_contract_status_validation(self):
        """Test contract status validation."""
        with pytest.raises(ValueError):
            Contract(
                deal_id=1,
                template_id=1,
                status="invalid_status"
            )

    def test_contract_relationships(self, session, sample_deal, sample_template):
        """Test contract relationships."""
        contract = Contract(
            deal_id=sample_deal.id,
            template_id=sample_template.id,
            status="draft"
        )
        session.add(contract)
        session.commit()
        session.refresh(contract)

        # Test relationships
        assert contract.deal.id == sample_deal.id
        assert contract.template.id == sample_template.id
        assert contract in sample_deal.contracts
        assert contract in sample_template.contracts


class TestVersionModel:
    """Test Version model functionality."""

    def test_create_version(self, session, sample_deal, sample_template):
        """Test creating a version."""
        # First create a contract
        contract = Contract(
            deal_id=sample_deal.id,
            template_id=sample_template.id,
            status="draft"
        )
        session.add(contract)
        session.commit()
        session.refresh(contract)

        # Create version
        version = Version(
            contract_id=contract.id,
            number=1,
            diff="Initial version",
            created_by="test_user",
            change_summary="Created initial contract",
            is_current=True
        )
        session.add(version)
        session.commit()
        session.refresh(version)

        assert version.id is not None
        assert version.contract_id == contract.id
        assert version.number == 1
        assert version.diff == "Initial version"
        assert version.is_current is True
        assert version.contract.id == contract.id


class TestSignerModel:
    """Test Signer model functionality."""

    def test_create_signer(self, session, sample_deal, sample_template):
        """Test creating a signer."""
        # Create contract first
        contract = Contract(
            deal_id=sample_deal.id,
            template_id=sample_template.id,
            status="draft"
        )
        session.add(contract)
        session.commit()
        session.refresh(contract)

        # Create signer
        signer = Signer(
            contract_id=contract.id,
            party_role="buyer",
            name="John Doe",
            email="john@example.com",
            phone="555-1234",
            order=1,
            status="pending"
        )
        session.add(signer)
        session.commit()
        session.refresh(signer)

        assert signer.id is not None
        assert signer.contract_id == contract.id
        assert signer.party_role == "buyer"
        assert signer.name == "John Doe"
        assert signer.email == "john@example.com"
        assert signer.order == 1
        assert signer.status == "pending"

    def test_signer_role_validation(self):
        """Test signer role validation."""
        with pytest.raises(ValueError):
            Signer(
                contract_id=1,
                party_role="invalid_role",
                name="John Doe",
                email="john@example.com",
                order=1,
                status="pending"
            )


class TestSignEventModel:
    """Test SignEvent model functionality."""

    def test_create_sign_event(self, session, sample_deal, sample_template):
        """Test creating a sign event."""
        # Create contract and signer first
        contract = Contract(
            deal_id=sample_deal.id,
            template_id=sample_template.id,
            status="draft"
        )
        session.add(contract)
        session.commit()
        session.refresh(contract)

        signer = Signer(
            contract_id=contract.id,
            party_role="buyer",
            name="John Doe",
            email="john@example.com",
            order=1,
            status="pending"
        )
        session.add(signer)
        session.commit()
        session.refresh(signer)

        # Create sign event
        sign_event = SignEvent(
            signer_id=signer.id,
            type="sent",
            ip="192.168.1.1",
            ua="Mozilla/5.0...",
            meta={"provider": "docusign"},
            description="Invitation sent to signer"
        )
        session.add(sign_event)
        session.commit()
        session.refresh(sign_event)

        assert sign_event.id is not None
        assert sign_event.signer_id == signer.id
        assert sign_event.type == "sent"
        assert sign_event.ip == "192.168.1.1"
        assert sign_event.meta["provider"] == "docusign"


class TestValidationModel:
    """Test Validation model functionality."""

    def test_create_validation(self, session, sample_deal, sample_template):
        """Test creating a validation."""
        # Create contract first
        contract = Contract(
            deal_id=sample_deal.id,
            template_id=sample_template.id,
            status="draft"
        )
        session.add(contract)
        session.commit()
        session.refresh(contract)

        # Create validation
        validation = Validation(
            contract_id=contract.id,
            rule_id="required_fields",
            severity="error",
            ok=False,
            detail="Missing required field: buyer_name",
            rule_name="Required Fields Check",
            suggestion="Please provide buyer name"
        )
        session.add(validation)
        session.commit()
        session.refresh(validation)

        assert validation.id is not None
        assert validation.contract_id == contract.id
        assert validation.rule_id == "required_fields"
        assert validation.severity == "error"
        assert validation.ok is False
        assert "buyer_name" in validation.detail


class TestAuditLogModel:
    """Test AuditLog model functionality."""

    def test_create_audit_log(self, session, sample_user, sample_deal):
        """Test creating an audit log."""
        audit_log = AuditLog(
            deal_id=sample_deal.id,
            user_id=sample_user.id,
            actor=f"user:{sample_user.id}",
            action="deal.create",
            resource_type="deal",
            resource_id=str(sample_deal.id),
            meta={"ip": "192.168.1.1"},
            success=True
        )
        session.add(audit_log)
        session.commit()
        session.refresh(audit_log)

        assert audit_log.id is not None
        assert audit_log.deal_id == sample_deal.id
        assert audit_log.user_id == sample_user.id
        assert audit_log.action == "deal.create"
        assert audit_log.success is True
        assert audit_log.meta["ip"] == "192.168.1.1"


# Export test classes
__all__ = [
    "TestUserModel",
    "TestDealModel",
    "TestUploadModel",
    "TestTemplateModel",
    "TestContractModel",
    "TestVersionModel",
    "TestSignerModel",
    "TestSignEventModel",
    "TestValidationModel",
    "TestAuditLogModel",
]
