"""
Tests for database configuration and session management.

This module tests database engine creation, session management,
connection handling, and utility functions.
"""

import pytest
from unittest.mock import patch, MagicMock
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.pool import StaticPool

from app.core.database import (
    create_db_and_tables,
    get_session,
    get_session_context,
    check_database_connection,
    get_database_info,
)
from app.core.config import Settings


# Test database engine
test_engine = create_engine(
    "sqlite://",  # In-memory database
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@pytest.fixture
def test_settings():
    """Create test settings with in-memory database."""
    return Settings(
        DATABASE_URL="sqlite:///:memory:",
        DATABASE_ECHO=False,
    )


@pytest.fixture
def mock_engine():
    """Create a mock database engine for testing."""
    engine = MagicMock()
    engine.pool.size = 5
    engine.pool.checkedout = 2
    return engine


def test_create_db_and_tables():
    """Test database table creation."""
    # This test uses the actual function but with a test database
    with patch("app.core.database.engine", test_engine):
        # Should not raise any exceptions
        create_db_and_tables()
        
        # Verify that metadata.create_all was called
        # (We can't easily test this without actual models, but we can test it doesn't crash)


def test_get_session_dependency():
    """Test the get_session dependency function."""
    with patch("app.core.database.engine", test_engine):
        # Get session generator
        session_gen = get_session()
        
        # Get the session
        session = next(session_gen)
        assert isinstance(session, Session)
        
        # Clean up
        try:
            next(session_gen)
        except StopIteration:
            pass  # Expected behavior


def test_get_session_context():
    """Test the get_session_context function."""
    with patch("app.core.database.engine", test_engine):
        session_context = get_session_context()
        
        # Should return a Session instance
        assert isinstance(session_context, Session)


def test_get_session_error_handling():
    """Test error handling in get_session."""
    # Create a mock engine that raises an exception
    mock_engine = MagicMock()
    mock_engine.begin.side_effect = Exception("Database connection failed")
    
    with patch("app.core.database.engine", mock_engine):
        session_gen = get_session()
        
        # Should handle the exception gracefully
        with pytest.raises(Exception):
            next(session_gen)


def test_check_database_connection_success():
    """Test successful database connection check."""
    with patch("app.core.database.engine", test_engine):
        result = check_database_connection()
        assert result is True


def test_check_database_connection_failure():
    """Test failed database connection check."""
    # Create a mock engine that raises an exception
    mock_engine = MagicMock()
    mock_session = MagicMock()
    mock_session.exec.side_effect = Exception("Connection failed")
    mock_engine.begin.return_value.__enter__.return_value = mock_session
    
    with patch("app.core.database.Session") as mock_session_class:
        mock_session_class.return_value.__enter__.return_value.exec.side_effect = Exception("Connection failed")
        
        result = check_database_connection()
        assert result is False


def test_get_database_info_sqlite():
    """Test get_database_info with SQLite database."""
    with patch("app.core.database.settings") as mock_settings:
        mock_settings.DATABASE_URL = "sqlite:///./test.db"
        mock_settings.DATABASE_ECHO = True
        
        with patch("app.core.database.check_database_connection", return_value=True):
            with patch("app.core.database.engine") as mock_engine:
                mock_engine.pool.size = 5
                mock_engine.pool.checkedout = 2
                
                info = get_database_info()
                
                assert info["type"] == "sqlite"
                assert info["url"] == "sqlite:///./test.db"
                assert info["echo"] is True
                assert info["connected"] is True
                assert info["pool_size"] == 5
                assert info["checked_out"] == 2


def test_get_database_info_postgresql():
    """Test get_database_info with PostgreSQL database."""
    with patch("app.core.database.settings") as mock_settings:
        mock_settings.DATABASE_URL = "postgresql://user:pass@localhost:5432/db"
        mock_settings.DATABASE_ECHO = False
        
        with patch("app.core.database.check_database_connection", return_value=True):
            with patch("app.core.database.engine") as mock_engine:
                mock_engine.pool.size = 10
                mock_engine.pool.checkedout = 3
                
                info = get_database_info()
                
                assert info["type"] == "postgresql"
                assert info["url"] == "localhost:5432/db"  # Should strip credentials
                assert info["echo"] is False
                assert info["connected"] is True


def test_get_database_info_error():
    """Test get_database_info when an error occurs."""
    with patch("app.core.database.check_database_connection", side_effect=Exception("Test error")):
        info = get_database_info()
        
        assert info["type"] == "unknown"
        assert info["connected"] is False
        assert "error" in info


def test_sqlite_engine_configuration():
    """Test SQLite engine configuration with different URLs."""
    # Test regular SQLite file
    with patch("app.core.database.settings") as mock_settings:
        mock_settings.DATABASE_URL = "sqlite:///./test.db"
        mock_settings.DATABASE_ECHO = False
        
        # Import should work without errors
        from app.core.database import engine
        assert engine is not None


def test_postgresql_engine_configuration():
    """Test PostgreSQL engine configuration."""
    with patch("app.core.database.settings") as mock_settings:
        mock_settings.DATABASE_URL = "postgresql://user:pass@localhost:5432/db"
        mock_settings.DATABASE_ECHO = False
        
        # Should configure with pool settings
        with patch("app.core.database.create_engine") as mock_create_engine:
            # Re-import to trigger engine creation
            import importlib
            import app.core.database
            importlib.reload(app.core.database)
            
            # Verify create_engine was called with correct parameters
            mock_create_engine.assert_called_with(
                "postgresql://user:pass@localhost:5432/db",
                echo=False,
                pool_pre_ping=True,
                pool_recycle=300,
            )


def test_in_memory_sqlite_configuration():
    """Test in-memory SQLite configuration."""
    with patch("app.core.database.settings") as mock_settings:
        mock_settings.DATABASE_URL = "sqlite:///:memory:"
        mock_settings.DATABASE_ECHO = False
        
        # Should use StaticPool for in-memory database
        with patch("app.core.database.create_engine") as mock_create_engine:
            # Re-import to trigger engine creation
            import importlib
            import app.core.database
            importlib.reload(app.core.database)
            
            # Verify create_engine was called with StaticPool
            mock_create_engine.assert_called_with(
                "sqlite:///:memory:",
                echo=False,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )


if __name__ == "__main__":
    pytest.main([__file__])
