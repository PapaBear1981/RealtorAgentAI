"""
AI Agent Authentication and Authorization.

This module provides authentication and authorization functionality
specifically for AI agent operations, including role-based permissions
and access controls.
"""

from typing import Dict, Any, List, Optional
from enum import Enum
from datetime import datetime

from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import structlog

from .auth import get_current_user, verify_token
from ..models.user import User
from ..services.agent_orchestrator import AgentRole

logger = structlog.get_logger(__name__)

security = HTTPBearer()


class AgentPermission(Enum):
    """Agent operation permissions."""
    EXECUTE_DATA_EXTRACTION = "execute_data_extraction"
    EXECUTE_CONTRACT_GENERATION = "execute_contract_generation"
    EXECUTE_COMPLIANCE_CHECK = "execute_compliance_check"
    EXECUTE_SIGNATURE_TRACKING = "execute_signature_tracking"
    EXECUTE_SUMMARY = "execute_summary"
    EXECUTE_HELP = "execute_help"
    
    CREATE_WORKFLOW = "create_workflow"
    MANAGE_WORKFLOW = "manage_workflow"
    VIEW_WORKFLOW = "view_workflow"
    
    VIEW_AGENT_TOOLS = "view_agent_tools"
    VIEW_AGENT_STATUS = "view_agent_status"
    VIEW_SYSTEM_METRICS = "view_system_metrics"
    
    ADMIN_AGENTS = "admin_agents"


class UserRole(Enum):
    """User roles for agent operations."""
    ADMIN = "admin"
    AGENT_MANAGER = "agent_manager"
    CONTRACT_SPECIALIST = "contract_specialist"
    COMPLIANCE_OFFICER = "compliance_officer"
    BASIC_USER = "basic_user"
    READONLY_USER = "readonly_user"


# Role-based permissions mapping
ROLE_PERMISSIONS = {
    UserRole.ADMIN: [
        # All permissions
        AgentPermission.EXECUTE_DATA_EXTRACTION,
        AgentPermission.EXECUTE_CONTRACT_GENERATION,
        AgentPermission.EXECUTE_COMPLIANCE_CHECK,
        AgentPermission.EXECUTE_SIGNATURE_TRACKING,
        AgentPermission.EXECUTE_SUMMARY,
        AgentPermission.EXECUTE_HELP,
        AgentPermission.CREATE_WORKFLOW,
        AgentPermission.MANAGE_WORKFLOW,
        AgentPermission.VIEW_WORKFLOW,
        AgentPermission.VIEW_AGENT_TOOLS,
        AgentPermission.VIEW_AGENT_STATUS,
        AgentPermission.VIEW_SYSTEM_METRICS,
        AgentPermission.ADMIN_AGENTS,
    ],
    
    UserRole.AGENT_MANAGER: [
        # Can execute all agents and manage workflows
        AgentPermission.EXECUTE_DATA_EXTRACTION,
        AgentPermission.EXECUTE_CONTRACT_GENERATION,
        AgentPermission.EXECUTE_COMPLIANCE_CHECK,
        AgentPermission.EXECUTE_SIGNATURE_TRACKING,
        AgentPermission.EXECUTE_SUMMARY,
        AgentPermission.EXECUTE_HELP,
        AgentPermission.CREATE_WORKFLOW,
        AgentPermission.MANAGE_WORKFLOW,
        AgentPermission.VIEW_WORKFLOW,
        AgentPermission.VIEW_AGENT_TOOLS,
        AgentPermission.VIEW_AGENT_STATUS,
        AgentPermission.VIEW_SYSTEM_METRICS,
    ],
    
    UserRole.CONTRACT_SPECIALIST: [
        # Focused on contract-related operations
        AgentPermission.EXECUTE_DATA_EXTRACTION,
        AgentPermission.EXECUTE_CONTRACT_GENERATION,
        AgentPermission.EXECUTE_SUMMARY,
        AgentPermission.EXECUTE_HELP,
        AgentPermission.CREATE_WORKFLOW,
        AgentPermission.VIEW_WORKFLOW,
        AgentPermission.VIEW_AGENT_TOOLS,
        AgentPermission.VIEW_AGENT_STATUS,
    ],
    
    UserRole.COMPLIANCE_OFFICER: [
        # Focused on compliance and signature tracking
        AgentPermission.EXECUTE_COMPLIANCE_CHECK,
        AgentPermission.EXECUTE_SIGNATURE_TRACKING,
        AgentPermission.EXECUTE_SUMMARY,
        AgentPermission.EXECUTE_HELP,
        AgentPermission.VIEW_WORKFLOW,
        AgentPermission.VIEW_AGENT_TOOLS,
        AgentPermission.VIEW_AGENT_STATUS,
    ],
    
    UserRole.BASIC_USER: [
        # Basic agent execution capabilities
        AgentPermission.EXECUTE_DATA_EXTRACTION,
        AgentPermission.EXECUTE_SUMMARY,
        AgentPermission.EXECUTE_HELP,
        AgentPermission.VIEW_WORKFLOW,
        AgentPermission.VIEW_AGENT_TOOLS,
        AgentPermission.VIEW_AGENT_STATUS,
    ],
    
    UserRole.READONLY_USER: [
        # View-only permissions
        AgentPermission.VIEW_WORKFLOW,
        AgentPermission.VIEW_AGENT_TOOLS,
        AgentPermission.VIEW_AGENT_STATUS,
    ],
}

# Agent role to permission mapping
AGENT_ROLE_PERMISSIONS = {
    AgentRole.DATA_EXTRACTION: AgentPermission.EXECUTE_DATA_EXTRACTION,
    AgentRole.CONTRACT_GENERATOR: AgentPermission.EXECUTE_CONTRACT_GENERATION,
    AgentRole.COMPLIANCE_CHECKER: AgentPermission.EXECUTE_COMPLIANCE_CHECK,
    AgentRole.SIGNATURE_TRACKER: AgentPermission.EXECUTE_SIGNATURE_TRACKING,
    AgentRole.SUMMARY_AGENT: AgentPermission.EXECUTE_SUMMARY,
    AgentRole.HELP_AGENT: AgentPermission.EXECUTE_HELP,
}


def get_user_role(user: User) -> UserRole:
    """Get user role from user object."""
    # This would typically come from the user's role field in the database
    # For now, we'll use a simple mapping based on user attributes
    
    if hasattr(user, 'role'):
        role_mapping = {
            'admin': UserRole.ADMIN,
            'agent_manager': UserRole.AGENT_MANAGER,
            'contract_specialist': UserRole.CONTRACT_SPECIALIST,
            'compliance_officer': UserRole.COMPLIANCE_OFFICER,
            'basic_user': UserRole.BASIC_USER,
            'readonly_user': UserRole.READONLY_USER,
        }
        return role_mapping.get(user.role, UserRole.BASIC_USER)
    
    # Default role for users without explicit role
    return UserRole.BASIC_USER


def get_user_permissions(user: User) -> List[AgentPermission]:
    """Get list of permissions for a user."""
    user_role = get_user_role(user)
    return ROLE_PERMISSIONS.get(user_role, [])


def has_permission(user: User, permission: AgentPermission) -> bool:
    """Check if user has a specific permission."""
    user_permissions = get_user_permissions(user)
    return permission in user_permissions


def require_permission(permission: AgentPermission):
    """Decorator to require a specific permission for an endpoint."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract user from kwargs (assumes get_current_user dependency)
            current_user = None
            for key, value in kwargs.items():
                if isinstance(value, User):
                    current_user = value
                    break
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if not has_permission(current_user, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission required: {permission.value}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


async def verify_agent_access(
    agent_role: str,
    current_user: User = Depends(get_current_user)
) -> User:
    """Verify user has access to execute a specific agent role."""
    try:
        # Convert string to AgentRole enum
        agent_role_enum = AgentRole(agent_role)
        
        # Get required permission for this agent
        required_permission = AGENT_ROLE_PERMISSIONS.get(agent_role_enum)
        
        if not required_permission:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid agent role: {agent_role}"
            )
        
        # Check if user has permission
        if not has_permission(current_user, required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied to {agent_role} agent"
            )
        
        return current_user
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid agent role: {agent_role}"
        )
    except Exception as e:
        logger.error(f"Agent access verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Access verification failed"
        )


async def verify_workflow_access(
    operation: str,
    current_user: User = Depends(get_current_user)
) -> User:
    """Verify user has access to workflow operations."""
    permission_mapping = {
        "create": AgentPermission.CREATE_WORKFLOW,
        "manage": AgentPermission.MANAGE_WORKFLOW,
        "view": AgentPermission.VIEW_WORKFLOW,
    }
    
    required_permission = permission_mapping.get(operation)
    if not required_permission:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid workflow operation: {operation}"
        )
    
    if not has_permission(current_user, required_permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied to workflow {operation}"
        )
    
    return current_user


async def verify_admin_access(
    current_user: User = Depends(get_current_user)
) -> User:
    """Verify user has admin access to agent system."""
    if not has_permission(current_user, AgentPermission.ADMIN_AGENTS):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return current_user


def get_user_agent_capabilities(user: User) -> Dict[str, Any]:
    """Get user's agent capabilities and permissions."""
    user_role = get_user_role(user)
    permissions = get_user_permissions(user)
    
    # Determine which agents the user can execute
    executable_agents = []
    for agent_role, permission in AGENT_ROLE_PERMISSIONS.items():
        if permission in permissions:
            executable_agents.append(agent_role.value)
    
    # Determine workflow capabilities
    workflow_capabilities = {
        "can_create": AgentPermission.CREATE_WORKFLOW in permissions,
        "can_manage": AgentPermission.MANAGE_WORKFLOW in permissions,
        "can_view": AgentPermission.VIEW_WORKFLOW in permissions,
    }
    
    # Determine system access
    system_access = {
        "can_view_tools": AgentPermission.VIEW_AGENT_TOOLS in permissions,
        "can_view_status": AgentPermission.VIEW_AGENT_STATUS in permissions,
        "can_view_metrics": AgentPermission.VIEW_SYSTEM_METRICS in permissions,
        "is_admin": AgentPermission.ADMIN_AGENTS in permissions,
    }
    
    return {
        "user_role": user_role.value,
        "executable_agents": executable_agents,
        "workflow_capabilities": workflow_capabilities,
        "system_access": system_access,
        "total_permissions": len(permissions)
    }


# Rate limiting for agent operations (simple in-memory implementation)
class RateLimiter:
    """Simple rate limiter for agent operations."""
    
    def __init__(self):
        self.user_requests = {}
        self.limits = {
            UserRole.ADMIN: {"requests": 1000, "window": 3600},  # 1000 per hour
            UserRole.AGENT_MANAGER: {"requests": 500, "window": 3600},  # 500 per hour
            UserRole.CONTRACT_SPECIALIST: {"requests": 200, "window": 3600},  # 200 per hour
            UserRole.COMPLIANCE_OFFICER: {"requests": 200, "window": 3600},  # 200 per hour
            UserRole.BASIC_USER: {"requests": 100, "window": 3600},  # 100 per hour
            UserRole.READONLY_USER: {"requests": 50, "window": 3600},  # 50 per hour
        }
    
    def check_rate_limit(self, user: User) -> bool:
        """Check if user is within rate limits."""
        user_role = get_user_role(user)
        user_id = str(user.id)
        current_time = datetime.utcnow().timestamp()
        
        if user_id not in self.user_requests:
            self.user_requests[user_id] = []
        
        # Clean old requests outside the window
        window_size = self.limits[user_role]["window"]
        self.user_requests[user_id] = [
            req_time for req_time in self.user_requests[user_id]
            if current_time - req_time < window_size
        ]
        
        # Check if under limit
        max_requests = self.limits[user_role]["requests"]
        if len(self.user_requests[user_id]) >= max_requests:
            return False
        
        # Add current request
        self.user_requests[user_id].append(current_time)
        return True
    
    def get_remaining_requests(self, user: User) -> int:
        """Get remaining requests for user."""
        user_role = get_user_role(user)
        user_id = str(user.id)
        
        if user_id not in self.user_requests:
            return self.limits[user_role]["requests"]
        
        current_time = datetime.utcnow().timestamp()
        window_size = self.limits[user_role]["window"]
        
        # Count recent requests
        recent_requests = [
            req_time for req_time in self.user_requests[user_id]
            if current_time - req_time < window_size
        ]
        
        max_requests = self.limits[user_role]["requests"]
        return max(0, max_requests - len(recent_requests))


# Global rate limiter instance
rate_limiter = RateLimiter()


async def check_rate_limit(current_user: User = Depends(get_current_user)) -> User:
    """Check rate limit for current user."""
    if not rate_limiter.check_rate_limit(current_user):
        user_role = get_user_role(current_user)
        limit_info = rate_limiter.limits[user_role]
        
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: {limit_info['requests']} requests per {limit_info['window']} seconds",
            headers={"Retry-After": str(limit_info["window"])}
        )
    
    return current_user


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    return rate_limiter
