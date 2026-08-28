import uuid
from datetime import datetime

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel

from app.models.user import get_datetime_utc

# Fallbacks used only when the catalog is empty (should not happen in production).
FALLBACK_TEXT_PROVIDER = "openai"
FALLBACK_TEXT_MODEL = "gpt-4o"
FALLBACK_COVER_IMAGE_MODEL = "gemini-2.5-flash-image"


class AIModelOption(SQLModel):
    id: str
    label: str
    description: str | None = None
    context_window_tokens: int | None = None


class CoverImageModelOption(AIModelOption):
    key_provider: str = Field(
        description="Provider slug whose API key is required for this cover model"
    )


class AIProviderCredentialPublic(SQLModel):
    slug: str
    label: str
    requires_api_key: bool = True
    auth_style: str = "bearer"


class AIProviderCatalogPublic(SQLModel):
    slug: str
    label: str
    description: str | None = None
    default_model: str
    models: list[AIModelOption]
    requires_api_key: bool = True
    auth_style: str = "bearer"
    sort_order: int = 0
    models_source: str = Field(
        default="catalog",
        description="catalog = database seed; ollama/live = fetched from provider API",
    )
    provider_id: uuid.UUID | None = Field(
        default=None,
        description="Set for user-created custom providers",
    )
    is_custom: bool = False
    can_refresh_models: bool = False


class ProviderModelsRefreshPublic(SQLModel):
    slug: str
    models: list[AIModelOption]
    added_count: int = 0
    total_count: int = 0
    message: str | None = None


class CustomAIProviderCreate(SQLModel):
    display_name: str = Field(max_length=128)
    base_url: str = Field(max_length=2048)
    api_adapter: str = Field(
        default="openai_compatible",
        max_length=64,
        description="openai_compatible or ollama",
    )
    auth_style: str = Field(default="bearer", max_length=32)
    auth_header_name: str | None = Field(default=None, max_length=64)
    api_key: str | None = Field(default=None, max_length=512)
    description: str | None = Field(default=None, max_length=512)


class CustomAIProviderPublic(SQLModel):
    id: uuid.UUID
    slug: str
    display_name: str
    description: str | None = None
    base_url: str
    api_adapter: str
    auth_style: str
    requires_api_key: bool
    has_api_key: bool
    models_source: str = "live"


class OllamaCatalogStatus(SQLModel):
    base_url: str
    reachable: bool
    message: str | None = None
    model_count: int = 0


class AIModelsCatalogPublic(SQLModel):
    providers: list[AIProviderCatalogPublic]
    cover_image_models: list[CoverImageModelOption]
    default_cover_image_model: str
    credential_providers: list[AIProviderCredentialPublic]
    ollama: OllamaCatalogStatus | None = None


class AIAgentConfigBase(SQLModel):
    provider: str = Field(default=FALLBACK_TEXT_PROVIDER, max_length=64)
    model: str = Field(default=FALLBACK_TEXT_MODEL, max_length=128)
    cover_image_model: str = Field(
        default=FALLBACK_COVER_IMAGE_MODEL, max_length=128
    )
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    system_prompt: str | None = Field(default=None, max_length=8000)


class AIAgentConfig(AIAgentConfigBase, table=True):
    __tablename__ = "ai_agent_config"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key="user.id", unique=True, index=True, ondelete="CASCADE"
    )
    text_model_id: uuid.UUID | None = Field(
        default=None, foreign_key="ai_model.id", ondelete="SET NULL"
    )
    cover_model_id: uuid.UUID | None = Field(
        default=None, foreign_key="ai_model.id", ondelete="SET NULL"
    )
    openai_api_key_encrypted: str | None = Field(default=None, max_length=2048)
    anthropic_api_key_encrypted: str | None = Field(default=None, max_length=2048)
    gemini_api_key_encrypted: str | None = Field(default=None, max_length=2048)
    groq_api_key_encrypted: str | None = Field(default=None, max_length=2048)
    openrouter_api_key_encrypted: str | None = Field(default=None, max_length=2048)
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class AIAgentConfigPublic(AIAgentConfigBase):
    id: uuid.UUID
    saved_api_keys: dict[str, bool] = Field(default_factory=dict)
    ollama_base_url: str | None = None


class AIAgentConfigUpdate(SQLModel):
    provider: str | None = Field(default=None, max_length=64)
    model: str | None = Field(default=None, max_length=128)
    cover_image_model: str | None = Field(default=None, max_length=128)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    system_prompt: str | None = Field(default=None, max_length=8000)
    ollama_base_url: str | None = Field(default=None, max_length=2048)
    provider_api_keys: dict[str, str] | None = None
    # Deprecated — merged into provider_api_keys on update
    openai_api_key: str | None = Field(default=None, max_length=512)
    anthropic_api_key: str | None = Field(default=None, max_length=512)
    gemini_api_key: str | None = Field(default=None, max_length=512)
    groq_api_key: str | None = Field(default=None, max_length=512)
    openrouter_api_key: str | None = Field(default=None, max_length=512)
