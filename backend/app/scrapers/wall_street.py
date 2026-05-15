from datetime import datetime, timezone
from typing import Any
from playwright.async_api import Page
from .playwright_base import PlaywrightBaseScraper
import logging

logger = logging.getLogger(__name__)

# Wall-Street.ro is a major Romanian financial/business news portal.
# RSS returns 403; the site uses dynamic rendering so Playwright is required.
# The homepage presents articles in card/tile format with clear <article> landmarks.


class WallStreetScraper(PlaywrightBaseScraper):
    source_name = "Wall-Street.ro"
    source_url = "https://www.wall-street.ro"

    # Wall-Street.ro uses a custom CMS.  Selectors target the known card structure
    # but fall back progressively so the scraper survives minor redesigns.
    _CARD_SELECTORS = [
        "article.article-card",
        "article.post-card",
        "div.article-card",
        "div.news-item",
        ".articles-grid article",
        ".listing-articles article",
        "article",
    ]

    _TITLE_SELECTORS = [
        "h2.article-card__title a",
        "h3.article-card__title a",
        ".article-card__title a",
        "h2.entry-title a",
        "h3.entry-title a",
        ".title a",
        "h2 a",
        "h3 a",
    ]

    _SUMMARY_SELECTORS = [
        ".article-card__excerpt",
        ".article-card__description",
        ".article-card__intro",
        ".excerpt",
        "p.lead",
        "p",
    ]

    _IMAGE_SELECTORS = [
        ".article-card__image img",
        ".article-card__thumb img",
        ".card-image img",
        "figure img",
        "img",
    ]

    _DATE_SELECTORS = [
        "time[datetime]",
        ".article-card__date time",
        ".article-card__date",
        ".post-date",
        "time",
        ".date",
        ".meta-date",
    ]

    _CATEGORY_SELECTORS = [
        ".article-card__category",
        ".category-label",
        ".article-category",
        ".cat-label",
        "span.category",
    ]

    _AUTHOR_SELECTORS = [
        ".article-card__author",
        ".author-name",
        "span.author",
        ".byline",
    ]

    async def scrape_page(self, page: Page) -> list[dict[str, Any]]:
        articles: list[dict[str, Any]] = []

        try:
            await page.goto(self.source_url, wait_until="domcontentloaded", timeout=60_000)
            await page.wait_for_timeout(3_000)

            # Scroll down to trigger any lazy-loaded article cards
            for _ in range(4):
                await page.evaluate("window.scrollBy(0, window.innerHeight)")
                await page.wait_for_timeout(700)

            # Locate article cards
            card_elements = []
            for selector in self._CARD_SELECTORS:
                card_elements = await page.query_selector_all(selector)
                if len(card_elements) >= 5:
                    logger.debug(
                        f"Wall-Street.ro: found {len(card_elements)} cards with '{selector}'"
                    )
                    break

            if not card_elements:
                logger.warning(
                    "Wall-Street.ro: no card elements found, falling back to link extraction"
                )
                articles = await self._fallback_link_extraction(page)
                return articles

            seen_urls: set[str] = set()
            for card in card_elements[:25]:
                try:
                    article = await self._parse_card(card)
                    if article and article["original_url"] not in seen_urls:
                        seen_urls.add(article["original_url"])
                        articles.append(article)
                except Exception as exc:
                    logger.warning(f"Wall-Street.ro: error parsing card: {exc}")

        except Exception as exc:
            logger.error(f"Wall-Street.ro scrape_page failed: {exc}", exc_info=True)
            raise

        logger.info(f"Wall-Street.ro: scraped {len(articles)} articles")
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

        # --- Category ---
        category: str | None = "financiar-business"
        for sel in self._CATEGORY_SELECTORS:
            el = await card.query_selector(sel)
            if el:
                cat_text = (await el.inner_text()).strip().lower()
                if cat_text:
                    category = cat_text
                break

        # --- Author ---
        author: str | None = None
        for sel in self._AUTHOR_SELECTORS:
            el = await card.query_selector(sel)
            if el:
                author = (await el.inner_text()).strip() or None
                break

        return {
            "title": title,
            "original_url": url,
            "summary": summary,
            "image_url": image_url,
            "published_at": published_at,
            "category": category,
            "tags": [],
            "author": author,
        }

    async def _fallback_link_extraction(self, page: Page) -> list[dict[str, Any]]:
        articles = []
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
                    "category": "financiar-business",
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
        if not url.startswith("http"):
            return False
        if "wall-street.ro" not in url:
            return False
        path = url.replace("https://www.wall-street.ro", "").replace(
            "http://www.wall-street.ro", ""
        ).strip("/")
        if not path:
            return False
        segments = [s for s in path.split("/") if s]
        # Article slugs are typically long; category-only pages have a single short segment
        if len(segments) == 1 and len(segments[0]) < 5:
            return False
        # Reject tag/author/page pagination paths
        skip_prefixes = {"tag", "autor", "autori", "page", "search", "abonamente"}
        if segments and segments[0] in skip_prefixes:
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
