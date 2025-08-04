"""
Enhanced Logging and Debugging Configuration for AI Agents.

This module provides comprehensive logging, debugging, and monitoring
capabilities specifically designed for AI agent operations and LLM interactions.
"""

import asyncio
import logging
import json
import time
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from functools import wraps
from contextlib import contextmanager

import structlog
from structlog.stdlib import LoggerFactory

from .config import get_settings

settings = get_settings()


class AIAgentLogger:
    """Enhanced logger for AI agent operations."""

    def __init__(self, name: str):
        self.name = name
        self.logger = structlog.get_logger(name)
        self._request_context = {}

    def log_llm_request(self,
                       model: str,
                       messages: List[Dict[str, str]],
                       request_id: Optional[str] = None,
                       **kwargs) -> str:
        """Log LLM request with full context."""
        request_id = request_id or str(uuid.uuid4())

        self.logger.info(
            "LLM request initiated",
            request_id=request_id,
            model=model,
            message_count=len(messages),
            total_chars=sum(len(msg.get("content", "")) for msg in messages),
            max_tokens=kwargs.get("max_tokens"),
            temperature=kwargs.get("temperature"),
            timestamp=datetime.utcnow().isoformat()
        )

        # Store request context for correlation
        self._request_context[request_id] = {
            "start_time": time.time(),
            "model": model,
            "messages": messages,
            "kwargs": kwargs
        }

        return request_id

    def log_llm_response(self,
                        request_id: str,
                        response_content: str,
                        model_used: str,
                        cost: float,
                        processing_time: float,
                        token_usage: Dict[str, int],
                        **metadata):
        """Log LLM response with metrics."""
        request_context = self._request_context.get(request_id, {})

        self.logger.info(
            "LLM response received",
            request_id=request_id,
            model_used=model_used,
            response_length=len(response_content),
            cost=cost,
            processing_time=processing_time,
            token_usage=token_usage,
            tokens_per_second=token_usage.get("completion_tokens", 0) / processing_time if processing_time > 0 else 0,
            cost_per_token=cost / token_usage.get("total_tokens", 1) if token_usage.get("total_tokens", 0) > 0 else 0,
            timestamp=datetime.utcnow().isoformat(),
            **metadata
        )

        # Clean up request context
        if request_id in self._request_context:
            del self._request_context[request_id]

    def log_llm_error(self,
                     request_id: str,
                     error: Exception,
                     error_type: str = "unknown",
                     retry_count: int = 0):
        """Log LLM errors with context."""
        request_context = self._request_context.get(request_id, {})

        self.logger.error(
            "LLM request failed",
            request_id=request_id,
            error_type=error_type,
            error_message=str(error),
            retry_count=retry_count,
            model=request_context.get("model"),
            elapsed_time=time.time() - request_context.get("start_time", time.time()),
            timestamp=datetime.utcnow().isoformat()
        )

    def log_agent_workflow_start(self,
                                workflow_id: str,
                                agent_role: str,
                                task_description: str,
                                context: Dict[str, Any]):
        """Log agent workflow initiation."""
        self.logger.info(
            "Agent workflow started",
            workflow_id=workflow_id,
            agent_role=agent_role,
            task_description=task_description,
            context_keys=list(context.keys()),
            context_size=len(json.dumps(context)),
            timestamp=datetime.utcnow().isoformat()
        )

    def log_agent_workflow_complete(self,
                                   workflow_id: str,
                                   status: str,
                                   execution_time: float,
                                   cost: float,
                                   results: Dict[str, Any]):
        """Log agent workflow completion."""
        self.logger.info(
            "Agent workflow completed",
            workflow_id=workflow_id,
            status=status,
            execution_time=execution_time,
            cost=cost,
            result_keys=list(results.keys()),
            result_size=len(json.dumps(results)),
            timestamp=datetime.utcnow().isoformat()
        )

    def log_performance_metrics(self,
                               operation: str,
                               duration: float,
                               memory_usage: Optional[float] = None,
                               **metrics):
        """Log performance metrics."""
        self.logger.info(
            "Performance metrics",
            operation=operation,
            duration=duration,
            memory_usage=memory_usage,
            timestamp=datetime.utcnow().isoformat(),
            **metrics
        )


def configure_ai_agent_logging():
    """Configure structured logging for AI agents."""

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=None,
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    )

    # Set specific logger levels
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)


def get_ai_agent_logger(name: str) -> AIAgentLogger:
    """Get an AI agent logger instance."""
    return AIAgentLogger(name)


def log_llm_interaction(logger_name: str = None):
    """Decorator to automatically log LLM interactions."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = get_ai_agent_logger(logger_name or func.__module__)
            request_id = str(uuid.uuid4())

            # Extract request details from args or kwargs
            request_obj = args[1] if len(args) > 1 else kwargs.get("request")
            if request_obj and hasattr(request_obj, 'model_preference'):
                model = request_obj.model_preference
                messages = request_obj.messages
            else:
                model = kwargs.get("model_preference", "unknown")
                messages = kwargs.get("messages", [])

            # Log request
            logger.log_llm_request(model, messages, request_id, **kwargs)

            try:
                start_time = time.time()
                result = await func(*args, **kwargs)
                end_time = time.time()

                # Log successful response
                if hasattr(result, 'content'):
                    logger.log_llm_response(
                        request_id=request_id,
                        response_content=result.content,
                        model_used=getattr(result, 'model_used', model),
                        cost=getattr(result, 'cost', 0),
                        processing_time=end_time - start_time,
                        token_usage=getattr(result, 'token_usage', {})
                    )

                return result

            except Exception as e:
                # Log error
                logger.log_llm_error(request_id, e, type(e).__name__)
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = get_ai_agent_logger(logger_name or func.__module__)
            request_id = str(uuid.uuid4())

            # Extract request details from args or kwargs
            request_obj = args[1] if len(args) > 1 else kwargs.get("request")
            if request_obj and hasattr(request_obj, 'model_preference'):
                model = request_obj.model_preference
                messages = request_obj.messages
            else:
                model = kwargs.get("model_preference", "unknown")
                messages = kwargs.get("messages", [])

            # Log request
            logger.log_llm_request(model, messages, request_id, **kwargs)

            try:
                start_time = time.time()
                result = func(*args, **kwargs)
                end_time = time.time()

                # Log successful response
                if hasattr(result, 'content'):
                    logger.log_llm_response(
                        request_id=request_id,
                        response_content=result.content,
                        model_used=getattr(result, 'model_used', model),
                        cost=getattr(result, 'cost', 0),
                        processing_time=end_time - start_time,
                        token_usage=getattr(result, 'token_usage', {})
                    )

                return result

            except Exception as e:
                # Log error
                logger.log_llm_error(request_id, e, type(e).__name__)
                raise

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


@contextmanager
def agent_workflow_context(workflow_id: str, agent_role: str, logger_name: str = None):
    """Context manager for agent workflow logging."""
    logger = get_ai_agent_logger(logger_name or "agent_workflow")
    start_time = time.time()

    try:
        yield logger
    except Exception as e:
        execution_time = time.time() - start_time
        logger.log_agent_workflow_complete(
            workflow_id=workflow_id,
            status="failed",
            execution_time=execution_time,
            cost=0,
            results={"error": str(e)}
        )
        raise
    else:
        execution_time = time.time() - start_time
        logger.log_agent_workflow_complete(
            workflow_id=workflow_id,
            status="completed",
            execution_time=execution_time,
            cost=0,  # Will be updated by actual implementation
            results={}  # Will be updated by actual implementation
        )


class DebugMode:
    """Debug mode utilities for AI agents."""

    @staticmethod
    def is_enabled() -> bool:
        """Check if debug mode is enabled."""
        return settings.DEBUG or settings.LOG_LEVEL.upper() == "DEBUG"

    @staticmethod
    def log_request_details(request_data: Dict[str, Any], logger: AIAgentLogger):
        """Log detailed request information in debug mode."""
        if DebugMode.is_enabled():
            logger.logger.debug(
                "Debug: Request details",
                request_data=request_data,
                timestamp=datetime.utcnow().isoformat()
            )

    @staticmethod
    def log_response_details(response_data: Dict[str, Any], logger: AIAgentLogger):
        """Log detailed response information in debug mode."""
        if DebugMode.is_enabled():
            logger.logger.debug(
                "Debug: Response details",
                response_data=response_data,
                timestamp=datetime.utcnow().isoformat()
            )


# Initialize logging configuration
configure_ai_agent_logging()
