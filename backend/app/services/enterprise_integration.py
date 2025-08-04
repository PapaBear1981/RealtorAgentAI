"""
Enterprise Integration Features.

This module provides enterprise-grade features including SSO integration,
enhanced security, audit logging, and compliance reporting for the AI agent system.
"""

import json
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import structlog
from urllib.parse import urlencode
import base64

logger = structlog.get_logger(__name__)


class SSOProvider(Enum):
    """Supported SSO providers."""
    AZURE_AD = "azure_ad"
    OKTA = "okta"
    GOOGLE_WORKSPACE = "google_workspace"
    SAML_GENERIC = "saml_generic"
    OIDC_GENERIC = "oidc_generic"


class AuditEventType(Enum):
    """Types of audit events."""
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    AGENT_EXECUTION = "agent_execution"
    WORKFLOW_CREATED = "workflow_created"
    WORKFLOW_COMPLETED = "workflow_completed"
    DATA_ACCESS = "data_access"
    PERMISSION_CHANGE = "permission_change"
    SYSTEM_CONFIG_CHANGE = "system_config_change"
    SECURITY_VIOLATION = "security_violation"
    DATA_EXPORT = "data_export"


class ComplianceFramework(Enum):
    """Supported compliance frameworks."""
    SOX = "sox"
    GDPR = "gdpr"
    CCPA = "ccpa"
    HIPAA = "hipaa"
    SOC2 = "soc2"
    ISO27001 = "iso27001"


@dataclass
class SSOConfiguration:
    """SSO provider configuration."""
    provider: SSOProvider
    client_id: str
    client_secret: str
    tenant_id: Optional[str] = None
    discovery_url: Optional[str] = None
    redirect_uri: str = ""
    scopes: List[str] = field(default_factory=lambda: ["openid", "profile", "email"])
    enabled: bool = True
    auto_provision_users: bool = True
    default_role: str = "basic_user"
    attribute_mapping: Dict[str, str] = field(default_factory=dict)


@dataclass
class AuditEvent:
    """Audit event record."""
    event_id: str
    event_type: AuditEventType
    timestamp: datetime
    user_id: str
    user_email: str
    ip_address: str
    user_agent: str
    resource_type: str
    resource_id: str
    action: str
    result: str  # "success", "failure", "partial"
    details: Dict[str, Any]
    risk_score: int = 0
    compliance_tags: List[str] = field(default_factory=list)


@dataclass
class DataPrivacyPolicy:
    """Data privacy and protection policy."""
    policy_id: str
    name: str
    description: str
    data_categories: List[str]
    retention_period_days: int
    encryption_required: bool
    anonymization_required: bool
    geographic_restrictions: List[str]
    compliance_frameworks: List[ComplianceFramework]
    created_at: datetime
    updated_at: datetime


class EnterpriseIntegrationService:
    """Enterprise integration and security service."""

    def __init__(self):
        self.sso_configurations: Dict[str, SSOConfiguration] = {}
        self.audit_events: List[AuditEvent] = []
        self.privacy_policies: Dict[str, DataPrivacyPolicy] = {}
        self.security_policies: Dict[str, Any] = {}
        self.compliance_reports: Dict[str, Any] = {}

        # Initialize default configurations
        self._initialize_security_policies()
        self._initialize_privacy_policies()

    # SSO Integration Methods

    def configure_sso_provider(self, config: SSOConfiguration) -> bool:
        """Configure an SSO provider."""
        try:
            # Validate configuration
            if not self._validate_sso_config(config):
                return False

            self.sso_configurations[config.provider.value] = config

            # Log configuration change
            self._log_audit_event(
                event_type=AuditEventType.SYSTEM_CONFIG_CHANGE,
                user_id="system",
                user_email="system@internal",
                ip_address="127.0.0.1",
                user_agent="system",
                resource_type="sso_configuration",
                resource_id=config.provider.value,
                action="configure",
                result="success",
                details={"provider": config.provider.value, "enabled": config.enabled}
            )

            logger.info(f"Configured SSO provider: {config.provider.value}")
            return True

        except Exception as e:
            logger.error(f"Failed to configure SSO provider {config.provider.value}: {e}")
            return False

    def get_sso_login_url(self, provider: SSOProvider, state: str = None) -> Optional[str]:
        """Generate SSO login URL."""
        if provider.value not in self.sso_configurations:
            return None

        config = self.sso_configurations[provider.value]
        if not config.enabled:
            return None

        try:
            if provider == SSOProvider.AZURE_AD:
                return self._generate_azure_ad_url(config, state)
            elif provider == SSOProvider.OKTA:
                return self._generate_okta_url(config, state)
            elif provider == SSOProvider.GOOGLE_WORKSPACE:
                return self._generate_google_url(config, state)
            else:
                return self._generate_generic_oidc_url(config, state)

        except Exception as e:
            logger.error(f"Failed to generate SSO URL for {provider.value}: {e}")
            return None

    def process_sso_callback(
        self,
        provider: SSOProvider,
        authorization_code: str,
        state: str = None
    ) -> Optional[Dict[str, Any]]:
        """Process SSO callback and extract user information."""
        if provider.value not in self.sso_configurations:
            return None

        config = self.sso_configurations[provider.value]

        try:
            # Exchange authorization code for tokens
            tokens = self._exchange_code_for_tokens(config, authorization_code)
            if not tokens:
                return None

            # Extract user information from tokens
            user_info = self._extract_user_info(config, tokens)
            if not user_info:
                return None

            # Map attributes according to configuration
            mapped_user = self._map_user_attributes(config, user_info)

            # Log successful SSO login
            self._log_audit_event(
                event_type=AuditEventType.USER_LOGIN,
                user_id=mapped_user.get("user_id", "unknown"),
                user_email=mapped_user.get("email", "unknown"),
                ip_address="unknown",  # Would be extracted from request
                user_agent="unknown",  # Would be extracted from request
                resource_type="sso_login",
                resource_id=provider.value,
                action="login",
                result="success",
                details={"provider": provider.value, "method": "sso"}
            )

            return mapped_user

        except Exception as e:
            logger.error(f"Failed to process SSO callback for {provider.value}: {e}")

            # Log failed SSO attempt
            self._log_audit_event(
                event_type=AuditEventType.SECURITY_VIOLATION,
                user_id="unknown",
                user_email="unknown",
                ip_address="unknown",
                user_agent="unknown",
                resource_type="sso_login",
                resource_id=provider.value,
                action="login",
                result="failure",
                details={"provider": provider.value, "error": str(e)}
            )

            return None

    # Audit Logging Methods

    def log_agent_execution(
        self,
        user_id: str,
        user_email: str,
        agent_role: str,
        execution_id: str,
        result: str,
        details: Dict[str, Any],
        ip_address: str = "unknown",
        user_agent: str = "unknown"
    ):
        """Log agent execution for audit purposes."""
        self._log_audit_event(
            event_type=AuditEventType.AGENT_EXECUTION,
            user_id=user_id,
            user_email=user_email,
            ip_address=ip_address,
            user_agent=user_agent,
            resource_type="agent",
            resource_id=agent_role,
            action="execute",
            result=result,
            details={
                "execution_id": execution_id,
                "agent_role": agent_role,
                **details
            }
        )

    def log_data_access(
        self,
        user_id: str,
        user_email: str,
        resource_type: str,
        resource_id: str,
        action: str,
        result: str,
        ip_address: str = "unknown",
        user_agent: str = "unknown"
    ):
        """Log data access for audit purposes."""
        # Calculate risk score based on action and resource
        risk_score = self._calculate_risk_score(action, resource_type)

        self._log_audit_event(
            event_type=AuditEventType.DATA_ACCESS,
            user_id=user_id,
            user_email=user_email,
            ip_address=ip_address,
            user_agent=user_agent,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            result=result,
            details={"risk_score": risk_score},
            risk_score=risk_score
        )

    def get_audit_events(
        self,
        start_date: datetime = None,
        end_date: datetime = None,
        user_id: str = None,
        event_type: AuditEventType = None,
        limit: int = 100
    ) -> List[AuditEvent]:
        """Retrieve audit events with filtering."""
        filtered_events = self.audit_events

        # Apply filters
        if start_date:
            filtered_events = [e for e in filtered_events if e.timestamp >= start_date]

        if end_date:
            filtered_events = [e for e in filtered_events if e.timestamp <= end_date]

        if user_id:
            filtered_events = [e for e in filtered_events if e.user_id == user_id]

        if event_type:
            filtered_events = [e for e in filtered_events if e.event_type == event_type]

        # Sort by timestamp (newest first) and limit
        filtered_events.sort(key=lambda x: x.timestamp, reverse=True)
        return filtered_events[:limit]

    # Compliance Reporting Methods

    def generate_compliance_report(
        self,
        framework: ComplianceFramework,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Generate compliance report for specified framework."""
        try:
            report_id = f"{framework.value}_{int(datetime.utcnow().timestamp())}"

            # Get relevant audit events
            events = self.get_audit_events(start_date=start_date, end_date=end_date)

            # Filter events relevant to compliance framework
            relevant_events = [
                e for e in events
                if framework.value in e.compliance_tags or self._is_event_relevant_to_framework(e, framework)
            ]

            # Generate framework-specific metrics
            if framework == ComplianceFramework.SOX:
                metrics = self._generate_sox_metrics(relevant_events)
            elif framework == ComplianceFramework.GDPR:
                metrics = self._generate_gdpr_metrics(relevant_events)
            elif framework == ComplianceFramework.SOC2:
                metrics = self._generate_soc2_metrics(relevant_events)
            else:
                metrics = self._generate_generic_metrics(relevant_events)

            report = {
                "report_id": report_id,
                "framework": framework.value,
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "generated_at": datetime.utcnow().isoformat(),
                "total_events": len(relevant_events),
                "metrics": metrics,
                "violations": self._identify_violations(relevant_events, framework),
                "recommendations": self._generate_recommendations(relevant_events, framework)
            }

            # Store report
            self.compliance_reports[report_id] = report

            # Log report generation
            self._log_audit_event(
                event_type=AuditEventType.DATA_EXPORT,
                user_id="system",
                user_email="system@internal",
                ip_address="127.0.0.1",
                user_agent="system",
                resource_type="compliance_report",
                resource_id=report_id,
                action="generate",
                result="success",
                details={"framework": framework.value, "events_analyzed": len(relevant_events)}
            )

            return report

        except Exception as e:
            logger.error(f"Failed to generate compliance report for {framework.value}: {e}")
            return {}

    # Data Privacy Methods

    def apply_data_privacy_policy(
        self,
        data: Dict[str, Any],
        policy_id: str,
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply data privacy policy to data."""
        if policy_id not in self.privacy_policies:
            return data

        policy = self.privacy_policies[policy_id]
        processed_data = data.copy()

        try:
            # Apply anonymization if required
            if policy.anonymization_required:
                processed_data = self._anonymize_data(processed_data, policy)

            # Apply geographic restrictions
            if policy.geographic_restrictions:
                user_location = user_context.get("location", "unknown")
                if user_location not in policy.geographic_restrictions:
                    logger.warning(f"Data access denied due to geographic restrictions: {user_location}")
                    return {}

            # Log data access
            self.log_data_access(
                user_id=user_context.get("user_id", "unknown"),
                user_email=user_context.get("user_email", "unknown"),
                resource_type="privacy_controlled_data",
                resource_id=policy_id,
                action="access",
                result="success"
            )

            return processed_data

        except Exception as e:
            logger.error(f"Failed to apply privacy policy {policy_id}: {e}")
            return {}

    def _log_audit_event(
        self,
        event_type: AuditEventType,
        user_id: str,
        user_email: str,
        ip_address: str,
        user_agent: str,
        resource_type: str,
        resource_id: str,
        action: str,
        result: str,
        details: Dict[str, Any],
        risk_score: int = 0
    ):
        """Log an audit event."""
        event = AuditEvent(
            event_id=f"audit_{int(datetime.utcnow().timestamp())}_{hash(f'{user_id}{resource_id}{action}') % 10000}",
            event_type=event_type,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            user_email=user_email,
            ip_address=ip_address,
            user_agent=user_agent,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            result=result,
            details=details,
            risk_score=risk_score,
            compliance_tags=self._determine_compliance_tags(event_type, resource_type, action)
        )

        self.audit_events.append(event)

        # Keep only recent events (last 10000)
        if len(self.audit_events) > 10000:
            self.audit_events = self.audit_events[-10000:]

        # Log high-risk events immediately
        if risk_score >= 80:
            logger.warning(f"High-risk audit event: {event.event_id}", extra={
                "event_type": event_type.value,
                "user_id": user_id,
                "resource_type": resource_type,
                "action": action,
                "risk_score": risk_score
            })

    def _validate_sso_config(self, config: SSOConfiguration) -> bool:
        """Validate SSO configuration."""
        if not config.client_id or not config.client_secret:
            return False

        if config.provider == SSOProvider.AZURE_AD and not config.tenant_id:
            return False

        return True

    def _generate_azure_ad_url(self, config: SSOConfiguration, state: str = None) -> str:
        """Generate Azure AD login URL."""
        base_url = f"https://login.microsoftonline.com/{config.tenant_id}/oauth2/v2.0/authorize"
        params = {
            "client_id": config.client_id,
            "response_type": "code",
            "redirect_uri": config.redirect_uri,
            "scope": " ".join(config.scopes),
            "response_mode": "query"
        }

        if state:
            params["state"] = state

        return f"{base_url}?{urlencode(params)}"

    def _exchange_code_for_tokens(self, config: SSOConfiguration, code: str) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for tokens (simplified implementation)."""
        # In a real implementation, this would make HTTP requests to the token endpoint
        return {
            "access_token": f"mock_access_token_{code[:10]}",
            "id_token": f"mock_id_token_{code[:10]}",
            "token_type": "Bearer",
            "expires_in": 3600
        }

    def _extract_user_info(self, config: SSOConfiguration, tokens: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract user information from tokens (simplified implementation)."""
        # In a real implementation, this would decode JWT tokens or call userinfo endpoint
        return {
            "sub": "mock_user_id",
            "email": "user@example.com",
            "name": "Mock User",
            "given_name": "Mock",
            "family_name": "User",
            "roles": ["basic_user"]
        }

    def _map_user_attributes(self, config: SSOConfiguration, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """Map user attributes according to configuration."""
        mapped = {
            "user_id": user_info.get("sub"),
            "email": user_info.get("email"),
            "full_name": user_info.get("name"),
            "first_name": user_info.get("given_name"),
            "last_name": user_info.get("family_name"),
            "role": config.default_role
        }

        # Apply custom attribute mapping
        for source_attr, target_attr in config.attribute_mapping.items():
            if source_attr in user_info:
                mapped[target_attr] = user_info[source_attr]

        return mapped

    def _calculate_risk_score(self, action: str, resource_type: str) -> int:
        """Calculate risk score for an action."""
        base_score = 10

        # High-risk actions
        if action in ["delete", "export", "modify_permissions"]:
            base_score += 40
        elif action in ["create", "update"]:
            base_score += 20
        elif action in ["read", "view"]:
            base_score += 5

        # High-risk resources
        if resource_type in ["user_data", "financial_data", "contracts"]:
            base_score += 30
        elif resource_type in ["templates", "configurations"]:
            base_score += 15

        return min(100, base_score)

    def _determine_compliance_tags(self, event_type: AuditEventType, resource_type: str, action: str) -> List[str]:
        """Determine compliance framework tags for an event."""
        tags = []

        # SOX compliance
        if resource_type in ["financial_data", "contracts"] or action in ["delete", "modify"]:
            tags.append("sox")

        # GDPR compliance
        if resource_type in ["user_data", "personal_data"] or event_type == AuditEventType.DATA_ACCESS:
            tags.append("gdpr")

        # SOC2 compliance
        if event_type in [AuditEventType.USER_LOGIN, AuditEventType.PERMISSION_CHANGE, AuditEventType.SYSTEM_CONFIG_CHANGE]:
            tags.append("soc2")

        return tags

    def _is_event_relevant_to_framework(self, event: AuditEvent, framework: ComplianceFramework) -> bool:
        """Check if an event is relevant to a compliance framework."""
        if framework == ComplianceFramework.SOX:
            return event.resource_type in ["financial_data", "contracts"] or event.action in ["delete", "modify"]
        elif framework == ComplianceFramework.GDPR:
            return event.resource_type in ["user_data", "personal_data"] or event.event_type == AuditEventType.DATA_ACCESS
        elif framework == ComplianceFramework.SOC2:
            return event.event_type in [AuditEventType.USER_LOGIN, AuditEventType.PERMISSION_CHANGE, AuditEventType.SYSTEM_CONFIG_CHANGE]

        return False

    def _generate_sox_metrics(self, events: List[AuditEvent]) -> Dict[str, Any]:
        """Generate SOX compliance metrics."""
        return {
            "financial_data_access_count": len([e for e in events if e.resource_type == "financial_data"]),
            "unauthorized_access_attempts": len([e for e in events if e.result == "failure"]),
            "data_modification_count": len([e for e in events if e.action in ["create", "update", "delete"]]),
            "high_risk_events": len([e for e in events if e.risk_score >= 70])
        }

    def _generate_gdpr_metrics(self, events: List[AuditEvent]) -> Dict[str, Any]:
        """Generate GDPR compliance metrics."""
        return {
            "personal_data_access_count": len([e for e in events if e.resource_type in ["user_data", "personal_data"]]),
            "data_export_count": len([e for e in events if e.event_type == AuditEventType.DATA_EXPORT]),
            "consent_violations": 0,  # Would be calculated based on actual consent tracking
            "data_retention_violations": 0  # Would be calculated based on retention policies
        }

    def _anonymize_data(self, data: Dict[str, Any], policy: DataPrivacyPolicy) -> Dict[str, Any]:
        """Anonymize data according to privacy policy."""
        anonymized = data.copy()

        # Simple anonymization - in production would be more sophisticated
        sensitive_fields = ["email", "phone", "ssn", "address"]

        for field in sensitive_fields:
            if field in anonymized:
                if isinstance(anonymized[field], str):
                    # Hash the value
                    anonymized[field] = hashlib.sha256(anonymized[field].encode()).hexdigest()[:8]

        return anonymized

    def _initialize_security_policies(self):
        """Initialize default security policies."""
        self.security_policies = {
            "password_policy": {
                "min_length": 12,
                "require_uppercase": True,
                "require_lowercase": True,
                "require_numbers": True,
                "require_special_chars": True,
                "max_age_days": 90
            },
            "session_policy": {
                "max_duration_hours": 8,
                "idle_timeout_minutes": 30,
                "require_mfa": True
            },
            "access_policy": {
                "max_failed_attempts": 5,
                "lockout_duration_minutes": 15,
                "require_approval_for_high_risk": True
            }
        }

    def _initialize_privacy_policies(self):
        """Initialize default privacy policies."""
        self.privacy_policies["general_data"] = DataPrivacyPolicy(
            policy_id="general_data",
            name="General Data Privacy Policy",
            description="Default privacy policy for general user data",
            data_categories=["user_profile", "preferences", "activity_logs"],
            retention_period_days=365,
            encryption_required=True,
            anonymization_required=False,
            geographic_restrictions=[],
            compliance_frameworks=[ComplianceFramework.GDPR, ComplianceFramework.CCPA],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )


# Global enterprise integration service instance
_enterprise_service = None


def get_enterprise_integration_service() -> EnterpriseIntegrationService:
    """Get the global enterprise integration service instance."""
    global _enterprise_service
    if _enterprise_service is None:
        _enterprise_service = EnterpriseIntegrationService()
    return _enterprise_service
