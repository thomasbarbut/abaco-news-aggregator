"""Sources API router (read-only for regular users)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.auth.dependencies import get_current_user
from app.models.news_source import NewsSource
from app.models.user import User
from app.schemas.source import NewsSourceResponse

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("", response_model=list[NewsSourceResponse])
async def list_sources(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[NewsSource]:
    """Return all enabled news sources."""
    result = await db.execute(
        select(NewsSource)
        .where(NewsSource.enabled.is_(True))
        .order_by(NewsSource.name.asc())
    )
    return list(result.scalars().all())
