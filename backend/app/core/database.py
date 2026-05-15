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
_is_sqlite = _async_url.startswith("sqlite")

if _is_sqlite:
    from sqlalchemy.pool import StaticPool
    engine = create_async_engine(
        _async_url,
        echo=settings.DEBUG,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    engine = create_async_engine(
        _async_url,
        echo=settings.DEBUG,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600,
    )

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


def _create_tables_sqlite(sync_conn: object) -> None:
    """Create all tables on SQLite, skipping PostgreSQL-specific GIN indexes."""
    from app.models.article import Article

    # The GIN full-text search index uses to_tsvector() which SQLite doesn't have.
    # Temporarily remove it so create_all succeeds, then restore for prod parity.
    table = Article.__table__  # type: ignore[attr-defined]
    fts_index = next(
        (idx for idx in table.indexes if idx.name == "ix_articles_fts"),
        None,
    )
    if fts_index:
        table.indexes.discard(fts_index)
    try:
        Base.metadata.create_all(sync_conn, checkfirst=True)  # type: ignore[arg-type]
    finally:
        if fts_index:
            table.indexes.add(fts_index)


async def init_db() -> None:
    """Create all tables that are registered on Base.metadata.

    In production migrations are handled by Alembic; this function is a
    convenience for local development and integration tests.
    """
    # Import models so they register themselves on Base.metadata
    import app.models  # noqa: F401

    async with engine.begin() as conn:
        if _is_sqlite:
            await conn.run_sync(_create_tables_sqlite)
        else:
            await conn.run_sync(Base.metadata.create_all)
