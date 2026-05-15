import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SyncLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_id: uuid.UUID
    status: str
    error_message: str | None = None
    started_at: datetime
    completed_at: datetime | None = None
    articles_added: int


class SyncRequest(BaseModel):
    """Request body for triggering a manual sync.

    source_id is optional; omitting it triggers a full sync of all enabled sources.
    """

    source_id: uuid.UUID | None = None


class AdminStatsResponse(BaseModel):
    total_articles: int
    articles_today: int
    active_sources: int
    failed_syncs: int
    last_sync_at: datetime | None
    redis_healthy: bool
    db_healthy: bool
