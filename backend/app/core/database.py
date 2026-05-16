from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
# asyncpg requires the postgresql+asyncpg:// scheme.  We normalise the URL in
# case the env var uses the plain postgres:// or postgresql:// scheme.
def _build_async_url(url: str) -> str:
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+asyncpg://" + url[len(prefix):]
    return url  # already has the correct driver prefix


_async_url = _build_async_url(settings.DATABASE_URL)

# SQLite uses NullPool and rejects pool_size/max_overflow. Postgres uses
# QueuePool and needs them. Branch on the URL.
_is_sqlite = _async_url.startswith("sqlite")
_engine_kwargs: dict = {"echo": settings.DEBUG}
if not _is_sqlite:
    _engine_kwargs.update(
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600,
    )

engine = create_async_engine(_async_url, **_engine_kwargs)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# ---------------------------------------------------------------------------
# Base class for all ORM models
# ---------------------------------------------------------------------------


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session and guarantee it is closed afterwards."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Helper used by startup event to create tables (dev/test only)
# ---------------------------------------------------------------------------


async def init_db() -> None:
    """Create all tables that are registered on Base.metadata.

    In production migrations are handled by Alembic; this function is a
    convenience for local development and integration tests.
    """
    # Import models so they register themselves on Base.metadata
    import app.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def ensure_schema_additions() -> None:
    """Apply additive, idempotent schema fixes that should run on every boot.

    Kept separate from ``init_db`` so it works in production too (where
    ``init_db`` is skipped). Only safe, IF-NOT-EXISTS-style statements should
    live here — anything destructive belongs in Alembic.
    """
    from sqlalchemy import text as _sa_text
    from app.core.logging import get_logger as _get_logger

    _log = _get_logger(__name__)
    _stmts = [
        "ALTER TABLE articles ADD COLUMN IF NOT EXISTS content_html TEXT",
    ]
    async with engine.begin() as conn:
        for stmt in _stmts:
            try:
                await conn.execute(_sa_text(stmt))
            except Exception as e:  # noqa: BLE001
                _log.warning(f"schema addition skipped ({stmt!r}): {e}")
