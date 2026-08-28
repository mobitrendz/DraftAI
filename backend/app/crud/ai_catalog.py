import structlog
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.encryption import (
    decrypt_secret,
    decrypt_secret_aes,
    encrypt_secret_aes,
)
from app.core.config import settings
from app.models.ai_agent_config import (
    AIModelOption,
    AIModelsCatalogPublic,
    AIProviderCatalogPublic,
    AIProviderCredentialPublic,
    CoverImageModelOption,
    CustomAIProviderCreate,
    CustomAIProviderPublic,
    FALLBACK_COVER_IMAGE_MODEL,
    FALLBACK_TEXT_MODEL,
    FALLBACK_TEXT_PROVIDER,
    OllamaCatalogStatus,
    ProviderModelsRefreshPublic,
)
from app.models.ai_catalog import AIModelModality, AIModelRow, AIProviderRow
from app.services.ai.model_discovery import discover_provider_models
from app.services.ai.ollama import list_ollama_models, normalize_ollama_base_url

logger = structlog.get_logger(__name__)

SUPPORTED_COVER_KEY_PROVIDERS = frozenset({"openai", "gemini"})


def filter_cover_image_models_for_user(
    models: list[CoverImageModelOption],
    saved_api_keys: dict[str, bool],
) -> list[CoverImageModelOption]:
    return [
        model
        for model in models
        if model.key_provider in SUPPORTED_COVER_KEY_PROVIDERS
        and saved_api_keys.get(model.key_provider) is True
    ]

CUSTOM_PROVIDER_ADAPTER_CHOICES = frozenset({"openai_compatible", "ollama"})
CUSTOM_PROVIDER_AUTH_STYLES = frozenset({"bearer", "none", "api_key_header"})


def _is_suitable_for_draft_generation(
    *,
    context_window_tokens: int | None,
    allow_unknown_context: bool = False,
) -> bool:
    """Whether a text model has enough context for Create Content drafts."""
    if context_window_tokens is None:
        return allow_unknown_context
    return context_window_tokens >= settings.AI_MIN_TEXT_CONTEXT_WINDOW_TOKENS


def _model_row_to_option(row: AIModelRow) -> AIModelOption:
    return AIModelOption(
        id=row.model_key,
        label=row.display_name,
        description=row.description,
        context_window_tokens=row.context_window_tokens,
    )


def _filter_model_rows_for_draft_generation(
    rows: list[AIModelRow],
) -> list[AIModelRow]:
    return [
        row
        for row in rows
        if _is_suitable_for_draft_generation(
            context_window_tokens=row.context_window_tokens,
            allow_unknown_context=False,
        )
    ]


def _filter_model_options_for_draft_generation(
    models: list[AIModelOption],
    *,
    allow_unknown_context: bool = False,
) -> list[AIModelOption]:
    return [
        model
        for model in models
        if _is_suitable_for_draft_generation(
            context_window_tokens=model.context_window_tokens,
            allow_unknown_context=allow_unknown_context,
        )
    ]


def _default_model_key(rows: list[AIModelRow]) -> str:
    if not rows:
        return ""
    return next((row.model_key for row in rows if row.is_default), rows[0].model_key)


def _custom_provider_slug() -> str:
    return f"custom-{uuid.uuid4().hex[:12]}"


def _normalize_custom_base_url(*, base_url: str, api_adapter: str) -> str:
    url = base_url.strip().rstrip("/")
    if api_adapter == "ollama":
        return normalize_ollama_base_url(url)
    if not url.endswith("/v1"):
        url = f"{url}/v1"
    return url


async def list_user_custom_providers(
    *, session: AsyncSession, user_id: uuid.UUID
) -> list[AIProviderRow]:
    result = await session.execute(
        select(AIProviderRow)
        .where(
            AIProviderRow.user_id == user_id,
            AIProviderRow.parent_provider_id.is_(None),
            AIProviderRow.is_active.is_(True),
        )
        .order_by(AIProviderRow.created_at)
    )
    return list(result.scalars().all())


async def get_user_custom_provider(
    *, session: AsyncSession, user_id: uuid.UUID, provider_slug: str
) -> AIProviderRow | None:
    if not provider_slug.startswith("custom-"):
        return None
    result = await session.execute(
        select(AIProviderRow).where(
            AIProviderRow.user_id == user_id,
            AIProviderRow.parent_provider_id.is_(None),
            AIProviderRow.slug == provider_slug,
            AIProviderRow.is_active.is_(True),
        )
    )
    return result.scalars().first()


async def get_user_custom_provider_by_id(
    *, session: AsyncSession, user_id: uuid.UUID, provider_id: uuid.UUID
) -> AIProviderRow | None:
    result = await session.execute(
        select(AIProviderRow).where(
            AIProviderRow.id == provider_id,
            AIProviderRow.user_id == user_id,
            AIProviderRow.parent_provider_id.is_(None),
            AIProviderRow.is_active.is_(True),
        )
    )
    return result.scalars().first()


def _can_refresh_models(*, provider: AIProviderRow, has_api_key: bool) -> bool:
    if provider.slug == "ollama":
        return True
    if provider.user_id is not None and provider.parent_provider_id is None:
        return provider.api_adapter in ("ollama", "openai_compatible")
    if provider.api_adapter == "openai_compatible":
        return provider.auth_style == "none" or has_api_key
    if provider.api_adapter in ("gemini", "anthropic_messages"):
        return has_api_key
    return False


async def _list_system_text_model_options(
    *, session: AsyncSession, provider: AIProviderRow
) -> list[AIModelOption]:
    models_result = await session.execute(
        select(AIModelRow)
        .where(
            AIModelRow.provider_id == provider.id,
            AIModelRow.modality == AIModelModality.TEXT,
            AIModelRow.is_active.is_(True),
        )
        .order_by(AIModelRow.sort_order)
    )
    return [
        _model_row_to_option(row)
        for row in _filter_model_rows_for_draft_generation(
            list(models_result.scalars().all())
        )
    ]


async def _sync_discovered_text_models(
    *,
    session: AsyncSession,
    provider: AIProviderRow,
    discovered: list[AIModelOption],
) -> int:
    existing_result = await session.execute(
        select(AIModelRow.model_key, AIModelRow.sort_order).where(
            AIModelRow.provider_id == provider.id,
            AIModelRow.modality == AIModelModality.TEXT,
        )
    )
    rows = existing_result.all()
    existing_keys = {row[0] for row in rows}
    max_sort = max((row[1] for row in rows), default=0)
    added = 0
    for model in discovered:
        if model.id in existing_keys:
            continue
        added += 1
        session.add(
            AIModelRow(
                provider_id=provider.id,
                model_key=model.id,
                display_name=model.label[:128],
                description=model.description or "Discovered from provider API",
                modality=AIModelModality.TEXT,
                context_window_tokens=model.context_window_tokens,
                is_default=False,
                sort_order=max_sort + added * 10,
            )
        )
    if added:
        await session.commit()
    return added


async def refresh_provider_models(
    *,
    session: AsyncSession,
    user_id: uuid.UUID,
    provider_slug: str,
    ollama_base_url: str | None = None,
) -> ProviderModelsRefreshPublic:
    await ensure_catalog_seeded(session=session)

    custom = await get_user_custom_provider(
        session=session, user_id=user_id, provider_slug=provider_slug
    )
    system = await get_system_provider(session=session, slug=provider_slug)
    if custom:
        provider_row = custom
    elif system:
        provider_row = system
    else:
        raise ValueError(f"Unknown provider: {provider_slug}")

    legacy_column = LEGACY_PROVIDER_KEY_COLUMNS.get(provider_slug)
    legacy_encrypted = None
    if legacy_column and not custom:
        from app.models.ai_agent_config import AIAgentConfig

        config_result = await session.execute(
            select(AIAgentConfig).where(AIAgentConfig.user_id == user_id)
        )
        config = config_result.scalars().first()
        if config:
            legacy_encrypted = getattr(config, legacy_column, None)

    has_key = await user_has_api_key(
        session=session,
        user_id=user_id,
        provider_slug=provider_slug,
        legacy_encrypted=legacy_encrypted,
    )
    if custom and custom.api_key_ciphertext:
        has_key = True

    if not _can_refresh_models(provider=provider_row, has_api_key=has_key):
        raise ValueError("This provider does not support live model refresh.")

    if provider_slug == "ollama":
        previous_models = (
            await _build_ollama_provider_catalog(
                provider=provider_row,
                base_url=ollama_base_url
                or await get_user_ollama_base_url(session=session, user_id=user_id),
            )
        )[0].models
        base_url = ollama_base_url or await get_user_ollama_base_url(
            session=session, user_id=user_id
        )
        discovered = await discover_provider_models(
            base_url=base_url,
            api_adapter="ollama",
            api_key=None,
            auth_style="none",
        )
        added_count = sum(
            1 for model in discovered if model.id not in {m.id for m in previous_models}
        )
        message = (
            f"Added {added_count} new model(s)."
            if added_count
            else "Models are up to date."
        )
        return ProviderModelsRefreshPublic(
            slug=provider_slug,
            models=discovered,
            added_count=added_count,
            total_count=len(discovered),
            message=message,
        )

    if custom:
        api_key = _decrypt_binding(custom)
        previous_models = (
            await _build_live_provider_catalog(provider=custom, api_key=api_key)
        ).models
        discovered = await discover_provider_models(
            base_url=custom.base_url,
            api_adapter=custom.api_adapter,
            api_key=api_key,
            auth_style=custom.auth_style,
            auth_header_name=custom.auth_header_name,
        )
        added_count = sum(
            1 for model in discovered if model.id not in {m.id for m in previous_models}
        )
        message = (
            f"Added {added_count} new model(s)."
            if added_count
            else "Models are up to date."
        )
        return ProviderModelsRefreshPublic(
            slug=provider_slug,
            models=discovered,
            added_count=added_count,
            total_count=len(discovered),
            message=message,
        )

    if system.auth_style != "none" and not has_key:
        raise ValueError("Save an API key for this provider before refreshing models.")

    previous_models = await _list_system_text_model_options(session=session, provider=system)
    binding = await get_user_provider_binding(
        session=session, user_id=user_id, provider_slug=provider_slug
    )
    base_url = binding.base_url if binding and binding.base_url else system.base_url
    api_key = await get_user_api_key(
        session=session,
        user_id=user_id,
        provider_slug=provider_slug,
        legacy_encrypted=legacy_encrypted,
    )
    discovered = await discover_provider_models(
        base_url=base_url,
        api_adapter=system.api_adapter,
        api_key=api_key,
        auth_style=system.auth_style,
        auth_header_name=system.auth_header_name,
    )
    added_count = await _sync_discovered_text_models(
        session=session, provider=system, discovered=discovered
    )
    updated_models = await _list_system_text_model_options(session=session, provider=system)
    message = (
        f"Added {added_count} new model(s) to the catalog."
        if added_count
        else "Models are up to date."
    )
    return ProviderModelsRefreshPublic(
        slug=provider_slug,
        models=updated_models,
        added_count=added_count,
        total_count=len(updated_models),
        message=message,
    )


async def _build_live_provider_catalog(
    *,
    provider: AIProviderRow,
    api_key: str | None = None,
) -> AIProviderCatalogPublic:
    live_models: list[AIModelOption] = []
    try:
        live_models = await discover_provider_models(
            base_url=provider.base_url,
            api_adapter=provider.api_adapter,
            api_key=api_key,
            auth_style=provider.auth_style,
            auth_header_name=provider.auth_header_name,
        )
    except Exception as exc:
        logger.warning(
            "Failed to discover provider models",
            provider_slug=provider.slug,
            error=str(exc),
        )

    live_models = _filter_model_options_for_draft_generation(
        live_models,
        allow_unknown_context=True,
    )

    models_source = "ollama" if provider.api_adapter == "ollama" else "live"
    default_model = live_models[0].id if live_models else ""
    requires_api_key = provider.auth_style != "none"
    return AIProviderCatalogPublic(
        slug=provider.slug,
        label=provider.display_name,
        description=provider.description,
        default_model=default_model,
        models=live_models,
        requires_api_key=requires_api_key,
        auth_style=provider.auth_style,
        sort_order=provider.sort_order,
        models_source=models_source,
        provider_id=provider.id,
        is_custom=True,
        can_refresh_models=_can_refresh_models(
            provider=provider, has_api_key=bool(api_key) or provider.auth_style == "none"
        ),
    )


async def create_custom_provider(
    *,
    session: AsyncSession,
    user_id: uuid.UUID,
    data: CustomAIProviderCreate,
) -> CustomAIProviderPublic:
    if data.api_adapter not in CUSTOM_PROVIDER_ADAPTER_CHOICES:
        raise ValueError(
            f"Unsupported adapter '{data.api_adapter}'. "
            f"Choose one of: {', '.join(sorted(CUSTOM_PROVIDER_ADAPTER_CHOICES))}."
        )
    if data.auth_style not in CUSTOM_PROVIDER_AUTH_STYLES:
        raise ValueError(
            f"Unsupported auth style '{data.auth_style}'. "
            f"Choose one of: {', '.join(sorted(CUSTOM_PROVIDER_AUTH_STYLES))}."
        )
    if data.auth_style == "api_key_header" and not data.auth_header_name:
        raise ValueError("auth_header_name is required when auth_style is api_key_header.")
    if data.auth_style != "none" and not data.api_key:
        raise ValueError("API key is required for this auth style.")

    normalized_url = _normalize_custom_base_url(
        base_url=data.base_url,
        api_adapter=data.api_adapter,
    )

    ciphertext = iv = tag = None
    if data.api_key:
        ciphertext, iv, tag = encrypt_secret_aes(data.api_key)

    provider = AIProviderRow(
        user_id=user_id,
        parent_provider_id=None,
        slug=_custom_provider_slug(),
        display_name=data.display_name.strip(),
        description=data.description,
        base_url=normalized_url,
        api_adapter=data.api_adapter,
        auth_style=data.auth_style,
        auth_header_name=data.auth_header_name,
        api_key_ciphertext=ciphertext,
        api_key_iv=iv,
        api_key_tag=tag,
        sort_order=1000,
    )
    session.add(provider)
    await session.flush()

    try:
        await discover_provider_models(
            base_url=provider.base_url,
            api_adapter=provider.api_adapter,
            api_key=data.api_key,
            auth_style=provider.auth_style,
            auth_header_name=provider.auth_header_name,
        )
    except Exception as exc:
        await session.rollback()
        raise ValueError(
            "Could not list models from this provider. "
            "Check the base URL, API key, and adapter type."
        ) from exc

    await session.commit()
    await session.refresh(provider)
    return _custom_provider_public(provider)


async def delete_custom_provider(
    *, session: AsyncSession, user_id: uuid.UUID, provider_id: uuid.UUID
) -> None:
    provider = await get_user_custom_provider_by_id(
        session=session, user_id=user_id, provider_id=provider_id
    )
    if not provider:
        raise ValueError("Custom provider not found.")
    await session.delete(provider)
    await session.commit()


def _custom_provider_public(provider: AIProviderRow) -> CustomAIProviderPublic:
    has_key = bool(provider.api_key_ciphertext)
    return CustomAIProviderPublic(
        id=provider.id,
        slug=provider.slug,
        display_name=provider.display_name,
        description=provider.description,
        base_url=provider.base_url,
        api_adapter=provider.api_adapter,
        auth_style=provider.auth_style,
        requires_api_key=provider.auth_style != "none",
        has_api_key=has_key,
        models_source="ollama" if provider.api_adapter == "ollama" else "live",
    )


PROVIDER_SEEDS: list[dict] = [
    {
        "slug": "openai",
        "display_name": "OpenAI",
        "description": "GPT and DALL-E APIs",
        "base_url": "https://api.openai.com/v1",
        "api_adapter": "openai_compatible",
        "auth_style": "bearer",
        "auth_header_name": "Authorization",
        "sort_order": 10,
    },
    {
        "slug": "anthropic",
        "display_name": "Anthropic",
        "description": "Claude Messages API",
        "base_url": "https://api.anthropic.com/v1",
        "api_adapter": "anthropic_messages",
        "auth_style": "api_key_header",
        "auth_header_name": "x-api-key",
        "sort_order": 20,
    },
    {
        "slug": "gemini",
        "display_name": "Google Gemini",
        "description": "Gemini generative language API",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "api_adapter": "gemini",
        "auth_style": "query_param",
        "auth_header_name": None,
        "sort_order": 30,
    },
    {
        "slug": "groq",
        "display_name": "Groq",
        "description": "Groq OpenAI-compatible inference",
        "base_url": "https://api.groq.com/openai/v1",
        "api_adapter": "openai_compatible",
        "auth_style": "bearer",
        "auth_header_name": "Authorization",
        "sort_order": 40,
    },
    {
        "slug": "openrouter",
        "display_name": "OpenRouter",
        "description": "Multi-model OpenAI-compatible router",
        "base_url": "https://openrouter.ai/api/v1",
        "api_adapter": "openai_compatible",
        "auth_style": "bearer",
        "auth_header_name": "Authorization",
        "extra_headers": {
            "HTTP-Referer": "https://draftai.local",
            "X-Title": "DraftAI",
        },
        "sort_order": 50,
    },
    {
        "slug": "ollama",
        "display_name": "Ollama (local)",
        "description": "Local Ollama OpenAI-compatible server",
        "base_url": "http://localhost:11434/v1",
        "api_adapter": "openai_compatible",
        "auth_style": "none",
        "auth_header_name": None,
        "sort_order": 60,
    },
]

MODEL_SEEDS: list[dict] = [
    # OpenAI text
    {"provider_slug": "openai", "model_key": "gpt-4o", "display_name": "GPT-4o", "description": "Best overall quality", "modality": "text", "context_window_tokens": 128000, "input_cost_per_million": 2.5, "output_cost_per_million": 10.0, "capabilities": {"json_mode": True, "vision": True, "tools": True}, "is_default": True, "sort_order": 10},
    {"provider_slug": "openai", "model_key": "gpt-4o-mini", "display_name": "GPT-4o mini", "description": "Fast and cost-effective", "modality": "text", "context_window_tokens": 128000, "input_cost_per_million": 0.15, "output_cost_per_million": 0.6, "capabilities": {"json_mode": True, "vision": True, "tools": True}, "is_default": False, "sort_order": 20},
    {"provider_slug": "openai", "model_key": "gpt-4.1", "display_name": "GPT-4.1", "description": "Latest flagship", "modality": "text", "context_window_tokens": 128000, "capabilities": {"json_mode": True, "tools": True}, "is_default": False, "sort_order": 30},
    {"provider_slug": "openai", "model_key": "gpt-4.1-mini", "display_name": "GPT-4.1 mini", "description": "Smaller GPT-4.1 variant", "modality": "text", "context_window_tokens": 128000, "capabilities": {"json_mode": True}, "is_default": False, "sort_order": 40},
    {"provider_slug": "openai", "model_key": "o1", "display_name": "o1", "description": "Advanced reasoning", "modality": "text", "capabilities": {"reasoning": True}, "is_default": False, "sort_order": 50},
    {"provider_slug": "openai", "model_key": "o1-mini", "display_name": "o1 mini", "description": "Faster reasoning", "modality": "text", "capabilities": {"reasoning": True}, "is_default": False, "sort_order": 60},
    {"provider_slug": "openai", "model_key": "dall-e-3", "display_name": "DALL-E 3", "description": "Widescreen cover images", "modality": "image", "capabilities": {"aspect_ratios": ["1792x1024"]}, "is_default": False, "sort_order": 10},
    # Anthropic
    {"provider_slug": "anthropic", "model_key": "claude-3-5-sonnet-20241022", "display_name": "Claude 3.5 Sonnet", "description": "Balanced quality and speed", "modality": "text", "context_window_tokens": 200000, "input_cost_per_million": 3.0, "output_cost_per_million": 15.0, "capabilities": {"json_mode": True, "vision": True, "tools": True}, "is_default": True, "sort_order": 10},
    {"provider_slug": "anthropic", "model_key": "claude-3-5-haiku-20241022", "display_name": "Claude 3.5 Haiku", "description": "Fast and economical", "modality": "text", "context_window_tokens": 200000, "input_cost_per_million": 0.8, "output_cost_per_million": 4.0, "capabilities": {"json_mode": True, "vision": True}, "is_default": False, "sort_order": 20},
    {"provider_slug": "anthropic", "model_key": "claude-3-opus-20240229", "display_name": "Claude 3 Opus", "description": "Highest quality Claude 3", "modality": "text", "context_window_tokens": 200000, "capabilities": {"json_mode": True, "vision": True}, "is_default": False, "sort_order": 30},
    {"provider_slug": "anthropic", "model_key": "claude-sonnet-4-20250514", "display_name": "Claude Sonnet 4", "description": "Latest Sonnet generation", "modality": "text", "context_window_tokens": 200000, "capabilities": {"json_mode": True, "vision": True, "tools": True}, "is_default": False, "sort_order": 40},
    # Gemini text
    {"provider_slug": "gemini", "model_key": "gemini-2.0-flash", "display_name": "Gemini 2.0 Flash", "description": "Default — fast multimodal", "modality": "text", "context_window_tokens": 1000000, "capabilities": {"json_mode": True, "vision": True}, "is_default": True, "sort_order": 10},
    {"provider_slug": "gemini", "model_key": "gemini-2.5-flash", "display_name": "Gemini 2.5 Flash", "description": "Improved speed and quality", "modality": "text", "context_window_tokens": 1000000, "capabilities": {"json_mode": True, "vision": True}, "is_default": False, "sort_order": 20},
    {"provider_slug": "gemini", "model_key": "gemini-2.5-pro", "display_name": "Gemini 2.5 Pro", "description": "Best for complex writing", "modality": "text", "context_window_tokens": 1000000, "capabilities": {"json_mode": True, "vision": True, "tools": True}, "is_default": False, "sort_order": 30},
    {"provider_slug": "gemini", "model_key": "gemini-1.5-pro", "display_name": "Gemini 1.5 Pro", "description": "Long-context tasks", "modality": "text", "context_window_tokens": 1000000, "capabilities": {"json_mode": True, "vision": True}, "is_default": False, "sort_order": 40},
    # Gemini image
    {"provider_slug": "gemini", "model_key": "gemini-3-pro-image", "display_name": "Gemini 3 Pro Image (Nano Banana Pro)", "description": "Best quality — professional cover art", "modality": "image", "capabilities": {"aspect_ratios": ["16:9"]}, "is_default": False, "sort_order": 10},
    {"provider_slug": "gemini", "model_key": "gemini-3.1-flash-image", "display_name": "Gemini 3.1 Flash Image (Nano Banana 2)", "description": "Fast, high-volume image generation", "modality": "image", "capabilities": {"aspect_ratios": ["16:9"]}, "is_default": False, "sort_order": 20},
    {"provider_slug": "gemini", "model_key": "gemini-2.5-flash-image", "display_name": "Gemini 2.5 Flash Image (Nano Banana)", "description": "Default — efficient cover art", "modality": "image", "capabilities": {"aspect_ratios": ["16:9"]}, "is_default": True, "sort_order": 30},
    # Groq
    {"provider_slug": "groq", "model_key": "llama-3.3-70b-versatile", "display_name": "Llama 3.3 70B", "description": "Default — versatile", "modality": "text", "context_window_tokens": 128000, "capabilities": {"json_mode": True}, "is_default": True, "sort_order": 10},
    {"provider_slug": "groq", "model_key": "llama-3.1-8b-instant", "display_name": "Llama 3.1 8B Instant", "description": "Fastest responses", "modality": "text", "context_window_tokens": 128000, "capabilities": {"json_mode": True}, "is_default": False, "sort_order": 20},
    {"provider_slug": "groq", "model_key": "mixtral-8x7b-32768", "display_name": "Mixtral 8x7B", "description": "32K context MoE", "modality": "text", "context_window_tokens": 32768, "capabilities": {"json_mode": True}, "is_default": False, "sort_order": 30},
    {"provider_slug": "groq", "model_key": "gemma2-9b-it", "display_name": "Gemma 2 9B", "description": "Compact instruction-tuned", "modality": "text", "context_window_tokens": 8192, "capabilities": {"json_mode": True}, "is_default": False, "sort_order": 40},
    # OpenRouter
    {"provider_slug": "openrouter", "model_key": "meta-llama/llama-3.3-70b-instruct:free", "display_name": "Llama 3.3 70B (free)", "description": "Default free tier", "modality": "text", "context_window_tokens": 128000, "input_cost_per_million": 0, "output_cost_per_million": 0, "capabilities": {"json_mode": True}, "is_default": True, "sort_order": 10},
    {"provider_slug": "openrouter", "model_key": "google/gemini-2.0-flash-exp:free", "display_name": "Gemini 2.0 Flash (free)", "description": "Google via OpenRouter", "modality": "text", "capabilities": {"json_mode": True}, "is_default": False, "sort_order": 20},
    {"provider_slug": "openrouter", "model_key": "mistralai/mistral-7b-instruct:free", "display_name": "Mistral 7B (free)", "description": "Lightweight free model", "modality": "text", "capabilities": {"json_mode": True}, "is_default": False, "sort_order": 30},
    {"provider_slug": "openrouter", "model_key": "qwen/qwen-2.5-72b-instruct:free", "display_name": "Qwen 2.5 72B (free)", "description": "Strong free alternative", "modality": "text", "capabilities": {"json_mode": True}, "is_default": False, "sort_order": 40},
    {"provider_slug": "openrouter", "model_key": "deepseek/deepseek-r1:free", "display_name": "DeepSeek R1 (free)", "description": "Reasoning-focused free tier", "modality": "text", "capabilities": {"json_mode": True, "reasoning": True}, "is_default": False, "sort_order": 50},
]

LEGACY_PROVIDER_KEY_COLUMNS: dict[str, str] = {
    "openai": "openai_api_key_encrypted",
    "anthropic": "anthropic_api_key_encrypted",
    "gemini": "gemini_api_key_encrypted",
    "groq": "groq_api_key_encrypted",
    "openrouter": "openrouter_api_key_encrypted",
}


@dataclass(frozen=True)
class TextGenerationContext:
    provider_slug: str
    api_adapter: str
    base_url: str
    auth_style: str
    auth_header_name: str | None
    extra_headers: dict
    api_key: str
    model_key: str


async def ensure_catalog_seeded(*, session: AsyncSession) -> None:
    existing = (
        await session.execute(
            select(AIProviderRow.id).where(AIProviderRow.user_id.is_(None)).limit(1)
        )
    ).first()
    if existing:
        return

    slug_to_id: dict[str, uuid.UUID] = {}
    for seed in PROVIDER_SEEDS:
        row = AIProviderRow(
            slug=seed["slug"],
            display_name=seed["display_name"],
            description=seed.get("description"),
            base_url=seed["base_url"],
            api_adapter=seed["api_adapter"],
            auth_style=seed.get("auth_style", "bearer"),
            auth_header_name=seed.get("auth_header_name"),
            extra_headers=seed.get("extra_headers", {}),
            sort_order=seed.get("sort_order", 0),
        )
        session.add(row)
        await session.flush()
        slug_to_id[row.slug] = row.id

    for seed in MODEL_SEEDS:
        provider_id = slug_to_id[seed["provider_slug"]]
        session.add(
            AIModelRow(
                provider_id=provider_id,
                model_key=seed["model_key"],
                display_name=seed["display_name"],
                description=seed.get("description"),
                modality=AIModelModality(seed["modality"]),
                context_window_tokens=seed.get("context_window_tokens"),
                max_output_tokens=seed.get("max_output_tokens"),
                input_cost_per_million=seed.get("input_cost_per_million"),
                output_cost_per_million=seed.get("output_cost_per_million"),
                capabilities=seed.get("capabilities", {}),
                is_default=seed.get("is_default", False),
                sort_order=seed.get("sort_order", 0),
            )
        )
    await session.commit()


async def get_system_provider(
    *, session: AsyncSession, slug: str
) -> AIProviderRow | None:
    result = await session.execute(
        select(AIProviderRow).where(
            AIProviderRow.slug == slug,
            AIProviderRow.user_id.is_(None),
        )
    )
    return result.scalars().first()


async def get_model_by_key(
    *, session: AsyncSession, provider_slug: str, model_key: str
) -> AIModelRow | None:
    result = await session.execute(
        select(AIModelRow)
        .join(AIProviderRow, AIModelRow.provider_id == AIProviderRow.id)
        .where(
            AIProviderRow.slug == provider_slug,
            AIProviderRow.user_id.is_(None),
            AIModelRow.model_key == model_key,
            AIModelRow.is_active.is_(True),
        )
    )
    return result.scalars().first()


async def get_default_text_model(
    *, session: AsyncSession, provider_slug: str
) -> AIModelRow | None:
    result = await session.execute(
        select(AIModelRow)
        .join(AIProviderRow, AIModelRow.provider_id == AIProviderRow.id)
        .where(
            AIProviderRow.slug == provider_slug,
            AIProviderRow.user_id.is_(None),
            AIModelRow.modality == AIModelModality.TEXT,
            AIModelRow.is_default.is_(True),
            AIModelRow.is_active.is_(True),
        )
    )
    return result.scalars().first()


async def get_default_cover_model(*, session: AsyncSession) -> AIModelRow | None:
    result = await session.execute(
        select(AIModelRow)
        .join(AIProviderRow, AIModelRow.provider_id == AIProviderRow.id)
        .where(
            AIModelRow.modality == AIModelModality.IMAGE,
            AIModelRow.is_default.is_(True),
            AIModelRow.is_active.is_(True),
            AIProviderRow.user_id.is_(None),
        )
        .order_by(AIProviderRow.sort_order, AIModelRow.sort_order)
        .limit(1)
    )
    return result.scalars().first()


async def get_default_cover_image_model_key(*, session: AsyncSession) -> str:
    default_row = await get_default_cover_model(session=session)
    return default_row.model_key if default_row else FALLBACK_COVER_IMAGE_MODEL


async def get_image_model_meta(
    *, session: AsyncSession, model_key: str
) -> CoverImageModelOption | None:
    await ensure_catalog_seeded(session=session)
    result = await session.execute(
        select(AIModelRow, AIProviderRow)
        .join(AIProviderRow, AIModelRow.provider_id == AIProviderRow.id)
        .where(
            AIModelRow.model_key == model_key,
            AIModelRow.modality == AIModelModality.IMAGE,
            AIModelRow.is_active.is_(True),
            AIProviderRow.user_id.is_(None),
        )
        .limit(1)
    )
    row = result.first()
    if not row:
        return None
    model, provider = row
    return CoverImageModelOption(
        id=model.model_key,
        label=model.display_name,
        description=model.description,
        key_provider=provider.slug,
    )


async def get_user_ollama_base_url(
    *, session: AsyncSession, user_id: uuid.UUID | None
) -> str:
    await ensure_catalog_seeded(session=session)
    system = await get_system_provider(session=session, slug="ollama")
    fallback = settings.OLLAMA_BASE_URL or (
        system.base_url if system is not None else "http://localhost:11434/v1"
    )
    if user_id is None:
        return normalize_ollama_base_url(fallback)
    binding = await get_user_provider_binding(
        session=session, user_id=user_id, provider_slug="ollama"
    )
    if binding and binding.base_url:
        return normalize_ollama_base_url(binding.base_url)
    return normalize_ollama_base_url(fallback)


async def upsert_user_ollama_base_url(
    *, session: AsyncSession, user_id: uuid.UUID, base_url: str | None
) -> None:
    system = await get_system_provider(session=session, slug="ollama")
    if not system:
        return

    normalized = normalize_ollama_base_url(
        base_url
        or settings.OLLAMA_BASE_URL
        or (system.base_url if system else "http://localhost:11434/v1")
    )
    binding = await get_user_provider_binding(
        session=session, user_id=user_id, provider_slug="ollama"
    )
    if binding:
        binding.base_url = normalized
        binding.updated_at = datetime.now(UTC)
        session.add(binding)
        return

    session.add(
        AIProviderRow(
            user_id=user_id,
            parent_provider_id=system.id,
            slug=system.slug,
            display_name=system.display_name,
            description=system.description,
            base_url=normalized,
            api_adapter=system.api_adapter,
            auth_style=system.auth_style,
            auth_header_name=system.auth_header_name,
            extra_headers=system.extra_headers,
        )
    )


async def _build_ollama_provider_catalog(
    *, provider: AIProviderRow, base_url: str
) -> tuple[AIProviderCatalogPublic, OllamaCatalogStatus]:
    status = OllamaCatalogStatus(
        base_url=base_url,
        reachable=False,
        message=None,
        model_count=0,
    )
    live_models: list[AIModelOption] = []
    try:
        live_models = await list_ollama_models(base_url=base_url)
        live_models = _filter_model_options_for_draft_generation(
            live_models,
            allow_unknown_context=True,
        )
        status.reachable = True
        status.model_count = len(live_models)
        if not live_models:
            status.message = "Ollama is running but no models are installed yet."
    except Exception as exc:
        status.message = (
            "Could not reach Ollama. Ensure it is running and the base URL is correct."
        )
        logger.warning("Failed to list Ollama models", error=str(exc), base_url=base_url)

    default_model = live_models[0].id if live_models else ""
    return (
        AIProviderCatalogPublic(
            slug=provider.slug,
            label=provider.display_name,
            description=provider.description,
            default_model=default_model,
            models=live_models,
            requires_api_key=False,
            auth_style=provider.auth_style,
            sort_order=provider.sort_order,
            models_source="ollama",
            can_refresh_models=True,
        ),
        status,
    )


async def list_text_provider_slugs(
    *, session: AsyncSession, user_id: uuid.UUID | None = None
) -> set[str]:
    await ensure_catalog_seeded(session=session)
    result = await session.execute(
        select(AIProviderRow.slug)
        .join(AIModelRow, AIModelRow.provider_id == AIProviderRow.id)
        .where(
            AIProviderRow.user_id.is_(None),
            AIProviderRow.is_active.is_(True),
            AIModelRow.modality == AIModelModality.TEXT,
            AIModelRow.is_active.is_(True),
        )
        .distinct()
    )
    slugs = {row for row in result.scalars().all()}
    if await get_system_provider(session=session, slug="ollama"):
        slugs.add("ollama")
    if user_id is not None:
        custom_providers = await list_user_custom_providers(
            session=session, user_id=user_id
        )
        slugs.update(provider.slug for provider in custom_providers)
    return slugs


async def resolve_text_model_id(
    *,
    session: AsyncSession,
    provider_slug: str,
    model_key: str,
) -> uuid.UUID | None:
    row = await get_model_by_key(
        session=session, provider_slug=provider_slug, model_key=model_key
    )
    if row:
        return row.id
    default_row = await get_default_text_model(
        session=session, provider_slug=provider_slug
    )
    return default_row.id if default_row else None


async def resolve_cover_model_id(
    *, session: AsyncSession, cover_image_model: str
) -> uuid.UUID | None:
    for slug in ("gemini", "openai"):
        row = await get_model_by_key(
            session=session, provider_slug=slug, model_key=cover_image_model
        )
        if row:
            return row.id
    default_row = await get_default_cover_model(session=session)
    return default_row.id if default_row else None


async def sync_config_model_fks(
    *, session: AsyncSession, config: object
) -> None:
    from app.models.ai_agent_config import AIAgentConfig

    assert isinstance(config, AIAgentConfig)
    if not config.text_model_id:
        config.text_model_id = await resolve_text_model_id(
            session=session,
            provider_slug=config.provider.lower(),
            model_key=config.model,
        )
    if not config.cover_model_id:
        config.cover_model_id = await resolve_cover_model_id(
            session=session, cover_image_model=config.cover_image_model
        )


async def get_user_provider_binding(
    *, session: AsyncSession, user_id: uuid.UUID, provider_slug: str
) -> AIProviderRow | None:
    system = await get_system_provider(session=session, slug=provider_slug)
    if not system:
        return None
    result = await session.execute(
        select(AIProviderRow).where(
            AIProviderRow.user_id == user_id,
            AIProviderRow.parent_provider_id == system.id,
        )
    )
    return result.scalars().first()


def _decrypt_binding(binding: AIProviderRow) -> str | None:
    if (
        binding.api_key_ciphertext is None
        or binding.api_key_iv is None
        or binding.api_key_tag is None
    ):
        return None
    return decrypt_secret_aes(
        ciphertext=binding.api_key_ciphertext,
        iv=binding.api_key_iv,
        tag=binding.api_key_tag,
    )


async def get_user_api_key(
    *,
    session: AsyncSession,
    user_id: uuid.UUID,
    provider_slug: str,
    legacy_encrypted: str | None = None,
) -> str | None:
    custom = await get_user_custom_provider(
        session=session, user_id=user_id, provider_slug=provider_slug
    )
    if custom:
        key = _decrypt_binding(custom)
        if key:
            return key

    binding = await get_user_provider_binding(
        session=session, user_id=user_id, provider_slug=provider_slug
    )
    if binding:
        key = _decrypt_binding(binding)
        if key:
            return key
    if legacy_encrypted:
        return decrypt_secret(legacy_encrypted)
    return None


async def user_has_api_key(
    *,
    session: AsyncSession,
    user_id: uuid.UUID,
    provider_slug: str,
    legacy_encrypted: str | None = None,
) -> bool:
    custom = await get_user_custom_provider(
        session=session, user_id=user_id, provider_slug=provider_slug
    )
    if custom and custom.api_key_ciphertext:
        return True

    binding = await get_user_provider_binding(
        session=session, user_id=user_id, provider_slug=provider_slug
    )
    if binding and binding.api_key_ciphertext:
        return True
    return bool(legacy_encrypted)


async def upsert_user_api_key(
    *,
    session: AsyncSession,
    user_id: uuid.UUID,
    provider_slug: str,
    api_key: str | None,
) -> None:
    custom = await get_user_custom_provider(
        session=session, user_id=user_id, provider_slug=provider_slug
    )
    if custom:
        if not api_key:
            custom.api_key_ciphertext = None
            custom.api_key_iv = None
            custom.api_key_tag = None
        else:
            ciphertext, iv, tag = encrypt_secret_aes(api_key)
            custom.api_key_ciphertext = ciphertext
            custom.api_key_iv = iv
            custom.api_key_tag = tag
        custom.updated_at = datetime.now(UTC)
        session.add(custom)
        return

    system = await get_system_provider(session=session, slug=provider_slug)
    if not system:
        return

    binding = await get_user_provider_binding(
        session=session, user_id=user_id, provider_slug=provider_slug
    )

    if not api_key:
        if binding:
            await session.delete(binding)
        return

    ciphertext, iv, tag = encrypt_secret_aes(api_key)
    if binding:
        binding.api_key_ciphertext = ciphertext
        binding.api_key_iv = iv
        binding.api_key_tag = tag
        binding.updated_at = datetime.now(UTC)
        session.add(binding)
        return

    session.add(
        AIProviderRow(
            user_id=user_id,
            parent_provider_id=system.id,
            slug=system.slug,
            display_name=system.display_name,
            description=system.description,
            base_url=system.base_url,
            api_adapter=system.api_adapter,
            auth_style=system.auth_style,
            auth_header_name=system.auth_header_name,
            extra_headers=system.extra_headers,
            api_key_ciphertext=ciphertext,
            api_key_iv=iv,
            api_key_tag=tag,
        )
    )


async def get_models_catalog(
    *,
    session: AsyncSession,
    user_id: uuid.UUID | None = None,
    ollama_base_url: str | None = None,
) -> AIModelsCatalogPublic:
    await ensure_catalog_seeded(session=session)

    providers_result = await session.execute(
        select(AIProviderRow)
        .where(AIProviderRow.user_id.is_(None), AIProviderRow.is_active.is_(True))
        .order_by(AIProviderRow.sort_order)
    )
    system_providers = providers_result.scalars().all()

    catalog_providers: list[AIProviderCatalogPublic] = []
    credential_providers: list[AIProviderCredentialPublic] = []
    ollama_status: OllamaCatalogStatus | None = None

    resolved_ollama_url = (
        normalize_ollama_base_url(ollama_base_url)
        if ollama_base_url
        else await get_user_ollama_base_url(session=session, user_id=user_id)
    )

    user_config = None
    if user_id is not None:
        from app.models.ai_agent_config import AIAgentConfig

        config_result = await session.execute(
            select(AIAgentConfig).where(AIAgentConfig.user_id == user_id)
        )
        user_config = config_result.scalars().first()

    for provider in system_providers:
        requires_api_key = provider.auth_style != "none"
        legacy_column = LEGACY_PROVIDER_KEY_COLUMNS.get(provider.slug)
        legacy_encrypted = (
            getattr(user_config, legacy_column, None)
            if user_config and legacy_column
            else None
        )
        provider_has_key = (
            await user_has_api_key(
                session=session,
                user_id=user_id,
                provider_slug=provider.slug,
                legacy_encrypted=legacy_encrypted,
            )
            if user_id
            else False
        )
        can_refresh = _can_refresh_models(
            provider=provider, has_api_key=provider_has_key
        )
        credential_providers.append(
            AIProviderCredentialPublic(
                slug=provider.slug,
                label=provider.display_name,
                requires_api_key=requires_api_key,
                auth_style=provider.auth_style,
            )
        )

        if provider.slug == "ollama":
            ollama_provider, ollama_status = await _build_ollama_provider_catalog(
                provider=provider,
                base_url=resolved_ollama_url,
            )
            catalog_providers.append(ollama_provider)
            continue

        models_result = await session.execute(
            select(AIModelRow)
            .where(
                AIModelRow.provider_id == provider.id,
                AIModelRow.modality == AIModelModality.TEXT,
                AIModelRow.is_active.is_(True),
            )
            .order_by(AIModelRow.sort_order)
        )
        text_models = list(models_result.scalars().all())
        eligible_models = _filter_model_rows_for_draft_generation(text_models)
        if not eligible_models:
            continue

        default_model = _default_model_key(eligible_models)
        catalog_providers.append(
            AIProviderCatalogPublic(
                slug=provider.slug,
                label=provider.display_name,
                description=provider.description,
                default_model=default_model,
                models=[_model_row_to_option(m) for m in eligible_models],
                requires_api_key=requires_api_key,
                auth_style=provider.auth_style,
                sort_order=provider.sort_order,
                models_source="catalog",
                can_refresh_models=can_refresh,
            )
        )

    cover_result = await session.execute(
        select(AIModelRow, AIProviderRow)
        .join(AIProviderRow, AIModelRow.provider_id == AIProviderRow.id)
        .where(
            AIModelRow.modality == AIModelModality.IMAGE,
            AIModelRow.is_active.is_(True),
            AIProviderRow.user_id.is_(None),
        )
        .order_by(AIProviderRow.sort_order, AIModelRow.sort_order)
    )
    cover_rows = cover_result.all()
    cover_image_models = [
        CoverImageModelOption(
            id=model.model_key,
            label=model.display_name,
            description=model.description,
            key_provider=provider.slug,
        )
        for model, provider in cover_rows
    ]

    default_cover = await get_default_cover_image_model_key(session=session)

    if user_id is not None:
        if user_config is not None:
            saved_cover_keys = await build_saved_api_keys(
                session=session, user_id=user_id, config=user_config
            )
            cover_image_models = filter_cover_image_models_for_user(
                cover_image_models, saved_cover_keys
            )
        else:
            cover_image_models = []

        custom_providers = await list_user_custom_providers(
            session=session, user_id=user_id
        )
        for provider in custom_providers:
            api_key = _decrypt_binding(provider)
            catalog_entry = await _build_live_provider_catalog(
                provider=provider,
                api_key=api_key,
            )
            catalog_entry.can_refresh_models = _can_refresh_models(
                provider=provider,
                has_api_key=bool(api_key) or provider.auth_style == "none",
            )
            catalog_providers.append(catalog_entry)
            credential_providers.append(
                AIProviderCredentialPublic(
                    slug=provider.slug,
                    label=provider.display_name,
                    requires_api_key=provider.auth_style != "none",
                    auth_style=provider.auth_style,
                )
            )

    return AIModelsCatalogPublic(
        providers=catalog_providers,
        cover_image_models=cover_image_models,
        default_cover_image_model=default_cover,
        credential_providers=credential_providers,
        ollama=ollama_status,
    )


async def build_saved_api_keys(
    *, session: AsyncSession, user_id: uuid.UUID, config: object
) -> dict[str, bool]:
    from app.models.ai_agent_config import AIAgentConfig

    assert isinstance(config, AIAgentConfig)
    await ensure_catalog_seeded(session=session)
    providers_result = await session.execute(
        select(AIProviderRow).where(
            AIProviderRow.user_id.is_(None), AIProviderRow.is_active.is_(True)
        )
    )
    saved: dict[str, bool] = {}
    for provider in providers_result.scalars().all():
        legacy_column = LEGACY_PROVIDER_KEY_COLUMNS.get(provider.slug)
        legacy_encrypted = (
            getattr(config, legacy_column) if legacy_column else None
        )
        saved[provider.slug] = await user_has_api_key(
            session=session,
            user_id=user_id,
            provider_slug=provider.slug,
            legacy_encrypted=legacy_encrypted,
        )
    custom_providers = await list_user_custom_providers(
        session=session, user_id=user_id
    )
    for provider in custom_providers:
        saved[provider.slug] = bool(provider.api_key_ciphertext)
    return saved


async def resolve_text_generation(
    *,
    session: AsyncSession,
    user_id: uuid.UUID,
    provider_slug: str,
    model_key: str,
    legacy_encrypted: str | None,
) -> TextGenerationContext:
    await ensure_catalog_seeded(session=session)

    custom = await get_user_custom_provider(
        session=session, user_id=user_id, provider_slug=provider_slug
    )
    if custom:
        api_key = _decrypt_binding(custom) or ""
        if custom.auth_style != "none" and not api_key:
            api_key = ""
        return TextGenerationContext(
            provider_slug=provider_slug,
            api_adapter=custom.api_adapter,
            base_url=custom.base_url,
            auth_style=custom.auth_style,
            auth_header_name=custom.auth_header_name,
            extra_headers=dict(custom.extra_headers or {}),
            api_key=api_key,
            model_key=model_key,
        )

    system = await get_system_provider(session=session, slug=provider_slug)
    if not system:
        raise ValueError(f"Unknown provider: {provider_slug}")

    binding = await get_user_provider_binding(
        session=session, user_id=user_id, provider_slug=provider_slug
    )
    if provider_slug == "ollama":
        base_url = await get_user_ollama_base_url(session=session, user_id=user_id)
    else:
        base_url = binding.base_url if binding else system.base_url
    api_key = await get_user_api_key(
        session=session,
        user_id=user_id,
        provider_slug=provider_slug,
        legacy_encrypted=legacy_encrypted,
    )
    if not api_key and system.auth_style != "none":
        api_key = ""

    resolved_model = model_key
    if provider_slug != "ollama":
        model_row = await get_model_by_key(
            session=session, provider_slug=provider_slug, model_key=model_key
        )
        if not model_row:
            default_row = await get_default_text_model(
                session=session, provider_slug=provider_slug
            )
            if default_row:
                resolved_model = default_row.model_key

    return TextGenerationContext(
        provider_slug=provider_slug,
        api_adapter=system.api_adapter,
        base_url=base_url,
        auth_style=system.auth_style,
        auth_header_name=system.auth_header_name,
        extra_headers=dict(system.extra_headers or {}),
        api_key=api_key or "",
        model_key=resolved_model,
    )
