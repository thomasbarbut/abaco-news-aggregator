"""Seed initial news sources into the database."""
import asyncio
from typing import Any

from app.core.database import AsyncSessionLocal as async_session_maker
from app.models.news_source import NewsSource, SourceType, SyncStatus

SOURCES: list[dict[str, Any]] = [
    {
        "name": "ZF - Ziarul Financiar",
        "url": "https://www.zf.ro",
        "rss_url": "https://www.zf.ro/rss",
        "source_type": SourceType.rss,
    },
    {
        "name": "Profit.ro",
        "url": "https://www.profit.ro",
        "rss_url": "https://www.profit.ro/rss",
        "source_type": SourceType.rss,
    },
    {
        "name": "Curs de Guvernare",
        "url": "https://cursdeguvernare.ro",
        "rss_url": "https://cursdeguvernare.ro/feed",
        "source_type": SourceType.rss,
    },
    {
        "name": "Manager.ro",
        "url": "https://www.manager.ro",
        "rss_url": "https://www.manager.ro/rss.php",
        "source_type": SourceType.rss,
    },
    {
        "name": "StartupCafe.ro",
        "url": "https://startupcafe.ro",
        "rss_url": "https://startupcafe.ro/feed",
        "source_type": SourceType.rss,
    },
    {
        "name": "Juridice.ro",
        "url": "https://juridice.ro",
        "rss_url": "https://juridice.ro/feed",
        "source_type": SourceType.rss,
    },
    {
        "name": "Economedia",
        "url": "https://economedia.ro",
        "rss_url": None,
        "source_type": SourceType.playwright,
    },
    {
        "name": "Wall-Street.ro",
        "url": "https://www.wall-street.ro",
        "rss_url": None,
        "source_type": SourceType.playwright,
    },
    {
        "name": "Forbes România",
        "url": "https://www.forbes.ro",
        "rss_url": None,
        "source_type": SourceType.playwright,
    },
    {
        "name": "Avocatnet.ro",
        "url": "https://www.avocatnet.ro",
        "rss_url": None,
        "source_type": SourceType.playwright,
    },
]


async def seed() -> None:
    from sqlalchemy import select

    async with async_session_maker() as session:
        for source_data in SOURCES:
            result = await session.execute(
                select(NewsSource).where(NewsSource.url == source_data["url"])
            )
            existing = result.scalar_one_or_none()
            if existing:
                print(f"  ⏭  Already exists: {source_data['name']}")
                continue

            source = NewsSource(
                name=source_data["name"],
                url=source_data["url"],
                rss_url=source_data["rss_url"],
                source_type=source_data["source_type"],
                enabled=True,
                sync_status=SyncStatus.pending,
            )
            session.add(source)
            print(f"  ✓  Added: {source_data['name']}")

        await session.commit()
    print("\nSeed complete.")


if __name__ == "__main__":
    asyncio.run(seed())
