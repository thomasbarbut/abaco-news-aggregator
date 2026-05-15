from datetime import datetime, timezone
from typing import Any
from playwright.async_api import Page
from .playwright_base import PlaywrightBaseScraper
import logging

logger = logging.getLogger(__name__)

# Avocatnet.ro is Romania's leading legal, HR, and fiscal news portal.
# RSS returns 403; the site uses server-side rendering with structured article listings.
# The homepage prominently lists articles in clearly delineated card blocks.
# We also visit the /stiri and /legislatie sections for broader coverage.


class AvocatnetScraper(PlaywrightBaseScraper):
    source_name = "Avocatnet.ro"
    source_url = "https://www.avocatnet.ro"

    _CARD_SELECTORS = [
        "article.article-card",
        "article.stire",
        "article.post",
        "div.article-card",
        "div.stire-item",
        "div.news-item",
        ".articles-listing article",
        ".stiri-listing article",
        "article",
    ]

    _TITLE_SELECTORS = [
        "h2.article-card__title a",
        "h3.article-card__title a",
        ".article-card__title a",
        "h2.stire-title a",
        "h3.stire-title a",
        "h2.entry-title a",
        "h3.entry-title a",
        ".title a",
        "h2 a",
        "h3 a",
    ]

    _SUMMARY_SELECTORS = [
        ".article-card__excerpt",
        ".article-card__description",
        ".stire-intro",
        ".excerpt",
        ".intro",
        "p.lead",
        "p",
    ]

    _IMAGE_SELECTORS = [
        ".article-card__image img",
        ".stire-image img",
        ".thumbnail img",
        "figure img",
        "img",
    ]

    _DATE_SELECTORS = [
        "time[datetime]",
        ".article-card__date time",
        ".article-card__date",
        ".stire-date",
        ".post-date",
        "time",
        ".date",
    ]

    _CATEGORY_SELECTORS = [
        ".article-card__category",
        ".stire-category",
        ".category-label",
        "span.cat",
    ]

    # Sections to visit for adequate article coverage
    _PAGES_TO_VISIT = [
        "https://www.avocatnet.ro",
        "https://www.avocatnet.ro/stiri",
        "https://www.avocatnet.ro/legislatie",
        "https://www.avocatnet.ro/fiscalitate",
    ]

    async def scrape_page(self, page: Page) -> list[dict[str, Any]]:
        seen_urls: set[str] = set()
        all_articles: list[dict[str, Any]] = []

        for target_url in self._PAGES_TO_VISIT:
            try:
                page_articles = await self._scrape_listing_page(page, target_url, seen_urls)
                all_articles.extend(page_articles)
                if len(all_articles) >= 20:
                    break
            except Exception as exc:
                logger.warning(f"Avocatnet.ro: failed to scrape {target_url}: {exc}")

        logger.info(f"Avocatnet.ro: scraped {len(all_articles)} articles total")
        return all_articles

    async def _scrape_listing_page(
        self,
        page: Page,
        url: str,
        seen_urls: set[str],
    ) -> list[dict[str, Any]]:
        articles: list[dict[str, Any]] = []

        await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        await page.wait_for_timeout(3_000)

        # Scroll to surface lazy-loaded content
        for _ in range(3):
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
            await page.wait_for_timeout(600)

        card_elements = []
        for selector in self._CARD_SELECTORS:
            card_elements = await page.query_selector_all(selector)
            if len(card_elements) >= 5:
                logger.debug(
                    f"Avocatnet.ro ({url}): {len(card_elements)} cards with '{selector}'"
                )
                break

        if not card_elements:
            logger.warning(f"Avocatnet.ro: no cards at {url}, using link fallback")
            fallback = await self._fallback_link_extraction(page)
            for art in fallback:
                if art["original_url"] not in seen_urls:
                    seen_urls.add(art["original_url"])
                    articles.append(art)
            return articles

        for card in card_elements[:20]:
            try:
                article = await self._parse_card(card)
                if article and article["original_url"] not in seen_urls:
                    seen_urls.add(article["original_url"])
                    articles.append(article)
            except Exception as exc:
                logger.warning(f"Avocatnet.ro: error parsing card: {exc}")

        return articles

    async def _parse_card(self, card) -> dict[str, Any] | None:
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
                src = await el.get_attribute("data-src") or await el.get_attribute("src")
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

        # --- Category ---
        # Avocatnet primarily covers legal / HR / fiscal; derive from URL path when possible
        category = self._category_from_url(url)
        for sel in self._CATEGORY_SELECTORS:
            el = await card.query_selector(sel)
            if el:
                cat_text = (await el.inner_text()).strip().lower()
                if cat_text:
                    category = cat_text
                break

        return {
            "title": title,
            "original_url": url,
            "summary": summary,
            "image_url": image_url,
            "published_at": published_at,
            "category": category,
            "tags": [],
            "author": None,
        }

    async def _fallback_link_extraction(self, page: Page) -> list[dict[str, Any]]:
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
                    title = (await anchor.get_attribute("aria-label") or "").strip()
                if not title or len(title) < 10:
                    continue

                articles.append({
                    "title": title,
                    "original_url": url,
                    "summary": None,
                    "image_url": None,
                    "published_at": datetime.now(timezone.utc),
                    "category": self._category_from_url(url),
                    "tags": [],
                    "author": None,
                })

                if len(articles) >= 15:
                    break
            except Exception:
                continue

        return articles

    def _category_from_url(self, url: str) -> str:
        """Infer content category from URL path segment."""
        mapping = {
            "legislatie": "legislatie",
            "fiscalitate": "fiscalitate",
            "stiri": "juridic-stiri",
            "munca": "munca-hr",
            "hr": "munca-hr",
            "contabilitate": "contabilitate",
            "taxe": "fiscalitate",
        }
        lower_url = url.lower()
        for key, cat in mapping.items():
            if f"/{key}" in lower_url or f"/{key}/" in lower_url:
                return cat
        return "juridic"

    def _absolute_url(self, href: str) -> str:
        if href.startswith("http"):
            return href
        if href.startswith("//"):
            return "https:" + href
        if href.startswith("/"):
            return self.source_url.rstrip("/") + href
        return self.source_url.rstrip("/") + "/" + href

    def _looks_like_article_url(self, url: str) -> bool:
        if not url.startswith("http"):
            return False
        if "avocatnet.ro" not in url:
            return False
        path = (
            url.replace("https://www.avocatnet.ro", "")
            .replace("http://www.avocatnet.ro", "")
            .strip("/")
        )
        if not path:
            return False
        segments = [s for s in path.split("/") if s]
        if not segments:
            return False
        skip_prefixes = {
            "tag", "tags", "autor", "autori", "page", "search",
            "contact", "despre", "newsletter", "abonare",
        }
        if segments[0] in skip_prefixes:
            return False
        # Reject anchor-only and query-only strings
        if path.startswith("#") or (len(segments) == 1 and len(segments[0]) < 4):
            return False
        return True

    def _parse_datetime(self, text: str) -> datetime | None:
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
