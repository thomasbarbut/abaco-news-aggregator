"""drymix.info newsletter archive scraper.

Source: https://www.drymix.info/index.php?id=53 — a plain HTML page that
lists every past "drymix.info News N/YYYY" newsletter as a link of the
form `index.php?id=<ID>&L=590`. No RSS, no JS, no bot protection.

Each newsletter entry becomes one Article with category="newsletter" so
the frontend can filter them into a dedicated tab.
"""
import re
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

from .base import BaseScraper
import logging

logger = logging.getLogger(__name__)


_LINK_RE = re.compile(r"drymix\.info\s*News\s+(\d+)\s*/\s*(\d{4})", re.IGNORECASE)
_BASE = "https://www.drymix.info/"
_ARCHIVE_URL = _BASE + "index.php?id=53"


class DrymixNewsletterScraper(BaseScraper):
    source_name = "Drymix Newsletter"
    source_url = _BASE
    headers: dict = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/131.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml",
    }

    async def fetch(self) -> list[dict]:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True, headers=self.headers) as client:
            response = await client.get(_ARCHIVE_URL)
            response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")
        items: list[dict] = []
        seen_urls: set[str] = set()
        for a in soup.find_all("a", href=True):
            text = (a.get_text() or "").strip()
            m = _LINK_RE.search(text)
            if not m:
                continue
            href = a["href"].strip()
            if href.startswith("index.php"):
                full_url = _BASE + href
            elif href.startswith("/"):
                full_url = "https://www.drymix.info" + href
            elif href.startswith("http"):
                full_url = href
            else:
                full_url = _BASE + href
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)
            number, year = int(m.group(1)), int(m.group(2))
            items.append({
                "title": f"drymix.info News {number}/{year}",
                "original_url": full_url,
                "number": number,
                "year": year,
            })
        return items

    async def parse(self, raw_items: list[dict]) -> list[dict]:
        # We have no real publication date for past newsletters (only number+year).
        # For *new* newsletters, use scraped_at; for historical, use Jan 1 of the year
        # so they sort sensibly but stay clearly older than today's items.
        now = datetime.now(timezone.utc)
        out: list[dict] = []
        for it in raw_items:
            # Heuristic published_at: end of year (approximates publication date well
            # enough for sorting). New items added in the current year get "now"
            # only if their number is higher than any existing — handled at save time.
            year = it["year"]
            if year >= now.year:
                published_at = now
            else:
                published_at = datetime(year, 12, 31, tzinfo=timezone.utc)
            out.append({
                "title": it["title"],
                "original_url": it["original_url"],
                "summary": None,
                "image_url": None,
                "author": None,
                "published_at": published_at,
                "category": "newsletter",
                "tags": ["newsletter", "drymix"],
                "language": "en",
            })
        return out
