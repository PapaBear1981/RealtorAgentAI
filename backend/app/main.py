"""
Multi-Agent Real-Estate Contract Platform - FastAPI Backend
Main application entry point

This module initializes the FastAPI application and configures all routers,
middleware, and core functionality according to the specification.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import time
import logging
from contextlib import asynccontextmanager

from .core.config import get_settings
from .core.database import create_db_and_tables
from .core.logging import setup_logging
from .core.security import (
    rate_limit_middleware,
    security_headers_middleware,
    log_requests_middleware,
    validate_request_size
)

# Import routers
from .api import auth, files, contracts, templates, signatures, webhooks, admin

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.

    This handles database initialization and cleanup operations.
    """
    # Startup
    logger.info("Starting Multi-Agent Real-Estate Contract Platform Backend")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")

    # Initialize database
    try:
        create_db_and_tables()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Multi-Agent Real-Estate Contract Platform Backend")


# Create FastAPI application
app = FastAPI(
    title="Multi-Agent Real-Estate Contract Platform API",
    description="""
    A comprehensive platform for automating real estate contract workflows with AI agents.

    ## Features

    * **Document Ingestion**: Upload and parse PDF, DOCX, and image documents
    * **AI-Powered Extraction**: Extract entities and data with confidence scoring
    * **Contract Generation**: Generate standardized contracts from templates
    * **Multi-Party Signatures**: Track and manage e-signature workflows
    * **Compliance Checking**: Validate contracts against rules and regulations
    * **Audit Trails**: Comprehensive logging of all actions and changes

    ## Authentication

    This API uses JWT (JSON Web Tokens) for authentication. Include the token in the
    Authorization header: `Authorization: Bearer <token>`
    """,
    version="0.1.0",
    contact={
        "name": "Chris",
        "email": "107969875+PapaBear1981@users.noreply.github.com",
    },
    license_info={
        "name": "MIT",
    },
    openapi_tags=[
        {
            "name": "auth",
            "description": "Authentication and user management operations",
        },
        {
            "name": "files",
            "description": "File upload and storage operations",
        },
        {
            "name": "contracts",
            "description": "Contract management and generation operations",
        },
        {
            "name": "signatures",
            "description": "E-signature workflow operations",
        },
        {
            "name": "admin",
            "description": "Administrative operations and system management",
        },
        {
            "name": "ai-agents",
            "description": "AI agent operations and orchestration",
        },
    ],
    lifespan=lifespan,
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS,
    )


# Security middleware
app.middleware("http")(rate_limit_middleware)
app.middleware("http")(security_headers_middleware)
app.middleware("http")(log_requests_middleware)
app.middleware("http")(validate_request_size())

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time header to all responses."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error_id": f"error_{int(time.time())}",
        },
    )


# Health check endpoint
@app.get("/health", tags=["system"])
async def health_check():
    """
    Health check endpoint for monitoring and load balancers.

    Returns the current status of the application and its dependencies.
    """
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "0.1.0",
        "environment": settings.ENVIRONMENT,
        "database": "connected",  # Will be enhanced with actual DB health check
    }


# Root endpoint
@app.get("/", tags=["system"])
async def root():
    """
    Root endpoint providing API information.

    Returns basic information about the API and available endpoints.
    """
    return {
        "message": "Multi-Agent Real-Estate Contract Platform API",
        "version": "0.1.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
    }


# Include routers
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(files.router, prefix="/files", tags=["files"])
app.include_router(contracts.router, prefix="/contracts", tags=["contracts"])
app.include_router(templates.router, prefix="/templates", tags=["templates"])
app.include_router(signatures.router, prefix="/signatures", tags=["signatures"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug",
    )
