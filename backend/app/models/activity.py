import uuid
from datetime import datetime
from typing import ClassVar

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel

from app.models.user import get_datetime_utc


class UserActivityBase(SQLModel):
    method: str = Field(max_length=10)
    path: str = Field(max_length=255)
    status_code: int
    ip_address: str | None = Field(default=None, max_length=45)
    user_agent: str | None = Field(default=None, max_length=1000)


class UserActivity(UserActivityBase, table=True):
    __tablename__: ClassVar[str] = "user_activity"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID | None = Field(
        default=None, foreign_key="user.id", index=True, ondelete="SET NULL"
    )
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class UserActivityPublic(UserActivityBase):
    id: uuid.UUID
    user_id: uuid.UUID | None
    created_at: datetime


class UserActivitiesPublic(SQLModel):
    data: list[UserActivityPublic]
    count: int
