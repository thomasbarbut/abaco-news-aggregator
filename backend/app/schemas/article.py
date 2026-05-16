import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.source import NewsSourceResponse


# ---------------------------------------------------------------------------
# Base / Create
# ---------------------------------------------------------------------------


class ArticleBase(BaseModel):
    title: str
    slug: str
    summary: str | None = None
    content: str | None = None
    content_html: str | None = None
    original_url: str
    image_url: str | None = None
    author: str | None = None
    published_at: datetime
    category: str | None = None
    tags: list[str] = Field(default_factory=list)
    language: str = "ro"


class ArticleCreate(ArticleBase):
    source_id: uuid.UUID
    checksum: str


# ---------------------------------------------------------------------------
# Response (detail) — includes full archived content
# ---------------------------------------------------------------------------


class ArticleResponse(ArticleBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_id: uuid.UUID
    checksum: str
    scraped_at: datetime
    created_at: datetime
    # Populated by the API layer; not a DB column
    source: NewsSourceResponse | None = None
    is_read: bool = False


# ---------------------------------------------------------------------------
# Lightweight list item — strips content + content_html to keep payloads small
# ---------------------------------------------------------------------------


class ArticleListItem(BaseModel):
    """Compact article representation used in feed/list responses.

    Excludes the full body (``content`` / ``content_html``) which can be tens
    of kilobytes per article. Surfaces a single ``has_archive`` boolean so the
    UI can show a "view archive" affordance without fetching the body.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_id: uuid.UUID
    title: str
    slug: str
    summary: str | None = None
    original_url: str
    image_url: str | None = None
    author: str | None = None
    published_at: datetime
    scraped_at: datetime
    created_at: datetime
    checksum: str
    category: str | None = None
    tags: list[str] = Field(default_factory=list)
    language: str = "ro"
    source: NewsSourceResponse | None = None
    is_read: bool = False
    has_archive: bool = False


# ---------------------------------------------------------------------------
# Paginated list
# ---------------------------------------------------------------------------


class ArticleListResponse(BaseModel):
    items: list[ArticleListItem]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Filter / query parameters
# ---------------------------------------------------------------------------


class ArticleFilter(BaseModel):
    source_ids: list[uuid.UUID] | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    category: str | None = None
    is_read: bool | None = None
    search: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
