import enum
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class UserRole(str, enum.Enum):
    admin = "admin"
    user = "user"


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    microsoft_id: str | None = None
    username: str | None = None
    email: EmailStr
    name: str
    role: UserRole
    created_at: datetime
    last_login: datetime | None = None
