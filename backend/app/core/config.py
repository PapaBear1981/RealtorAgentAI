"""
Configuration management for the Multi-Agent Real-Estate Contract Platform.

This module handles all application settings using Pydantic Settings,
supporting environment variables and configuration validation.
"""

from functools import lru_cache
from typing import List, Optional
from pydantic import Field, field_validator, ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings with environment variable support.

    All settings can be overridden using environment variables.
    For example, DATABASE_URL can be set via the DATABASE_URL env var.
    """

    # Application settings
    APP_NAME: str = "Multi-Agent Real-Estate Contract Platform"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = Field(default="development", description="Environment: development, staging, production")
    DEBUG: bool = Field(default=True, description="Enable debug mode")

    # Server settings
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, description="Server port")
    ALLOWED_HOSTS: List[str] = Field(default=["*"], description="Allowed hosts for CORS")

    # Database settings
    DATABASE_URL: str = Field(
        default="sqlite:///./database.db",
        description="Database connection URL"
    )
    DATABASE_ECHO: bool = Field(default=False, description="Echo SQL queries")

    # Redis settings (for Celery and caching)
    REDIS_URL: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/1", description="Celery broker URL")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/2", description="Celery result backend URL")

    # JWT settings
    JWT_SECRET_KEY: str = Field(
        default="dev-secret-key-change-in-production",
        description="JWT secret key for token signing"
    )
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, description="Access token expiration in minutes")
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, description="Refresh token expiration in days")

    # S3/MinIO settings
    S3_ENDPOINT: Optional[str] = Field(default=None, description="S3 endpoint URL")
    S3_ACCESS_KEY: Optional[str] = Field(default=None, description="S3 access key")
    S3_SECRET_KEY: Optional[str] = Field(default=None, description="S3 secret key")
    S3_BUCKET_NAME: str = Field(default="realestate-files", description="S3 bucket name")
    S3_REGION: str = Field(default="us-east-1", description="S3 region")
    S3_USE_SSL: bool = Field(default=True, description="Use SSL for S3 connections")

    # File upload settings
    MAX_FILE_SIZE: int = Field(default=100 * 1024 * 1024, description="Maximum file size in bytes (100MB)")
    ALLOWED_FILE_TYPES: List[str] = Field(
        default=["pdf", "docx", "doc", "png", "jpg", "jpeg", "tiff"],
        description="Allowed file extensions"
    )

    # OCR settings
    TESSERACT_CMD: Optional[str] = Field(default=None, description="Tesseract command path")
    TESSERACT_CMD_PATH: Optional[str] = Field(default=None, description="Tesseract executable path")
    OCR_LANGUAGES: List[str] = Field(default=["eng"], description="OCR languages")
    ENABLE_OCR: bool = Field(default=True, description="Enable OCR processing")

    # Document processing settings
    PROCESSING_TIMEOUT_SECONDS: int = Field(default=300, description="Document processing timeout")

    # Storage settings (aliases for compatibility)
    STORAGE_BUCKET_NAME: str = Field(default="realestate-files", description="Storage bucket name")
    STORAGE_ENDPOINT_URL: Optional[str] = Field(default=None, description="Storage endpoint URL")
    STORAGE_ENCRYPT_FILES: bool = Field(default=True, description="Encrypt files in storage")
    AWS_ACCESS_KEY_ID: Optional[str] = Field(default=None, description="AWS access key ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = Field(default=None, description="AWS secret access key")
    AWS_REGION: str = Field(default="us-east-1", description="AWS region")

    # Storage quotas
    DEFAULT_STORAGE_QUOTA_BYTES: int = Field(default=1024*1024*1024, description="Default storage quota (1GB)")
    DEFAULT_FILE_COUNT_QUOTA: int = Field(default=1000, description="Default file count quota")

    # Rate limiting
    RATE_LIMIT_REQUESTS: int = Field(default=100, description="Rate limit requests per window")
    RATE_LIMIT_WINDOW: int = Field(default=60, description="Rate limit window in seconds")

    # AI/LLM settings
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API key")
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, description="Anthropic API key")
    OPENROUTER_API_KEY: Optional[str] = Field(default=None, description="OpenRouter API key")
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434", description="Ollama base URL")

    # Default AI model settings
    DEFAULT_LLM_MODEL: str = Field(default="gpt-4o-mini", description="Default LLM model")
    DEFAULT_EMBEDDING_MODEL: str = Field(default="text-embedding-3-small", description="Default embedding model")

    # E-signature settings
    DOCUSIGN_INTEGRATION_KEY: Optional[str] = Field(default=None, description="DocuSign integration key")
    DOCUSIGN_USER_ID: Optional[str] = Field(default=None, description="DocuSign user ID")
    DOCUSIGN_ACCOUNT_ID: Optional[str] = Field(default=None, description="DocuSign account ID")
    DOCUSIGN_PRIVATE_KEY: Optional[str] = Field(default=None, description="DocuSign private key")
    DOCUSIGN_BASE_URL: str = Field(default="https://demo.docusign.net", description="DocuSign base URL")

    # Logging settings
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format"
    )

    # Security settings
    BCRYPT_ROUNDS: int = Field(default=12, description="Bcrypt hashing rounds")
    SESSION_EXPIRE_HOURS: int = Field(default=24, description="Session expiration in hours")

    # Rate limiting settings
    RATE_LIMIT_REQUESTS: int = Field(default=100, description="Rate limit requests per minute")
    RATE_LIMIT_WINDOW: int = Field(default=60, description="Rate limit window in seconds")

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v):
        """Validate environment setting."""
        allowed_environments = ["development", "staging", "production"]
        if v not in allowed_environments:
            raise ValueError(f"Environment must be one of: {allowed_environments}")
        return v

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, v, info):
        """Validate JWT secret key in production."""
        environment = info.data.get("ENVIRONMENT", "development")
        if environment == "production" and v == "dev-secret-key-change-in-production":
            raise ValueError("JWT_SECRET_KEY must be changed in production environment")
        return v

    @field_validator("ALLOWED_HOSTS")
    @classmethod
    def validate_allowed_hosts(cls, v, info):
        """Validate allowed hosts in production."""
        environment = info.data.get("ENVIRONMENT", "development")
        if environment == "production" and "*" in v:
            raise ValueError("Wildcard hosts not allowed in production environment")
        return v

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    @property
    def STORAGE_BUCKET_NAME_COMPUTED(self) -> str:
        """Get storage bucket name (compatibility with S3_BUCKET_NAME)."""
        return self.S3_BUCKET_NAME

    @property
    def STORAGE_ENDPOINT_URL_COMPUTED(self) -> Optional[str]:
        """Get storage endpoint URL (compatibility with S3_ENDPOINT)."""
        return self.S3_ENDPOINT

    @property
    def AWS_ACCESS_KEY_ID_COMPUTED(self) -> Optional[str]:
        """Get AWS access key ID (compatibility with S3_ACCESS_KEY)."""
        return self.S3_ACCESS_KEY

    @property
    def AWS_SECRET_ACCESS_KEY_COMPUTED(self) -> Optional[str]:
        """Get AWS secret access key (compatibility with S3_SECRET_KEY)."""
        return self.S3_SECRET_KEY

    @property
    def AWS_REGION_COMPUTED(self) -> str:
        """Get AWS region (compatibility with S3_REGION)."""
        return self.S3_REGION


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached application settings.

    This function uses LRU cache to ensure settings are loaded only once
    and reused throughout the application lifecycle.

    Returns:
        Settings: Application settings instance
    """
    return Settings()


# Export settings instance for convenience
settings = get_settings()
