"""Tests for admin sync, stats, and log endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.news_source import NewsSource, SourceType, SyncStatus
from app.models.sync_log import SyncLog, SyncLogStatus
from app.models.user import User
from tests.conftest import auth_headers_for

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Access control
# ---------------------------------------------------------------------------


async def test_sync_stats_admin_only(
    client: AsyncClient,
    test_user: User,
) -> None:
    """Regular users should be forbidden from accessing admin stats."""
    response = await client.get(
        "/api/admin/stats",
        headers=auth_headers_for(test_user),
    )
    assert response.status_code == 403


async def test_trigger_sync_requires_admin(
    client: AsyncClient,
    test_user: User,
) -> None:
    """Regular users should be forbidden from triggering a sync."""
    response = await client.post(
        "/api/admin/sync",
        json={},
        headers=auth_headers_for(test_user),
    )
    assert response.status_code == 403


async def test_get_sync_logs_requires_admin(
    client: AsyncClient,
    test_user: User,
) -> None:
    """GET /api/admin/logs should require admin role."""
    response = await client.get(
        "/api/admin/logs",
        headers=auth_headers_for(test_user),
    )
    assert response.status_code == 403


async def test_unauthenticated_admin_endpoints(client: AsyncClient) -> None:
    """All admin endpoints should return 401 without a token."""
    for path in ["/api/admin/stats", "/api/admin/logs"]:
        r = await client.get(path)
        assert r.status_code == 401, f"Expected 401 for {path}, got {r.status_code}"


# ---------------------------------------------------------------------------
# Admin stats
# ---------------------------------------------------------------------------


async def test_get_admin_stats(
    client: AsyncClient,
    db: AsyncSession,
    test_admin: User,
    test_source: NewsSource,
) -> None:
    """Admin should receive a valid stats payload."""
    # Patch redis health check to avoid connecting to a real broker
    with patch(
        "app.api.admin._check_redis",
        return_value=True,
    ):
        response = await client.get(
            "/api/admin/stats",
            headers=auth_headers_for(test_admin),
        )

    assert response.status_code == 200
    data = response.json()
    required_keys = {
        "total_articles",
        "articles_today",
        "active_sources",
        "failed_syncs",
        "redis_healthy",
        "db_healthy",
    }
    assert required_keys.issubset(data.keys())
    assert isinstance(data["total_articles"], int)
    assert isinstance(data["active_sources"], int)
    assert isinstance(data["db_healthy"], bool)


# ---------------------------------------------------------------------------
# Sync logs
# ---------------------------------------------------------------------------


async def test_get_sync_logs(
    client: AsyncClient,
    db: AsyncSession,
    test_admin: User,
    test_source: NewsSource,
) -> None:
    """Admin can retrieve sync logs; empty list is valid."""
    response = await client.get(
        "/api/admin/logs",
        headers=auth_headers_for(test_admin),
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


async def test_get_sync_logs_with_data(
    client: AsyncClient,
    db: AsyncSession,
    test_admin: User,
    test_source: NewsSource,
) -> None:
    """Sync log records should appear in the /api/admin/logs response."""
    now = datetime.now(timezone.utc)
    log = SyncLog(
        id=uuid.uuid4(),
        source_id=test_source.id,
        status=SyncLogStatus.success,
        started_at=now,
        completed_at=now,
        articles_added=5,
    )
    db.add(log)
    await db.flush()

    response = await client.get(
        "/api/admin/logs",
        headers=auth_headers_for(test_admin),
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    ids = [item["id"] for item in data]
    assert str(log.id) in ids


async def test_get_sync_logs_filter_by_source(
    client: AsyncClient,
    db: AsyncSession,
    test_admin: User,
    test_source: NewsSource,
) -> None:
    """The source_id query param should filter sync logs correctly."""
    other_source = NewsSource(
        id=uuid.uuid4(),
        name="Other",
        url="https://other-sync.ro",
        source_type=SourceType.rss,
        enabled=True,
        sync_status=SyncStatus.ok,
        created_at=datetime.now(timezone.utc),
    )
    db.add(other_source)
    await db.flush()

    now = datetime.now(timezone.utc)
    log_a = SyncLog(
        id=uuid.uuid4(),
        source_id=test_source.id,
        status=SyncLogStatus.success,
        started_at=now,
        completed_at=now,
        articles_added=1,
    )
    log_b = SyncLog(
        id=uuid.uuid4(),
        source_id=other_source.id,
        status=SyncLogStatus.error,
        started_at=now,
        articles_added=0,
    )
    db.add(log_a)
    db.add(log_b)
    await db.flush()

    response = await client.get(
        "/api/admin/logs",
        params={"source_id": str(test_source.id)},
        headers=auth_headers_for(test_admin),
    )
    assert response.status_code == 200
    data = response.json()
    returned_ids = [item["id"] for item in data]
    assert str(log_a.id) in returned_ids
    assert str(log_b.id) not in returned_ids


# ---------------------------------------------------------------------------
# Trigger sync (Celery task mocked)
# ---------------------------------------------------------------------------


async def test_trigger_sync_all(
    client: AsyncClient,
    test_admin: User,
) -> None:
    """Admin triggering a full sync should return 202 with a task_id."""
    mock_task = MagicMock()
    mock_task.id = "fake-celery-task-id"

    with patch("app.tasks.sync_tasks.sync_all_sources") as mock_sync:
        mock_sync.delay.return_value = mock_task
        response = await client.post(
            "/api/admin/sync",
            json={},
            headers=auth_headers_for(test_admin),
        )

    assert response.status_code == 202
    data = response.json()
    assert "task_id" in data


async def test_trigger_sync_single_source(
    client: AsyncClient,
    test_admin: User,
    test_source: NewsSource,
) -> None:
    """Admin can trigger a sync for a specific source."""
    mock_task = MagicMock()
    mock_task.id = "fake-celery-task-id-single"

    with patch("app.tasks.sync_tasks.sync_single_source") as mock_sync:
        mock_sync.delay.return_value = mock_task
        response = await client.post(
            "/api/admin/sync",
            json={"source_id": str(test_source.id)},
            headers=auth_headers_for(test_admin),
        )

    assert response.status_code == 202
    data = response.json()
    assert "task_id" in data
    assert "source_id" in data
