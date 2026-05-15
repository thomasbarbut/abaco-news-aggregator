"""Articles endpoints."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.logging import get_logger
from app.models.article import Article
from app.models.article_read import ArticleRead
from app.models.news_source import NewsSource
from app.models.user import User
from app.schemas.article import ArticleListResponse, ArticleResponse
from app.schemas.source import NewsSourceResponse

router = APIRouter()
logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _article_to_response(
    article: Article,
    source: NewsSource | None,
    is_read: bool,
) -> ArticleResponse:
    source_schema = NewsSourceResponse.model_validate(source) if source else None
    data = ArticleResponse.model_validate(article)
    data.source = source_schema
    data.is_read = is_read
    return data


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("", response_model=ArticleListResponse, summary="List articles")
async def list_articles(
    source_ids: list[uuid.UUID] | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    category: str | None = Query(default=None),
    is_read: bool | None = Query(default=None),
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ArticleListResponse:
    stmt = select(Article)

    if source_ids:
        stmt = stmt.where(Article.source_id.in_(source_ids))
    if date_from:
        stmt = stmt.where(Article.published_at >= date_from)
    if date_to:
        stmt = stmt.where(Article.published_at <= date_to)
    if category:
        stmt = stmt.where(Article.category == category)
    if search:
        # PostgreSQL full-text search using the GIN index
        ts_query = func.plainto_tsquery("simple", search)
        ts_vector = func.to_tsvector(
            "simple",
            Article.title
            + " "
            + func.coalesce(Article.summary, "")
            + " "
            + func.coalesce(Article.content, ""),
        )
        stmt = stmt.where(ts_vector.op("@@")(ts_query))

    # Filter by read status
    if is_read is True:
        read_subq = select(ArticleRead.article_id).where(
            ArticleRead.user_id == current_user.id
        )
        stmt = stmt.where(Article.id.in_(read_subq))
    elif is_read is False:
        read_subq = select(ArticleRead.article_id).where(
            ArticleRead.user_id == current_user.id
        )
        stmt = stmt.where(Article.id.not_in(read_subq))

    # Count total before pagination
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total: int = (await db.execute(count_stmt)).scalar_one()

    # Pagination
    offset = (page - 1) * page_size
    stmt = stmt.order_by(Article.published_at.desc()).offset(offset).limit(page_size)

    articles = (await db.execute(stmt)).scalars().all()

    # Bulk-fetch sources and read records for the result set
    article_ids = [a.id for a in articles]
    source_ids_result = list({a.source_id for a in articles})

    sources_map: dict[uuid.UUID, NewsSource] = {}
    if source_ids_result:
        src_rows = (
            await db.execute(select(NewsSource).where(NewsSource.id.in_(source_ids_result)))
        ).scalars().all()
        sources_map = {s.id: s for s in src_rows}

    read_set: set[uuid.UUID] = set()
    if article_ids:
        read_rows = (
            await db.execute(
                select(ArticleRead.article_id).where(
                    ArticleRead.user_id == current_user.id,
                    ArticleRead.article_id.in_(article_ids),
                )
            )
        ).scalars().all()
        read_set = set(read_rows)

    items = [
        _article_to_response(a, sources_map.get(a.source_id), a.id in read_set)
        for a in articles
    ]

    return ArticleListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{article_id}", response_model=ArticleResponse, summary="Get single article")
async def get_article(
    article_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ArticleResponse:
    article = (
        await db.execute(select(Article).where(Article.id == article_id))
    ).scalar_one_or_none()
    if article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")

    source = (
        await db.execute(select(NewsSource).where(NewsSource.id == article.source_id))
    ).scalar_one_or_none()

    read_record = (
        await db.execute(
            select(ArticleRead).where(
                ArticleRead.user_id == current_user.id,
                ArticleRead.article_id == article_id,
            )
        )
    ).scalar_one_or_none()

    return _article_to_response(article, source, read_record is not None)


@router.post("/{article_id}/read", status_code=status.HTTP_204_NO_CONTENT, summary="Mark as read")
async def mark_read(
    article_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    article = (
        await db.execute(select(Article).where(Article.id == article_id))
    ).scalar_one_or_none()
    if article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")

    existing = (
        await db.execute(
            select(ArticleRead).where(
                ArticleRead.user_id == current_user.id,
                ArticleRead.article_id == article_id,
            )
        )
    ).scalar_one_or_none()

    if existing is None:
        db.add(ArticleRead(user_id=current_user.id, article_id=article_id))
        await db.commit()


@router.delete(
    "/{article_id}/read",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Mark as unread",
)
async def mark_unread(
    article_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    existing = (
        await db.execute(
            select(ArticleRead).where(
                ArticleRead.user_id == current_user.id,
                ArticleRead.article_id == article_id,
            )
        )
    ).scalar_one_or_none()

    if existing is not None:
        await db.delete(existing)
        await db.commit()
