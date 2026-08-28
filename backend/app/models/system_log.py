import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Column, DateTime
from sqlmodel import Field, SQLModel


class SystemLogBase(SQLModel):
    level: str = Field(index=True)
    message: str
    path: str | None = None
    method: str | None = None
    status_code: int | None = None
    user_id: uuid.UUID | None = None


class SystemLog(SystemLogBase, table=True):
    __tablename__: str = "system_log"  # type: ignore
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    stack_trace: str | None = None
    context: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class SystemLogPublic(SystemLogBase):
    id: uuid.UUID
    stack_trace: str | None = None
    created_at: datetime


class SystemLogsPublic(SQLModel):
    data: list[SystemLogPublic]
    count: int
