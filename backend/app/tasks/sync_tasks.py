"""Celery tasks for syncing news sources."""
from __future__ import annotations

import asyncio
import traceback
from datetime import datetime, timezone

from app.core.logging import get_logger
from app.tasks.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(
    name="app.tasks.sync_tasks.sync_all_sources",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    soft_time_limit=600,
    time_limit=700,
)
def sync_all_sources(self) -> dict:
    """Sync all enabled news sources.

    Runs async service code inside ``asyncio.run`` since Celery workers are
    synchronous by default.  Sends an email alert for any failed sources.
    """
    logger.info("Celery task sync_all_sources started")
    try:
        result = asyncio.run(_sync_all_async())
        logger.info(
            "sync_all_sources completed",
            extra={"total": result["total"], "failed": result["failed"]},
        )
        return result
    except Exception as exc:
        logger.error("sync_all_sources task raised unexpectedly", exc_info=True)
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.tasks.sync_tasks.sync_single_source",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    soft_time_limit=300,
    time_limit=360,
)
def sync_single_source(self, source_id: str) -> dict:
    """Sync a single news source identified by ``source_id`` (UUID string)."""
    logger.info("Celery task sync_single_source started", extra={"source_id": source_id})
    try:
        result = asyncio.run(_sync_single_async(source_id))
        return result
    except Exception as exc:
        logger.error(
            "sync_single_source task raised unexpectedly",
            extra={"source_id": source_id},
            exc_info=True,
        )
        raise self.retry(exc=exc)


# ---------------------------------------------------------------------------
# Async implementations
# ---------------------------------------------------------------------------


async def _sync_all_async() -> dict:
    """Sync every enabled source in its own DB session so a single failure
    (e.g. UniqueViolationError from one source) can't poison the run for
    the others. Failure alerts go out via /opt/mail/send_mail.py."""
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.core.config import settings
    from app.models.news_source import NewsSource
    from app.services.sync_service import SyncService
    from app.services.mailer import send_alert

    failed_sources: list[dict] = []
    total = 0

    # 1) List enabled sources (uses one session; read-only, safe)
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(NewsSource).where(NewsSource.enabled.is_(True))
        )
        sources = list(result.scalars().all())
        total = len(sources)

    # 2) Sync each source in an isolated session + transaction
    for source in sources:
        try:
            async with AsyncSessionLocal() as db:
                # Re-attach the source to this session
                attached = await db.get(NewsSource, source.id)
                if attached is None:
                    continue
                log = await SyncService.sync_source(db, attached)
                if log.error_message:
                    failed_sources.append({
                        "name": attached.name,
                        "error": log.error_message,
                    })
                await db.commit()
        except Exception as exc:
            import traceback as _tb
            failed_sources.append({
                "name": source.name,
                "error": f"{type(exc).__name__}: {exc}\n{_tb.format_exc()}",
            })

    # 3) Send one consolidated alert if anything failed
    if failed_sources:
        try:
            lines = [
                f"Failed sources: {len(failed_sources)} of {total}",
                f"Time: {datetime.now(timezone.utc).isoformat()}",
                "",
            ]
            for f in failed_sources:
                lines.append(f"=== {f['name']} ===")
                lines.append(f["error"][:1500])
                lines.append("")
            body = "\n".join(lines)
            subject = (
                f"[ABACO News] Sync errors: "
                f"{len(failed_sources)}/{total} sources failed"
            )
            await send_alert(settings.ALERT_EMAIL, subject, body)
        except Exception as e:
            # Never let mailing break the sync result
            from app.core.logging import get_logger
            get_logger(__name__).warning(f"Failure-alert email send failed: {e}")

    return {
        "total": total,
        "failed": len(failed_sources),
        "succeeded": total - len(failed_sources),
    }


async def _sync_single_async(source_id_str: str) -> dict:
    import uuid as _uuid
    from app.core.database import AsyncSessionLocal
    from app.core.config import settings
    from app.models.news_source import NewsSource
    from app.services.sync_service import SyncService
    from app.services.mailer import send_alert

    source_id = _uuid.UUID(source_id_str)

    async with AsyncSessionLocal() as db:
        source = await db.get(NewsSource, source_id)
        if source is None:
            logger.warning("sync_single_source: source not found", extra={"source_id": source_id_str})
            return {"error": "Source not found", "source_id": source_id_str}

        log = await SyncService.sync_source(db, source)
        await db.commit()

    if log.error_message:
        try:
            await send_alert(
                settings.ALERT_EMAIL,
                f"[ABACO News] Sync failure: {source.name}",
                f"Source: {source.name}\nTime: {datetime.now(timezone.utc).isoformat()}\n\n{log.error_message[:3000]}",
            )
        except Exception as e:
            logger.warning(f"Failure-alert email send failed: {e}")

    return {
        "source_id": source_id_str,
        "source_name": source.name,
        "status": log.status.value,
        "articles_added": log.articles_added,
    }
