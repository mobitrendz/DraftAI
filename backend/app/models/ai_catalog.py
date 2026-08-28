import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import DateTime, Enum as SAEnum, JSON, LargeBinary
from sqlmodel import Column, Field, SQLModel

from app.models.user import get_datetime_utc


class AIModelModality(StrEnum):
    TEXT = "text"
    IMAGE = "image"
    EMBEDDING = "embedding"
    MULTIMODAL = "multimodal"


class AIProviderRow(SQLModel, table=True):
    """System catalog row (user_id NULL) or per-user BYOK binding."""

    __tablename__ = "ai_provider"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID | None = Field(
        default=None, foreign_key="user.id", ondelete="CASCADE", index=True
    )
    parent_provider_id: uuid.UUID | None = Field(
        default=None, foreign_key="ai_provider.id", ondelete="CASCADE"
    )

    slug: str = Field(max_length=64)
    display_name: str = Field(max_length=128)
    description: str | None = Field(default=None)

    base_url: str = Field(max_length=2048)
    api_adapter: str = Field(max_length=64)
    auth_style: str = Field(default="bearer", max_length=32)
    auth_header_name: str | None = Field(default=None, max_length=64)
    extra_headers: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )

    api_key_ciphertext: bytes | None = Field(
        default=None, sa_column=Column(LargeBinary, nullable=True)
    )
    api_key_iv: bytes | None = Field(
        default=None, sa_column=Column(LargeBinary, nullable=True)
    )
    api_key_tag: bytes | None = Field(
        default=None, sa_column=Column(LargeBinary, nullable=True)
    )

    is_active: bool = Field(default=True)
    sort_order: int = Field(default=0)

    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class AIModelRow(SQLModel, table=True):
    __tablename__ = "ai_model"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    provider_id: uuid.UUID = Field(foreign_key="ai_provider.id", ondelete="RESTRICT")

    model_key: str = Field(max_length=256)
    display_name: str = Field(max_length=128)
    description: str | None = Field(default=None)

    modality: AIModelModality = Field(
        default=AIModelModality.TEXT,
        sa_column=Column(
            SAEnum(
                AIModelModality,
                name="aimodelmodality",
                values_callable=lambda enum: [member.value for member in enum],
            ),
            nullable=False,
        ),
    )

    context_window_tokens: int | None = Field(default=None)
    max_output_tokens: int | None = Field(default=None)
    input_cost_per_million: float | None = Field(default=None)
    output_cost_per_million: float | None = Field(default=None)
    capabilities: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )

    is_active: bool = Field(default=True)
    is_default: bool = Field(default=False)
    sort_order: int = Field(default=0)

    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
