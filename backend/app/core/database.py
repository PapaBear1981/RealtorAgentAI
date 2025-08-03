"""
Database configuration and session management for SQLModel.

This module handles database engine creation, session management,
and table initialization following SQLModel best practices.
"""

from typing import Generator
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.pool import StaticPool
import logging

from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Database engine configuration
connect_args = {}

# Configure connection arguments based on database type
if settings.DATABASE_URL.startswith("sqlite"):
    # SQLite-specific configuration
    connect_args = {
        "check_same_thread": False,  # Allow multi-threading for FastAPI
    }
    
    # Use StaticPool for in-memory databases to maintain state across connections
    if ":memory:" in settings.DATABASE_URL or settings.DATABASE_URL == "sqlite://":
        engine = create_engine(
            settings.DATABASE_URL,
            echo=settings.DATABASE_ECHO,
            connect_args=connect_args,
            poolclass=StaticPool,
        )
    else:
        engine = create_engine(
            settings.DATABASE_URL,
            echo=settings.DATABASE_ECHO,
            connect_args=connect_args,
        )
else:
    # PostgreSQL and other databases
    engine = create_engine(
        settings.DATABASE_URL,
        echo=settings.DATABASE_ECHO,
        pool_pre_ping=True,  # Verify connections before use
        pool_recycle=300,    # Recycle connections every 5 minutes
    )


def create_db_and_tables():
    """
    Create database tables based on SQLModel metadata.
    
    This function should be called during application startup to ensure
    all required tables exist in the database.
    
    Note: In production, use Alembic migrations instead of this function.
    """
    try:
        logger.info("Creating database tables...")
        SQLModel.metadata.create_all(engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise


def get_session() -> Generator[Session, None, None]:
    """
    Get database session for dependency injection.
    
    This function provides a database session that automatically handles
    connection management and cleanup. Use with FastAPI's Depends().
    
    Yields:
        Session: SQLModel database session
        
    Example:
        @app.get("/users/")
        def get_users(session: Session = Depends(get_session)):
            return session.exec(select(User)).all()
    """
    with Session(engine) as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {e}")
            session.rollback()
            raise
        finally:
            session.close()


def get_session_context():
    """
    Get database session for use outside of FastAPI dependency injection.
    
    This function returns a session context manager for use in background
    tasks, CLI commands, or other contexts where dependency injection
    is not available.
    
    Returns:
        Session: SQLModel database session context manager
        
    Example:
        with get_session_context() as session:
            user = session.get(User, user_id)
            session.add(new_user)
            session.commit()
    """
    return Session(engine)


def check_database_connection() -> bool:
    """
    Check if database connection is working.
    
    This function attempts to connect to the database and execute a simple
    query to verify connectivity. Useful for health checks.
    
    Returns:
        bool: True if connection is successful, False otherwise
    """
    try:
        with Session(engine) as session:
            # Execute a simple query to test connection
            session.exec("SELECT 1").first()
            return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


def get_database_info() -> dict:
    """
    Get database information for monitoring and debugging.
    
    Returns:
        dict: Database information including URL, driver, and connection status
    """
    try:
        connection_status = check_database_connection()
        
        # Extract database type from URL
        db_type = "unknown"
        if settings.DATABASE_URL.startswith("sqlite"):
            db_type = "sqlite"
        elif settings.DATABASE_URL.startswith("postgresql"):
            db_type = "postgresql"
        elif settings.DATABASE_URL.startswith("mysql"):
            db_type = "mysql"
        
        return {
            "type": db_type,
            "url": settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else settings.DATABASE_URL,
            "echo": settings.DATABASE_ECHO,
            "connected": connection_status,
            "pool_size": getattr(engine.pool, "size", "N/A"),
            "checked_out": getattr(engine.pool, "checkedout", "N/A"),
        }
    except Exception as e:
        logger.error(f"Failed to get database info: {e}")
        return {
            "type": "unknown",
            "url": "unknown",
            "echo": settings.DATABASE_ECHO,
            "connected": False,
            "error": str(e),
        }


# Export commonly used objects
__all__ = [
    "engine",
    "create_db_and_tables",
    "get_session",
    "get_session_context",
    "check_database_connection",
    "get_database_info",
]
