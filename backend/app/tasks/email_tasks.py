"""Celery tasks for email notifications."""
from __future__ import annotations

import asyncio
import textwrap
from datetime import datetime

from app.core.config import settings
from app.core.logging import get_logger
from app.tasks.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(
    name="app.tasks.email_tasks.send_sync_failure_alert",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def send_sync_failure_alert(
    self,
    source_name: str,
    error_details: str,
    timestamp: str,
    stack_trace: str,
) -> dict:
    """Send an email alert when a source sync fails.

    Targets the configured ALERT_EMAIL address using aiosmtplib.
    """
    logger.warning(
        "Sending sync failure alert email",
        extra={"source": source_name, "timestamp": timestamp},
    )
    try:
        asyncio.run(
            _send_email_async(
                to_address=settings.ALERT_EMAIL,
                subject=f"[ABACO News] Sync failure: {source_name}",
                body=_build_email_body(source_name, error_details, timestamp, stack_trace),
            )
        )
        return {"sent": True, "to": settings.ALERT_EMAIL, "source": source_name}
    except Exception as exc:
        logger.error(
            "Failed to send sync failure alert",
            extra={"source": source_name, "error": str(exc)},
        )
        raise self.retry(exc=exc)


# ---------------------------------------------------------------------------
# Async SMTP helper
# ---------------------------------------------------------------------------


async def _send_email_async(to_address: str, subject: str, body: str) -> None:
    """Send a plain-text email via aiosmtplib."""
    import aiosmtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    if not settings.SMTP_HOST:
        logger.warning("SMTP_HOST is not configured — skipping email send")
        return

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = settings.SMTP_USER or f"noreply@{settings.DOMAIN}"
    message["To"] = to_address
    message.attach(MIMEText(body, "plain", "utf-8"))

    await aiosmtplib.send(
        message,
        hostname=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USER or None,
        password=settings.SMTP_PASSWORD or None,
        start_tls=True,
        timeout=30,
    )
    logger.info("Alert email sent", extra={"to": to_address, "subject": subject})


# ---------------------------------------------------------------------------
# Email body builder
# ---------------------------------------------------------------------------


def _build_email_body(
    source_name: str,
    error_details: str,
    timestamp: str,
    stack_trace: str,
) -> str:
    return textwrap.dedent(f"""\
        ABACO News Aggregation Platform — Sync Failure Alert
        =====================================================

        Source   : {source_name}
        Timestamp: {timestamp}

        Error Details
        -------------
        {error_details}

        Stack Trace
        -----------
        {stack_trace}

        ---
        This is an automated alert from the ABACO News Aggregation Platform.
        Do not reply to this email.
    """)
