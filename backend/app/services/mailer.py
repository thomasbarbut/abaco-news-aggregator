"""Send alert emails via the ABACO server's mail utility.

Wraps the standalone /opt/mail/send_mail.py script (Microsoft Graph,
no-reply@abaco.ro). The script is preinstalled on the production server
and uses application-level Graph credentials, so it works without our
backend needing any extra Azure config.

If the script is missing (e.g. local dev), send_alert is a no-op and
logs a warning — never raises.
"""
from __future__ import annotations

import asyncio
import os
import shutil
from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)

MAIL_SCRIPT = Path("/opt/mail/send_mail.py")


async def send_alert(to: str, subject: str, body: str) -> bool:
    """Best-effort send. Returns True on success, False on failure (logged)."""
    if not MAIL_SCRIPT.exists():
        logger.warning(
            "Mail script not found, skipping alert",
            extra={"path": str(MAIL_SCRIPT), "to": to, "subject": subject},
        )
        return False

    python = shutil.which("python3") or "/usr/bin/python3"
    try:
        proc = await asyncio.create_subprocess_exec(
            python, str(MAIL_SCRIPT),
            "--to", to,
            "--subject", subject,
            "--body", body,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        out, err = await asyncio.wait_for(proc.communicate(), timeout=30)
        if proc.returncode != 0:
            logger.warning(
                "Mail send failed",
                extra={
                    "rc": proc.returncode,
                    "stderr": err.decode("utf-8", errors="replace")[:400],
                },
            )
            return False
        logger.info("Alert email sent", extra={"to": to, "subject": subject})
        return True
    except Exception as e:
        logger.warning(f"Mail send exception: {e}")
        return False
