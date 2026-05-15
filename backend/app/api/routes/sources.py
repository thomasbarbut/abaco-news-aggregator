"""News sources endpoints (read-only for regular users; admin can mutate)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.core.logging import get_logger
from app.models.news_source import NewsSource, SourceType, SyncStatus
from app.models.user import User
from app.schemas.source import NewsSourceResponse

router = APIRouter()
logger = get_logger(__name__)


@router.get("", response_model=list[NewsSourceResponse], summary="List all enabled sources")
async def list_sources(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[NewsSourceResponse]:
    rows = (
        await db.execute(select(NewsSource).where(NewsSource.enabled.is_(True)))
    ).scalars().all()
    return [NewsSourceResponse.model_validate(r) for r in rows]


@router.get("/{source_id}", response_model=NewsSourceResponse, summary="Get a single source")
async def get_source(
    source_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NewsSourceResponse:
    source = (
        await db.execute(select(NewsSource).where(NewsSource.id == source_id))
    ).scalar_one_or_none()
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    return NewsSourceResponse.model_validate(source)


# ---------------------------------------------------------------------------
# Admin-only mutations
# ---------------------------------------------------------------------------


class _SourceCreate(NewsSourceResponse.__class__.__bases__[0]):  # type: ignore[misc]
    """Internal schema – we reuse it rather than importing from schemas."""
    pass


from pydantic import BaseModel


class SourceCreate(BaseModel):
    name: str
    url: str
    rss_url: str | None = None
    source_type: str = "rss"
    enabled: bool = True


class SourceUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    rss_url: str | None = None
    source_type: str | None = None
    enabled: bool | None = None


@router.post(
    "",
    response_model=NewsSourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new source (admin only)",
)
async def create_source(
    body: SourceCreate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> NewsSourceResponse:
    source = NewsSource(
        name=body.name,
        url=body.url,
        rss_url=body.rss_url,
        source_type=SourceType(body.source_type),
        enabled=body.enabled,
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)
    logger.info("Source created", extra={"source_id": str(source.id), "name": source.name})
    return NewsSourceResponse.model_validate(source)


@router.patch(
    "/{source_id}",
    response_model=NewsSourceResponse,
    summary="Update a source (admin only)",
)
async def update_source(
    source_id: uuid.UUID,
    body: SourceUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> NewsSourceResponse:
    source = (
        await db.execute(select(NewsSource).where(NewsSource.id == source_id))
    ).scalar_one_or_none()
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")

    if body.name is not None:
        source.name = body.name
    if body.url is not None:
        source.url = body.url
    if body.rss_url is not None:
        source.rss_url = body.rss_url
    if body.source_type is not None:
        source.source_type = SourceType(body.source_type)
    if body.enabled is not None:
        source.enabled = body.enabled

    await db.commit()
    await db.refresh(source)
    return NewsSourceResponse.model_validate(source)


@router.delete(
    "/{source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a source (admin only)",
)
async def delete_source(
    source_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    source = (
        await db.execute(select(NewsSource).where(NewsSource.id == source_id))
    ).scalar_one_or_none()
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    await db.delete(source)
    await db.commit()
    logger.info("Source deleted", extra={"source_id": str(source_id)})
