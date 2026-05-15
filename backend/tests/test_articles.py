"""Tests for the /api/articles endpoints."""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article
from app.models.article_read import ArticleRead
from app.models.news_source import NewsSource, SourceType, SyncStatus
from app.models.user import User
from tests.conftest import auth_headers_for

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_article(source_id: uuid.UUID, suffix: str = "1") -> Article:
    url = f"https://test-source.ro/article/{suffix}"
    return Article(
        id=uuid.uuid4(),
        source_id=source_id,
        title=f"Test Article {suffix}",
        slug=f"test-article-{suffix}",
        summary=f"Summary of article {suffix}",
        original_url=url,
        published_at=datetime.now(timezone.utc),
        scraped_at=datetime.now(timezone.utc),
        tags=[],
        language="ro",
        checksum=hashlib.sha256(url.encode()).hexdigest(),
        created_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_get_articles_unauthenticated(client: AsyncClient) -> None:
    """Unauthenticated request should return HTTP 401."""
    response = await client.get("/api/articles")
    assert response.status_code == 401


async def test_get_articles_empty(
    client: AsyncClient,
    test_user: User,
) -> None:
    """Authenticated request with empty DB should return empty list."""
    response = await client.get("/api/articles", headers=auth_headers_for(test_user))
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []
    assert data["page"] == 1
    assert data["page_size"] == 20


async def test_get_articles_with_data(
    client: AsyncClient,
    db: AsyncSession,
    test_user: User,
    test_source: NewsSource,
) -> None:
    """Should return paginated articles when data exists."""
    # Create 3 articles
    for i in range(1, 4):
        db.add(_make_article(test_source.id, str(i)))
    await db.flush()

    response = await client.get(
        "/api/articles",
        params={"page": 1, "page_size": 2},
        headers=auth_headers_for(test_user),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["page_size"] == 2


async def test_get_article_marks_read(
    client: AsyncClient,
    db: AsyncSession,
    test_user: User,
    test_source: NewsSource,
) -> None:
    """Fetching an article detail should auto-mark it as read."""
    article = _make_article(test_source.id, "mark-read")
    db.add(article)
    await db.flush()

    response = await client.get(
        f"/api/articles/{article.id}",
        headers=auth_headers_for(test_user),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_read"] is True


async def test_mark_read_unread(
    client: AsyncClient,
    db: AsyncSession,
    test_user: User,
    test_source: NewsSource,
) -> None:
    """POST /read then POST /unread should toggle the read state."""
    article = _make_article(test_source.id, "toggle-read")
    db.add(article)
    await db.flush()

    headers = auth_headers_for(test_user)

    # Mark as read
    r = await client.post(f"/api/articles/{article.id}/read", headers=headers)
    assert r.status_code == 200

    # Verify read
    r = await client.get(f"/api/articles/{article.id}", headers=headers)
    assert r.json()["is_read"] is True

    # Mark as unread
    r = await client.post(f"/api/articles/{article.id}/unread", headers=headers)
    assert r.status_code == 200

    # Verify unread — we need a fresh fetch via the list endpoint
    list_r = await client.get(
        "/api/articles",
        params={"is_read": "false"},
        headers=headers,
    )
    ids = [item["id"] for item in list_r.json()["items"]]
    assert str(article.id) in ids


async def test_filter_by_source(
    client: AsyncClient,
    db: AsyncSession,
    test_user: User,
    test_source: NewsSource,
) -> None:
    """Filter by source_ids should only return articles from that source."""
    other_source = NewsSource(
        id=uuid.uuid4(),
        name="Other Source",
        url="https://other.ro",
        rss_url="https://other.ro/rss",
        source_type=SourceType.rss,
        enabled=True,
        sync_status=SyncStatus.ok,
        created_at=datetime.now(timezone.utc),
    )
    db.add(other_source)
    await db.flush()

    a1 = _make_article(test_source.id, "source-filter-1")
    a2 = _make_article(other_source.id, "source-filter-2")
    db.add(a1)
    db.add(a2)
    await db.flush()

    headers = auth_headers_for(test_user)
    r = await client.get(
        "/api/articles",
        params={"source_ids": str(test_source.id)},
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()
    returned_ids = [item["id"] for item in data["items"]]
    assert str(a1.id) in returned_ids
    assert str(a2.id) not in returned_ids


async def test_search_articles(
    client: AsyncClient,
    db: AsyncSession,
    test_user: User,
    test_source: NewsSource,
) -> None:
    """Search param should filter articles by title/summary keyword."""
    a_match = _make_article(test_source.id, "search-match")
    a_match.title = "European Union Economy Report"
    a_match.summary = "Analysis of the EU economy"

    a_no_match = _make_article(test_source.id, "search-no-match")
    a_no_match.title = "Local Sports News"
    a_no_match.summary = "Football results this week"

    db.add(a_match)
    db.add(a_no_match)
    await db.flush()

    headers = auth_headers_for(test_user)
    r = await client.get(
        "/api/articles",
        params={"search": "European"},
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()
    returned_ids = [item["id"] for item in data["items"]]
    assert str(a_match.id) in returned_ids
    assert str(a_no_match.id) not in returned_ids
