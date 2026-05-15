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


# In-memory sync status (single-process dev). Production with Celery would
# track this in Redis; for our eager-mode dev setup, a module global is fine.
import time as _time
_SYNC_STATE: dict = {
    "in_progress": False,
    "started_at": None,
    "source_id": None,
    "last_finished_at": None,
    "last_result": None,
}


@router.get("/sync/status", summary="Current sync status (poll for live progress)")
async def sync_status(_admin: User = Depends(get_current_admin)) -> dict:
    return dict(_SYNC_STATE)


# ── Auto-sync interval configuration ────────────────────────────────────
import json as _json
from pathlib import Path as _Path

_SETTINGS_FILE = _Path("./dev.settings.json")


def _load_settings() -> dict:
    if _SETTINGS_FILE.exists():
        try:
            return _json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_settings(data: dict) -> None:
    _SETTINGS_FILE.write_text(_json.dumps(data, indent=2), encoding="utf-8")


def get_auto_sync_interval_minutes() -> int:
    saved = _load_settings().get("auto_sync_interval_minutes")
    if isinstance(saved, int) and saved > 0:
        return saved
    return int(settings.SYNC_INTERVAL_MINUTES)


def is_auto_sync_enabled() -> bool:
    s = _load_settings()
    return bool(s.get("auto_sync_enabled", True))


@router.get("/sync/config", summary="Auto-sync interval and enable flag")
async def sync_config(_admin: User = Depends(get_current_admin)) -> dict:
    return {
        "interval_minutes": get_auto_sync_interval_minutes(),
        "enabled": is_auto_sync_enabled(),
        "last_finished_at": _SYNC_STATE.get("last_finished_at"),
        "in_progress": _SYNC_STATE.get("in_progress", False),
    }


class _SyncConfigPatch(BaseModel):
    interval_minutes: Optional[int] = None
    enabled: Optional[bool] = None


@router.patch("/sync/config", summary="Update auto-sync interval / enabled")
async def sync_config_update(
    body: _SyncConfigPatch,
    _admin: User = Depends(get_current_admin),
) -> dict:
    current = _load_settings()
    if body.interval_minutes is not None:
        if body.interval_minutes < 1 or body.interval_minutes > 1440:
            raise HTTPException(status_code=400, detail="interval_minutes must be 1..1440")
        current["auto_sync_interval_minutes"] = int(body.interval_minutes)
    if body.enabled is not None:
        current["auto_sync_enabled"] = bool(body.enabled)
    _save_settings(current)
    logger.info(f"Auto-sync config updated: {current}")
    return {
        "interval_minutes": get_auto_sync_interval_minutes(),
        "enabled": is_auto_sync_enabled(),
    }


async def auto_sync_loop() -> None:
    """Background task: trigger a full sync every N minutes when enabled.
    Skips when a sync is already in progress."""
    import asyncio
    import time as _t
    from app.tasks.sync_tasks import _sync_all_async
    logger.info("Auto-sync loop entering wait")
    # Wait a bit before the first run so the app finishes startup cleanly
    await asyncio.sleep(15)
    while True:
        try:
            if is_auto_sync_enabled() and not _SYNC_STATE.get("in_progress"):
                _SYNC_STATE.update({
                    "in_progress": True,
                    "started_at": _t.time(),
                    "source_id": None,
                    "last_result": None,
                })
                try:
                    result = await _sync_all_async()
                    _SYNC_STATE["last_result"] = result
                    logger.info(f"Auto-sync done: {result}")
                except Exception as e:
                    _SYNC_STATE["last_result"] = {"error": str(e)}
                    logger.error(f"Auto-sync failed: {e}", exc_info=True)
                finally:
                    _SYNC_STATE["in_progress"] = False
                    _SYNC_STATE["last_finished_at"] = _t.time()
            await asyncio.sleep(max(60, get_auto_sync_interval_minutes() * 60))
        except asyncio.CancelledError:
            logger.info("Auto-sync loop cancelled")
            return
        except Exception as e:
            logger.error(f"Auto-sync loop error: {e}", exc_info=True)
            await asyncio.sleep(60)


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
    # When running in eager mode (no Celery worker / no Redis broker), calling
    # task.delay() blows up because the task body uses asyncio.run() from inside
    # an already-running event loop. Bypass Celery and await the async impl
    # directly. Check CELERY_TASK_ALWAYS_EAGER env or DEBUG mode.
    from app.core.config import settings
    import os as _os
    _eager = _os.environ.get("CELERY_TASK_ALWAYS_EAGER", "").lower() in ("1", "true", "yes")
    if _eager or settings.DEBUG:
        from app.tasks.sync_tasks import _sync_all_async, _sync_single_async
        _SYNC_STATE.update({
            "in_progress": True,
            "started_at": _time.time(),
            "source_id": str(body.source_id) if body.source_id else None,
            "last_result": None,
        })
        try:
            if body.source_id is not None:
                result = await _sync_single_async(str(body.source_id))
                _SYNC_STATE["last_result"] = {"source_id": str(body.source_id), **(result or {})}
                return {"message": "Sync completed (dev mode, inline)", "result": result, "source_id": str(body.source_id)}
            result = await _sync_all_async()
            _SYNC_STATE["last_result"] = result
            return {"message": "Full sync completed (dev mode, inline)", "result": result}
        finally:
            _SYNC_STATE["in_progress"] = False
            _SYNC_STATE["last_finished_at"] = _time.time()

    # Production path: enqueue via Celery
    from app.tasks.sync_tasks import sync_all_sources, sync_single_source
    if body.source_id is not None:
        task = sync_single_source.delay(str(body.source_id))
        return {"message": "Sync task enqueued", "task_id": task.id, "source_id": str(body.source_id)}
    task = sync_all_sources.delay()
    return {"message": "Full sync task enqueued", "task_id": task.id}


# ---------------------------------------------------------------------------
# Sync logs
# ---------------------------------------------------------------------------


@router.get("/logs")
async def get_sync_logs(
    source_id: Optional[uuid.UUID] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return paginated sync logs with total count, optionally filtered by source.
    Response shape matches the frontend's PaginatedResponse<SyncLog>: {items, total, page, page_size}."""
    from sqlalchemy import func
    base = select(SyncLog)
    if source_id is not None:
        base = base.where(SyncLog.source_id == source_id)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    stmt = base.order_by(SyncLog.started_at.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = list((await db.execute(stmt)).scalars().all())
    # Load source name eagerly to populate `log.source.name` on the frontend
    items = []
    for log in rows:
        src = await db.get(NewsSource, log.source_id)
        items.append({
            "id": str(log.id),
            "source_id": str(log.source_id),
            "source": {"id": str(src.id), "name": src.name} if src else None,
            "status": log.status.value if hasattr(log.status, "value") else log.status,
            "error_message": log.error_message,
            "started_at": log.started_at.isoformat() if log.started_at else None,
            "completed_at": log.completed_at.isoformat() if log.completed_at else None,
            "articles_added": log.articles_added,
        })
    return {"items": items, "total": total, "page": page, "page_size": page_size}


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


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: uuid.UUID,
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Remove a user from the local DB."""
    if _admin.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    await db.delete(user)
    await db.commit()
    return {"ok": True, "deleted": str(user_id)}


# ── Entra ID user management (search + invite) ──────────────────────────


@router.get("/users/entra/search", summary="Search users in the Entra ID tenant")
async def entra_search_users(
    q: str = Query("", description="Search by displayName or mail"),
    top: int = Query(20, ge=1, le=50),
    _admin: User = Depends(get_current_admin),
) -> dict:
    """Search the Microsoft Entra ID directory. Requires real MICROSOFT_* env
    vars (not placeholders) and Graph User.Read.All app permission."""
    from app.auth.microsoft import search_entra_users
    try:
        users = await search_entra_users(q, top=top)
        return {"configured": True, "users": users}
    except RuntimeError as e:
        # Entra credentials missing — return a structured "not configured"
        # response so the UI can show actionable guidance instead of an error.
        return {"configured": False, "message": str(e), "users": []}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Entra search failed: {e}")


class _InviteUserRequest(BaseModel):
    microsoft_id: str
    email: str
    name: str
    role: UserRole = UserRole.user


@router.post("/users", response_model=UserResponse, status_code=201)
async def add_user(
    body: _InviteUserRequest,
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Add an Entra user to the local DB so they can log in.
    The microsoft_id should be the Entra object id (from /users/entra/search)."""
    existing = (
        await db.execute(select(User).where(User.email == body.email))
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail=f"User with email {body.email} already exists")
    user = User(
        microsoft_id=body.microsoft_id,
        email=body.email,
        name=body.name,
        role=body.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info(f"Admin added user id={user.id} email={user.email} role={user.role}")
    return user


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
