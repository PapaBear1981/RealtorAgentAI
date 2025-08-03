"""
Admin service for system administration functionality.

This module provides comprehensive admin management capabilities including
user management, role management, system monitoring, and configuration.
"""

import logging
import csv
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union
from sqlmodel import Session, select, and_, or_, func, desc
from fastapi import HTTPException, status
from io import StringIO

from ..models.user import User, UserCreate, UserUpdate, UserPublic
from ..models.audit_log import AuditLog, AuditLogFilter, AuditLogPublic, AuditLogWithDetails, AuditAction
from ..models.template import (
    Template, TemplateCreate, TemplateUpdate, TemplatePublic, TemplateWithUsage,
    TemplateWithDetails, TemplateStatus, TemplateType
)
from ..models.contract import Contract
from ..models.deal import Deal
from ..core.auth import hash_password
from ..core.database import get_session_context

logger = logging.getLogger(__name__)


class AdminServiceError(Exception):
    """Exception raised during admin service operations."""
    pass


class AdminService:
    """
    Comprehensive admin service for system administration.

    Provides user management, role management, audit trail management,
    system monitoring, and configuration management capabilities.
    """

    def __init__(self):
        """Initialize admin service."""
        pass

    # User Management Methods
    async def create_user(
        self,
        user_data: UserCreate,
        admin_user: User,
        session: Session
    ) -> UserPublic:
        """
        Create a new user with admin privileges.

        Args:
            user_data: User creation data
            admin_user: Admin user creating the user
            session: Database session

        Returns:
            UserPublic: Created user information
        """
        try:
            # Check if user already exists
            existing_user = session.exec(
                select(User).where(User.email == user_data.email)
            ).first()

            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User with this email already exists"
                )

            # Hash password
            hashed_password = hash_password(user_data.password)

            # Create user
            new_user = User(
                email=user_data.email,
                name=user_data.name,
                role=user_data.role,
                disabled=user_data.disabled,
                password_hash=hashed_password,
                created_at=datetime.utcnow()
            )

            session.add(new_user)
            session.commit()
            session.refresh(new_user)

            # Log user creation
            audit_log = AuditLog(
                user_id=admin_user.id,
                actor=f"admin:{admin_user.id}",
                action=AuditAction.USER_CREATE,
                success=True,
                meta={
                    "created_user_id": new_user.id,
                    "created_user_email": new_user.email,
                    "created_user_role": new_user.role,
                    "admin_user_id": admin_user.id
                }
            )
            session.add(audit_log)
            session.commit()

            return self._to_user_public(new_user)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"User creation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User creation failed"
            )

    async def list_users(
        self,
        admin_user: User,
        session: Session,
        role: Optional[str] = None,
        disabled: Optional[bool] = None,
        search_query: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        List users with filtering and pagination.

        Args:
            admin_user: Admin user requesting the list
            session: Database session
            role: Filter by role
            disabled: Filter by disabled status
            search_query: Search in name and email
            limit: Maximum results
            offset: Results offset

        Returns:
            Dict: Users list with metadata
        """
        try:
            # Build query
            query = select(User)
            filters = []

            if role:
                filters.append(User.role == role)

            if disabled is not None:
                filters.append(User.disabled == disabled)

            if search_query:
                search_filters = [
                    User.name.ilike(f"%{search_query}%"),
                    User.email.ilike(f"%{search_query}%")
                ]
                filters.append(or_(*search_filters))

            if filters:
                query = query.where(and_(*filters))

            # Get total count
            count_query = select(func.count(User.id))
            if filters:
                count_query = count_query.where(and_(*filters))
            total_count = session.exec(count_query).first() or 0

            # Apply ordering and pagination
            query = query.order_by(desc(User.created_at)).offset(offset).limit(limit)

            # Execute query
            users = session.exec(query).all()

            # Log user list access
            audit_log = AuditLog(
                user_id=admin_user.id,
                actor=f"admin:{admin_user.id}",
                action=AuditAction.USER_LIST,
                success=True,
                meta={
                    "filters": {
                        "role": role,
                        "disabled": disabled,
                        "search_query": search_query
                    },
                    "result_count": len(users),
                    "total_count": total_count
                }
            )
            session.add(audit_log)
            session.commit()

            return {
                "users": [self._to_user_public(user) for user in users],
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + len(users) < total_count
            }

        except Exception as e:
            logger.error(f"User listing failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to list users"
            )

    async def get_user(
        self,
        user_id: int,
        admin_user: User,
        session: Session
    ) -> UserPublic:
        """
        Get user details by ID.

        Args:
            user_id: User ID to retrieve
            admin_user: Admin user requesting the details
            session: Database session

        Returns:
            UserPublic: User information
        """
        try:
            user = session.get(User, user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )

            # Log user access
            audit_log = AuditLog(
                user_id=admin_user.id,
                actor=f"admin:{admin_user.id}",
                action=AuditAction.USER_READ,
                success=True,
                meta={
                    "accessed_user_id": user_id,
                    "accessed_user_email": user.email
                }
            )
            session.add(audit_log)
            session.commit()

            return self._to_user_public(user)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"User retrieval failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve user"
            )

    async def update_user(
        self,
        user_id: int,
        user_data: UserUpdate,
        admin_user: User,
        session: Session
    ) -> UserPublic:
        """
        Update user information.

        Args:
            user_id: User ID to update
            user_data: User update data
            admin_user: Admin user performing the update
            session: Database session

        Returns:
            UserPublic: Updated user information
        """
        try:
            user = session.get(User, user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )

            # Store original state for audit
            original_state = {
                "email": user.email,
                "name": user.name,
                "role": user.role,
                "disabled": user.disabled
            }

            # Update fields
            update_data = user_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(user, field, value)

            session.add(user)
            session.commit()
            session.refresh(user)

            # Log user update
            audit_log = AuditLog(
                user_id=admin_user.id,
                actor=f"admin:{admin_user.id}",
                action=AuditAction.USER_UPDATE,
                success=True,
                before_state=original_state,
                after_state={
                    "email": user.email,
                    "name": user.name,
                    "role": user.role,
                    "disabled": user.disabled
                },
                meta={
                    "updated_user_id": user_id,
                    "updated_fields": list(update_data.keys())
                }
            )
            session.add(audit_log)
            session.commit()

            return self._to_user_public(user)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"User update failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User update failed"
            )

    async def delete_user(
        self,
        user_id: int,
        admin_user: User,
        session: Session
    ) -> bool:
        """
        Delete a user (soft delete by disabling).

        Args:
            user_id: User ID to delete
            admin_user: Admin user performing the deletion
            session: Database session

        Returns:
            bool: True if successful
        """
        try:
            user = session.get(User, user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )

            # Prevent admin from deleting themselves
            if user_id == admin_user.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot delete your own account"
                )

            # Soft delete by disabling
            user.disabled = True
            session.add(user)
            session.commit()

            # Log user deletion
            audit_log = AuditLog(
                user_id=admin_user.id,
                actor=f"admin:{admin_user.id}",
                action=AuditAction.USER_DELETE,
                success=True,
                meta={
                    "deleted_user_id": user_id,
                    "deleted_user_email": user.email,
                    "deletion_type": "soft_delete"
                }
            )
            session.add(audit_log)
            session.commit()

            return True

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"User deletion failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User deletion failed"
            )

    def _to_user_public(self, user: User) -> UserPublic:
        """Convert User to UserPublic model."""
        return UserPublic(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role,
            disabled=user.disabled,
            created_at=user.created_at,
            last_login=user.last_login,
            login_count=user.login_count
        )

    # Audit Trail Management Methods
    async def search_audit_logs(
        self,
        admin_user: User,
        session: Session,
        filters: AuditLogFilter,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Search audit logs with comprehensive filtering.

        Args:
            admin_user: Admin user performing the search
            session: Database session
            filters: Audit log filters
            limit: Maximum results
            offset: Results offset

        Returns:
            Dict: Audit logs with metadata
        """
        try:
            # Build query
            query = select(AuditLog)
            query_filters = []

            if filters.deal_id:
                query_filters.append(AuditLog.deal_id == filters.deal_id)

            if filters.user_id:
                query_filters.append(AuditLog.user_id == filters.user_id)

            if filters.actor:
                query_filters.append(AuditLog.actor.ilike(f"%{filters.actor}%"))

            if filters.action:
                query_filters.append(AuditLog.action == filters.action)

            if filters.resource_type:
                query_filters.append(AuditLog.resource_type == filters.resource_type)

            if filters.success is not None:
                query_filters.append(AuditLog.success == filters.success)

            if filters.start_date:
                query_filters.append(AuditLog.ts >= filters.start_date)

            if filters.end_date:
                query_filters.append(AuditLog.ts <= filters.end_date)

            if query_filters:
                query = query.where(and_(*query_filters))

            # Get total count
            count_query = select(func.count(AuditLog.id))
            if query_filters:
                count_query = count_query.where(and_(*query_filters))
            total_count = session.exec(count_query).first() or 0

            # Apply ordering and pagination
            query = query.order_by(desc(AuditLog.ts)).offset(offset).limit(limit)

            # Execute query
            audit_logs = session.exec(query).all()

            # Log audit search
            search_audit_log = AuditLog(
                user_id=admin_user.id,
                actor=f"admin:{admin_user.id}",
                action="AUDIT_SEARCH",
                success=True,
                meta={
                    "filters": filters.dict(exclude_unset=True),
                    "result_count": len(audit_logs),
                    "total_count": total_count
                }
            )
            session.add(search_audit_log)
            session.commit()

            return {
                "audit_logs": [self._to_audit_log_public(log) for log in audit_logs],
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + len(audit_logs) < total_count
            }

        except Exception as e:
            logger.error(f"Audit log search failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to search audit logs"
            )

    async def export_audit_logs(
        self,
        admin_user: User,
        session: Session,
        filters: AuditLogFilter,
        export_format: str = "csv",
        limit: int = 1000
    ) -> Union[str, Dict[str, Any]]:
        """
        Export audit logs in CSV or JSON format.

        Args:
            admin_user: Admin user performing the export
            session: Database session
            filters: Audit log filters
            export_format: Export format (csv or json)
            limit: Maximum records to export

        Returns:
            Union[str, Dict]: Exported data as string (CSV) or dict (JSON)
        """
        try:
            # Get audit logs
            result = await self.search_audit_logs(
                admin_user, session, filters, limit=limit, offset=0
            )
            audit_logs = result["audit_logs"]

            if export_format.lower() == "csv":
                # Generate CSV
                output = StringIO()
                writer = csv.writer(output)

                # Write header
                writer.writerow([
                    "ID", "Timestamp", "User ID", "Actor", "Action",
                    "Success", "Resource Type", "Resource ID", "Deal ID"
                ])

                # Write data
                for log in audit_logs:
                    writer.writerow([
                        log.id,
                        log.ts.isoformat(),
                        log.user_id,
                        log.actor,
                        log.action,
                        log.success,
                        log.resource_type,
                        log.resource_id,
                        log.deal_id
                    ])

                csv_content = output.getvalue()
                output.close()

                # Log export
                export_audit_log = AuditLog(
                    user_id=admin_user.id,
                    actor=f"admin:{admin_user.id}",
                    action="AUDIT_EXPORT",
                    success=True,
                    meta={
                        "export_format": "csv",
                        "record_count": len(audit_logs),
                        "filters": filters.dict(exclude_unset=True)
                    }
                )
                session.add(export_audit_log)
                session.commit()

                return csv_content

            elif export_format.lower() == "json":
                # Generate JSON
                json_data = {
                    "export_timestamp": datetime.utcnow().isoformat(),
                    "exported_by": admin_user.email,
                    "filters": filters.dict(exclude_unset=True),
                    "total_records": len(audit_logs),
                    "audit_logs": [log.dict() for log in audit_logs]
                }

                # Log export
                export_audit_log = AuditLog(
                    user_id=admin_user.id,
                    actor=f"admin:{admin_user.id}",
                    action="AUDIT_EXPORT",
                    success=True,
                    meta={
                        "export_format": "json",
                        "record_count": len(audit_logs),
                        "filters": filters.dict(exclude_unset=True)
                    }
                )
                session.add(export_audit_log)
                session.commit()

                return json_data

            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid export format. Use 'csv' or 'json'"
                )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Audit log export failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to export audit logs"
            )

    def _to_audit_log_public(self, audit_log: AuditLog) -> AuditLogPublic:
        """Convert AuditLog to AuditLogPublic model."""
        return AuditLogPublic(
            id=audit_log.id,
            deal_id=audit_log.deal_id,
            user_id=audit_log.user_id,
            actor=audit_log.actor,
            action=audit_log.action,
            ts=audit_log.ts,
            resource_type=audit_log.resource_type,
            resource_id=audit_log.resource_id,
            success=audit_log.success
        )

    # System Monitoring and Analytics Methods
    async def get_system_health(
        self,
        admin_user: User,
        session: Session
    ) -> Dict[str, Any]:
        """
        Get comprehensive system health metrics.

        Args:
            admin_user: Admin user requesting health metrics
            session: Database session

        Returns:
            Dict: System health information
        """
        try:
            # Database health
            db_health = await self._check_database_health(session)

            # User statistics
            user_stats = await self._get_user_statistics(session)

            # Activity statistics
            activity_stats = await self._get_activity_statistics(session)

            # System performance
            performance_stats = await self._get_performance_statistics(session)

            health_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "overall_status": "healthy",
                "database": db_health,
                "users": user_stats,
                "activity": activity_stats,
                "performance": performance_stats
            }

            # Determine overall health status
            if not db_health["healthy"]:
                health_data["overall_status"] = "unhealthy"
            elif (user_stats["active_users_24h"] == 0 and
                  activity_stats["total_actions_24h"] == 0):
                health_data["overall_status"] = "warning"

            # Log health check
            audit_log = AuditLog(
                user_id=admin_user.id,
                actor=f"admin:{admin_user.id}",
                action="SYSTEM_HEALTH_CHECK",
                success=True,
                meta={
                    "overall_status": health_data["overall_status"],
                    "db_healthy": db_health["healthy"]
                }
            )
            session.add(audit_log)
            session.commit()

            return health_data

        except Exception as e:
            logger.error(f"System health check failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get system health"
            )

    async def get_usage_analytics(
        self,
        admin_user: User,
        session: Session,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get usage analytics for the specified period.

        Args:
            admin_user: Admin user requesting analytics
            session: Database session
            days: Number of days to analyze

        Returns:
            Dict: Usage analytics
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)

            # User activity analytics
            user_activity = await self._get_user_activity_analytics(session, start_date)

            # Template usage analytics
            template_usage = await self._get_template_usage_analytics(session, start_date)

            # Contract analytics
            contract_analytics = await self._get_contract_analytics(session, start_date)

            # Error analytics
            error_analytics = await self._get_error_analytics(session, start_date)

            analytics_data = {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": datetime.utcnow().isoformat(),
                    "days": days
                },
                "user_activity": user_activity,
                "template_usage": template_usage,
                "contracts": contract_analytics,
                "errors": error_analytics,
                "generated_at": datetime.utcnow().isoformat()
            }

            # Log analytics access
            audit_log = AuditLog(
                user_id=admin_user.id,
                actor=f"admin:{admin_user.id}",
                action="ANALYTICS_ACCESS",
                success=True,
                meta={
                    "period_days": days,
                    "analytics_types": ["user_activity", "template_usage", "contracts", "errors"]
                }
            )
            session.add(audit_log)
            session.commit()

            return analytics_data

        except Exception as e:
            logger.error(f"Usage analytics failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get usage analytics"
            )

    async def _check_database_health(self, session: Session) -> Dict[str, Any]:
        """Check database health and connectivity."""
        try:
            # Test basic query
            result = session.exec(select(func.count(User.id))).first()

            return {
                "healthy": True,
                "user_count": result or 0,
                "connection_status": "connected",
                "last_check": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "healthy": False,
                "error": str(e),
                "connection_status": "failed",
                "last_check": datetime.utcnow().isoformat()
            }

    async def _get_user_statistics(self, session: Session) -> Dict[str, Any]:
        """Get user statistics."""
        try:
            total_users = session.exec(select(func.count(User.id))).first() or 0
            active_users = session.exec(
                select(func.count(User.id)).where(User.disabled == False)
            ).first() or 0

            # Users active in last 24 hours
            yesterday = datetime.utcnow() - timedelta(days=1)
            active_24h = session.exec(
                select(func.count(User.id)).where(
                    and_(User.last_login >= yesterday, User.disabled == False)
                )
            ).first() or 0

            # Role distribution
            role_stats = {}
            for role in ["admin", "agent", "tc", "signer"]:
                count = session.exec(
                    select(func.count(User.id)).where(User.role == role)
                ).first() or 0
                role_stats[role] = count

            return {
                "total_users": total_users,
                "active_users": active_users,
                "active_users_24h": active_24h,
                "disabled_users": total_users - active_users,
                "role_distribution": role_stats
            }
        except Exception as e:
            logger.error(f"User statistics failed: {e}")
            return {"error": str(e)}

    async def _get_activity_statistics(self, session: Session) -> Dict[str, Any]:
        """Get activity statistics."""
        try:
            # Total actions in last 24 hours
            yesterday = datetime.utcnow() - timedelta(days=1)
            total_actions_24h = session.exec(
                select(func.count(AuditLog.id)).where(AuditLog.ts >= yesterday)
            ).first() or 0

            # Success rate in last 24 hours
            successful_actions_24h = session.exec(
                select(func.count(AuditLog.id)).where(
                    and_(AuditLog.ts >= yesterday, AuditLog.success == True)
                )
            ).first() or 0

            success_rate = (successful_actions_24h / total_actions_24h * 100) if total_actions_24h > 0 else 100

            # Most common actions
            common_actions = session.exec(
                select(AuditLog.action, func.count(AuditLog.id).label('count'))
                .where(AuditLog.ts >= yesterday)
                .group_by(AuditLog.action)
                .order_by(desc('count'))
                .limit(5)
            ).all()

            return {
                "total_actions_24h": total_actions_24h,
                "successful_actions_24h": successful_actions_24h,
                "success_rate_24h": round(success_rate, 2),
                "most_common_actions": [
                    {"action": action, "count": count}
                    for action, count in common_actions
                ]
            }
        except Exception as e:
            logger.error(f"Activity statistics failed: {e}")
            return {"error": str(e)}

    async def _get_performance_statistics(self, session: Session) -> Dict[str, Any]:
        """Get performance statistics."""
        try:
            # Template usage
            total_templates = session.exec(select(func.count(Template.id))).first() or 0
            active_templates = session.exec(
                select(func.count(Template.id)).where(Template.status == "active")
            ).first() or 0

            # Contract statistics
            total_contracts = session.exec(select(func.count(Contract.id))).first() or 0

            # Deal statistics
            total_deals = session.exec(select(func.count(Deal.id))).first() or 0

            return {
                "templates": {
                    "total": total_templates,
                    "active": active_templates
                },
                "contracts": {
                    "total": total_contracts
                },
                "deals": {
                    "total": total_deals
                }
            }
        except Exception as e:
            logger.error(f"Performance statistics failed: {e}")
            return {"error": str(e)}

    async def _get_user_activity_analytics(self, session: Session, start_date: datetime) -> Dict[str, Any]:
        """Get user activity analytics."""
        try:
            # Daily active users
            daily_active = session.exec(
                select(func.count(func.distinct(AuditLog.user_id)))
                .where(AuditLog.ts >= start_date)
            ).first() or 0

            # Most active users
            active_users = session.exec(
                select(AuditLog.user_id, func.count(AuditLog.id).label('action_count'))
                .where(AuditLog.ts >= start_date)
                .group_by(AuditLog.user_id)
                .order_by(desc('action_count'))
                .limit(10)
            ).all()

            return {
                "daily_active_users": daily_active,
                "most_active_users": [
                    {"user_id": user_id, "action_count": count}
                    for user_id, count in active_users
                ]
            }
        except Exception as e:
            logger.error(f"User activity analytics failed: {e}")
            return {"error": str(e)}

    async def _get_template_usage_analytics(self, session: Session, start_date: datetime) -> Dict[str, Any]:
        """Get template usage analytics."""
        try:
            # Most used templates
            template_usage = session.exec(
                select(Contract.template_id, func.count(Contract.id).label('usage_count'))
                .where(Contract.created_at >= start_date)
                .group_by(Contract.template_id)
                .order_by(desc('usage_count'))
                .limit(10)
            ).all()

            return {
                "most_used_templates": [
                    {"template_id": template_id, "usage_count": count}
                    for template_id, count in template_usage
                ]
            }
        except Exception as e:
            logger.error(f"Template usage analytics failed: {e}")
            return {"error": str(e)}

    async def _get_contract_analytics(self, session: Session, start_date: datetime) -> Dict[str, Any]:
        """Get contract analytics."""
        try:
            # Contracts created in period
            contracts_created = session.exec(
                select(func.count(Contract.id)).where(Contract.created_at >= start_date)
            ).first() or 0

            # Contract status distribution
            status_distribution = {}
            for status in ["draft", "active", "completed", "cancelled"]:
                count = session.exec(
                    select(func.count(Contract.id)).where(
                        and_(Contract.created_at >= start_date, Contract.status == status)
                    )
                ).first() or 0
                status_distribution[status] = count

            return {
                "contracts_created": contracts_created,
                "status_distribution": status_distribution
            }
        except Exception as e:
            logger.error(f"Contract analytics failed: {e}")
            return {"error": str(e)}

    async def _get_error_analytics(self, session: Session, start_date: datetime) -> Dict[str, Any]:
        """Get error analytics."""
        try:
            # Failed actions
            failed_actions = session.exec(
                select(func.count(AuditLog.id)).where(
                    and_(AuditLog.ts >= start_date, AuditLog.success == False)
                )
            ).first() or 0

            # Most common errors
            common_errors = session.exec(
                select(AuditLog.action, func.count(AuditLog.id).label('error_count'))
                .where(and_(AuditLog.ts >= start_date, AuditLog.success == False))
                .group_by(AuditLog.action)
                .order_by(desc('error_count'))
                .limit(5)
            ).all()

            return {
                "failed_actions": failed_actions,
                "most_common_errors": [
                    {"action": action, "error_count": count}
                    for action, count in common_errors
                ]
            }
        except Exception as e:
            logger.error(f"Error analytics failed: {e}")
            return {"error": str(e)}

    # Template Management Methods
    async def list_templates(
        self,
        admin_user: User,
        session: Session,
        status: Optional[TemplateStatus] = None,
        template_type: Optional[TemplateType] = None,
        search_query: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        List templates with filtering and pagination.

        Args:
            admin_user: Admin user requesting the list
            session: Database session
            status: Filter by template status
            template_type: Filter by template type
            search_query: Search in name and description
            limit: Maximum results
            offset: Results offset

        Returns:
            Dict: Templates list with metadata
        """
        try:
            # Build query
            query = select(Template)
            filters = []

            if status:
                filters.append(Template.status == status)

            if template_type:
                filters.append(Template.template_type == template_type)

            if search_query:
                search_filters = [
                    Template.name.ilike(f"%{search_query}%"),
                    Template.description.ilike(f"%{search_query}%")
                ]
                filters.append(or_(*search_filters))

            if filters:
                query = query.where(and_(*filters))

            # Get total count
            count_query = select(func.count(Template.id))
            if filters:
                count_query = count_query.where(and_(*filters))
            total_count = session.exec(count_query).first() or 0

            # Apply ordering and pagination
            query = query.order_by(desc(Template.created_at)).offset(offset).limit(limit)

            # Execute query
            templates = session.exec(query).all()

            # Log template list access
            audit_log = AuditLog(
                user_id=admin_user.id,
                actor=f"admin:{admin_user.id}",
                action="TEMPLATE_LIST",
                success=True,
                meta={
                    "filters": {
                        "status": status.value if status else None,
                        "template_type": template_type.value if template_type else None,
                        "search_query": search_query
                    },
                    "result_count": len(templates),
                    "total_count": total_count
                }
            )
            session.add(audit_log)
            session.commit()

            return {
                "templates": [self._to_template_public(template) for template in templates],
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + len(templates) < total_count
            }

        except Exception as e:
            logger.error(f"Template listing failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to list templates"
            )

    async def get_template(
        self,
        template_id: int,
        admin_user: User,
        session: Session,
        include_details: bool = False
    ) -> Union[TemplatePublic, TemplateWithDetails]:
        """
        Get template details by ID.

        Args:
            template_id: Template ID to retrieve
            admin_user: Admin user requesting the details
            session: Database session
            include_details: Whether to include detailed information

        Returns:
            Union[TemplatePublic, TemplateWithDetails]: Template information
        """
        try:
            template = session.get(Template, template_id)
            if not template:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Template not found"
                )

            # Log template access
            audit_log = AuditLog(
                user_id=admin_user.id,
                actor=f"admin:{admin_user.id}",
                action="TEMPLATE_READ",
                success=True,
                meta={
                    "accessed_template_id": template_id,
                    "accessed_template_name": template.name,
                    "include_details": include_details
                }
            )
            session.add(audit_log)
            session.commit()

            if include_details:
                return self._to_template_with_details(template)
            else:
                return self._to_template_public(template)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Template retrieval failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve template"
            )

    async def update_template_status(
        self,
        template_id: int,
        new_status: TemplateStatus,
        admin_user: User,
        session: Session
    ) -> TemplatePublic:
        """
        Update template status (activate, deactivate, archive).

        Args:
            template_id: Template ID to update
            new_status: New template status
            admin_user: Admin user performing the update
            session: Database session

        Returns:
            TemplatePublic: Updated template information
        """
        try:
            template = session.get(Template, template_id)
            if not template:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Template not found"
                )

            # Store original status for audit
            original_status = template.status

            # Update status
            template.status = new_status
            session.add(template)
            session.commit()
            session.refresh(template)

            # Log template status update
            audit_log = AuditLog(
                user_id=admin_user.id,
                actor=f"admin:{admin_user.id}",
                action="TEMPLATE_STATUS_UPDATE",
                success=True,
                before_state={"status": original_status.value},
                after_state={"status": new_status.value},
                meta={
                    "template_id": template_id,
                    "template_name": template.name,
                    "status_change": f"{original_status.value} -> {new_status.value}"
                }
            )
            session.add(audit_log)
            session.commit()

            return self._to_template_public(template)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Template status update failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Template status update failed"
            )

    async def get_template_usage_analytics(
        self,
        template_id: int,
        admin_user: User,
        session: Session,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get template usage analytics.

        Args:
            template_id: Template ID to analyze
            admin_user: Admin user requesting analytics
            session: Database session
            days: Number of days to analyze

        Returns:
            Dict: Template usage analytics
        """
        try:
            template = session.get(Template, template_id)
            if not template:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Template not found"
                )

            start_date = datetime.utcnow() - timedelta(days=days)

            # Usage statistics
            total_contracts = session.exec(
                select(func.count(Contract.id)).where(Contract.template_id == template_id)
            ).first() or 0

            recent_contracts = session.exec(
                select(func.count(Contract.id)).where(
                    and_(Contract.template_id == template_id, Contract.created_at >= start_date)
                )
            ).first() or 0

            # Contract status distribution
            status_distribution = {}
            for contract_status in ["draft", "active", "completed", "cancelled"]:
                count = session.exec(
                    select(func.count(Contract.id)).where(
                        and_(
                            Contract.template_id == template_id,
                            Contract.status == contract_status,
                            Contract.created_at >= start_date
                        )
                    )
                ).first() or 0
                status_distribution[contract_status] = count

            analytics_data = {
                "template_id": template_id,
                "template_name": template.name,
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": datetime.utcnow().isoformat(),
                    "days": days
                },
                "usage_stats": {
                    "total_contracts": total_contracts,
                    "recent_contracts": recent_contracts,
                    "status_distribution": status_distribution
                },
                "generated_at": datetime.utcnow().isoformat()
            }

            # Log analytics access
            audit_log = AuditLog(
                user_id=admin_user.id,
                actor=f"admin:{admin_user.id}",
                action="TEMPLATE_ANALYTICS",
                success=True,
                meta={
                    "template_id": template_id,
                    "period_days": days,
                    "total_contracts": total_contracts
                }
            )
            session.add(audit_log)
            session.commit()

            return analytics_data

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Template analytics failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get template analytics"
            )

    def _to_template_public(self, template: Template) -> TemplatePublic:
        """Convert Template to TemplatePublic model."""
        return TemplatePublic(
            id=template.id,
            name=template.name,
            version=template.version,
            template_type=template.template_type,
            status=template.status,
            description=template.description,
            category=template.category,
            tags=template.tags or [],
            supported_formats=template.supported_formats or [],
            created_at=template.created_at,
            updated_at=template.updated_at,
            created_by=template.created_by,
            updated_by=template.updated_by
        )

    def _to_template_with_details(self, template: Template) -> TemplateWithDetails:
        """Convert Template to TemplateWithDetails model."""
        return TemplateWithDetails(
            id=template.id,
            name=template.name,
            version=template.version,
            template_type=template.template_type,
            status=template.status,
            description=template.description,
            category=template.category,
            tags=template.tags or [],
            supported_formats=template.supported_formats or [],
            created_at=template.created_at,
            updated_at=template.updated_at,
            created_by=template.created_by,
            updated_by=template.updated_by,
            variables=template.variables or [],
            schema=template.schema,
            ruleset=template.ruleset,
            conditional_logic=template.conditional_logic,
            business_rules=template.business_rules
        )


# Global admin service instance
_admin_service: Optional[AdminService] = None


def get_admin_service() -> AdminService:
    """
    Get global admin service instance.

    Returns:
        AdminService: Configured admin service
    """
    global _admin_service

    if _admin_service is None:
        _admin_service = AdminService()

    return _admin_service


# Export service
__all__ = [
    "AdminService",
    "AdminServiceError",
    "get_admin_service",
]
