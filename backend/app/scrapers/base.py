import hashlib
import re
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any
import logging

logger = logging.getLogger(__name__)


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text[:200]


def make_checksum(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()


class BaseScraper(ABC):
    source_name: str
    source_url: str

    async def fetch(self) -> list[dict[str, Any]]:
        """Fetch raw data from source. Returns list of raw items."""
        raise NotImplementedError

    @abstractmethod
    async def parse(self, raw_items: list[Any]) -> list[dict]:
        """Parse raw items into normalized article dicts."""
        raise NotImplementedError

    def normalize(self, article: dict) -> dict:
        """Ensure all required fields are present and correctly typed."""
        article.setdefault("summary", None)
        article.setdefault("content", None)
        article.setdefault("image_url", None)
        article.setdefault("author", None)
        article.setdefault("category", None)
        article.setdefault("tags", [])
        article.setdefault("language", "ro")
        article["checksum"] = make_checksum(article["original_url"])
        article["slug"] = slugify(article.get("title", "untitled"))
        if article.get("published_at") and article["published_at"].tzinfo is None:
            article["published_at"] = article["published_at"].replace(tzinfo=timezone.utc)
        return article

    async def scrape(self) -> list[dict]:
        """Main entry point: fetch → parse → normalize."""
        try:
            raw = await self.fetch()
            articles = await self.parse(raw)
            return [self.normalize(a) for a in articles]
        except Exception as e:
            logger.error(f"Scraper {self.source_name} failed: {e}", exc_info=True)
            raise
