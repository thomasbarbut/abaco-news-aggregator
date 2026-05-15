import hashlib
from difflib import SequenceMatcher
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
# Import lazily to avoid circular imports
import logging

logger = logging.getLogger(__name__)


def make_checksum(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()


def title_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


async def filter_new_articles(
    session: AsyncSession,
    articles: list[dict],
    source_id: str,
) -> list[dict]:
    """Filter out articles that already exist in the database."""
    from app.models.article import Article

    if not articles:
        return []

    # Get checksums of all proposed articles
    checksums = [a["checksum"] for a in articles]
    urls = [a["original_url"] for a in articles]

    # Query existing checksums
    existing_checksums = set(
        row[0] for row in (
            await session.execute(
                select(Article.checksum).where(Article.checksum.in_(checksums))
            )
        ).all()
    )

    # Query existing URLs
    existing_urls = set(
        row[0] for row in (
            await session.execute(
                select(Article.original_url).where(Article.original_url.in_(urls))
            )
        ).all()
    )

    new_articles = []
    for article in articles:
        if article["checksum"] in existing_checksums:
            continue
        if article["original_url"] in existing_urls:
            continue
        new_articles.append(article)

    logger.info(
        f"Deduplication: {len(articles)} fetched, {len(new_articles)} new for source {source_id}"
    )
    return new_articles
