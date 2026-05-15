from datetime import datetime, timezone
from typing import Any
from playwright.async_api import Page
from .playwright_base import PlaywrightBaseScraper
import logging

logger = logging.getLogger(__name__)

# Economedia.ro returns 403 on RSS feed requests; browser automation is required.
# The site is built on a modern CMS with article cards on the homepage listing.


class EconomiediaScraper(PlaywrightBaseScraper):
    source_name = "Economedia"
    source_url = "https://www.economedia.ro"

    # Candidate CSS selectors for article cards on the homepage.
    # Economedia uses a card-based layout; selectors are ordered from most
    # specific to most generic so we can fall back gracefully.
    _CARD_SELECTORS = [
        "article.article-card",
        "article.post",
        "div.article-card",
        "div.article-item",
        ".articles-list article",
        ".listing article",
        "article",
    ]

    _TITLE_SELECTORS = [
        "h2.article-card__title a",
        "h3.article-card__title a",
        "h2.entry-title a",
        "h3.entry-title a",
        ".article-title a",
        ".card-title a",
        "h2 a",
        "h3 a",
        "a.article-link",
    ]

    _SUMMARY_SELECTORS = [
        ".article-card__excerpt",
        ".article-card__description",
        ".entry-excerpt",
        ".excerpt",
        "p.description",
        "p.summary",
        "p",
    ]

    _IMAGE_SELECTORS = [
        ".article-card__image img",
        ".article-card__thumbnail img",
        ".post-thumbnail img",
        ".thumbnail img",
        "figure img",
        "img",
    ]

    _DATE_SELECTORS = [
        "time[datetime]",
        ".article-card__date",
        ".entry-date",
        ".post-date",
        "time",
        ".date",
    ]

    async def scrape_page(self, page: Page) -> list[dict[str, Any]]:
        articles: list[dict[str, Any]] = []

        try:
            await page.goto(self.source_url, wait_until="domcontentloaded", timeout=60_000)
            # Let lazy-loaded content settle
            await page.wait_for_timeout(3_000)

            # Scroll to trigger lazy loading of more articles
            for _ in range(3):
                await page.evaluate("window.scrollBy(0, window.innerHeight)")
                await page.wait_for_timeout(800)

            # Try each card selector until we find cards
            card_elements = []
            for selector in self._CARD_SELECTORS:
                card_elements = await page.query_selector_all(selector)
                if len(card_elements) >= 5:
                    logger.debug(
                        f"Economedia: found {len(card_elements)} cards with '{selector}'"
                    )
                    break

            if not card_elements:
                # Last-resort: grab all <a> tags that look like article links
                logger.warning(
                    "Economedia: no card elements found, falling back to link extraction"
                )
                articles = await self._fallback_link_extraction(page)
                return articles

            for card in card_elements[:20]:  # cap at 20 articles per run
                try:
                    article = await self._parse_card(card, page)
                    if article:
                        articles.append(article)
                except Exception as exc:
                    logger.warning(f"Economedia: error parsing card: {exc}")

        except Exception as exc:
            logger.error(f"Economedia scrape_page failed: {exc}", exc_info=True)
            raise

        logger.info(f"Economedia: scraped {len(articles)} articles")
        return articles

    async def _parse_card(self, card, page: Page) -> dict[str, Any] | None:
        """Extract a single article dict from a card element."""
        # --- Title + URL ---
        title: str | None = None
        url: str | None = None

        for sel in self._TITLE_SELECTORS:
            el = await card.query_selector(sel)
            if el:
                title = (await el.inner_text()).strip()
                href = await el.get_attribute("href")
                if href:
                    url = self._absolute_url(href)
                break

        # If title selector didn't include an <a>, look for any <a> in card
        if not url:
            a_el = await card.query_selector("a[href]")
            if a_el:
                href = await a_el.get_attribute("href")
                if href:
                    url = self._absolute_url(href)
        if not title:
            a_el = await card.query_selector("a")
            if a_el:
                title = (await a_el.inner_text()).strip()

        if not title or not url:
            return None

        # Skip non-article links (navigation, category pages, etc.)
        if not self._looks_like_article_url(url):
            return None

        # --- Summary ---
        summary: str | None = None
        for sel in self._SUMMARY_SELECTORS:
            el = await card.query_selector(sel)
            if el:
                text = (await el.inner_text()).strip()
                if text and text != title and len(text) > 20:
                    summary = text[:500]
                    break

        # --- Image ---
        image_url: str | None = None
        for sel in self._IMAGE_SELECTORS:
            el = await card.query_selector(sel)
            if el:
                src = await el.get_attribute("src") or await el.get_attribute("data-src")
                if src and not src.startswith("data:"):
                    image_url = self._absolute_url(src)
                    break

        # --- Published date ---
        published_at = datetime.now(timezone.utc)
        for sel in self._DATE_SELECTORS:
            el = await card.query_selector(sel)
            if el:
                dt_attr = await el.get_attribute("datetime")
                if dt_attr:
                    parsed = self._parse_datetime(dt_attr)
                    if parsed:
                        published_at = parsed
                        break
                text = (await el.inner_text()).strip()
                if text:
                    parsed = self._parse_datetime(text)
                    if parsed:
                        published_at = parsed
                        break

        return {
            "title": title,
            "original_url": url,
            "summary": summary,
            "image_url": image_url,
            "published_at": published_at,
            "category": "economic",
            "tags": [],
            "author": None,
        }

    async def _fallback_link_extraction(self, page: Page) -> list[dict[str, Any]]:
        """Last-resort: extract article links from all anchors on the page."""
        articles: list[dict] = []
        anchors = await page.query_selector_all("a[href]")
        seen_urls: set[str] = set()

        for anchor in anchors:
            try:
                href = await anchor.get_attribute("href")
                if not href:
                    continue
                url = self._absolute_url(href)
                if url in seen_urls or not self._looks_like_article_url(url):
                    continue
                seen_urls.add(url)

                title = (await anchor.inner_text()).strip()
                if not title or len(title) < 10:
                    # Try aria-label
                    title = await anchor.get_attribute("aria-label") or ""
                    title = title.strip()
                if not title or len(title) < 10:
                    continue

                articles.append({
                    "title": title,
                    "original_url": url,
                    "summary": None,
                    "image_url": None,
                    "published_at": datetime.now(timezone.utc),
                    "category": "economic",
                    "tags": [],
                    "author": None,
                })

                if len(articles) >= 15:
                    break
            except Exception:
                continue

        return articles

    def _absolute_url(self, href: str) -> str:
        if href.startswith("http"):
            return href
        if href.startswith("//"):
            return "https:" + href
        if href.startswith("/"):
            return self.source_url.rstrip("/") + href
        return self.source_url.rstrip("/") + "/" + href

    def _looks_like_article_url(self, url: str) -> bool:
        """Heuristic: article URLs typically contain a date segment or are deep paths."""
        if not url.startswith("http"):
            return False
        # Exclude root, category pages, pagination
        path = url.replace(self.source_url, "").strip("/")
        if not path or path in {"#", "contact", "despre-noi", "advertorial"}:
            return False
        # Must be from the same domain
        if "economedia.ro" not in url:
            return False
        # Must have at least one path segment of meaningful length
        segments = [s for s in path.split("/") if s]
        if not segments:
            return False
        # Reject pure category / tag pages (no slug after category)
        if len(segments) == 1 and len(segments[0]) < 4:
            return False
        return True

    def _parse_datetime(self, text: str) -> datetime | None:
        """Attempt to parse several datetime formats used by Romanian news sites."""
        text = text.strip()
        formats = [
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%d.%m.%Y %H:%M",
            "%d.%m.%Y",
            "%d/%m/%Y %H:%M",
            "%d/%m/%Y",
        ]
        for fmt in formats:
            try:
                dt = datetime.strptime(text, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue
        return None
