"""
Tests for database model relationships and foreign key constraints.

This module tests all relationships between models according to the ER diagram
in Section 7.1 of the specification.
"""

import pytest
from sqlmodel import SQLModel, create_engine, Session, select
from sqlalchemy.pool import StaticPool
from sqlalchemy.exc import IntegrityError

from app.models import (
    User, Deal, Upload, Template, Contract, Version,
    Signer, SignEvent, Validation, AuditLog
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
def complete_data_set(session):
    """Create a complete set of related data for testing."""
    # Create user
    user = User(
        email="test@example.com",
        name="Test User",
        role="agent",
        password_hash="hashed_password"
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    
    # Create deal
    deal = Deal(
        title="Test Deal",
        status="active",
        owner_id=user.id,
        property_address="123 Test St"
    )
    session.add(deal)
    session.commit()
    session.refresh(deal)
    
    # Create template
    template = Template(
        name="Test Template",
        version="1.0",
        docx_key="templates/test.docx",
        schema={"buyer_name": "string"},
        ruleset={"required": ["buyer_name"]}
    )
    session.add(template)
    session.commit()
    session.refresh(template)
    
    # Create upload
    upload = Upload(
        deal_id=deal.id,
        filename="document.pdf",
        s3_key="uploads/document.pdf",
        content_type="application/pdf"
    )
    session.add(upload)
    session.commit()
    session.refresh(upload)
    
    # Create contract
    contract = Contract(
        deal_id=deal.id,
        template_id=template.id,
        status="draft",
        variables={"buyer_name": "John Doe"}
    )
    session.add(contract)
    session.commit()
    session.refresh(contract)
    
    # Create version
    version = Version(
        contract_id=contract.id,
        number=1,
        diff="Initial version",
        is_current=True
    )
    session.add(version)
    session.commit()
    session.refresh(version)
    
    # Create signer
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
        ip="192.168.1.1"
    )
    session.add(sign_event)
    session.commit()
    session.refresh(sign_event)
    
    # Create validation
    validation = Validation(
        contract_id=contract.id,
        rule_id="required_fields",
        severity="info",
        ok=True,
        detail="All required fields present"
    )
    session.add(validation)
    session.commit()
    session.refresh(validation)
    
    # Create audit log
    audit_log = AuditLog(
        deal_id=deal.id,
        user_id=user.id,
        actor=f"user:{user.id}",
        action="deal.create",
        success=True
    )
    session.add(audit_log)
    session.commit()
    session.refresh(audit_log)
    
    return {
        "user": user,
        "deal": deal,
        "template": template,
        "upload": upload,
        "contract": contract,
        "version": version,
        "signer": signer,
        "sign_event": sign_event,
        "validation": validation,
        "audit_log": audit_log
    }


class TestUserDealRelationship:
    """Test User-Deal relationship (one-to-many)."""
    
    def test_user_owns_deals(self, complete_data_set):
        """Test that user can own multiple deals."""
        data = complete_data_set
        user = data["user"]
        deal = data["deal"]
        
        # Verify relationship
        assert deal.owner.id == user.id
        assert deal in user.deals
        assert len(user.deals) == 1
    
    def test_deal_requires_owner(self, session):
        """Test that deal requires a valid owner."""
        with pytest.raises(IntegrityError):
            deal = Deal(
                title="Invalid Deal",
                status="active",
                owner_id=999  # Non-existent user
            )
            session.add(deal)
            session.commit()


class TestDealUploadRelationship:
    """Test Deal-Upload relationship (one-to-many)."""
    
    def test_deal_has_uploads(self, complete_data_set):
        """Test that deal can have multiple uploads."""
        data = complete_data_set
        deal = data["deal"]
        upload = data["upload"]
        
        # Verify relationship
        assert upload.deal.id == deal.id
        assert upload in deal.uploads
        assert len(deal.uploads) == 1
    
    def test_upload_requires_deal(self, session):
        """Test that upload requires a valid deal."""
        with pytest.raises(IntegrityError):
            upload = Upload(
                deal_id=999,  # Non-existent deal
                filename="test.pdf",
                s3_key="uploads/test.pdf",
                content_type="application/pdf"
            )
            session.add(upload)
            session.commit()


class TestDealContractRelationship:
    """Test Deal-Contract relationship (one-to-many)."""
    
    def test_deal_has_contracts(self, complete_data_set):
        """Test that deal can have multiple contracts."""
        data = complete_data_set
        deal = data["deal"]
        contract = data["contract"]
        
        # Verify relationship
        assert contract.deal.id == deal.id
        assert contract in deal.contracts
        assert len(deal.contracts) == 1


class TestTemplateContractRelationship:
    """Test Template-Contract relationship (one-to-many)."""
    
    def test_template_used_for_contracts(self, complete_data_set):
        """Test that template can be used for multiple contracts."""
        data = complete_data_set
        template = data["template"]
        contract = data["contract"]
        
        # Verify relationship
        assert contract.template.id == template.id
        assert contract in template.contracts
        assert len(template.contracts) == 1


class TestContractVersionRelationship:
    """Test Contract-Version relationship (one-to-many)."""
    
    def test_contract_has_versions(self, complete_data_set):
        """Test that contract can have multiple versions."""
        data = complete_data_set
        contract = data["contract"]
        version = data["version"]
        
        # Verify relationship
        assert version.contract.id == contract.id
        assert version in contract.versions
        assert len(contract.versions) == 1


class TestContractSignerRelationship:
    """Test Contract-Signer relationship (one-to-many)."""
    
    def test_contract_has_signers(self, complete_data_set):
        """Test that contract can have multiple signers."""
        data = complete_data_set
        contract = data["contract"]
        signer = data["signer"]
        
        # Verify relationship
        assert signer.contract.id == contract.id
        assert signer in contract.signers
        assert len(contract.signers) == 1


class TestSignerSignEventRelationship:
    """Test Signer-SignEvent relationship (one-to-many)."""
    
    def test_signer_has_sign_events(self, complete_data_set):
        """Test that signer can have multiple sign events."""
        data = complete_data_set
        signer = data["signer"]
        sign_event = data["sign_event"]
        
        # Verify relationship
        assert sign_event.signer.id == signer.id
        assert sign_event in signer.sign_events
        assert len(signer.sign_events) == 1


class TestContractValidationRelationship:
    """Test Contract-Validation relationship (one-to-many)."""
    
    def test_contract_has_validations(self, complete_data_set):
        """Test that contract can have multiple validations."""
        data = complete_data_set
        contract = data["contract"]
        validation = data["validation"]
        
        # Verify relationship
        assert validation.contract.id == contract.id
        assert validation in contract.validations
        assert len(contract.validations) == 1


class TestDealAuditLogRelationship:
    """Test Deal-AuditLog relationship (one-to-many)."""
    
    def test_deal_has_audit_logs(self, complete_data_set):
        """Test that deal can have multiple audit logs."""
        data = complete_data_set
        deal = data["deal"]
        audit_log = data["audit_log"]
        
        # Verify relationship
        assert audit_log.deal.id == deal.id
        assert audit_log in deal.audit_logs
        assert len(deal.audit_logs) == 1


class TestUserAuditLogRelationship:
    """Test User-AuditLog relationship (one-to-many)."""
    
    def test_user_has_audit_logs(self, complete_data_set):
        """Test that user can have multiple audit logs."""
        data = complete_data_set
        user = data["user"]
        audit_log = data["audit_log"]
        
        # Verify relationship
        assert audit_log.user.id == user.id
        assert audit_log in user.audit_logs
        assert len(user.audit_logs) == 1


class TestCascadeDeletes:
    """Test cascade delete behavior."""
    
    def test_deal_cascade_deletes(self, session, complete_data_set):
        """Test that deleting a deal cascades to uploads and contracts."""
        data = complete_data_set
        deal = data["deal"]
        deal_id = deal.id
        
        # Delete the deal
        session.delete(deal)
        session.commit()
        
        # Verify cascaded deletes
        uploads = session.exec(select(Upload).where(Upload.deal_id == deal_id)).all()
        contracts = session.exec(select(Contract).where(Contract.deal_id == deal_id)).all()
        
        assert len(uploads) == 0  # Should be deleted
        assert len(contracts) == 0  # Should be deleted
    
    def test_contract_cascade_deletes(self, session, complete_data_set):
        """Test that deleting a contract cascades to versions, signers, and validations."""
        data = complete_data_set
        contract = data["contract"]
        contract_id = contract.id
        
        # Delete the contract
        session.delete(contract)
        session.commit()
        
        # Verify cascaded deletes
        versions = session.exec(select(Version).where(Version.contract_id == contract_id)).all()
        signers = session.exec(select(Signer).where(Signer.contract_id == contract_id)).all()
        validations = session.exec(select(Validation).where(Validation.contract_id == contract_id)).all()
        
        assert len(versions) == 0  # Should be deleted
        assert len(signers) == 0  # Should be deleted
        assert len(validations) == 0  # Should be deleted
