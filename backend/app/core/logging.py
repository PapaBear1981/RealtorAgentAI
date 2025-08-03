"""
Logging configuration for the Multi-Agent Real-Estate Contract Platform.

This module sets up structured logging with appropriate formatters,
handlers, and log levels for different environments.
"""

import logging
import logging.config
import sys
from pathlib import Path
from typing import Dict, Any

from .config import get_settings

settings = get_settings()


def setup_logging() -> None:
    """
    Configure application logging.
    
    Sets up logging with appropriate handlers, formatters, and levels
    based on the current environment and configuration.
    """
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Determine log level
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Configure logging
    logging_config = get_logging_config(log_level)
    logging.config.dictConfig(logging_config)
    
    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured - Level: {settings.LOG_LEVEL}, Environment: {settings.ENVIRONMENT}")


def get_logging_config(log_level: int) -> Dict[str, Any]:
    """
    Get logging configuration dictionary.
    
    Args:
        log_level: Logging level (e.g., logging.INFO)
        
    Returns:
        Dict: Logging configuration for dictConfig
    """
    
    # Base formatter for structured logging
    detailed_formatter = {
        "format": "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(funcName)s | %(message)s",
        "datefmt": "%Y-%m-%d %H:%M:%S",
    }
    
    # Simple formatter for console output
    simple_formatter = {
        "format": "%(levelname)-8s | %(name)s | %(message)s",
    }
    
    # JSON formatter for production (if needed)
    json_formatter = {
        "format": '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "line": %(lineno)d, "function": "%(funcName)s", "message": "%(message)s"}',
        "datefmt": "%Y-%m-%dT%H:%M:%S",
    }
    
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "detailed": detailed_formatter,
            "simple": simple_formatter,
            "json": json_formatter,
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "simple" if settings.DEBUG else "detailed",
                "stream": sys.stdout,
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": log_level,
                "formatter": "detailed",
                "filename": "logs/app.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf8",
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": logging.ERROR,
                "formatter": "detailed",
                "filename": "logs/error.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf8",
            },
        },
        "loggers": {
            # Application loggers
            "app": {
                "level": log_level,
                "handlers": ["console", "file"],
                "propagate": False,
            },
            # FastAPI logger
            "fastapi": {
                "level": log_level,
                "handlers": ["console", "file"],
                "propagate": False,
            },
            # Uvicorn loggers
            "uvicorn": {
                "level": log_level,
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "uvicorn.access": {
                "level": logging.INFO,
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "uvicorn.error": {
                "level": logging.INFO,
                "handlers": ["console", "error_file"],
                "propagate": False,
            },
            # SQLAlchemy logger
            "sqlalchemy": {
                "level": logging.WARNING,
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "sqlalchemy.engine": {
                "level": logging.INFO if settings.DATABASE_ECHO else logging.WARNING,
                "handlers": ["console", "file"],
                "propagate": False,
            },
            # Celery logger
            "celery": {
                "level": log_level,
                "handlers": ["console", "file"],
                "propagate": False,
            },
            # AI/LLM loggers
            "openai": {
                "level": logging.WARNING,
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "anthropic": {
                "level": logging.WARNING,
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "crewai": {
                "level": log_level,
                "handlers": ["console", "file"],
                "propagate": False,
            },
        },
        "root": {
            "level": log_level,
            "handlers": ["console", "file", "error_file"],
        },
    }
    
    # Adjust configuration for production
    if settings.ENVIRONMENT == "production":
        # Use JSON formatter for production
        config["handlers"]["console"]["formatter"] = "json"
        config["handlers"]["file"]["formatter"] = "json"
        
        # Reduce console logging in production
        config["handlers"]["console"]["level"] = logging.WARNING
        
        # Add additional production-specific handlers if needed
        # e.g., syslog, external logging services
    
    return config


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(name)


# Convenience function for getting module loggers
def get_module_logger(module_name: str) -> logging.Logger:
    """
    Get a logger for a specific module.
    
    Args:
        module_name: Module name (e.g., "app.api.auth")
        
    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(f"app.{module_name}")


# Export commonly used functions
__all__ = [
    "setup_logging",
    "get_logger",
    "get_module_logger",
]
