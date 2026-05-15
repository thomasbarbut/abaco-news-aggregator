import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SourceType(str, enum.Enum):
    rss = "rss"
    playwright = "playwright"


class SyncStatus(str, enum.Enum):
    ok = "ok"
    error = "error"
    pending = "pending"


class NewsSource(Base):
    __tablename__ = "news_sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), unique=True, nullable=False)
    rss_url: Mapped[str | None] = mapped_column(String(2048), nullable=True, default=None)
    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType, name="sourcetype", create_type=True),
        nullable=False,
        default=SourceType.rss,
        server_default=SourceType.rss.value,
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    last_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
    sync_status: Mapped[SyncStatus] = mapped_column(
        Enum(SyncStatus, name="source_syncstatus", create_type=True),
        nullable=False,
        default=SyncStatus.pending,
        server_default=SyncStatus.pending.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<NewsSource id={self.id} name={self.name!r} type={self.source_type}>"
