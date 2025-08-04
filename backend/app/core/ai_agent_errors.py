"""
AI Agent Error Handling and Recovery.

This module provides comprehensive error handling, recovery mechanisms,
and fallback strategies for AI agent operations.
"""

import traceback
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
import asyncio

import structlog
from pydantic import BaseModel

logger = structlog.get_logger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification."""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    AGENT_EXECUTION = "agent_execution"
    TOOL_FAILURE = "tool_failure"
    WORKFLOW = "workflow"
    NETWORK = "network"
    DATABASE = "database"
    EXTERNAL_SERVICE = "external_service"
    SYSTEM = "system"
    UNKNOWN = "unknown"


class RecoveryStrategy(Enum):
    """Recovery strategies for different error types."""
    RETRY = "retry"
    FALLBACK = "fallback"
    SKIP = "skip"
    ABORT = "abort"
    MANUAL_INTERVENTION = "manual_intervention"


class AgentError(BaseModel):
    """Structured error information for agent operations."""
    error_id: str
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    context: Dict[str, Any]
    stack_trace: Optional[str] = None
    recovery_strategy: Optional[RecoveryStrategy] = None
    retry_count: int = 0
    max_retries: int = 3


class ErrorHandler:
    """Centralized error handling for AI agent operations."""
    
    def __init__(self):
        self.error_history: List[AgentError] = []
        self.recovery_strategies: Dict[ErrorCategory, RecoveryStrategy] = {
            ErrorCategory.AUTHENTICATION: RecoveryStrategy.ABORT,
            ErrorCategory.AUTHORIZATION: RecoveryStrategy.ABORT,
            ErrorCategory.VALIDATION: RecoveryStrategy.ABORT,
            ErrorCategory.AGENT_EXECUTION: RecoveryStrategy.RETRY,
            ErrorCategory.TOOL_FAILURE: RecoveryStrategy.FALLBACK,
            ErrorCategory.WORKFLOW: RecoveryStrategy.RETRY,
            ErrorCategory.NETWORK: RecoveryStrategy.RETRY,
            ErrorCategory.DATABASE: RecoveryStrategy.RETRY,
            ErrorCategory.EXTERNAL_SERVICE: RecoveryStrategy.FALLBACK,
            ErrorCategory.SYSTEM: RecoveryStrategy.MANUAL_INTERVENTION,
            ErrorCategory.UNKNOWN: RecoveryStrategy.RETRY,
        }
        self.fallback_handlers: Dict[str, Callable] = {}
    
    def classify_error(self, error: Exception, context: Dict[str, Any] = None) -> ErrorCategory:
        """Classify an error into a category."""
        error_type = type(error).__name__
        error_message = str(error).lower()
        
        # Authentication errors
        if "unauthorized" in error_message or "authentication" in error_message:
            return ErrorCategory.AUTHENTICATION
        
        # Authorization errors
        if "forbidden" in error_message or "permission" in error_message:
            return ErrorCategory.AUTHORIZATION
        
        # Validation errors
        if "validation" in error_message or "invalid" in error_message:
            return ErrorCategory.VALIDATION
        
        # Network errors
        if any(keyword in error_message for keyword in ["connection", "timeout", "network", "unreachable"]):
            return ErrorCategory.NETWORK
        
        # Database errors
        if any(keyword in error_message for keyword in ["database", "sql", "connection pool"]):
            return ErrorCategory.DATABASE
        
        # Tool-specific errors
        if context and context.get("tool_name"):
            return ErrorCategory.TOOL_FAILURE
        
        # Agent execution errors
        if context and context.get("agent_role"):
            return ErrorCategory.AGENT_EXECUTION
        
        # Workflow errors
        if context and context.get("workflow_id"):
            return ErrorCategory.WORKFLOW
        
        return ErrorCategory.UNKNOWN
    
    def assess_severity(self, error: Exception, category: ErrorCategory, context: Dict[str, Any] = None) -> ErrorSeverity:
        """Assess the severity of an error."""
        # Critical errors that require immediate attention
        if category in [ErrorCategory.SYSTEM, ErrorCategory.DATABASE]:
            return ErrorSeverity.CRITICAL
        
        # High severity errors that significantly impact functionality
        if category in [ErrorCategory.AUTHENTICATION, ErrorCategory.AUTHORIZATION]:
            return ErrorSeverity.HIGH
        
        # Medium severity errors that impact specific operations
        if category in [ErrorCategory.AGENT_EXECUTION, ErrorCategory.WORKFLOW]:
            return ErrorSeverity.MEDIUM
        
        # Low severity errors that have minimal impact
        return ErrorSeverity.LOW
    
    async def handle_error(
        self,
        error: Exception,
        context: Dict[str, Any] = None,
        error_id: str = None
    ) -> AgentError:
        """Handle an error with appropriate recovery strategy."""
        import uuid
        
        if not error_id:
            error_id = str(uuid.uuid4())
        
        category = self.classify_error(error, context)
        severity = self.assess_severity(error, category, context)
        recovery_strategy = self.recovery_strategies.get(category, RecoveryStrategy.ABORT)
        
        agent_error = AgentError(
            error_id=error_id,
            category=category,
            severity=severity,
            message=str(error),
            details={"error_type": type(error).__name__},
            timestamp=datetime.utcnow(),
            context=context or {},
            stack_trace=traceback.format_exc(),
            recovery_strategy=recovery_strategy,
            retry_count=0,
            max_retries=self._get_max_retries(category)
        )
        
        # Log the error
        await self._log_error(agent_error)
        
        # Store in history
        self.error_history.append(agent_error)
        
        # Keep only recent errors (last 1000)
        if len(self.error_history) > 1000:
            self.error_history = self.error_history[-1000:]
        
        return agent_error
    
    def _get_max_retries(self, category: ErrorCategory) -> int:
        """Get maximum retry count for error category."""
        retry_limits = {
            ErrorCategory.NETWORK: 5,
            ErrorCategory.DATABASE: 3,
            ErrorCategory.EXTERNAL_SERVICE: 3,
            ErrorCategory.AGENT_EXECUTION: 2,
            ErrorCategory.TOOL_FAILURE: 2,
            ErrorCategory.WORKFLOW: 1,
        }
        return retry_limits.get(category, 1)
    
    async def _log_error(self, agent_error: AgentError):
        """Log error with appropriate level."""
        log_data = {
            "error_id": agent_error.error_id,
            "category": agent_error.category.value,
            "severity": agent_error.severity.value,
            "message": agent_error.message,
            "context": agent_error.context,
            "recovery_strategy": agent_error.recovery_strategy.value if agent_error.recovery_strategy else None
        }
        
        if agent_error.severity == ErrorSeverity.CRITICAL:
            logger.critical("Critical agent error", **log_data)
        elif agent_error.severity == ErrorSeverity.HIGH:
            logger.error("High severity agent error", **log_data)
        elif agent_error.severity == ErrorSeverity.MEDIUM:
            logger.warning("Medium severity agent error", **log_data)
        else:
            logger.info("Low severity agent error", **log_data)
    
    def register_fallback_handler(self, operation: str, handler: Callable):
        """Register a fallback handler for a specific operation."""
        self.fallback_handlers[operation] = handler
    
    async def execute_with_recovery(
        self,
        operation: Callable,
        context: Dict[str, Any] = None,
        operation_name: str = None
    ) -> Any:
        """Execute an operation with error handling and recovery."""
        context = context or {}
        operation_name = operation_name or operation.__name__
        
        for attempt in range(3):  # Maximum 3 attempts
            try:
                result = await operation() if asyncio.iscoroutinefunction(operation) else operation()
                return result
                
            except Exception as error:
                agent_error = await self.handle_error(error, context)
                agent_error.retry_count = attempt + 1
                
                # Determine if we should retry
                if attempt < agent_error.max_retries and agent_error.recovery_strategy == RecoveryStrategy.RETRY:
                    # Calculate backoff delay
                    delay = min(2 ** attempt, 30)  # Exponential backoff, max 30 seconds
                    logger.info(f"Retrying operation {operation_name} in {delay} seconds (attempt {attempt + 1})")
                    await asyncio.sleep(delay)
                    continue
                
                # Try fallback if available
                if agent_error.recovery_strategy == RecoveryStrategy.FALLBACK:
                    fallback_result = await self._try_fallback(operation_name, context, error)
                    if fallback_result is not None:
                        return fallback_result
                
                # If we reach here, operation failed
                logger.error(f"Operation {operation_name} failed after {attempt + 1} attempts")
                raise error
        
        # Should not reach here, but just in case
        raise Exception(f"Operation {operation_name} failed after maximum retries")
    
    async def _try_fallback(self, operation_name: str, context: Dict[str, Any], original_error: Exception) -> Any:
        """Try fallback handler for failed operation."""
        if operation_name in self.fallback_handlers:
            try:
                fallback_handler = self.fallback_handlers[operation_name]
                logger.info(f"Executing fallback for {operation_name}")
                
                if asyncio.iscoroutinefunction(fallback_handler):
                    return await fallback_handler(context, original_error)
                else:
                    return fallback_handler(context, original_error)
                    
            except Exception as fallback_error:
                logger.error(f"Fallback for {operation_name} also failed: {fallback_error}")
                return None
        
        return None
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics and trends."""
        if not self.error_history:
            return {"total_errors": 0}
        
        # Count by category
        category_counts = {}
        severity_counts = {}
        recent_errors = []
        
        # Look at errors from last 24 hours
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        for error in self.error_history:
            # All-time counts
            category_counts[error.category.value] = category_counts.get(error.category.value, 0) + 1
            severity_counts[error.severity.value] = severity_counts.get(error.severity.value, 0) + 1
            
            # Recent errors
            if error.timestamp >= cutoff_time:
                recent_errors.append(error)
        
        # Calculate error rate (errors per hour in last 24 hours)
        error_rate = len(recent_errors) / 24 if recent_errors else 0
        
        return {
            "total_errors": len(self.error_history),
            "recent_errors_24h": len(recent_errors),
            "error_rate_per_hour": round(error_rate, 2),
            "category_breakdown": category_counts,
            "severity_breakdown": severity_counts,
            "most_common_category": max(category_counts.items(), key=lambda x: x[1])[0] if category_counts else None,
            "most_common_severity": max(severity_counts.items(), key=lambda x: x[1])[0] if severity_counts else None
        }
    
    def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent errors for monitoring."""
        recent_errors = sorted(self.error_history, key=lambda x: x.timestamp, reverse=True)[:limit]
        
        return [
            {
                "error_id": error.error_id,
                "category": error.category.value,
                "severity": error.severity.value,
                "message": error.message,
                "timestamp": error.timestamp.isoformat(),
                "context": error.context,
                "retry_count": error.retry_count
            }
            for error in recent_errors
        ]


# Global error handler instance
_error_handler = ErrorHandler()


def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance."""
    return _error_handler


# Decorator for automatic error handling
def handle_agent_errors(operation_name: str = None):
    """Decorator to automatically handle errors in agent operations."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            context = {
                "function": func.__name__,
                "module": func.__module__,
                "args_count": len(args),
                "kwargs_keys": list(kwargs.keys())
            }
            
            # Extract additional context from kwargs
            if "user_id" in kwargs:
                context["user_id"] = kwargs["user_id"]
            if "agent_role" in kwargs:
                context["agent_role"] = kwargs["agent_role"]
            if "workflow_id" in kwargs:
                context["workflow_id"] = kwargs["workflow_id"]
            
            return await _error_handler.execute_with_recovery(
                lambda: func(*args, **kwargs),
                context,
                operation_name or func.__name__
            )
        
        return wrapper
    return decorator


# Circuit breaker for external services
class CircuitBreaker:
    """Circuit breaker pattern for external service calls."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half-open"
            else:
                raise Exception("Circuit breaker is open - service unavailable")
        
        try:
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            self._on_success()
            return result
            
        except Exception as error:
            self._on_failure()
            raise error
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset the circuit breaker."""
        if self.last_failure_time is None:
            return True
        
        return (datetime.utcnow() - self.last_failure_time).total_seconds() >= self.recovery_timeout
    
    def _on_success(self):
        """Handle successful operation."""
        self.failure_count = 0
        self.state = "closed"
    
    def _on_failure(self):
        """Handle failed operation."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
    
    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state."""
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None
        }


# Global circuit breakers for different services
_circuit_breakers = {
    "database": CircuitBreaker(failure_threshold=3, recovery_timeout=30),
    "external_api": CircuitBreaker(failure_threshold=5, recovery_timeout=60),
    "file_service": CircuitBreaker(failure_threshold=3, recovery_timeout=30),
}


def get_circuit_breaker(service_name: str) -> CircuitBreaker:
    """Get circuit breaker for a specific service."""
    if service_name not in _circuit_breakers:
        _circuit_breakers[service_name] = CircuitBreaker()
    
    return _circuit_breakers[service_name]
