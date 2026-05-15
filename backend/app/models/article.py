import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy import text as sa_text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("news_sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    content: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    original_url: Mapped[str] = mapped_column(String(2048), unique=True, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(2048), nullable=True, default=None)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    category: Mapped[str | None] = mapped_column(String(128), nullable=True, default=None)
    tags: Mapped[list[Any]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default="[]",
    )
    language: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="ro",
        server_default="ro",
    )
    # SHA-256 hex digest of original_url – used for fast deduplication
    checksum: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    __table_args__ = (
        # Composite B-tree index on published_at (already created above as
        # a single-column index) plus source_id for feed queries
        Index("ix_articles_source_published", "source_id", "published_at"),
        # PostgreSQL GIN full-text search index
        Index(
            "ix_articles_fts",
            sa_text(
                "to_tsvector('simple', "
                "title || ' ' || coalesce(summary, '') || ' ' || coalesce(content, ''))"
            ),
            postgresql_using="gin",
        ),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Article id={self.id} slug={self.slug!r}>"
