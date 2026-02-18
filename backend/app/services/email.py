"""
Email notification service.

In development, emails are logged to console.
In production, configure SMTP or use a service like SendGrid, AWS SES, etc.
"""

import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Email notification service with pluggable backends."""

    @staticmethod
    async def send_email(
        to_email: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
    ) -> bool:
        """
        Send an email notification.

        In development mode, this logs to console.
        In production, implement actual email sending.
        """
        # For development, just log the email
        logger.info(f"""
        ========== EMAIL NOTIFICATION ==========
        To: {to_email}
        Subject: {subject}
        Body:
        {body}
        ========================================
        """)

        # In production, uncomment and configure one of these:
        # return await _send_via_smtp(to_email, subject, body, html_body)
        # return await _send_via_sendgrid(to_email, subject, body, html_body)
        # return await _send_via_ses(to_email, subject, body, html_body)

        return True

    @staticmethod
    async def send_timesheet_submitted(
        employee_email: str,
        employee_name: str,
        manager_email: str,
        manager_name: str,
        pay_period: str,
        total_hours: float,
    ) -> None:
        """Notify manager when a timesheet is submitted."""
        subject = f"Timesheet Submitted: {employee_name}"
        body = f"""
Hello {manager_name},

{employee_name} has submitted their timesheet for review.

Pay Period: {pay_period}
Total Hours: {total_hours}

Please review and approve at your earliest convenience.

- MyHours System
        """.strip()

        await EmailService.send_email(manager_email, subject, body)

    @staticmethod
    async def send_timesheet_approved(
        employee_email: str,
        employee_name: str,
        pay_period: str,
        approved_by: str,
    ) -> None:
        """Notify employee when their timesheet is approved."""
        subject = f"Timesheet Approved - {pay_period}"
        body = f"""
Hello {employee_name},

Great news! Your timesheet for {pay_period} has been approved by {approved_by}.

No further action is required.

- MyHours System
        """.strip()

        await EmailService.send_email(employee_email, subject, body)

    @staticmethod
    async def send_timesheet_rejected(
        employee_email: str,
        employee_name: str,
        pay_period: str,
        rejected_by: str,
        reason: str,
    ) -> None:
        """Notify employee when their timesheet is rejected."""
        subject = f"Timesheet Requires Changes - {pay_period}"
        body = f"""
Hello {employee_name},

Your timesheet for {pay_period} requires changes before it can be approved.

Rejected by: {rejected_by}
Reason: {reason}

Please log in and make the necessary corrections, then resubmit.

- MyHours System
        """.strip()

        await EmailService.send_email(employee_email, subject, body)

    @staticmethod
    async def send_password_reset(
        email: str,
        name: str,
        reset_url: str,
    ) -> None:
        """Send password reset email."""
        subject = "Password Reset Request - MyHours"
        body = f"""
Hello {name},

We received a request to reset your password.

Click the link below to reset your password:
{reset_url}

This link will expire in 1 hour.

If you didn't request this, you can safely ignore this email.

- MyHours System
        """.strip()

        await EmailService.send_email(email, subject, body)


# Singleton instance
email_service = EmailService()
