"""Pytest configuration and shared fixtures."""
from __future__ import annotations

import asyncio
import hashlib
import os
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator

# Set required env vars before any app module is imported.
# app.core.config instantiates Settings() at module level; without these,
# pydantic-settings raises ValidationError on import.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test_secret_for_pytest_not_for_production")
os.environ.setdefault("MICROSOFT_CLIENT_ID", "test-client-id")
os.environ.setdefault("MICROSOFT_CLIENT_SECRET", "test-client-secret")
os.environ.setdefault("MICROSOFT_TENANT_ID", "test-tenant-id")

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.models.user import User, UserRole
from app.models.news_source import NewsSource, SourceType, SyncStatus
from app.models.article import Article

# ---------------------------------------------------------------------------
# Use an in-memory SQLite database for tests (aiosqlite driver)
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


# pytest-asyncio 0.24 requires the event_loop fixture to be session-scoped
# explicitly when using session-scoped async fixtures.
@pytest.fixture(scope="session")
def event_loop_policy():
    return asyncio.DefaultEventLoopPolicy()


# We set asyncio_mode = auto in pytest.ini; these session-scoped async fixtures
# share the same loop via the session-wide event loop created by pytest-asyncio.
def _create_tables_sqlite(sync_conn: object) -> None:
    """Create tables for SQLite, skipping the PostgreSQL GIN FTS index."""
    fts_index = next(
        (idx for idx in Article.__table__.indexes if idx.name == "ix_articles_fts"),
        None,
    )
    if fts_index:
        Article.__table__.indexes.discard(fts_index)
    try:
        Base.metadata.create_all(sync_conn, checkfirst=True)  # type: ignore[arg-type]
    finally:
        if fts_index:
            Article.__table__.indexes.add(fts_index)


@pytest_asyncio.fixture(scope="session")
async def async_engine():
    """Create the async SQLite engine and all tables once per session."""
    from sqlalchemy.pool import StaticPool

    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Import all models so they register on Base.metadata
    import app.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(_create_tables_sqlite)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture()
async def db(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide an async session that rolls back after each test.

    Uses a savepoint-based approach: we begin a connection-level transaction
    before yielding the session, then roll back after the test finishes so
    data doesn't bleed between tests.
    """
    async with async_engine.connect() as conn:
        await conn.begin()
        # Nest a SAVEPOINT so ORM-level commits inside the session don't
        # permanently write to the in-memory DB.
        await conn.begin_nested()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            # Roll back the outer transaction so all changes are discarded.
            await conn.rollback()


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------


def auth_headers_for(user: User) -> dict[str, str]:
    """Return Authorization headers carrying a valid JWT for the given user."""
    token = create_access_token(
        subject=str(user.id),
        extra_claims={"role": user.role.value},
    )
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# User fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture()
async def test_user(db: AsyncSession) -> User:
    """Create a regular (non-admin) test user."""
    user = User(
        id=uuid.uuid4(),
        microsoft_id="ms-test-user-001",
        email="testuser@abaco.ro",
        name="Test User",
        role=UserRole.user,
        created_at=datetime.now(timezone.utc),
        last_login=datetime.now(timezone.utc),
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture()
async def test_admin(db: AsyncSession) -> User:
    """Create an admin test user."""
    admin = User(
        id=uuid.uuid4(),
        microsoft_id="ms-test-admin-001",
        email="admin@abaco.ro",
        name="Test Admin",
        role=UserRole.admin,
        created_at=datetime.now(timezone.utc),
        last_login=datetime.now(timezone.utc),
    )
    db.add(admin)
    await db.flush()
    await db.refresh(admin)
    return admin


@pytest.fixture()
def user_headers(test_user: User) -> dict[str, str]:
    return auth_headers_for(test_user)


@pytest.fixture()
def admin_headers(test_admin: User) -> dict[str, str]:
    return auth_headers_for(test_admin)


# ---------------------------------------------------------------------------
# HTTP client fixture
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture()
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Return an httpx AsyncClient wired to the FastAPI app with the test DB."""
    # Import lazily to avoid importing Celery/settings at collection time
    from app.main import app

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db

    app.dependency_overrides[get_db] = _override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac

    app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Domain object fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture()
async def test_source(db: AsyncSession) -> NewsSource:
    """Create a test news source."""
    source = NewsSource(
        id=uuid.uuid4(),
        name="Test Source",
        url="https://test-source.ro",
        rss_url="https://test-source.ro/rss",
        source_type=SourceType.rss,
        enabled=True,
        sync_status=SyncStatus.ok,
        created_at=datetime.now(timezone.utc),
    )
    db.add(source)
    await db.flush()
    await db.refresh(source)
    return source


@pytest_asyncio.fixture()
async def test_article(db: AsyncSession, test_source: NewsSource) -> Article:
    """Create a single test article linked to test_source."""
    url = "https://test-source.ro/article/test-article-1"
    article = Article(
        id=uuid.uuid4(),
        source_id=test_source.id,
        title="Test Article One",
        slug="test-article-one",
        summary="A brief summary of the test article.",
        original_url=url,
        published_at=datetime.now(timezone.utc),
        scraped_at=datetime.now(timezone.utc),
        tags=[],
        language="ro",
        checksum=hashlib.sha256(url.encode()).hexdigest(),
        created_at=datetime.now(timezone.utc),
    )
    db.add(article)
    await db.flush()
    await db.refresh(article)
    return article
