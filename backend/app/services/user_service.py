"""User management service."""
from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.user import User, UserRole

logger = get_logger(__name__)


class UserService:
    """Encapsulates user management operations."""

    @staticmethod
    async def get_users(db: AsyncSession) -> list[User]:
        """Return all users ordered by creation date."""
        result = await db.execute(select(User).order_by(User.created_at.asc()))
        return list(result.scalars().all())

    @staticmethod
    async def update_role(
        db: AsyncSession,
        user_id: uuid.UUID,
        role: UserRole,
    ) -> User:
        """Update a user's role.

        Raises HTTP 404 if the user does not exist.
        """
        user = await db.get(User, user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found",
            )
        user.role = role
        await db.flush()
        await db.refresh(user)
        logger.info(
            "User role updated",
            extra={"user_id": str(user_id), "role": role.value},
        )
        return user
