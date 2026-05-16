"""Sync service: orchestrates scraping and persisting articles."""
from __future__ import annotations

import traceback
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.article import Article
from app.models.news_source import NewsSource, SyncStatus
from app.models.sync_log import SyncLog, SyncLogStatus
from app.services.article_service import ArticleService

logger = get_logger(__name__)


class SyncService:
    """Handles synchronization of news sources."""

    # ------------------------------------------------------------------
    # Per-source sync
    # ------------------------------------------------------------------

    @staticmethod
    async def sync_source(db: AsyncSession, source: NewsSource) -> SyncLog:
        """Scrape a single source, deduplicate, save articles, and record a SyncLog.

        Updates ``source.last_sync_at`` and ``source.sync_status`` regardless of
        outcome so the caller always gets an accurate log entry.
        """
        started_at = datetime.now(timezone.utc)
        log = SyncLog(
            source_id=source.id,
            status=SyncLogStatus.success,
            started_at=started_at,
        )

        try:
            scraper = _get_scraper_for_source(source)
            articles = await scraper.scrape()
            count = await ArticleService.save_articles(db, articles, source.id)

            log.articles_added = count
            log.status = SyncLogStatus.success
            source.sync_status = SyncStatus.ok

            logger.info(
                "Source synced",
                extra={"source": source.name, "articles_added": count},
            )

            # Newsletter notifications: when new newsletter articles land,
            # email the ALERT_EMAIL with the titles + links.
            if count > 0 and any(
                (a.get("category") == "newsletter") for a in articles
            ):
                # Look up which of THIS scrape's articles got inserted (those
                # whose original_url was not already in DB before this batch).
                try:
                    await _notify_newsletter_arrivals(db, source, articles)
                except Exception as e:
                    logger.warning(f"Newsletter notification failed: {e}")

        except Exception as exc:
            tb = traceback.format_exc()
            log.status = SyncLogStatus.error
            log.error_message = f"{type(exc).__name__}: {exc}\n{tb}"
            source.sync_status = SyncStatus.error
            logger.error(
                "Source sync failed",
                extra={"source": source.name, "error": str(exc)},
            )

        finally:
            log.completed_at = datetime.now(timezone.utc)
            source.last_sync_at = log.completed_at
            db.add(log)
            await db.flush()
            await db.refresh(log)

        return log

    # ------------------------------------------------------------------
    # Bulk sync
    # ------------------------------------------------------------------

    @staticmethod
    async def sync_all(db: AsyncSession) -> list[SyncLog]:
        """Sync all enabled news sources sequentially.

        Returns a list of SyncLog records (one per source).
        """
        result = await db.execute(
            select(NewsSource).where(NewsSource.enabled.is_(True))
        )
        sources: list[NewsSource] = list(result.scalars().all())

        logs: list[SyncLog] = []
        for source in sources:
            log = await SyncService.sync_source(db, source)
            logs.append(log)

        return logs

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    @staticmethod
    async def get_stats(db: AsyncSession) -> dict:
        """Return aggregate statistics for the admin dashboard."""
        total_articles: int = (
            await db.execute(select(func.count(Article.id)))
        ).scalar_one()

        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        articles_today: int = (
            await db.execute(
                select(func.count(Article.id)).where(
                    Article.published_at >= today_start
                )
            )
        ).scalar_one()

        active_sources: int = (
            await db.execute(
                select(func.count(NewsSource.id)).where(NewsSource.enabled.is_(True))
            )
        ).scalar_one()

        # Failed syncs = sources whose current sync_status is error
        failed_syncs: int = (
            await db.execute(
                select(func.count(NewsSource.id)).where(
                    NewsSource.sync_status == SyncStatus.error
                )
            )
        ).scalar_one()

        last_sync_at = (
            await db.execute(
                select(func.max(NewsSource.last_sync_at))
            )
        ).scalar_one()

        return {
            "total_articles": total_articles,
            "articles_today": articles_today,
            "active_sources": active_sources,
            "failed_syncs": failed_syncs,
            "last_sync_at": last_sync_at,
        }


# ---------------------------------------------------------------------------
# Scraper factory
# ---------------------------------------------------------------------------


def _get_scraper_for_source(source: NewsSource):  # noqa: ANN201
    """Return an appropriate scraper instance for the given NewsSource.

    First attempts to look up the scraper by source name in the registry;
    falls back to a generic RSS or Playwright scraper if not found.
    """
    from app.scrapers.rss_base import RSSBaseScraper
    from app.scrapers.playwright_base import PlaywrightBaseScraper
    from app.scrapers.registry import SCRAPER_REGISTRY
    from app.models.news_source import SourceType

    # If the source has been configured with source_type=rss AND an rss_url,
    # honor that even when a custom (Playwright-based) scraper exists in the
    # registry. Operators may switch a source from Playwright to RSS when the
    # custom scraper's selectors are broken or when a real feed becomes
    # available.
    if source.source_type == SourceType.rss and source.rss_url:
        class _GenericRSS(RSSBaseScraper):
            source_name = source.name
            source_url = source.url
            rss_url = source.rss_url  # type: ignore[assignment]

        return _GenericRSS()

    # Try the registry next (keyed by source.name)
    scraper_cls = SCRAPER_REGISTRY.get(source.name)
    if scraper_cls is not None:
        return scraper_cls()

    if source.source_type == SourceType.playwright:
        class _GenericPlaywright(PlaywrightBaseScraper):
            source_name = source.name
            source_url = source.url

        return _GenericPlaywright()

    # Last resort: generic RSS using the main URL as feed URL
    class _FallbackRSS(RSSBaseScraper):
        source_name = source.name
        source_url = source.url
        rss_url = source.rss_url or source.url  # type: ignore[assignment]

    return _FallbackRSS()


# ---------------------------------------------------------------------------
# Newsletter notifications
# ---------------------------------------------------------------------------


async def _notify_newsletter_arrivals(db: AsyncSession, source: NewsSource, scraped: list[dict]) -> None:
    """Email an alert when newly-inserted newsletter articles arrived.

    Looks at scraped URLs for this run and checks which of them are recent
    insertions (created in the last 90 seconds) — those are the new ones
    `save_articles` actually committed."""
    from datetime import timedelta
    from sqlalchemy import select as _select

    from app.core.config import settings
    from app.models.article import Article
    from app.services.mailer import send_alert

    if not scraped:
        return
    urls = [a["original_url"] for a in scraped if a.get("category") == "newsletter"]
    if not urls:
        return
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=90)
    stmt = (
        _select(Article.title, Article.original_url, Article.created_at)
        .where(Article.source_id == source.id)
        .where(Article.original_url.in_(urls))
        .where(Article.created_at >= cutoff)
        .order_by(Article.created_at.desc())
    )
    rows = (await db.execute(stmt)).all()
    if not rows:
        return  # all were duplicates, nothing new

    lines = [
        f"{len(rows)} newsletter nou la {source.name}",
        "",
    ]
    for title, url, _ts in rows:
        lines.append(f"• {title}\n  {url}")
    body = "\n".join(lines)
    subject = f"[ABACO News] {len(rows)} newsletter nou: {source.name}"
    await send_alert(settings.ALERT_EMAIL, subject, body)
