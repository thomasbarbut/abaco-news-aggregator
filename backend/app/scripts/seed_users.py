"""Seed local username/password users.

Usage:
    python -m app.scripts.seed_users

Idempotent — if a user with the given username exists, the password is
updated (so re-running rotates the password to what's in this script).
"""
import asyncio

import bcrypt
from sqlalchemy import func, select

from app.core.database import AsyncSessionLocal
from app.models.user import User, UserRole


# (username, email, name, role, password)
SEED_USERS = [
    ("thomas", "thomas@abaco.local", "Thomas",   UserRole.admin, "tuberozelor123"),
    ("alex",   "alex@abaco.local",   "Alex",     UserRole.admin, "horea123"),
]


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        for username, email, name, role, password in SEED_USERS:
            stmt = select(User).where(func.lower(User.username) == username.lower())
            existing = (await db.execute(stmt)).scalar_one_or_none()
            pwd_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")
            if existing is None:
                u = User(
                    username=username,
                    email=email,
                    name=name,
                    role=role,
                    password_hash=pwd_hash,
                )
                db.add(u)
                action = "Created"
            else:
                existing.password_hash = pwd_hash
                existing.role = role
                existing.name = name
                action = "Updated"
            print(f"  {action}: {username} (role={role.value})")
        await db.commit()
    print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())
