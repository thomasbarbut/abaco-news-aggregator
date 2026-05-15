"""Admin API router — all endpoints require the admin role."""
from __future__ import annotations

import uuid
from typing import Optional

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.logging import get_logger
from app.auth.dependencies import get_current_admin
from app.models.news_source import NewsSource
from app.models.sync_log import SyncLog
from app.models.user import User, UserRole
from app.schemas.source import NewsSourceResponse
from app.schemas.sync import AdminStatsResponse, SyncLogResponse, SyncRequest
from app.schemas.user import UserResponse
from app.services.sync_service import SyncService
from app.services.user_service import UserService

logger = get_logger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Sync endpoints
# ---------------------------------------------------------------------------


@router.post("/sync", status_code=status.HTTP_202_ACCEPTED)
async def trigger_sync(
    body: SyncRequest,
    _admin: User = Depends(get_current_admin),
) -> dict:
    """Enqueue a Celery sync task.

    If ``source_id`` is provided only that source is synced; otherwise all
    enabled sources are synced.
    """
    # Lazy import to avoid initializing the Celery app at module import time
    from app.tasks.sync_tasks import sync_all_sources, sync_single_source

    if body.source_id is not None:
        task = sync_single_source.delay(str(body.source_id))
        return {"message": "Sync task enqueued", "task_id": task.id, "source_id": str(body.source_id)}

    task = sync_all_sources.delay()
    return {"message": "Full sync task enqueued", "task_id": task.id}


# ---------------------------------------------------------------------------
# Sync logs
# ---------------------------------------------------------------------------


@router.get("/logs", response_model=list[SyncLogResponse])
async def get_sync_logs(
    source_id: Optional[uuid.UUID] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> list[SyncLog]:
    """Return paginated sync logs, optionally filtered by source."""
    stmt = select(SyncLog).order_by(SyncLog.started_at.desc())
    if source_id is not None:
        stmt = stmt.where(SyncLog.source_id == source_id)
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


@router.get("/stats", response_model=AdminStatsResponse)
async def get_admin_stats(
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> AdminStatsResponse:
    """Return aggregate statistics for the admin dashboard."""
    stats = await SyncService.get_stats(db)

    # Health checks
    redis_healthy = await _check_redis()
    db_healthy = await _check_db(db)

    return AdminStatsResponse(
        total_articles=stats["total_articles"],
        articles_today=stats["articles_today"],
        active_sources=stats["active_sources"],
        failed_syncs=stats["failed_syncs"],
        last_sync_at=stats["last_sync_at"],
        redis_healthy=redis_healthy,
        db_healthy=db_healthy,
    )


# ---------------------------------------------------------------------------
# Sources management
# ---------------------------------------------------------------------------


@router.get("/sources", response_model=list[NewsSourceResponse])
async def list_all_sources(
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> list[NewsSource]:
    """Return all sources (including disabled ones)."""
    result = await db.execute(
        select(NewsSource).order_by(NewsSource.name.asc())
    )
    return list(result.scalars().all())


@router.patch("/sources/{source_id}", response_model=NewsSourceResponse)
async def update_source(
    source_id: uuid.UUID,
    enabled: Optional[bool] = None,
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> NewsSource:
    """Update a news source (currently supports toggling enabled state)."""
    source = await db.get(NewsSource, source_id)
    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source {source_id} not found",
        )
    if enabled is not None:
        source.enabled = enabled
    await db.flush()
    await db.refresh(source)
    return source


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> list[User]:
    """Return all users."""
    return await UserService.get_users(db)


class RoleUpdateRequest(BaseModel):
    role: UserRole


@router.patch("/users/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: uuid.UUID,
    body: RoleUpdateRequest,
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Update a user's role."""
    return await UserService.update_role(db, user_id, body.role)


# ---------------------------------------------------------------------------
# Internal health helpers
# ---------------------------------------------------------------------------


async def _check_redis() -> bool:
    try:
        client = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        await client.ping()
        await client.aclose()
        return True
    except Exception:
        return False


async def _check_db(db: AsyncSession) -> bool:
    try:
        from sqlalchemy import text
        await db.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
