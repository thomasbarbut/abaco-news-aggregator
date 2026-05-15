import feedparser
import httpx
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from .base import BaseScraper
import logging

logger = logging.getLogger(__name__)


class RSSBaseScraper(BaseScraper):
    rss_url: str
    headers: dict = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ABACO-NewsBot/1.0",
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    }

    async def fetch(self) -> list:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True, headers=self.headers) as client:
            response = await client.get(self.rss_url)
            response.raise_for_status()
        feed = feedparser.parse(response.text)
        return feed.entries

    async def parse(self, entries: list) -> list[dict]:
        articles = []
        for entry in entries:
            try:
                article = self._parse_entry(entry)
                if article:
                    articles.append(article)
            except Exception as e:
                logger.warning(f"Failed to parse RSS entry: {e}")
        return articles

    def _parse_entry(self, entry) -> dict | None:
        url = getattr(entry, 'link', None)
        title = getattr(entry, 'title', None)
        if not url or not title:
            return None

        # Parse published date
        published_at = datetime.now(timezone.utc)
        if hasattr(entry, 'published'):
            try:
                published_at = parsedate_to_datetime(entry.published)
                if published_at.tzinfo is None:
                    published_at = published_at.replace(tzinfo=timezone.utc)
            except Exception:
                pass
        elif hasattr(entry, 'updated'):
            try:
                published_at = parsedate_to_datetime(entry.updated)
                if published_at.tzinfo is None:
                    published_at = published_at.replace(tzinfo=timezone.utc)
            except Exception:
                pass

        # Extract summary
        summary = None
        if hasattr(entry, 'summary'):
            from bs4 import BeautifulSoup
            summary = BeautifulSoup(entry.summary, 'lxml').get_text(strip=True)[:500]

        # Extract image
        image_url = None
        if hasattr(entry, 'media_content') and entry.media_content:
            image_url = entry.media_content[0].get('url')
        elif hasattr(entry, 'enclosures') and entry.enclosures:
            for enc in entry.enclosures:
                if enc.get('type', '').startswith('image/'):
                    image_url = enc.get('href')
                    break

        # Tags
        tags = []
        if hasattr(entry, 'tags'):
            tags = [t.term for t in entry.tags if hasattr(t, 'term')]

        return {
            "title": title.strip(),
            "original_url": url.strip(),
            "summary": summary,
            "image_url": image_url,
            "author": getattr(entry, 'author', None),
            "published_at": published_at,
            "tags": tags,
        }
