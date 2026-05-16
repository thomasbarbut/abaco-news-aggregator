"""Article business-logic service."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select, and_, or_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.article import Article
from app.models.article_read import ArticleRead
from app.models.news_source import NewsSource
from app.schemas.article import ArticleFilter

logger = get_logger(__name__)


class ArticleService:
    """Encapsulates all article-related database operations."""

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    @staticmethod
    async def get_articles(
        db: AsyncSession,
        filters: ArticleFilter,
        user_id: uuid.UUID,
    ) -> tuple[list[dict[str, Any]], int]:
        """Return a paginated list of articles enriched with read state.

        Returns a tuple of (items, total_count) where each item is a dict
        containing all Article columns plus ``source`` (NewsSource) and
        ``is_read`` (bool).
        """
        # Sub-query: article IDs the current user has read
        read_subq = (
            select(ArticleRead.article_id)
            .where(ArticleRead.user_id == user_id)
            .scalar_subquery()
        )

        # Build base query
        stmt = select(Article, NewsSource).join(
            NewsSource, Article.source_id == NewsSource.id
        )

        # Apply filters
        conditions: list = []

        if filters.source_ids:
            conditions.append(Article.source_id.in_(filters.source_ids))

        if filters.date_from is not None:
            conditions.append(Article.published_at >= filters.date_from)

        if filters.date_to is not None:
            conditions.append(Article.published_at <= filters.date_to)

        if filters.category is not None:
            conditions.append(Article.category == filters.category)

        if filters.search:
            term = f"%{filters.search}%"
            conditions.append(
                or_(
                    Article.title.ilike(term),
                    Article.summary.ilike(term),
                )
            )

        if conditions:
            stmt = stmt.where(and_(*conditions))

        # is_read filter needs the read sub-query
        if filters.is_read is True:
            stmt = stmt.where(Article.id.in_(read_subq))
        elif filters.is_read is False:
            stmt = stmt.where(Article.id.notin_(read_subq))

        # Count total (before pagination)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total: int = (await db.execute(count_stmt)).scalar_one()

        # Ordering and pagination
        stmt = (
            stmt.order_by(Article.published_at.desc())
            .offset((filters.page - 1) * filters.page_size)
            .limit(filters.page_size)
        )

        rows = (await db.execute(stmt)).all()

        # Build read-set for this page
        page_article_ids = [row[0].id for row in rows]
        read_ids: set[uuid.UUID] = set()
        if page_article_ids:
            read_rows = await db.execute(
                select(ArticleRead.article_id).where(
                    and_(
                        ArticleRead.user_id == user_id,
                        ArticleRead.article_id.in_(page_article_ids),
                    )
                )
            )
            read_ids = {r[0] for r in read_rows.all()}

        items: list[dict[str, Any]] = []
        for article, source in rows:
            data = _article_to_dict(article)
            data["source"] = source
            data["is_read"] = article.id in read_ids
            items.append(data)

        return items, total

    @staticmethod
    async def get_article(
        db: AsyncSession,
        article_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> dict[str, Any] | None:
        """Return a single article by ID, enriched with source and read state."""
        row = (
            await db.execute(
                select(Article, NewsSource)
                .join(NewsSource, Article.source_id == NewsSource.id)
                .where(Article.id == article_id)
            )
        ).first()

        if row is None:
            return None

        article, source = row
        read_record = (
            await db.execute(
                select(ArticleRead).where(
                    and_(
                        ArticleRead.user_id == user_id,
                        ArticleRead.article_id == article_id,
                    )
                )
            )
        ).scalar_one_or_none()

        data = _article_to_dict(article)
        data["source"] = source
        data["is_read"] = read_record is not None
        return data

    # ------------------------------------------------------------------
    # Read state mutations
    # ------------------------------------------------------------------

    @staticmethod
    async def mark_read(
        db: AsyncSession,
        user_id: uuid.UUID,
        article_id: uuid.UUID,
    ) -> ArticleRead:
        """Mark an article as read for the given user (idempotent)."""
        existing = (
            await db.execute(
                select(ArticleRead).where(
                    and_(
                        ArticleRead.user_id == user_id,
                        ArticleRead.article_id == article_id,
                    )
                )
            )
        ).scalar_one_or_none()

        if existing is not None:
            return existing

        record = ArticleRead(
            user_id=user_id,
            article_id=article_id,
            read_at=datetime.now(timezone.utc),
        )
        db.add(record)
        await db.flush()
        await db.refresh(record)
        return record

    @staticmethod
    async def mark_unread(
        db: AsyncSession,
        user_id: uuid.UUID,
        article_id: uuid.UUID,
    ) -> None:
        """Remove the read record for the given user/article pair (idempotent)."""
        await db.execute(
            delete(ArticleRead).where(
                and_(
                    ArticleRead.user_id == user_id,
                    ArticleRead.article_id == article_id,
                )
            )
        )
        await db.flush()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    @staticmethod
    async def save_articles(
        db: AsyncSession,
        articles: list[dict[str, Any]],
        source_id: uuid.UUID,
    ) -> int:
        """Persist new articles to the database, skipping duplicates.

        Returns the number of articles actually inserted.
        """
        if not articles:
            return 0

        checksums = [a["checksum"] for a in articles]
        urls = [a["original_url"] for a in articles]
        candidate_slugs = [a.get("slug", "untitled") for a in articles]

        existing_checksums: set[str] = {
            row[0]
            for row in (
                await db.execute(
                    select(Article.checksum).where(Article.checksum.in_(checksums))
                )
            ).all()
        }
        existing_urls: set[str] = {
            row[0]
            for row in (
                await db.execute(
                    select(Article.original_url).where(Article.original_url.in_(urls))
                )
            ).all()
        }
        # Load existing slugs that collide with our candidates so _unique_slug
        # can avoid them. Without this, an article whose checksum changed
        # (re-edited at the source) but whose title stayed the same would crash
        # the whole transaction with articles_slug_key.
        existing_slugs: set[str] = {
            row[0]
            for row in (
                await db.execute(
                    select(Article.slug).where(Article.slug.in_(candidate_slugs))
                )
            ).all()
        }

        saved = 0
        seen_checksums: set[str] = set()
        seen_urls: set[str] = set()
        # Seed the slug-collision tracker with what's already in the DB.
        seen_slugs: set[str] = set(existing_slugs)

        for article_data in articles:
            checksum = article_data["checksum"]
            url = article_data["original_url"]

            if checksum in existing_checksums or checksum in seen_checksums:
                continue
            if url in existing_urls or url in seen_urls:
                continue

            # Ensure slug uniqueness against this batch AND the DB.
            base_slug: str = article_data.get("slug", "untitled")
            slug = _unique_slug(base_slug, seen_slugs)

            article = Article(
                source_id=source_id,
                title=article_data["title"],
                slug=slug,
                summary=article_data.get("summary"),
                content=article_data.get("content"),
                original_url=url,
                image_url=article_data.get("image_url"),
                author=article_data.get("author"),
                published_at=article_data["published_at"],
                category=article_data.get("category"),
                tags=article_data.get("tags", []),
                language=article_data.get("language", "ro"),
                checksum=checksum,
            )
            db.add(article)
            seen_checksums.add(checksum)
            seen_urls.add(url)
            saved += 1

        if saved:
            await db.flush()
        logger.info(
            "Articles saved",
            extra={"source_id": str(source_id), "count": saved},
        )
        return saved


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _article_to_dict(article: Article) -> dict[str, Any]:
    return {
        "id": article.id,
        "source_id": article.source_id,
        "title": article.title,
        "slug": article.slug,
        "summary": article.summary,
        "content": article.content,
        "original_url": article.original_url,
        "image_url": article.image_url,
        "author": article.author,
        "published_at": article.published_at,
        "scraped_at": article.scraped_at,
        "category": article.category,
        "tags": article.tags,
        "language": article.language,
        "checksum": article.checksum,
        "created_at": article.created_at,
    }


def _unique_slug(base: str, seen: set[str]) -> str:
    """Append a numeric suffix to a slug if needed to avoid collisions."""
    slug = base
    counter = 1
    while slug in seen:
        slug = f"{base}-{counter}"
        counter += 1
    seen.add(slug)
    return slug
