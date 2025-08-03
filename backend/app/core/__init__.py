"""
Core module for the Multi-Agent Real-Estate Contract Platform.

This module contains core functionality including configuration,
database management, logging, and other foundational components.
"""

from .config import get_settings, settings
from .database import (
    engine,
    create_db_and_tables,
    get_session,
    get_session_context,
    check_database_connection,
    get_database_info,
)
from .logging import setup_logging, get_logger, get_module_logger
from .auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
    create_token_response,
)
from .dependencies import (
    oauth2_scheme,
    get_current_user,
    get_current_active_user,
    require_role,
    require_admin,
    require_agent_or_admin,
    require_tc_or_admin,
)
from .security import (
    RateLimiter,
    sanitize_input,
    rate_limit_middleware,
    security_headers_middleware,
)

__all__ = [
    # Configuration
    "get_settings",
    "settings",

    # Database
    "engine",
    "create_db_and_tables",
    "get_session",
    "get_session_context",
    "check_database_connection",
    "get_database_info",

    # Logging
    "setup_logging",
    "get_logger",
    "get_module_logger",

    # Authentication
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    "create_token_response",

    # Dependencies
    "oauth2_scheme",
    "get_current_user",
    "get_current_active_user",
    "require_role",
    "require_admin",
    "require_agent_or_admin",
    "require_tc_or_admin",

    # Security
    "RateLimiter",
    "sanitize_input",
    "rate_limit_middleware",
    "security_headers_middleware",
]
