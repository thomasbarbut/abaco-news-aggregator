import enum
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, HttpUrl


class SourceType(str, enum.Enum):
    rss = "rss"
    playwright = "playwright"


class SyncStatus(str, enum.Enum):
    ok = "ok"
    error = "error"
    pending = "pending"


class NewsSourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    url: str
    rss_url: str | None = None
    source_type: SourceType
    enabled: bool
    last_sync_at: datetime | None = None
    sync_status: SyncStatus
    created_at: datetime
