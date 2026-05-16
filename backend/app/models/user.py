import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserRole(str, enum.Enum):
    admin = "admin"
    user = "user"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # microsoft_id stays for legacy users (kept for migration safety); new
    # users use username + password_hash for username/password login.
    microsoft_id: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
        index=True,
    )
    username: Mapped[str | None] = mapped_column(
        String(64),
        unique=True,
        nullable=True,
        index=True,
    )
    password_hash: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    email: Mapped[str] = mapped_column(
        String(320),
        unique=True,
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="userrole", create_type=True),
        nullable=False,
        default=UserRole.user,
        server_default=UserRole.user.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User id={self.id} email={self.email!r} role={self.role}>"
