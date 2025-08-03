"""
Tests for admin service functionality.

This module contains unit tests for the AdminService class and its methods.
"""

import pytest
from datetime import datetime, timedelta
from sqlmodel import SQLModel, Session, select, create_engine
from sqlalchemy.pool import StaticPool

from app.services.admin_service import AdminService, AdminServiceError
from app.models.user import User, UserCreate, UserUpdate
from app.models.audit_log import AuditLog, AuditLogFilter
from app.core.auth import hash_password


# Test database engine
test_engine = create_engine(
    "sqlite://",  # In-memory SQLite database
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@pytest.fixture(scope="function")
def setup_database():
    """Set up test database."""
    SQLModel.metadata.create_all(test_engine)
    yield
    SQLModel.metadata.drop_all(test_engine)


@pytest.fixture(scope="function")
def admin_user(setup_database):
    """Create admin user for testing."""
    with Session(test_engine) as session:
        admin = User(
            email="admin@example.com",
            name="Admin User",
            role="admin",
            password_hash=hash_password("adminpassword"),
            disabled=False,
            created_at=datetime.utcnow()
        )
        session.add(admin)
        session.commit()
        session.refresh(admin)
        return admin


@pytest.fixture(scope="function")
def test_user(setup_database):
    """Create test user for testing."""
    with Session(test_engine) as session:
        user = User(
            email="testuser@example.com",
            name="Test User",
            role="agent",
            password_hash=hash_password("testpassword"),
            disabled=False,
            created_at=datetime.utcnow()
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


class TestAdminService:
    """Test AdminService functionality."""

    def setup_method(self):
        """Set up test method."""
        self.admin_service = AdminService()

    @pytest.mark.asyncio
    async def test_create_user_success(self, admin_user: User):
        """Test successful user creation."""
        user_data = UserCreate(
            email="newuser@example.com",
            name="New User",
            role="agent",
            password="testpassword123",
            disabled=False
        )

        with Session(test_engine) as session:
            result = await self.admin_service.create_user(user_data, admin_user, session)

            assert result.email == user_data.email
            assert result.name == user_data.name
            assert result.role == user_data.role
            assert result.disabled == user_data.disabled
            assert result.id is not None

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(self, admin_user: User):
        """Test user creation with duplicate email."""
        user_data = UserCreate(
            email=admin_user.email,  # Duplicate email
            name="Duplicate User",
            role="agent",
            password="testpassword123",
            disabled=False
        )

        with Session(test_engine) as session:
            with pytest.raises(Exception):  # Should raise HTTPException
                await self.admin_service.create_user(user_data, admin_user, session)

    @pytest.mark.asyncio
    async def test_list_users_success(self, admin_user: User):
        """Test successful user listing."""
        with Session(test_engine) as session:
            result = await self.admin_service.list_users(admin_user, session)

            assert "users" in result
            assert "total_count" in result
            assert "limit" in result
            assert "offset" in result
            assert "has_more" in result
            assert isinstance(result["users"], list)
            assert result["total_count"] >= 1  # At least admin user

    @pytest.mark.asyncio
    async def test_list_users_with_filters(self, admin_user: User):
        """Test user listing with filters."""
        with Session(test_engine) as session:
            result = await self.admin_service.list_users(
                admin_user, session, role="admin", disabled=False
            )

            assert "users" in result
            for user in result["users"]:
                assert user.role == "admin"
                assert user.disabled == False

    @pytest.mark.asyncio
    async def test_get_user_success(self, admin_user: User, test_user: User):
        """Test successful user retrieval."""
        with Session(test_engine) as session:
            result = await self.admin_service.get_user(test_user.id, admin_user, session)

            assert result.id == test_user.id
            assert result.email == test_user.email
            assert result.name == test_user.name
            assert result.role == test_user.role

    @pytest.mark.asyncio
    async def test_get_user_not_found(self, admin_user: User):
        """Test user retrieval with non-existent ID."""
        with Session(test_engine) as session:
            with pytest.raises(Exception):  # Should raise HTTPException
                await self.admin_service.get_user(99999, admin_user, session)

    @pytest.mark.asyncio
    async def test_update_user_success(self, admin_user: User, test_user: User):
        """Test successful user update."""
        update_data = UserUpdate(name="Updated Name", role="tc")

        with Session(test_engine) as session:
            result = await self.admin_service.update_user(
                test_user.id, update_data, admin_user, session
            )

            assert result.name == "Updated Name"
            assert result.role == "tc"
            assert result.id == test_user.id

    @pytest.mark.asyncio
    async def test_update_user_not_found(self, admin_user: User):
        """Test user update with non-existent ID."""
        update_data = UserUpdate(name="Updated Name")

        with Session(test_engine) as session:
            with pytest.raises(Exception):  # Should raise HTTPException
                await self.admin_service.update_user(99999, update_data, admin_user, session)

    @pytest.mark.asyncio
    async def test_delete_user_success(self, admin_user: User, test_user: User):
        """Test successful user deletion."""
        with Session(test_engine) as session:
            result = await self.admin_service.delete_user(test_user.id, admin_user, session)

            assert result == True

            # Verify user is disabled
            updated_user = session.get(User, test_user.id)
            assert updated_user.disabled == True

    @pytest.mark.asyncio
    async def test_delete_user_self(self, admin_user: User):
        """Test that admin cannot delete their own account."""
        with Session(test_engine) as session:
            with pytest.raises(Exception):  # Should raise HTTPException
                await self.admin_service.delete_user(admin_user.id, admin_user, session)

    @pytest.mark.asyncio
    async def test_search_audit_logs_success(self, admin_user: User):
        """Test successful audit log search."""
        filters = AuditLogFilter()

        with Session(test_engine) as session:
            result = await self.admin_service.search_audit_logs(
                admin_user, session, filters
            )

            assert "audit_logs" in result
            assert "total_count" in result
            assert "limit" in result
            assert "offset" in result
            assert "has_more" in result
            assert isinstance(result["audit_logs"], list)

    @pytest.mark.asyncio
    async def test_search_audit_logs_with_filters(self, admin_user: User):
        """Test audit log search with filters."""
        filters = AuditLogFilter(
            user_id=admin_user.id,
            success=True,
            start_date=datetime.utcnow() - timedelta(days=1)
        )

        with Session(test_engine) as session:
            result = await self.admin_service.search_audit_logs(
                admin_user, session, filters
            )

            assert "audit_logs" in result

    @pytest.mark.asyncio
    async def test_export_audit_logs_csv(self, admin_user: User):
        """Test audit log export in CSV format."""
        filters = AuditLogFilter()

        with Session(test_engine) as session:
            result = await self.admin_service.export_audit_logs(
                admin_user, session, filters, "csv", 100
            )

            assert isinstance(result, str)
            assert "ID,Timestamp,User ID" in result  # CSV header

    @pytest.mark.asyncio
    async def test_export_audit_logs_json(self, admin_user: User):
        """Test audit log export in JSON format."""
        filters = AuditLogFilter()

        with Session(test_engine) as session:
            result = await self.admin_service.export_audit_logs(
                admin_user, session, filters, "json", 100
            )

            assert isinstance(result, dict)
            assert "export_timestamp" in result
            assert "exported_by" in result
            assert "audit_logs" in result

    @pytest.mark.asyncio
    async def test_export_audit_logs_invalid_format(self, admin_user: User):
        """Test audit log export with invalid format."""
        filters = AuditLogFilter()

        with Session(test_engine) as session:
            with pytest.raises(Exception):  # Should raise HTTPException
                await self.admin_service.export_audit_logs(
                    admin_user, session, filters, "xml", 100
                )

    @pytest.mark.asyncio
    async def test_get_system_health_success(self, admin_user: User):
        """Test successful system health check."""
        with Session(test_engine) as session:
            result = await self.admin_service.get_system_health(admin_user, session)

            assert "timestamp" in result
            assert "overall_status" in result
            assert "database" in result
            assert "users" in result
            assert "activity" in result
            assert "performance" in result

            # Check database health
            assert "healthy" in result["database"]
            assert "user_count" in result["database"]

            # Check user statistics
            assert "total_users" in result["users"]
            assert "active_users" in result["users"]
            assert "role_distribution" in result["users"]

    @pytest.mark.asyncio
    async def test_get_usage_analytics_success(self, admin_user: User):
        """Test successful usage analytics retrieval."""
        with Session(test_engine) as session:
            result = await self.admin_service.get_usage_analytics(admin_user, session, 7)

            assert "period" in result
            assert "user_activity" in result
            assert "template_usage" in result
            assert "contracts" in result
            assert "errors" in result
            assert "generated_at" in result

            # Check period
            assert result["period"]["days"] == 7
            assert "start_date" in result["period"]
            assert "end_date" in result["period"]

    @pytest.mark.asyncio
    async def test_database_health_check(self, admin_user: User):
        """Test database health check method."""
        with Session(test_engine) as session:
            result = await self.admin_service._check_database_health(session)

            assert "healthy" in result
            assert "user_count" in result
            assert "connection_status" in result
            assert "last_check" in result
            assert result["healthy"] == True
            assert result["connection_status"] == "connected"

    @pytest.mark.asyncio
    async def test_user_statistics(self, admin_user: User):
        """Test user statistics method."""
        with Session(test_engine) as session:
            result = await self.admin_service._get_user_statistics(session)

            assert "total_users" in result
            assert "active_users" in result
            assert "active_users_24h" in result
            assert "disabled_users" in result
            assert "role_distribution" in result

            # Check role distribution
            assert isinstance(result["role_distribution"], dict)
            assert "admin" in result["role_distribution"]
            assert "agent" in result["role_distribution"]
            assert "tc" in result["role_distribution"]
            assert "signer" in result["role_distribution"]

    @pytest.mark.asyncio
    async def test_activity_statistics(self, admin_user: User):
        """Test activity statistics method."""
        with Session(test_engine) as session:
            result = await self.admin_service._get_activity_statistics(session)

            assert "total_actions_24h" in result
            assert "successful_actions_24h" in result
            assert "success_rate_24h" in result
            assert "most_common_actions" in result

            # Check success rate is a percentage
            assert 0 <= result["success_rate_24h"] <= 100

    @pytest.mark.asyncio
    async def test_performance_statistics(self, admin_user: User):
        """Test performance statistics method."""
        with Session(test_engine) as session:
            result = await self.admin_service._get_performance_statistics(session)

            assert "templates" in result
            assert "contracts" in result
            assert "deals" in result

            # Check templates stats
            assert "total" in result["templates"]
            assert "active" in result["templates"]

            # Check contracts stats
            assert "total" in result["contracts"]

            # Check deals stats
            assert "total" in result["deals"]
