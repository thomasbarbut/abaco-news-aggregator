"""Admin-only routes: stats, manual sync triggering, sync logs."""

import uuid
from datetime import datetime, timedelta, timezone

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.config import settings
from app.core.database import get_db
from app.core.logging import get_logger
from app.models.article import Article
from app.models.news_source import NewsSource
from app.models.sync_log import SyncLog, SyncLogStatus
from app.models.user import User
from app.schemas.sync import AdminStatsResponse, SyncLogResponse, SyncRequest

router = APIRouter()
logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


@router.get("/stats", response_model=AdminStatsResponse, summary="Platform statistics")
async def get_stats(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AdminStatsResponse:
    # Total articles
    total_articles: int = (
        await db.execute(select(func.count(Article.id)))
    ).scalar_one()

    # Articles added today
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    articles_today: int = (
        await db.execute(
            select(func.count(Article.id)).where(Article.created_at >= today_start)
        )
    ).scalar_one()

    # Active sources
    active_sources: int = (
        await db.execute(
            select(func.count(NewsSource.id)).where(NewsSource.enabled.is_(True))
        )
    ).scalar_one()

    # Failed syncs in the last 24 h
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    failed_syncs: int = (
        await db.execute(
            select(func.count(SyncLog.id)).where(
                SyncLog.status == SyncLogStatus.error,
                SyncLog.started_at >= cutoff,
            )
        )
    ).scalar_one()

    # Last sync timestamp
    last_sync_row = (
        await db.execute(
            select(SyncLog.completed_at)
            .where(SyncLog.completed_at.isnot(None))
            .order_by(SyncLog.completed_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    # Redis health
    redis_healthy = False
    try:
        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        await r.ping()
        await r.aclose()
        redis_healthy = True
    except Exception:
        pass

    # DB health (already connected if we got here)
    db_healthy = True

    return AdminStatsResponse(
        total_articles=total_articles,
        articles_today=articles_today,
        active_sources=active_sources,
        failed_syncs=failed_syncs,
        last_sync_at=last_sync_row,
        redis_healthy=redis_healthy,
        db_healthy=db_healthy,
    )


# ---------------------------------------------------------------------------
# Manual sync
# ---------------------------------------------------------------------------


@router.post("/sync", status_code=status.HTTP_202_ACCEPTED, summary="Trigger manual sync")
async def trigger_sync(
    body: SyncRequest,
    admin: User = Depends(require_admin),
) -> dict:
    """Enqueue a Celery sync task.  Returns the task id."""
    # Import here to avoid circular imports at module level
    from app.worker.tasks import sync_source, sync_all_sources

    if body.source_id is not None:
        task = sync_source.delay(str(body.source_id))
        logger.info("Manual sync triggered", extra={"source_id": str(body.source_id)})
    else:
        task = sync_all_sources.delay()
        logger.info("Full manual sync triggered")

    return {"task_id": task.id, "status": "queued"}


# ---------------------------------------------------------------------------
# Sync logs
# ---------------------------------------------------------------------------


@router.get(
    "/sync-logs",
    response_model=list[SyncLogResponse],
    summary="Recent sync logs",
)
async def list_sync_logs(
    source_id: uuid.UUID | None = None,
    limit: int = 50,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[SyncLogResponse]:
    stmt = select(SyncLog).order_by(SyncLog.started_at.desc()).limit(limit)
    if source_id is not None:
        stmt = stmt.where(SyncLog.source_id == source_id)
    rows = (await db.execute(stmt)).scalars().all()
    return [SyncLogResponse.model_validate(r) for r in rows]


# ---------------------------------------------------------------------------
# Users (list)
# ---------------------------------------------------------------------------


@router.get("/users", summary="List all users (admin only)")
async def list_users(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list:
    from app.schemas.user import UserResponse

    rows = (await db.execute(select(User).order_by(User.created_at))).scalars().all()
    return [UserResponse.model_validate(u) for u in rows]
