"""Avocatnet.ro scraper — Romanian legal/HR/fiscal news.

Avocatnet returns 403 on its RSS feed, so Playwright is required. The real
article container is `article.articol-listing` (and modifier variants like
`.articol-mare`, `.articol-headline`); article URLs match the pattern
`/articol_<NUMBER>/...` which is the discriminator we use to skip nav,
login, newsletter, and category links.
"""
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from playwright.async_api import Page

from .playwright_base import PlaywrightBaseScraper
import logging

logger = logging.getLogger(__name__)


_ARTICLE_URL_RE = re.compile(r"/articol_\d+/")


class AvocatnetScraper(PlaywrightBaseScraper):
    source_name = "Avocatnet.ro"
    source_url = "https://www.avocatnet.ro"

    _PAGES = [
        "https://www.avocatnet.ro/",
        "https://www.avocatnet.ro/categorie_2/Fiscalitate.html",
        "https://www.avocatnet.ro/categorie_5/Resurse-umane.html",
    ]

    async def scrape_page(self, page: Page) -> list[dict]:
        seen_urls: set[str] = set()
        articles: list[dict] = []

        for url in self._PAGES:
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            except Exception as e:
                logger.warning(f"avocatnet: failed to load {url}: {e}")
                continue

            items = await page.evaluate(
                """() => {
                    const out = [];
                    // Avocatnet uses <div class="articol-listing ...">, not <article>
                    const containers = document.querySelectorAll(
                        '.articol-listing, .articol-mare, .articol-headline, .articol-legatura'
                    );
                    for (const c of containers) {
                        const titleA = c.querySelector('h2 a[href], h3 a[href]');
                        if (!titleA) continue;
                        const title = (titleA.textContent || '').trim();
                        const href  = titleA.href || '';
                        if (!title || !href) continue;
                        if (!/\\/articol_\\d+\\//.test(href)) continue;

                        // Description: first <p> in container after the heading
                        let summary = '';
                        const pTag = c.querySelector('p');
                        if (pTag) summary = (pTag.textContent || '').trim().slice(0, 500);

                        // Image
                        let image = null;
                        const imgEl = c.querySelector('img');
                        if (imgEl) image = imgEl.src || imgEl.getAttribute('data-src') || null;

                        // Date
                        let datetimeAttr = null;
                        const t = c.querySelector('time[datetime]');
                        if (t) datetimeAttr = t.getAttribute('datetime');

                        // Author
                        let author = null;
                        const aEl = c.querySelector('.autor a, .author a, span.author');
                        if (aEl) author = (aEl.textContent || '').trim() || null;

                        out.push({title, href, summary, image, datetimeAttr, author});
                    }
                    return out;
                }"""
            )

            for it in items:
                href = it.get("href")
                if not href or href in seen_urls:
                    continue
                if not _ARTICLE_URL_RE.search(href):
                    continue
                seen_urls.add(href)

                published_at = datetime.now(timezone.utc)
                dt_attr = it.get("datetimeAttr")
                if dt_attr:
                    try:
                        try:
                            published_at = datetime.fromisoformat(dt_attr.replace("Z", "+00:00"))
                        except ValueError:
                            published_at = parsedate_to_datetime(dt_attr)
                        if published_at.tzinfo is None:
                            published_at = published_at.replace(tzinfo=timezone.utc)
                    except Exception:
                        pass

                articles.append({
                    "title": it["title"].strip(),
                    "original_url": href.strip(),
                    "summary": (it.get("summary") or "").strip() or None,
                    "image_url": it.get("image"),
                    "author": it.get("author"),
                    "published_at": published_at,
                    "tags": [],
                })

        logger.info(f"avocatnet: scraped {len(articles)} unique articles from {len(self._PAGES)} pages")
        return articles
