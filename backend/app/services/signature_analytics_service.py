"""
Signature analytics and reporting service.

This module provides comprehensive analytics, reporting, and insights
for signature workflows, performance metrics, and compliance tracking.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from sqlmodel import Session, select, func, and_, or_
from sqlalchemy import text

from ..core.config import get_settings
from ..models.signature import (
    SignatureRequest, SignatureRequestStatus, SignatureProvider,
    SignatureAudit, SignatureAnalytics, SignatureReport
)
from ..models.signer import Signer
from ..models.user import User

logger = logging.getLogger(__name__)
settings = get_settings()


class SignatureAnalyticsError(Exception):
    """Exception raised during analytics operations."""
    pass


class SignatureAnalyticsService:
    """
    Comprehensive signature analytics and reporting service.
    
    Provides analytics, metrics, reporting, and insights for
    signature workflows and performance tracking.
    """
    
    def __init__(self):
        """Initialize signature analytics service."""
        pass
    
    async def get_signature_analytics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        user_id: Optional[int] = None,
        provider: Optional[SignatureProvider] = None,
        session: Session = None
    ) -> SignatureAnalytics:
        """
        Get comprehensive signature analytics.
        
        Args:
            start_date: Start date for analytics period
            end_date: End date for analytics period
            user_id: Filter by specific user
            provider: Filter by signature provider
            session: Database session
            
        Returns:
            SignatureAnalytics: Analytics data
        """
        try:
            # Set default date range if not provided
            if not end_date:
                end_date = datetime.utcnow()
            if not start_date:
                start_date = end_date - timedelta(days=30)
            
            # Build base query
            query = select(SignatureRequest).where(
                and_(
                    SignatureRequest.created_at >= start_date,
                    SignatureRequest.created_at <= end_date
                )
            )
            
            # Apply filters
            if user_id:
                query = query.where(SignatureRequest.created_by == user_id)
            
            if provider:
                query = query.where(SignatureRequest.provider == provider)
            
            # Get all signature requests in period
            signature_requests = session.exec(query).all()
            
            # Calculate metrics
            total_requests = len(signature_requests)
            completed_requests = len([r for r in signature_requests if r.status == SignatureRequestStatus.COMPLETED])
            pending_requests = len([r for r in signature_requests if r.status in [SignatureRequestStatus.SENT, SignatureRequestStatus.IN_PROGRESS]])
            declined_requests = len([r for r in signature_requests if r.status == SignatureRequestStatus.DECLINED])
            expired_requests = len([r for r in signature_requests if r.status == SignatureRequestStatus.EXPIRED])
            
            # Calculate rates
            completion_rate = (completed_requests / total_requests * 100) if total_requests > 0 else 0
            decline_rate = (declined_requests / total_requests * 100) if total_requests > 0 else 0
            
            # Calculate average completion time
            avg_completion_time = await self._calculate_average_completion_time(
                signature_requests, session
            )
            
            # Get provider breakdown
            provider_breakdown = await self._get_provider_breakdown(
                signature_requests, session
            )
            
            # Get monthly trends
            monthly_trends = await self._get_monthly_trends(
                start_date, end_date, user_id, provider, session
            )
            
            return SignatureAnalytics(
                total_requests=total_requests,
                completed_requests=completed_requests,
                pending_requests=pending_requests,
                declined_requests=declined_requests,
                expired_requests=expired_requests,
                average_completion_time=avg_completion_time,
                completion_rate=completion_rate,
                decline_rate=decline_rate,
                provider_breakdown=provider_breakdown,
                monthly_trends=monthly_trends
            )
            
        except Exception as e:
            logger.error(f"Failed to get signature analytics: {e}")
            raise SignatureAnalyticsError(f"Analytics generation failed: {str(e)}")
    
    async def generate_signature_report(
        self,
        report_type: str,
        filters: Dict[str, Any],
        user_id: int,
        session: Session
    ) -> SignatureReport:
        """
        Generate detailed signature report.
        
        Args:
            report_type: Type of report to generate
            filters: Report filters and parameters
            user_id: User requesting the report
            session: Database session
            
        Returns:
            SignatureReport: Generated report
        """
        try:
            start_date = filters.get("start_date")
            end_date = filters.get("end_date")
            
            if isinstance(start_date, str):
                start_date = datetime.fromisoformat(start_date)
            if isinstance(end_date, str):
                end_date = datetime.fromisoformat(end_date)
            
            report_data = {}
            
            if report_type == "completion_summary":
                report_data = await self._generate_completion_summary_report(
                    start_date, end_date, filters, session
                )
            elif report_type == "provider_performance":
                report_data = await self._generate_provider_performance_report(
                    start_date, end_date, filters, session
                )
            elif report_type == "user_activity":
                report_data = await self._generate_user_activity_report(
                    start_date, end_date, filters, session
                )
            elif report_type == "compliance_audit":
                report_data = await self._generate_compliance_audit_report(
                    start_date, end_date, filters, session
                )
            else:
                raise SignatureAnalyticsError(f"Unsupported report type: {report_type}")
            
            return SignatureReport(
                report_type=report_type,
                date_range={"start": start_date, "end": end_date},
                filters=filters,
                data=report_data,
                generated_at=datetime.utcnow(),
                generated_by=user_id
            )
            
        except Exception as e:
            logger.error(f"Failed to generate signature report: {e}")
            raise SignatureAnalyticsError(f"Report generation failed: {str(e)}")
    
    async def get_signature_performance_metrics(
        self,
        user_id: Optional[int] = None,
        session: Session = None
    ) -> Dict[str, Any]:
        """
        Get signature performance metrics.
        
        Args:
            user_id: Filter by specific user
            session: Database session
            
        Returns:
            Dict: Performance metrics
        """
        try:
            # Get metrics for different time periods
            metrics = {}
            
            for period_name, days in [("7_days", 7), ("30_days", 30), ("90_days", 90)]:
                start_date = datetime.utcnow() - timedelta(days=days)
                end_date = datetime.utcnow()
                
                analytics = await self.get_signature_analytics(
                    start_date, end_date, user_id, None, session
                )
                
                metrics[period_name] = {
                    "total_requests": analytics.total_requests,
                    "completion_rate": analytics.completion_rate,
                    "decline_rate": analytics.decline_rate,
                    "average_completion_time": analytics.average_completion_time
                }
            
            # Get top performing providers
            top_providers = await self._get_top_performing_providers(session)
            
            # Get recent activity
            recent_activity = await self._get_recent_signature_activity(user_id, session)
            
            return {
                "period_metrics": metrics,
                "top_providers": top_providers,
                "recent_activity": recent_activity,
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            raise SignatureAnalyticsError(f"Performance metrics failed: {str(e)}")
    
    async def get_signature_trends(
        self,
        period: str = "monthly",
        user_id: Optional[int] = None,
        session: Session = None
    ) -> Dict[str, Any]:
        """
        Get signature trends over time.
        
        Args:
            period: Trend period (daily, weekly, monthly)
            user_id: Filter by specific user
            session: Database session
            
        Returns:
            Dict: Trend data
        """
        try:
            # Calculate date range based on period
            if period == "daily":
                start_date = datetime.utcnow() - timedelta(days=30)
                date_format = "%Y-%m-%d"
            elif period == "weekly":
                start_date = datetime.utcnow() - timedelta(weeks=12)
                date_format = "%Y-W%U"
            else:  # monthly
                start_date = datetime.utcnow() - timedelta(days=365)
                date_format = "%Y-%m"
            
            end_date = datetime.utcnow()
            
            # Build query
            query = select(
                func.date_format(SignatureRequest.created_at, date_format).label("period"),
                func.count(SignatureRequest.id).label("total_requests"),
                func.sum(
                    func.case(
                        (SignatureRequest.status == SignatureRequestStatus.COMPLETED, 1),
                        else_=0
                    )
                ).label("completed_requests"),
                func.sum(
                    func.case(
                        (SignatureRequest.status == SignatureRequestStatus.DECLINED, 1),
                        else_=0
                    )
                ).label("declined_requests")
            ).where(
                and_(
                    SignatureRequest.created_at >= start_date,
                    SignatureRequest.created_at <= end_date
                )
            ).group_by("period").order_by("period")
            
            if user_id:
                query = query.where(SignatureRequest.created_by == user_id)
            
            # Execute query
            results = session.exec(query).all()
            
            # Format results
            trends = []
            for result in results:
                completion_rate = (result.completed_requests / result.total_requests * 100) if result.total_requests > 0 else 0
                decline_rate = (result.declined_requests / result.total_requests * 100) if result.total_requests > 0 else 0
                
                trends.append({
                    "period": result.period,
                    "total_requests": result.total_requests,
                    "completed_requests": result.completed_requests,
                    "declined_requests": result.declined_requests,
                    "completion_rate": completion_rate,
                    "decline_rate": decline_rate
                })
            
            return {
                "period_type": period,
                "date_range": {"start": start_date.isoformat(), "end": end_date.isoformat()},
                "trends": trends
            }
            
        except Exception as e:
            logger.error(f"Failed to get signature trends: {e}")
            raise SignatureAnalyticsError(f"Trend analysis failed: {str(e)}")
    
    # Helper methods
    async def _calculate_average_completion_time(
        self,
        signature_requests: List[SignatureRequest],
        session: Session
    ) -> Optional[float]:
        """Calculate average completion time in hours."""
        try:
            completed_requests = [
                r for r in signature_requests 
                if r.status == SignatureRequestStatus.COMPLETED and r.sent_at and r.completed_at
            ]
            
            if not completed_requests:
                return None
            
            total_time = 0
            for request in completed_requests:
                completion_time = (request.completed_at - request.sent_at).total_seconds() / 3600
                total_time += completion_time
            
            return total_time / len(completed_requests)
            
        except Exception as e:
            logger.error(f"Failed to calculate average completion time: {e}")
            return None
    
    async def _get_provider_breakdown(
        self,
        signature_requests: List[SignatureRequest],
        session: Session
    ) -> Dict[str, int]:
        """Get breakdown by signature provider."""
        try:
            breakdown = {}
            
            for request in signature_requests:
                provider = request.provider.value if request.provider else "unknown"
                breakdown[provider] = breakdown.get(provider, 0) + 1
            
            return breakdown
            
        except Exception as e:
            logger.error(f"Failed to get provider breakdown: {e}")
            return {}
    
    async def _get_monthly_trends(
        self,
        start_date: datetime,
        end_date: datetime,
        user_id: Optional[int],
        provider: Optional[SignatureProvider],
        session: Session
    ) -> List[Dict[str, Any]]:
        """Get monthly trend data."""
        try:
            # Generate monthly buckets
            current_date = start_date.replace(day=1)
            trends = []
            
            while current_date <= end_date:
                next_month = (current_date.replace(day=28) + timedelta(days=4)).replace(day=1)
                
                # Query for this month
                query = select(func.count(SignatureRequest.id)).where(
                    and_(
                        SignatureRequest.created_at >= current_date,
                        SignatureRequest.created_at < next_month
                    )
                )
                
                if user_id:
                    query = query.where(SignatureRequest.created_by == user_id)
                
                if provider:
                    query = query.where(SignatureRequest.provider == provider)
                
                count = session.exec(query).first() or 0
                
                trends.append({
                    "month": current_date.strftime("%Y-%m"),
                    "requests": count
                })
                
                current_date = next_month
            
            return trends
            
        except Exception as e:
            logger.error(f"Failed to get monthly trends: {e}")
            return []
    
    async def _generate_completion_summary_report(
        self,
        start_date: datetime,
        end_date: datetime,
        filters: Dict[str, Any],
        session: Session
    ) -> Dict[str, Any]:
        """Generate completion summary report."""
        try:
            # Get basic analytics
            analytics = await self.get_signature_analytics(
                start_date, end_date, filters.get("user_id"), filters.get("provider"), session
            )
            
            # Get detailed completion data
            query = select(SignatureRequest).where(
                and_(
                    SignatureRequest.created_at >= start_date,
                    SignatureRequest.created_at <= end_date,
                    SignatureRequest.status == SignatureRequestStatus.COMPLETED
                )
            )
            
            completed_requests = session.exec(query).all()
            
            # Calculate detailed metrics
            completion_times = []
            for request in completed_requests:
                if request.sent_at and request.completed_at:
                    time_diff = (request.completed_at - request.sent_at).total_seconds() / 3600
                    completion_times.append(time_diff)
            
            return {
                "summary": analytics.model_dump(),
                "completion_times": {
                    "average": sum(completion_times) / len(completion_times) if completion_times else 0,
                    "median": sorted(completion_times)[len(completion_times) // 2] if completion_times else 0,
                    "min": min(completion_times) if completion_times else 0,
                    "max": max(completion_times) if completion_times else 0
                },
                "completed_requests_detail": [
                    {
                        "id": r.id,
                        "title": r.title,
                        "sent_at": r.sent_at.isoformat() if r.sent_at else None,
                        "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                        "provider": r.provider.value if r.provider else None
                    }
                    for r in completed_requests[:100]  # Limit to 100 for report size
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to generate completion summary report: {e}")
            return {"error": str(e)}
    
    async def _generate_provider_performance_report(
        self,
        start_date: datetime,
        end_date: datetime,
        filters: Dict[str, Any],
        session: Session
    ) -> Dict[str, Any]:
        """Generate provider performance report."""
        try:
            provider_stats = {}
            
            for provider in SignatureProvider:
                analytics = await self.get_signature_analytics(
                    start_date, end_date, filters.get("user_id"), provider, session
                )
                
                provider_stats[provider.value] = {
                    "total_requests": analytics.total_requests,
                    "completion_rate": analytics.completion_rate,
                    "decline_rate": analytics.decline_rate,
                    "average_completion_time": analytics.average_completion_time
                }
            
            return {
                "provider_performance": provider_stats,
                "best_performing_provider": max(
                    provider_stats.items(),
                    key=lambda x: x[1]["completion_rate"]
                )[0] if provider_stats else None
            }
            
        except Exception as e:
            logger.error(f"Failed to generate provider performance report: {e}")
            return {"error": str(e)}
    
    async def _generate_user_activity_report(
        self,
        start_date: datetime,
        end_date: datetime,
        filters: Dict[str, Any],
        session: Session
    ) -> Dict[str, Any]:
        """Generate user activity report."""
        try:
            # Get user activity data
            query = select(
                SignatureRequest.created_by,
                func.count(SignatureRequest.id).label("total_requests"),
                func.sum(
                    func.case(
                        (SignatureRequest.status == SignatureRequestStatus.COMPLETED, 1),
                        else_=0
                    )
                ).label("completed_requests")
            ).where(
                and_(
                    SignatureRequest.created_at >= start_date,
                    SignatureRequest.created_at <= end_date
                )
            ).group_by(SignatureRequest.created_by)
            
            results = session.exec(query).all()
            
            user_activity = []
            for result in results:
                user = session.get(User, result.created_by)
                completion_rate = (result.completed_requests / result.total_requests * 100) if result.total_requests > 0 else 0
                
                user_activity.append({
                    "user_id": result.created_by,
                    "user_name": user.name if user else "Unknown",
                    "user_email": user.email if user else "Unknown",
                    "total_requests": result.total_requests,
                    "completed_requests": result.completed_requests,
                    "completion_rate": completion_rate
                })
            
            # Sort by total requests
            user_activity.sort(key=lambda x: x["total_requests"], reverse=True)
            
            return {
                "user_activity": user_activity,
                "total_active_users": len(user_activity),
                "top_user": user_activity[0] if user_activity else None
            }
            
        except Exception as e:
            logger.error(f"Failed to generate user activity report: {e}")
            return {"error": str(e)}
    
    async def _generate_compliance_audit_report(
        self,
        start_date: datetime,
        end_date: datetime,
        filters: Dict[str, Any],
        session: Session
    ) -> Dict[str, Any]:
        """Generate compliance audit report."""
        try:
            # Get audit events
            query = select(SignatureAudit).where(
                and_(
                    SignatureAudit.timestamp >= start_date,
                    SignatureAudit.timestamp <= end_date
                )
            ).order_by(SignatureAudit.timestamp.desc())
            
            audit_events = session.exec(query).all()
            
            # Categorize events
            event_categories = {}
            for event in audit_events:
                category = event.event_type
                if category not in event_categories:
                    event_categories[category] = 0
                event_categories[category] += 1
            
            return {
                "audit_summary": {
                    "total_events": len(audit_events),
                    "event_categories": event_categories,
                    "date_range": {
                        "start": start_date.isoformat(),
                        "end": end_date.isoformat()
                    }
                },
                "recent_events": [
                    {
                        "timestamp": event.timestamp.isoformat(),
                        "event_type": event.event_type,
                        "description": event.event_description,
                        "user_id": event.user_id,
                        "ip_address": event.ip_address
                    }
                    for event in audit_events[:50]  # Limit to 50 recent events
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to generate compliance audit report: {e}")
            return {"error": str(e)}
    
    async def _get_top_performing_providers(self, session: Session) -> List[Dict[str, Any]]:
        """Get top performing providers."""
        try:
            provider_performance = []
            
            for provider in SignatureProvider:
                analytics = await self.get_signature_analytics(
                    provider=provider, session=session
                )
                
                if analytics.total_requests > 0:
                    provider_performance.append({
                        "provider": provider.value,
                        "completion_rate": analytics.completion_rate,
                        "total_requests": analytics.total_requests
                    })
            
            # Sort by completion rate
            provider_performance.sort(key=lambda x: x["completion_rate"], reverse=True)
            
            return provider_performance[:5]  # Top 5
            
        except Exception as e:
            logger.error(f"Failed to get top performing providers: {e}")
            return []
    
    async def _get_recent_signature_activity(
        self,
        user_id: Optional[int],
        session: Session
    ) -> List[Dict[str, Any]]:
        """Get recent signature activity."""
        try:
            query = select(SignatureRequest).order_by(
                SignatureRequest.created_at.desc()
            ).limit(10)
            
            if user_id:
                query = query.where(SignatureRequest.created_by == user_id)
            
            recent_requests = session.exec(query).all()
            
            return [
                {
                    "id": request.id,
                    "title": request.title,
                    "status": request.status.value,
                    "created_at": request.created_at.isoformat(),
                    "provider": request.provider.value if request.provider else None
                }
                for request in recent_requests
            ]
            
        except Exception as e:
            logger.error(f"Failed to get recent signature activity: {e}")
            return []


# Global signature analytics service instance
_signature_analytics_service: Optional[SignatureAnalyticsService] = None


def get_signature_analytics_service() -> SignatureAnalyticsService:
    """
    Get global signature analytics service instance.
    
    Returns:
        SignatureAnalyticsService: Configured signature analytics service
    """
    global _signature_analytics_service
    
    if _signature_analytics_service is None:
        _signature_analytics_service = SignatureAnalyticsService()
    
    return _signature_analytics_service


# Export service
__all__ = [
    "SignatureAnalyticsService",
    "SignatureAnalyticsError",
    "get_signature_analytics_service",
]
