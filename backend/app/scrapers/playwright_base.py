from typing import Any
from playwright.async_api import async_playwright
from .base import BaseScraper
import logging

logger = logging.getLogger(__name__)


class PlaywrightBaseScraper(BaseScraper):
    """Base for sites that block RSS and require browser automation."""

    browser_args: list[str] = [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
    ]
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    async def fetch(self) -> list[dict[str, Any]]:
        """Returns list of article dicts scraped with Playwright."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(args=self.browser_args, headless=True)
            context = await browser.new_context(
                user_agent=self.user_agent,
                locale="ro-RO",
            )
            page = await context.new_page()
            articles = await self.scrape_page(page)
            await browser.close()
        return articles

    async def scrape_page(self, page) -> list[dict]:
        """Override this to implement site-specific scraping logic."""
        raise NotImplementedError

    async def parse(self, raw_items: list) -> list[dict]:
        return raw_items  # Already parsed in scrape_page
