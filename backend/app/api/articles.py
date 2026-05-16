"""Articles API router."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.schemas.article import (
    ArticleFilter,
    ArticleListItem,
    ArticleListResponse,
    ArticleResponse,
)
from app.schemas.source import NewsSourceResponse
from app.services.article_service import ArticleService

router = APIRouter(prefix="/articles", tags=["articles"])


@router.get("/sync-status")
async def user_sync_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Sync state visible to any authenticated user.

    Returns whether a sync is currently running, when the last one finished,
    and the names of any sources currently in error state — so the feed can
    show a refresh button and an error indicator without needing admin rights.
    """
    from sqlalchemy import select
    from app.api.admin import _SYNC_STATE
    from app.models.news_source import NewsSource, SyncStatus

    failed_rows = (
        await db.execute(
            select(NewsSource.name)
            .where(NewsSource.enabled.is_(True))
            .where(NewsSource.sync_status == SyncStatus.error)
            .order_by(NewsSource.name.asc())
        )
    ).all()

    return {
        "in_progress": bool(_SYNC_STATE.get("in_progress", False)),
        "last_finished_at": _SYNC_STATE.get("last_finished_at"),
        "failed_sources": [r[0] for r in failed_rows],
    }


@router.post("/sync", status_code=status.HTTP_202_ACCEPTED)
async def user_trigger_sync(
    current_user: User = Depends(get_current_user),
) -> dict:
    """Trigger a full sync of all enabled sources (any authenticated user).

    Fire-and-forget: spawns the sync as a background task and returns
    immediately. Poll /api/articles/sync-status for progress.
    """
    import asyncio as _asyncio
    import time as _time
    from app.api.admin import _SYNC_STATE
    from app.tasks.sync_tasks import _sync_all_async

    if _SYNC_STATE.get("in_progress"):
        return {"message": "Sync already in progress", "in_progress": True}

    async def _runner() -> None:
        _SYNC_STATE.update({
            "in_progress": True,
            "started_at": _time.time(),
            "source_id": None,
            "last_result": None,
        })
        try:
            result = await _sync_all_async()
            _SYNC_STATE["last_result"] = result
        except Exception as exc:  # noqa: BLE001
            _SYNC_STATE["last_result"] = {"error": str(exc)}
        finally:
            _SYNC_STATE["in_progress"] = False
            _SYNC_STATE["last_finished_at"] = _time.time()

    _asyncio.create_task(_runner())
    return {"message": "Sync started", "in_progress": True}


@router.get("/unread-counts")
async def unread_counts(
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return unread article counts for the current user, bucketed by tab.

    Date filters mirror those of /articles so the counts match what the
    user actually sees in the feed. Newsletter tab doesn't apply the date
    filter (newsletters land weekly), so newsletter count ignores it.

    Response: {"news": N, "newsletter": M}
    """
    from sqlalchemy import func, select
    from app.models.article import Article
    from app.models.article_read import ArticleRead

    read_subq = (
        select(ArticleRead.article_id)
        .where(ArticleRead.user_id == current_user.id)
        .scalar_subquery()
    )

    news_q = (
        select(func.count())
        .select_from(Article)
        .where(Article.id.notin_(read_subq))
        .where((Article.category.is_(None)) | (Article.category != "newsletter"))
    )
    if date_from is not None:
        news_q = news_q.where(Article.published_at >= date_from)
    if date_to is not None:
        news_q = news_q.where(Article.published_at <= date_to)

    newsletter_q = (
        select(func.count())
        .select_from(Article)
        .where(Article.id.notin_(read_subq))
        .where(Article.category == "newsletter")
    )
    news_count = (await db.execute(news_q)).scalar_one()
    nl_count = (await db.execute(newsletter_q)).scalar_one()
    return {"news": int(news_count), "newsletter": int(nl_count)}


def _build_response(data: dict) -> ArticleResponse:
    """Convert the service-layer dict into an ArticleResponse, embedding source."""
    source_orm = data.pop("source", None)
    source_resp: NewsSourceResponse | None = None
    if source_orm is not None:
        source_resp = NewsSourceResponse.model_validate(source_orm)

    resp = ArticleResponse(**data)
    resp.source = source_resp
    return resp


def _build_list_item(data: dict) -> ArticleListItem:
    """Build a compact list-item from the service dict.

    Drops the heavy body fields and replaces them with a single ``has_archive``
    boolean so the UI can decide whether to offer a 'view archive' action.
    """
    source_orm = data.pop("source", None)
    has_archive = bool(data.get("content") or data.get("content_html"))
    # Strip the heavy fields before model construction
    light = {k: v for k, v in data.items() if k not in ("content", "content_html")}
    item = ArticleListItem(**light, has_archive=has_archive)
    if source_orm is not None:
        item.source = NewsSourceResponse.model_validate(source_orm)
    return item


@router.get("", response_model=ArticleListResponse)
async def list_articles(
    source_ids: Optional[list[uuid.UUID]] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    category: Optional[str] = Query(None),
    is_read: Optional[bool] = Query(None),
    search: Optional[str] = Query(None, max_length=200),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ArticleListResponse:
    """Return a paginated list of articles.

    Supports filtering by source, date range, category, read state, and
    keyword search (ILIKE on title and summary).
    """
    filters = ArticleFilter(
        source_ids=source_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
        is_read=is_read,
        search=search,
        page=page,
        page_size=page_size,
    )

    items_raw, total = await ArticleService.get_articles(db, filters, current_user.id)
    items = [_build_list_item(d) for d in items_raw]

    return ArticleListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{article_id}", response_model=ArticleResponse)
async def get_article(
    article_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ArticleResponse:
    """Return a single article by ID and auto-mark it as read."""
    data = await ArticleService.get_article(db, article_id, current_user.id)
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found",
        )

    # Auto-mark as read
    await ArticleService.mark_read(db, current_user.id, article_id)
    data["is_read"] = True

    return _build_response(data)


@router.post("/{article_id}/read", status_code=status.HTTP_200_OK)
async def mark_article_read(
    article_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Mark an article as read (idempotent)."""
    # Verify article exists
    data = await ArticleService.get_article(db, article_id, current_user.id)
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found",
        )
    await ArticleService.mark_read(db, current_user.id, article_id)
    return {"message": "Article marked as read"}


@router.post("/{article_id}/unread", status_code=status.HTTP_200_OK)
async def mark_article_unread(
    article_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Mark an article as unread (idempotent)."""
    # Verify article exists
    data = await ArticleService.get_article(db, article_id, current_user.id)
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found",
        )
    await ArticleService.mark_unread(db, current_user.id, article_id)
    return {"message": "Article marked as unread"}
