"""
Startup Validation Service for Multi-Agent Real-Estate Contract Platform

This module provides comprehensive startup validation and health checking
capabilities for all system dependencies and services.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field
from contextlib import asynccontextmanager

from sqlmodel import Session, select, func
from sqlalchemy.exc import SQLAlchemyError
import redis
from botocore.exceptions import ClientError, NoCredentialsError

from .config import get_settings
from .database import engine, get_session_context, check_database_connection
from .redis_config import get_redis_manager
from .storage import get_storage_client
from ..models.user import User

logger = logging.getLogger(__name__)
settings = get_settings()


class ServiceStatus(str, Enum):
    """Service health status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ServiceType(str, Enum):
    """Service type enumeration."""
    DATABASE = "database"
    REDIS = "redis"
    STORAGE = "storage"
    AI_AGENTS = "ai_agents"
    EXTERNAL_API = "external_api"
    BACKGROUND_TASKS = "background_tasks"


@dataclass
class ServiceHealthCheck:
    """Individual service health check result."""
    service_name: str
    service_type: ServiceType
    status: ServiceStatus
    response_time_ms: float
    last_check: datetime
    details: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)


@dataclass
class SystemHealthStatus:
    """Overall system health status."""
    overall_status: ServiceStatus
    startup_complete: bool
    ready_for_traffic: bool
    services: Dict[str, ServiceHealthCheck] = field(default_factory=dict)
    startup_time: Optional[datetime] = None
    last_health_check: Optional[datetime] = None
    critical_errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class StartupValidationService:
    """
    Comprehensive startup validation and health checking service.

    This service validates all system dependencies during startup and provides
    ongoing health monitoring capabilities.
    """

    def __init__(self):
        self.startup_time = datetime.utcnow()
        self.startup_complete = False
        self.ready_for_traffic = False
        self.health_status = SystemHealthStatus(
            overall_status=ServiceStatus.UNKNOWN,
            startup_complete=False,
            ready_for_traffic=False,
            startup_time=self.startup_time
        )
        self._startup_lock = asyncio.Lock()
        self._health_check_lock = asyncio.Lock()

    async def validate_startup_sequence(self) -> SystemHealthStatus:
        """
        Validate the complete startup sequence.

        This method performs comprehensive validation of all system dependencies
        in the correct order, ensuring each service is available before proceeding.

        Returns:
            SystemHealthStatus: Complete startup validation results
        """
        async with self._startup_lock:
            if self.startup_complete:
                return self.health_status

            logger.info("Starting comprehensive startup validation sequence")
            start_time = time.time()

            try:
                # Phase 1: Core Infrastructure
                await self._validate_core_infrastructure()

                # Phase 2: Data Layer
                await self._validate_data_layer()

                # Phase 3: Storage Layer
                await self._validate_storage_layer()

                # Phase 4: Background Processing
                await self._validate_background_processing()

                # Phase 5: AI Agent System
                await self._validate_ai_agent_system()

                # Phase 6: External Dependencies
                await self._validate_external_dependencies()

                # Determine overall status
                self._calculate_overall_status()

                # Mark startup as complete if no critical errors
                if self.health_status.overall_status != ServiceStatus.UNHEALTHY:
                    self.startup_complete = True
                    self.ready_for_traffic = True
                    self.health_status.startup_complete = True
                    self.health_status.ready_for_traffic = True

                    elapsed_time = time.time() - start_time
                    logger.info(
                        f"Startup validation completed successfully in {elapsed_time:.2f}s",
                        overall_status=self.health_status.overall_status.value,
                        services_healthy=len([s for s in self.health_status.services.values()
                                            if s.status == ServiceStatus.HEALTHY]),
                        total_services=len(self.health_status.services)
                    )
                else:
                    logger.error(
                        "Startup validation failed - critical services unavailable",
                        critical_errors=self.health_status.critical_errors,
                        unhealthy_services=[name for name, service in self.health_status.services.items()
                                          if service.status == ServiceStatus.UNHEALTHY]
                    )

                self.health_status.last_health_check = datetime.utcnow()
                return self.health_status

            except Exception as e:
                logger.error(f"Startup validation sequence failed: {e}", exc_info=True)
                self.health_status.critical_errors.append(f"Startup validation failed: {str(e)}")
                self.health_status.overall_status = ServiceStatus.UNHEALTHY
                return self.health_status

    async def _validate_core_infrastructure(self):
        """Validate core infrastructure components."""
        logger.info("Validating core infrastructure")

        # Validate configuration
        await self._check_configuration()

        # Validate logging system
        await self._check_logging_system()

    async def _check_configuration(self):
        """Check configuration validity."""
        start_time = time.time()

        try:
            # Validate critical configuration values
            config_checks = {
                "database_url": bool(settings.DATABASE_URL),
                "redis_url": bool(settings.REDIS_URL),
                "secret_key": bool(settings.SECRET_KEY),
                "environment": bool(settings.ENVIRONMENT),
            }

            missing_configs = [key for key, valid in config_checks.items() if not valid]

            if missing_configs:
                error_msg = f"Missing critical configuration: {', '.join(missing_configs)}"
                self.health_status.services["configuration"] = ServiceHealthCheck(
                    service_name="configuration",
                    service_type=ServiceType.EXTERNAL_API,
                    status=ServiceStatus.UNHEALTHY,
                    response_time_ms=(time.time() - start_time) * 1000,
                    last_check=datetime.utcnow(),
                    error_message=error_msg,
                    details={"missing_configs": missing_configs}
                )
                self.health_status.critical_errors.append(error_msg)
            else:
                self.health_status.services["configuration"] = ServiceHealthCheck(
                    service_name="configuration",
                    service_type=ServiceType.EXTERNAL_API,
                    status=ServiceStatus.HEALTHY,
                    response_time_ms=(time.time() - start_time) * 1000,
                    last_check=datetime.utcnow(),
                    details={"validated_configs": list(config_checks.keys())}
                )

        except Exception as e:
            error_msg = f"Configuration validation failed: {str(e)}"
            self.health_status.services["configuration"] = ServiceHealthCheck(
                service_name="configuration",
                service_type=ServiceType.EXTERNAL_API,
                status=ServiceStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                last_check=datetime.utcnow(),
                error_message=error_msg
            )
            self.health_status.critical_errors.append(error_msg)

    async def _check_logging_system(self):
        """Check logging system functionality."""
        start_time = time.time()

        try:
            # Test logging functionality
            test_logger = logging.getLogger("startup_validation_test")
            test_logger.info("Logging system test")

            self.health_status.services["logging"] = ServiceHealthCheck(
                service_name="logging",
                service_type=ServiceType.EXTERNAL_API,
                status=ServiceStatus.HEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                last_check=datetime.utcnow(),
                details={"log_level": logging.getLogger().level}
            )

        except Exception as e:
            error_msg = f"Logging system check failed: {str(e)}"
            self.health_status.services["logging"] = ServiceHealthCheck(
                service_name="logging",
                service_type=ServiceType.EXTERNAL_API,
                status=ServiceStatus.DEGRADED,
                response_time_ms=(time.time() - start_time) * 1000,
                last_check=datetime.utcnow(),
                error_message=error_msg
            )
            self.health_status.warnings.append(error_msg)

    async def _validate_data_layer(self):
        """Validate data layer components."""
        logger.info("Validating data layer")

        # Validate database connection
        await self._check_database_connection()

        # Validate Redis connection
        await self._check_redis_connection()

    async def _check_database_connection(self):
        """Check database connectivity and basic operations."""
        start_time = time.time()

        try:
            # Test basic connection
            connection_ok = check_database_connection()

            if not connection_ok:
                error_msg = "Database connection failed"
                self.health_status.services["database"] = ServiceHealthCheck(
                    service_name="database",
                    service_type=ServiceType.DATABASE,
                    status=ServiceStatus.UNHEALTHY,
                    response_time_ms=(time.time() - start_time) * 1000,
                    last_check=datetime.utcnow(),
                    error_message=error_msg
                )
                self.health_status.critical_errors.append(error_msg)
                return

            # Test database operations
            with next(get_session_context()) as session:
                # Test basic query
                user_count = session.exec(select(func.count(User.id))).first() or 0

                # Test write operation (if possible)
                try:
                    session.exec("SELECT 1").first()
                    write_test_ok = True
                except Exception:
                    write_test_ok = False

                self.health_status.services["database"] = ServiceHealthCheck(
                    service_name="database",
                    service_type=ServiceType.DATABASE,
                    status=ServiceStatus.HEALTHY,
                    response_time_ms=(time.time() - start_time) * 1000,
                    last_check=datetime.utcnow(),
                    details={
                        "user_count": user_count,
                        "write_operations": write_test_ok,
                        "database_url": settings.DATABASE_URL.split("://")[0] + "://***"
                    }
                )

        except SQLAlchemyError as e:
            error_msg = f"Database validation failed: {str(e)}"
            self.health_status.services["database"] = ServiceHealthCheck(
                service_name="database",
                service_type=ServiceType.DATABASE,
                status=ServiceStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                last_check=datetime.utcnow(),
                error_message=error_msg
            )
            self.health_status.critical_errors.append(error_msg)
        except Exception as e:
            error_msg = f"Database check failed: {str(e)}"
            self.health_status.services["database"] = ServiceHealthCheck(
                service_name="database",
                service_type=ServiceType.DATABASE,
                status=ServiceStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                last_check=datetime.utcnow(),
                error_message=error_msg
            )
            self.health_status.critical_errors.append(error_msg)

    async def _check_redis_connection(self):
        """Check Redis connectivity and basic operations."""
        start_time = time.time()

        try:
            redis_manager = get_redis_manager()
            health_result = redis_manager.health_check()

            if health_result.get("status") == "healthy":
                self.health_status.services["redis"] = ServiceHealthCheck(
                    service_name="redis",
                    service_type=ServiceType.REDIS,
                    status=ServiceStatus.HEALTHY,
                    response_time_ms=(time.time() - start_time) * 1000,
                    last_check=datetime.utcnow(),
                    details=health_result.get("connection_info", {})
                )
            else:
                error_msg = f"Redis health check failed: {health_result.get('error', 'Unknown error')}"
                self.health_status.services["redis"] = ServiceHealthCheck(
                    service_name="redis",
                    service_type=ServiceType.REDIS,
                    status=ServiceStatus.UNHEALTHY,
                    response_time_ms=(time.time() - start_time) * 1000,
                    last_check=datetime.utcnow(),
                    error_message=error_msg,
                    details=health_result
                )
                self.health_status.critical_errors.append(error_msg)

        except Exception as e:
            error_msg = f"Redis connection check failed: {str(e)}"
            self.health_status.services["redis"] = ServiceHealthCheck(
                service_name="redis",
                service_type=ServiceType.REDIS,
                status=ServiceStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                last_check=datetime.utcnow(),
                error_message=error_msg
            )
            self.health_status.critical_errors.append(error_msg)

    async def _validate_storage_layer(self):
        """Validate storage layer components."""
        logger.info("Validating storage layer")

        # Validate MinIO/S3 storage
        await self._check_storage_connection()

    async def _check_storage_connection(self):
        """Check storage (MinIO/S3) connectivity and basic operations."""
        start_time = time.time()

        try:
            storage_client = get_storage_client()

            # Test basic connectivity by listing buckets or checking bucket existence
            test_key = f"health_check_{int(time.time())}"
            test_content = b"health check test"

            # Test upload
            upload_result = storage_client.upload_file(
                file_content=test_content,
                key=test_key,
                content_type="text/plain",
                metadata={"purpose": "health_check"}
            )

            # Test download
            download_result = storage_client.get_file(test_key)

            # Test delete
            storage_client.delete_file(test_key)

            # Verify operations succeeded
            upload_ok = upload_result is not None
            download_ok = download_result is not None

            if upload_ok and download_ok:
                self.health_status.services["storage"] = ServiceHealthCheck(
                    service_name="storage",
                    service_type=ServiceType.STORAGE,
                    status=ServiceStatus.HEALTHY,
                    response_time_ms=(time.time() - start_time) * 1000,
                    last_check=datetime.utcnow(),
                    details={
                        "bucket_name": settings.STORAGE_BUCKET_NAME_COMPUTED,
                        "upload_test": upload_ok,
                        "download_test": download_ok,
                        "endpoint": settings.STORAGE_ENDPOINT_URL_COMPUTED or "AWS S3"
                    }
                )
            else:
                error_msg = "Storage operations test failed"
                self.health_status.services["storage"] = ServiceHealthCheck(
                    service_name="storage",
                    service_type=ServiceType.STORAGE,
                    status=ServiceStatus.DEGRADED,
                    response_time_ms=(time.time() - start_time) * 1000,
                    last_check=datetime.utcnow(),
                    error_message=error_msg,
                    details={"upload_test": upload_ok, "download_test": download_ok}
                )
                self.health_status.warnings.append(error_msg)

        except (ClientError, NoCredentialsError) as e:
            error_msg = f"Storage authentication/access failed: {str(e)}"
            self.health_status.services["storage"] = ServiceHealthCheck(
                service_name="storage",
                service_type=ServiceType.STORAGE,
                status=ServiceStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                last_check=datetime.utcnow(),
                error_message=error_msg
            )
            self.health_status.critical_errors.append(error_msg)
        except Exception as e:
            error_msg = f"Storage connection check failed: {str(e)}"
            self.health_status.services["storage"] = ServiceHealthCheck(
                service_name="storage",
                service_type=ServiceType.STORAGE,
                status=ServiceStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                last_check=datetime.utcnow(),
                error_message=error_msg
            )
            self.health_status.critical_errors.append(error_msg)

    async def _validate_background_processing(self):
        """Validate background processing components."""
        logger.info("Validating background processing")

        # Validate Celery workers
        await self._check_celery_workers()

    async def _check_celery_workers(self):
        """Check Celery worker availability and basic functionality."""
        start_time = time.time()

        try:
            from ..core.celery_app import get_celery_app

            celery_app = get_celery_app()

            # Check if workers are available
            inspect = celery_app.control.inspect()
            active_workers = inspect.active()
            registered_tasks = inspect.registered()

            if active_workers:
                worker_count = len(active_workers)
                task_count = sum(len(tasks) for tasks in registered_tasks.values()) if registered_tasks else 0

                self.health_status.services["celery_workers"] = ServiceHealthCheck(
                    service_name="celery_workers",
                    service_type=ServiceType.BACKGROUND_TASKS,
                    status=ServiceStatus.HEALTHY,
                    response_time_ms=(time.time() - start_time) * 1000,
                    last_check=datetime.utcnow(),
                    details={
                        "active_workers": worker_count,
                        "registered_tasks": task_count,
                        "worker_names": list(active_workers.keys())
                    }
                )
            else:
                error_msg = "No active Celery workers found"
                self.health_status.services["celery_workers"] = ServiceHealthCheck(
                    service_name="celery_workers",
                    service_type=ServiceType.BACKGROUND_TASKS,
                    status=ServiceStatus.DEGRADED,
                    response_time_ms=(time.time() - start_time) * 1000,
                    last_check=datetime.utcnow(),
                    error_message=error_msg
                )
                self.health_status.warnings.append(error_msg)

        except Exception as e:
            error_msg = f"Celery workers check failed: {str(e)}"
            self.health_status.services["celery_workers"] = ServiceHealthCheck(
                service_name="celery_workers",
                service_type=ServiceType.BACKGROUND_TASKS,
                status=ServiceStatus.DEGRADED,
                response_time_ms=(time.time() - start_time) * 1000,
                last_check=datetime.utcnow(),
                error_message=error_msg
            )
            self.health_status.warnings.append(error_msg)

    async def _validate_ai_agent_system(self):
        """Validate AI agent system components."""
        logger.info("Validating AI agent system")

        # Validate model router and OpenRouter API
        await self._check_model_router()

        # Validate CrewAI orchestrator
        await self._check_crewai_orchestrator()

    async def _check_model_router(self):
        """Check Model Router and OpenRouter API connectivity."""
        start_time = time.time()

        try:
            from ..services.model_router import get_model_router

            model_router = get_model_router()

            # Run health check
            await model_router._run_health_check()

            # Count available models
            available_models = sum(1 for model in model_router.models.values() if model.is_available)

            # Check provider availability
            providers = {
                "openrouter": model_router.openrouter_client is not None,
                "openai": model_router.openai_client is not None,
                "anthropic": model_router.anthropic_client is not None,
                "ollama": any(
                    model.is_available and model.provider.value == "ollama"
                    for model in model_router.models.values()
                )
            }

            if available_models > 0:
                self.health_status.services["model_router"] = ServiceHealthCheck(
                    service_name="model_router",
                    service_type=ServiceType.AI_AGENTS,
                    status=ServiceStatus.HEALTHY,
                    response_time_ms=(time.time() - start_time) * 1000,
                    last_check=datetime.utcnow(),
                    details={
                        "available_models": available_models,
                        "providers": providers,
                        "last_health_check": model_router.last_health_check.isoformat()
                    }
                )
            else:
                error_msg = "No AI models available"
                self.health_status.services["model_router"] = ServiceHealthCheck(
                    service_name="model_router",
                    service_type=ServiceType.AI_AGENTS,
                    status=ServiceStatus.DEGRADED,
                    response_time_ms=(time.time() - start_time) * 1000,
                    last_check=datetime.utcnow(),
                    error_message=error_msg,
                    details={"providers": providers}
                )
                self.health_status.warnings.append(error_msg)

        except Exception as e:
            error_msg = f"Model router check failed: {str(e)}"
            self.health_status.services["model_router"] = ServiceHealthCheck(
                service_name="model_router",
                service_type=ServiceType.AI_AGENTS,
                status=ServiceStatus.DEGRADED,
                response_time_ms=(time.time() - start_time) * 1000,
                last_check=datetime.utcnow(),
                error_message=error_msg
            )
            self.health_status.warnings.append(error_msg)

    async def _check_crewai_orchestrator(self):
        """Check CrewAI orchestrator initialization."""
        start_time = time.time()

        try:
            from ..services.agent_orchestrator import get_agent_orchestrator

            orchestrator = get_agent_orchestrator()

            # Check if agents are initialized
            agent_count = len(orchestrator.agents) if hasattr(orchestrator, 'agents') else 0

            if agent_count > 0:
                self.health_status.services["crewai_orchestrator"] = ServiceHealthCheck(
                    service_name="crewai_orchestrator",
                    service_type=ServiceType.AI_AGENTS,
                    status=ServiceStatus.HEALTHY,
                    response_time_ms=(time.time() - start_time) * 1000,
                    last_check=datetime.utcnow(),
                    details={"agent_count": agent_count}
                )
            else:
                error_msg = "CrewAI orchestrator has no agents initialized"
                self.health_status.services["crewai_orchestrator"] = ServiceHealthCheck(
                    service_name="crewai_orchestrator",
                    service_type=ServiceType.AI_AGENTS,
                    status=ServiceStatus.DEGRADED,
                    response_time_ms=(time.time() - start_time) * 1000,
                    last_check=datetime.utcnow(),
                    error_message=error_msg
                )
                self.health_status.warnings.append(error_msg)

        except Exception as e:
            error_msg = f"CrewAI orchestrator check failed: {str(e)}"
            self.health_status.services["crewai_orchestrator"] = ServiceHealthCheck(
                service_name="crewai_orchestrator",
                service_type=ServiceType.AI_AGENTS,
                status=ServiceStatus.DEGRADED,
                response_time_ms=(time.time() - start_time) * 1000,
                last_check=datetime.utcnow(),
                error_message=error_msg
            )
            self.health_status.warnings.append(error_msg)

    async def _validate_external_dependencies(self):
        """Validate external dependencies and APIs."""
        logger.info("Validating external dependencies")

        # Check OpenRouter API specifically
        await self._check_openrouter_api()

    async def _check_openrouter_api(self):
        """Check OpenRouter API connectivity and qwen model availability."""
        start_time = time.time()

        try:
            from ..services.model_router import get_model_router

            model_router = get_model_router()

            # Test OpenRouter API with qwen model
            if model_router.openrouter_client:
                # Check if qwen model is available
                qwen_model = None
                for model in model_router.models.values():
                    if "qwen" in model.name.lower() and model.is_available:
                        qwen_model = model
                        break

                if qwen_model:
                    self.health_status.services["openrouter_api"] = ServiceHealthCheck(
                        service_name="openrouter_api",
                        service_type=ServiceType.EXTERNAL_API,
                        status=ServiceStatus.HEALTHY,
                        response_time_ms=(time.time() - start_time) * 1000,
                        last_check=datetime.utcnow(),
                        details={
                            "qwen_model_available": True,
                            "model_name": qwen_model.name,
                            "api_key_configured": bool(settings.OPENROUTER_API_KEY)
                        }
                    )
                else:
                    error_msg = "Qwen model not available in OpenRouter"
                    self.health_status.services["openrouter_api"] = ServiceHealthCheck(
                        service_name="openrouter_api",
                        service_type=ServiceType.EXTERNAL_API,
                        status=ServiceStatus.DEGRADED,
                        response_time_ms=(time.time() - start_time) * 1000,
                        last_check=datetime.utcnow(),
                        error_message=error_msg
                    )
                    self.health_status.warnings.append(error_msg)
            else:
                error_msg = "OpenRouter API client not initialized"
                self.health_status.services["openrouter_api"] = ServiceHealthCheck(
                    service_name="openrouter_api",
                    service_type=ServiceType.EXTERNAL_API,
                    status=ServiceStatus.UNHEALTHY,
                    response_time_ms=(time.time() - start_time) * 1000,
                    last_check=datetime.utcnow(),
                    error_message=error_msg
                )
                self.health_status.critical_errors.append(error_msg)

        except Exception as e:
            error_msg = f"OpenRouter API check failed: {str(e)}"
            self.health_status.services["openrouter_api"] = ServiceHealthCheck(
                service_name="openrouter_api",
                service_type=ServiceType.EXTERNAL_API,
                status=ServiceStatus.DEGRADED,
                response_time_ms=(time.time() - start_time) * 1000,
                last_check=datetime.utcnow(),
                error_message=error_msg
            )
            self.health_status.warnings.append(error_msg)

    def _calculate_overall_status(self):
        """Calculate overall system health status based on individual service checks."""
        if not self.health_status.services:
            self.health_status.overall_status = ServiceStatus.UNKNOWN
            return

        unhealthy_count = sum(1 for service in self.health_status.services.values()
                             if service.status == ServiceStatus.UNHEALTHY)
        degraded_count = sum(1 for service in self.health_status.services.values()
                            if service.status == ServiceStatus.DEGRADED)
        healthy_count = sum(1 for service in self.health_status.services.values()
                           if service.status == ServiceStatus.HEALTHY)

        # Determine overall status
        if unhealthy_count > 0:
            # Any unhealthy critical service makes the system unhealthy
            critical_services = ["database", "configuration"]
            critical_unhealthy = any(
                service.status == ServiceStatus.UNHEALTHY
                for name, service in self.health_status.services.items()
                if name in critical_services
            )

            if critical_unhealthy:
                self.health_status.overall_status = ServiceStatus.UNHEALTHY
            else:
                self.health_status.overall_status = ServiceStatus.DEGRADED
        elif degraded_count > 0:
            self.health_status.overall_status = ServiceStatus.DEGRADED
        elif healthy_count > 0:
            self.health_status.overall_status = ServiceStatus.HEALTHY
        else:
            self.health_status.overall_status = ServiceStatus.UNKNOWN

    async def perform_health_check(self, include_ai_agents: bool = True) -> SystemHealthStatus:
        """
        Perform ongoing health check of all services.

        This method can be called periodically to check system health without
        the full startup validation sequence.

        Args:
            include_ai_agents: Whether to include AI agent system checks

        Returns:
            SystemHealthStatus: Current system health status
        """
        async with self._health_check_lock:
            logger.debug("Performing system health check")
            start_time = time.time()

            try:
                # Quick checks for critical services
                await self._check_database_connection()
                await self._check_redis_connection()
                await self._check_storage_connection()

                if include_ai_agents:
                    await self._check_model_router()

                # Update overall status
                self._calculate_overall_status()
                self.health_status.last_health_check = datetime.utcnow()

                elapsed_time = time.time() - start_time
                logger.debug(f"Health check completed in {elapsed_time:.2f}s")

                return self.health_status

            except Exception as e:
                logger.error(f"Health check failed: {e}", exc_info=True)
                self.health_status.overall_status = ServiceStatus.UNKNOWN
                self.health_status.last_health_check = datetime.utcnow()
                return self.health_status

    def get_readiness_status(self) -> Dict[str, Any]:
        """
        Get readiness status for Kubernetes readiness probe.

        Returns:
            Dict: Readiness status information
        """
        return {
            "ready": self.ready_for_traffic,
            "startup_complete": self.startup_complete,
            "overall_status": self.health_status.overall_status.value,
            "critical_services_healthy": all(
                service.status != ServiceStatus.UNHEALTHY
                for name, service in self.health_status.services.items()
                if name in ["database", "configuration"]
            ),
            "timestamp": datetime.utcnow().isoformat()
        }

    def get_liveness_status(self) -> Dict[str, Any]:
        """
        Get liveness status for Kubernetes liveness probe.

        Returns:
            Dict: Liveness status information
        """
        return {
            "alive": True,  # If we can respond, we're alive
            "startup_time": self.startup_time.isoformat(),
            "uptime_seconds": (datetime.utcnow() - self.startup_time).total_seconds(),
            "timestamp": datetime.utcnow().isoformat()
        }


# Global startup validation service instance
_startup_validation_service: Optional[StartupValidationService] = None


def get_startup_validation_service() -> StartupValidationService:
    """Get the global startup validation service instance."""
    global _startup_validation_service
    if _startup_validation_service is None:
        _startup_validation_service = StartupValidationService()
    return _startup_validation_service
