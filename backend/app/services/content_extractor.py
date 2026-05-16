"""Fetch an article URL and extract the main body in both text and HTML.

Used during sync to populate ``Article.content`` (plain text, for search) and
``Article.content_html`` (cleaned HTML, for the in-app reader/archive view).

The HTTP fetch and the trafilatura parse both run in worker threads so they
don't block the event loop. Failures return (None, None) — callers should
proceed without raising, since extraction is best-effort enrichment.
"""
from __future__ import annotations

import asyncio
import logging

import httpx
import trafilatura

logger = logging.getLogger(__name__)

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0 Safari/537.36 ABACO-NewsBot/1.0"
)
_HEADERS = {
    "User-Agent": _USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ro,en;q=0.8",
}
_TIMEOUT = 20.0


async def fetch_html(url: str) -> str | None:
    """GET ``url`` and return the response text, or None on failure."""
    try:
        async with httpx.AsyncClient(
            timeout=_TIMEOUT,
            follow_redirects=True,
            headers=_HEADERS,
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.text
    except Exception as e:  # noqa: BLE001
        logger.info(f"content fetch failed for {url}: {type(e).__name__}: {e}")
        return None


def _extract_sync(raw_html: str, url: str) -> tuple[str | None, str | None]:
    """Run trafilatura on raw HTML. Returns (text, body_html)."""
    try:
        text = trafilatura.extract(
            raw_html,
            url=url,
            include_comments=False,
            include_tables=True,
            favor_recall=True,
        )
    except Exception as e:  # noqa: BLE001
        logger.info(f"trafilatura text extract failed for {url}: {e}")
        text = None
    try:
        body_html = trafilatura.extract(
            raw_html,
            url=url,
            include_comments=False,
            include_tables=True,
            include_images=True,
            include_links=True,
            output_format="html",
            favor_recall=True,
        )
    except Exception as e:  # noqa: BLE001
        logger.info(f"trafilatura html extract failed for {url}: {e}")
        body_html = None
    return text, body_html


async def fetch_and_extract(url: str) -> tuple[str | None, str | None]:
    """Fetch ``url`` and return (text, html) of the article body.

    Both values may be None when the page is unreachable, blocked, or has
    no extractable main content.
    """
    raw = await fetch_html(url)
    if not raw:
        return None, None
    return await asyncio.to_thread(_extract_sync, raw, url)
