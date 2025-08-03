"""
Notification service for email and SMS notifications.

This module provides comprehensive notification capabilities
for signature requests, reminders, completions, and system alerts.
"""

import logging
import asyncio
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any, List
from jinja2 import Environment, BaseLoader

from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class NotificationError(Exception):
    """Exception raised during notification operations."""
    pass


class NotificationService:
    """
    Comprehensive notification service.

    Provides email and SMS notifications for signature workflows,
    reminders, completions, and system alerts.
    """

    def __init__(self):
        """Initialize notification service."""
        self.email_enabled = bool(getattr(settings, 'smtp_host', None))
        self.sms_enabled = bool(getattr(settings, 'sms_provider', None))
        self.template_env = Environment(loader=BaseLoader())

    async def send_signature_notification(
        self,
        recipient_email: str,
        recipient_name: str,
        document_title: str,
        signing_url: str
    ):
        """Send signature request notification."""
        try:
            subject = f"Signature Required: {document_title}"

            message = f"""
            Hello {recipient_name},

            You have been requested to sign the following document:

            Document: {document_title}

            Please click the link below to review and sign the document:
            {signing_url}

            If you have any questions about this document, please contact the sender.

            Best regards,
            The Contract Platform Team
            """

            await self._send_email(recipient_email, subject, message)

        except Exception as e:
            logger.error(f"Failed to send signature notification: {e}")

    async def send_signature_reminder(
        self,
        recipient_email: str,
        recipient_name: str,
        document_title: str,
        signing_url: str,
        days_remaining: Optional[int] = None
    ):
        """Send signature reminder notification."""
        try:
            subject = f"Reminder: Signature Required for {document_title}"

            expiry_text = ""
            if days_remaining is not None:
                if days_remaining > 0:
                    expiry_text = f"\n\nPlease note: This signature request will expire in {days_remaining} day(s)."
                else:
                    expiry_text = "\n\nPlease note: This signature request expires today."

            message = f"""
            Hello {recipient_name},

            This is a friendly reminder that you have a pending signature request:

            Document: {document_title}

            Please click the link below to review and sign the document:
            {signing_url}
            {expiry_text}

            If you have any questions about this document, please contact the sender.

            Best regards,
            The Contract Platform Team
            """

            await self._send_email(recipient_email, subject, message)

        except Exception as e:
            logger.error(f"Failed to send signature reminder: {e}")

    async def send_completion_notification(
        self,
        recipient_email: str,
        recipient_name: str,
        document_title: str
    ):
        """Send signature completion notification."""
        try:
            subject = f"Document Signed: {document_title}"

            message = f"""
            Hello {recipient_name},

            Great news! The following document has been fully signed by all parties:

            Document: {document_title}

            You can download the completed document from your dashboard.

            Thank you for using our signature service.

            Best regards,
            The Contract Platform Team
            """

            await self._send_email(recipient_email, subject, message)

        except Exception as e:
            logger.error(f"Failed to send completion notification: {e}")

    async def send_signature_declined_notification(
        self,
        recipient_email: str,
        recipient_name: str,
        document_title: str,
        signer_name: str,
        decline_reason: Optional[str] = None
    ):
        """Send signature declined notification."""
        try:
            subject = f"Signature Declined: {document_title}"

            reason_text = ""
            if decline_reason:
                reason_text = f"\n\nReason provided: {decline_reason}"

            message = f"""
            Hello {recipient_name},

            We wanted to inform you that {signer_name} has declined to sign the following document:

            Document: {document_title}
            {reason_text}

            You may want to contact {signer_name} directly to discuss this matter.

            Best regards,
            The Contract Platform Team
            """

            await self._send_email(recipient_email, subject, message)

        except Exception as e:
            logger.error(f"Failed to send signature declined notification: {e}")

    async def send_signature_expired_notification(
        self,
        recipient_email: str,
        recipient_name: str,
        document_title: str
    ):
        """Send signature expired notification."""
        try:
            subject = f"Signature Request Expired: {document_title}"

            message = f"""
            Hello {recipient_name},

            The signature request for the following document has expired:

            Document: {document_title}

            If you still need this document signed, please create a new signature request.

            Best regards,
            The Contract Platform Team
            """

            await self._send_email(recipient_email, subject, message)

        except Exception as e:
            logger.error(f"Failed to send signature expired notification: {e}")

    async def send_bulk_notification(
        self,
        notifications: List[Dict[str, Any]]
    ):
        """Send multiple notifications in bulk."""
        try:
            tasks = []

            for notification in notifications:
                notification_type = notification.get("type")

                if notification_type == "signature_request":
                    task = self.send_signature_notification(
                        notification["recipient_email"],
                        notification["recipient_name"],
                        notification["document_title"],
                        notification["signing_url"]
                    )
                elif notification_type == "signature_reminder":
                    task = self.send_signature_reminder(
                        notification["recipient_email"],
                        notification["recipient_name"],
                        notification["document_title"],
                        notification["signing_url"],
                        notification.get("days_remaining")
                    )
                elif notification_type == "completion":
                    task = self.send_completion_notification(
                        notification["recipient_email"],
                        notification["recipient_name"],
                        notification["document_title"]
                    )
                else:
                    continue

                tasks.append(task)

            # Send all notifications concurrently
            await asyncio.gather(*tasks, return_exceptions=True)

        except Exception as e:
            logger.error(f"Failed to send bulk notifications: {e}")

    async def send_sms_notification(
        self,
        phone_number: str,
        message: str
    ):
        """Send SMS notification."""
        try:
            if not self.sms_enabled:
                logger.warning("SMS notifications not configured")
                return

            # SMS implementation would go here
            # For now, just log the message
            logger.info(f"SMS to {phone_number}: {message}")

        except Exception as e:
            logger.error(f"Failed to send SMS notification: {e}")

    async def _send_email(
        self,
        recipient_email: str,
        subject: str,
        message: str,
        html_message: Optional[str] = None
    ):
        """Send email notification."""
        try:
            if not self.email_enabled:
                logger.warning("Email notifications not configured")
                return

            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = getattr(settings, 'smtp_from_email', 'noreply@example.com')
            msg['To'] = recipient_email

            # Add text part
            text_part = MIMEText(message, 'plain')
            msg.attach(text_part)

            # Add HTML part if provided
            if html_message:
                html_part = MIMEText(html_message, 'html')
                msg.attach(html_part)

            # Send email
            smtp_host = getattr(settings, 'smtp_host', 'localhost')
            smtp_port = getattr(settings, 'smtp_port', 587)
            smtp_use_tls = getattr(settings, 'smtp_use_tls', True)
            smtp_username = getattr(settings, 'smtp_username', None)
            smtp_password = getattr(settings, 'smtp_password', None)

            with smtplib.SMTP(smtp_host, smtp_port) as server:
                if smtp_use_tls:
                    server.starttls()

                if smtp_username and smtp_password:
                    server.login(smtp_username, smtp_password)

                server.send_message(msg)

            logger.info(f"Email sent to {recipient_email}: {subject}")

        except Exception as e:
            logger.error(f"Failed to send email to {recipient_email}: {e}")
            raise NotificationError(f"Email sending failed: {str(e)}")

    def _render_template(
        self,
        template_content: str,
        variables: Dict[str, Any]
    ) -> str:
        """Render notification template."""
        try:
            template = self.template_env.from_string(template_content)
            return template.render(**variables)
        except Exception as e:
            logger.error(f"Template rendering failed: {e}")
            return template_content


# Global notification service instance
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """
    Get global notification service instance.

    Returns:
        NotificationService: Configured notification service
    """
    global _notification_service

    if _notification_service is None:
        _notification_service = NotificationService()

    return _notification_service


# Export service
__all__ = [
    "NotificationService",
    "NotificationError",
    "get_notification_service",
]
