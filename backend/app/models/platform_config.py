import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel

from app.models.user import get_datetime_utc


class PlatformConfigBase(SQLModel):
    devto_enabled: bool = Field(default=True)
    linkedin_enabled: bool = Field(default=True)
    devto_profile_url: str | None = Field(default=None, max_length=2048)
    linkedin_profile_url: str | None = Field(default=None, max_length=2048)


class PlatformConfig(PlatformConfigBase, table=True):
    __tablename__ = "platform_config"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key="user.id", unique=True, index=True, ondelete="CASCADE"
    )
    devto_api_key_encrypted: str | None = Field(default=None, max_length=2048)
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class PlatformConfigPublic(PlatformConfigBase):
    id: uuid.UUID
    has_devto_api_key: bool = False


class PlatformConfigUpdate(SQLModel):
    devto_enabled: bool | None = None
    linkedin_enabled: bool | None = None
    devto_profile_url: str | None = None
    linkedin_profile_url: str | None = None
    devto_api_key: str | None = Field(default=None, max_length=512)
