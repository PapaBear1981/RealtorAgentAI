"""
Tests for configuration management.

This module tests the application configuration system,
environment variable handling, and validation.
"""

import pytest
import os
from unittest.mock import patch
from pydantic import ValidationError

from app.core.config import Settings, get_settings


def test_default_settings():
    """Test that default settings are properly configured."""
    settings = Settings()
    
    # Test default values
    assert settings.APP_NAME == "Multi-Agent Real-Estate Contract Platform"
    assert settings.VERSION == "0.1.0"
    assert settings.ENVIRONMENT == "development"
    assert settings.DEBUG is True
    assert settings.HOST == "0.0.0.0"
    assert settings.PORT == 8000
    assert settings.ALLOWED_HOSTS == ["*"]
    
    # Test database defaults
    assert settings.DATABASE_URL == "sqlite:///./database.db"
    assert settings.DATABASE_ECHO is False
    
    # Test JWT defaults
    assert settings.JWT_ALGORITHM == "HS256"
    assert settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES == 30
    assert settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS == 7


def test_environment_variable_override():
    """Test that environment variables override default settings."""
    with patch.dict(os.environ, {
        "ENVIRONMENT": "production",
        "DEBUG": "false",
        "PORT": "9000",
        "DATABASE_URL": "postgresql://user:pass@localhost/db",
    }):
        settings = Settings()
        
        assert settings.ENVIRONMENT == "production"
        assert settings.DEBUG is False
        assert settings.PORT == 9000
        assert settings.DATABASE_URL == "postgresql://user:pass@localhost/db"


def test_environment_validation():
    """Test that environment validation works correctly."""
    # Valid environments should work
    for env in ["development", "staging", "production"]:
        settings = Settings(ENVIRONMENT=env)
        assert settings.ENVIRONMENT == env
    
    # Invalid environment should raise error
    with pytest.raises(ValidationError):
        Settings(ENVIRONMENT="invalid")


def test_jwt_secret_validation_development():
    """Test JWT secret validation in development environment."""
    # Default secret should be allowed in development
    settings = Settings(ENVIRONMENT="development")
    assert settings.JWT_SECRET_KEY == "dev-secret-key-change-in-production"


def test_jwt_secret_validation_production():
    """Test JWT secret validation in production environment."""
    # Default secret should not be allowed in production
    with pytest.raises(ValidationError):
        Settings(
            ENVIRONMENT="production",
            JWT_SECRET_KEY="dev-secret-key-change-in-production"
        )
    
    # Custom secret should be allowed in production
    settings = Settings(
        ENVIRONMENT="production",
        JWT_SECRET_KEY="custom-production-secret-key",
        ALLOWED_HOSTS=["example.com"]  # Required for production
    )
    assert settings.JWT_SECRET_KEY == "custom-production-secret-key"


def test_allowed_hosts_validation_development():
    """Test allowed hosts validation in development environment."""
    # Wildcard should be allowed in development
    settings = Settings(ENVIRONMENT="development", ALLOWED_HOSTS=["*"])
    assert settings.ALLOWED_HOSTS == ["*"]


def test_allowed_hosts_validation_production():
    """Test allowed hosts validation in production environment."""
    # Wildcard should not be allowed in production
    with pytest.raises(ValidationError):
        Settings(
            ENVIRONMENT="production",
            ALLOWED_HOSTS=["*"],
            JWT_SECRET_KEY="custom-secret"
        )
    
    # Specific hosts should be allowed in production
    settings = Settings(
        ENVIRONMENT="production",
        ALLOWED_HOSTS=["example.com", "api.example.com"],
        JWT_SECRET_KEY="custom-secret"
    )
    assert "example.com" in settings.ALLOWED_HOSTS
    assert "*" not in settings.ALLOWED_HOSTS


def test_settings_caching():
    """Test that get_settings() returns cached instance."""
    settings1 = get_settings()
    settings2 = get_settings()
    
    # Should be the same instance due to lru_cache
    assert settings1 is settings2


def test_database_url_formats():
    """Test various database URL formats."""
    # SQLite
    settings = Settings(DATABASE_URL="sqlite:///./test.db")
    assert settings.DATABASE_URL == "sqlite:///./test.db"
    
    # PostgreSQL
    settings = Settings(DATABASE_URL="postgresql://user:pass@localhost:5432/db")
    assert settings.DATABASE_URL == "postgresql://user:pass@localhost:5432/db"
    
    # In-memory SQLite
    settings = Settings(DATABASE_URL="sqlite:///:memory:")
    assert settings.DATABASE_URL == "sqlite:///:memory:"


def test_file_upload_settings():
    """Test file upload configuration."""
    settings = Settings()
    
    assert settings.MAX_FILE_SIZE == 100 * 1024 * 1024  # 100MB
    assert "pdf" in settings.ALLOWED_FILE_TYPES
    assert "docx" in settings.ALLOWED_FILE_TYPES
    assert "png" in settings.ALLOWED_FILE_TYPES


def test_s3_settings():
    """Test S3/MinIO configuration."""
    settings = Settings(
        S3_ENDPOINT="http://localhost:9000",
        S3_ACCESS_KEY="minioadmin",
        S3_SECRET_KEY="minioadmin123",
        S3_BUCKET_NAME="test-bucket"
    )
    
    assert settings.S3_ENDPOINT == "http://localhost:9000"
    assert settings.S3_ACCESS_KEY == "minioadmin"
    assert settings.S3_SECRET_KEY == "minioadmin123"
    assert settings.S3_BUCKET_NAME == "test-bucket"
    assert settings.S3_REGION == "us-east-1"  # Default
    assert settings.S3_USE_SSL is True  # Default


def test_ai_model_settings():
    """Test AI/LLM model configuration."""
    settings = Settings()
    
    assert settings.DEFAULT_LLM_MODEL == "gpt-4o-mini"
    assert settings.DEFAULT_EMBEDDING_MODEL == "text-embedding-3-small"
    assert settings.OLLAMA_BASE_URL == "http://localhost:11434"


def test_security_settings():
    """Test security-related configuration."""
    settings = Settings()
    
    assert settings.BCRYPT_ROUNDS == 12
    assert settings.SESSION_EXPIRE_HOURS == 24
    assert settings.RATE_LIMIT_REQUESTS == 100
    assert settings.RATE_LIMIT_WINDOW == 60


def test_logging_settings():
    """Test logging configuration."""
    settings = Settings()
    
    assert settings.LOG_LEVEL == "INFO"
    assert "%(asctime)s" in settings.LOG_FORMAT
    assert "%(levelname)s" in settings.LOG_FORMAT


def test_celery_settings():
    """Test Celery configuration."""
    settings = Settings()
    
    assert settings.REDIS_URL == "redis://localhost:6379/0"
    assert settings.CELERY_BROKER_URL == "redis://localhost:6379/1"
    assert settings.CELERY_RESULT_BACKEND == "redis://localhost:6379/2"


if __name__ == "__main__":
    pytest.main([__file__])
