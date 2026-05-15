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
from app.schemas.article import ArticleFilter, ArticleListResponse, ArticleResponse
from app.schemas.source import NewsSourceResponse
from app.services.article_service import ArticleService

router = APIRouter(prefix="/articles", tags=["articles"])


def _build_response(data: dict) -> ArticleResponse:
    """Convert the service-layer dict into an ArticleResponse, embedding source."""
    source_orm = data.pop("source", None)
    source_resp: NewsSourceResponse | None = None
    if source_orm is not None:
        source_resp = NewsSourceResponse.model_validate(source_orm)

    resp = ArticleResponse(**data)
    resp.source = source_resp
    return resp


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
    items = [_build_response(d) for d in items_raw]

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
