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
from .core.startup_validation import get_startup_validation_service
from .core.security import (
    rate_limit_middleware,
    security_headers_middleware,
    log_requests_middleware,
    validate_request_size
)

# Import routers
from .api import auth, files, contracts, templates, signatures, webhooks, admin, tasks, model_router, agent_orchestrator
from .api.v1 import ai_agents, ai_agents_ws, advanced_agents, performance, analytics

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

    # Initialize Celery and Redis connections
    try:
        from .core.celery_app import get_celery_app
        from .core.redis_config import get_redis_manager

        celery_app = get_celery_app()
        redis_manager = get_redis_manager()

        # Test Redis connection
        redis_health = redis_manager.health_check()
        if redis_health["status"] == "healthy":
            logger.info("Redis connection established successfully")
        else:
            logger.warning("Redis connection issues detected", extra={"health": redis_health})

        logger.info("Background processing system initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize background processing: {e}")
        # Continue startup even if background processing fails

    # Run comprehensive startup validation
    try:
        startup_service = get_startup_validation_service()
        validation_result = await startup_service.validate_startup_sequence()

        if validation_result.overall_status == "healthy":
            logger.info("All startup validation checks passed successfully")
        elif validation_result.overall_status == "degraded":
            logger.warning(
                "Startup validation completed with warnings",
                warnings=validation_result.warnings,
                degraded_services=[name for name, service in validation_result.services.items()
                                 if service.status == "degraded"]
            )
        else:
            logger.error(
                "Startup validation failed - some services are unhealthy",
                critical_errors=validation_result.critical_errors,
                unhealthy_services=[name for name, service in validation_result.services.items()
                                  if service.status == "unhealthy"]
            )

    except Exception as e:
        logger.error(f"Startup validation failed: {e}")
        # Continue startup even if validation fails

    yield

    # Shutdown
    logger.info("Shutting down Multi-Agent Real-Estate Contract Platform Backend")

    # Close Redis connections
    try:
        from .core.redis_config import get_redis_manager
        redis_manager = get_redis_manager()
        redis_manager.close()
        logger.info("Redis connections closed successfully")
    except Exception as e:
        logger.error(f"Error closing Redis connections: {e}")


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
        {
            "name": "analytics",
            "description": "Analytics and reporting operations",
        },
    ],
    lifespan=lifespan,
)

# Add middleware
# Add specific frontend origins for development
frontend_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001"
]
allowed_origins = settings.ALLOWED_HOSTS + frontend_origins if settings.ALLOWED_HOSTS != ["*"] else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
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


# Enhanced Health Check Endpoints

@app.get("/health", tags=["system"])
async def health_check():
    """
    Basic health check endpoint for monitoring and load balancers.

    This endpoint provides a quick health status without detailed service checks.
    Use /health/detailed for comprehensive health information.
    """
    startup_service = get_startup_validation_service()

    # Perform quick health check
    health_status = await startup_service.perform_health_check(include_ai_agents=False)

    return {
        "status": health_status.overall_status.value,
        "timestamp": time.time(),
        "version": "0.1.0",
        "environment": settings.ENVIRONMENT,
        "startup_complete": health_status.startup_complete,
        "ready_for_traffic": health_status.ready_for_traffic,
        "services_healthy": len([s for s in health_status.services.values()
                               if s.status.value == "healthy"]),
        "total_services": len(health_status.services)
    }


@app.get("/health/detailed", tags=["system"])
async def detailed_health_check():
    """
    Detailed health check endpoint with comprehensive service status.

    Returns detailed information about all system components and their health status.
    """
    startup_service = get_startup_validation_service()

    # Perform comprehensive health check
    health_status = await startup_service.perform_health_check(include_ai_agents=True)

    # Format service details for response
    services = {}
    for name, service in health_status.services.items():
        services[name] = {
            "status": service.status.value,
            "response_time_ms": service.response_time_ms,
            "last_check": service.last_check.isoformat(),
            "details": service.details,
            "error_message": service.error_message
        }

    return {
        "overall_status": health_status.overall_status.value,
        "startup_complete": health_status.startup_complete,
        "ready_for_traffic": health_status.ready_for_traffic,
        "startup_time": health_status.startup_time.isoformat() if health_status.startup_time else None,
        "last_health_check": health_status.last_health_check.isoformat() if health_status.last_health_check else None,
        "services": services,
        "critical_errors": health_status.critical_errors,
        "warnings": health_status.warnings,
        "timestamp": time.time(),
        "version": "0.1.0",
        "environment": settings.ENVIRONMENT
    }


@app.get("/health/ready", tags=["system"])
async def readiness_probe():
    """
    Kubernetes readiness probe endpoint.

    Returns 200 if the application is ready to serve traffic, 503 otherwise.
    """
    startup_service = get_startup_validation_service()
    readiness_status = startup_service.get_readiness_status()

    if readiness_status["ready"]:
        return readiness_status
    else:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Application not ready to serve traffic"
        )


@app.get("/health/live", tags=["system"])
async def liveness_probe():
    """
    Kubernetes liveness probe endpoint.

    Returns 200 if the application is alive and running.
    """
    startup_service = get_startup_validation_service()
    return startup_service.get_liveness_status()


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
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(model_router.router, prefix="/ai-agents/model-router", tags=["ai-agents"])
app.include_router(agent_orchestrator.router, tags=["ai-agents"])
app.include_router(ai_agents.router, prefix="/api/v1", tags=["ai-agents"])
app.include_router(ai_agents_ws.ws_router, prefix="/api/v1", tags=["ai-agents-websocket"])
app.include_router(advanced_agents.router, prefix="/api/v1", tags=["advanced-ai-agents"])
app.include_router(performance.router, prefix="/api/v1", tags=["performance-optimization"])
app.include_router(analytics.router, prefix="/api/v1", tags=["analytics"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug",
    )
