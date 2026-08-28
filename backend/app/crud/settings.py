import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.encryption import encrypt_secret
from app.crud import ai_catalog
from app.models.ai_agent_config import (
    AIAgentConfig,
    AIAgentConfigPublic,
    AIAgentConfigUpdate,
    FALLBACK_TEXT_MODEL,
)
from app.models.platform_config import (
    PlatformConfig,
    PlatformConfigPublic,
    PlatformConfigUpdate,
)

LEGACY_API_KEY_FIELDS: dict[str, str] = {
    "openai_api_key": "openai",
    "anthropic_api_key": "anthropic",
    "gemini_api_key": "gemini",
    "groq_api_key": "groq",
    "openrouter_api_key": "openrouter",
}


def _normalize_provider_slug(provider: str) -> str:
    return provider.lower()


async def _normalize_ai_config_provider(
    *, session: AsyncSession, config: AIAgentConfig
) -> None:
    normalized = _normalize_provider_slug(config.provider)
    if config.provider != normalized:
        config.provider = normalized
        session.add(config)
        await session.commit()
        await session.refresh(config)


def _platform_public(config: PlatformConfig) -> PlatformConfigPublic:
    return PlatformConfigPublic(
        id=config.id,
        devto_enabled=config.devto_enabled,
        linkedin_enabled=config.linkedin_enabled,
        devto_profile_url=config.devto_profile_url,
        linkedin_profile_url=config.linkedin_profile_url,
        has_devto_api_key=bool(config.devto_api_key_encrypted),
    )


async def get_or_create_platform_config(
    *, session: AsyncSession, user_id: uuid.UUID
) -> PlatformConfig:
    statement = select(PlatformConfig).where(PlatformConfig.user_id == user_id)
    result = await session.execute(statement)
    config = result.scalars().first()
    if config:
        return config
    config = PlatformConfig(user_id=user_id)
    session.add(config)
    await session.commit()
    await session.refresh(config)
    return config


async def get_platform_config_public(
    *, session: AsyncSession, user_id: uuid.UUID
) -> PlatformConfigPublic:
    config = await get_or_create_platform_config(session=session, user_id=user_id)
    return _platform_public(config)


async def update_platform_config(
    *, session: AsyncSession, user_id: uuid.UUID, update: PlatformConfigUpdate
) -> PlatformConfigPublic:
    config = await get_or_create_platform_config(session=session, user_id=user_id)
    data = update.model_dump(exclude_unset=True)
    api_key = data.pop("devto_api_key", None)
    for key, value in data.items():
        setattr(config, key, value)
    if api_key is not None:
        config.devto_api_key_encrypted = (
            encrypt_secret(api_key) if api_key else None
        )
    config.updated_at = datetime.now(UTC)
    session.add(config)
    await session.commit()
    await session.refresh(config)
    return _platform_public(config)


def get_devto_api_key(config: PlatformConfig) -> str | None:
    from app.core.encryption import decrypt_secret

    if not config.devto_api_key_encrypted:
        return None
    return decrypt_secret(config.devto_api_key_encrypted)


async def _ai_public(
    *, session: AsyncSession, config: AIAgentConfig
) -> AIAgentConfigPublic:
    return AIAgentConfigPublic(
        id=config.id,
        provider=config.provider,
        model=config.model,
        cover_image_model=config.cover_image_model,
        temperature=config.temperature,
        system_prompt=config.system_prompt,
        saved_api_keys=await ai_catalog.build_saved_api_keys(
            session=session, user_id=config.user_id, config=config
        ),
        ollama_base_url=await ai_catalog.get_user_ollama_base_url(
            session=session, user_id=config.user_id
        ),
    )


async def get_or_create_ai_config(
    *, session: AsyncSession, user_id: uuid.UUID
) -> AIAgentConfig:
    await ai_catalog.ensure_catalog_seeded(session=session)
    statement = select(AIAgentConfig).where(AIAgentConfig.user_id == user_id)
    result = await session.execute(statement)
    config = result.scalars().first()
    if config:
        await _normalize_ai_config_provider(session=session, config=config)
        await ai_catalog.sync_config_model_fks(session=session, config=config)
        return config

    catalog = await ai_catalog.get_models_catalog(session=session, user_id=user_id)
    default_provider = catalog.providers[0].slug if catalog.providers else "openai"
    default_model = (
        catalog.providers[0].default_model if catalog.providers else FALLBACK_TEXT_MODEL
    )
    config = AIAgentConfig(
        user_id=user_id,
        provider=default_provider,
        model=default_model,
        cover_image_model=catalog.default_cover_image_model,
    )
    session.add(config)
    await session.flush()
    await ai_catalog.sync_config_model_fks(session=session, config=config)
    await session.commit()
    await session.refresh(config)
    return config


async def get_ai_config_public(
    *, session: AsyncSession, user_id: uuid.UUID
) -> AIAgentConfigPublic:
    config = await get_or_create_ai_config(session=session, user_id=user_id)
    return await _ai_public(session=session, config=config)


def _merge_provider_api_keys(update: AIAgentConfigUpdate) -> dict[str, str]:
    merged: dict[str, str] = dict(update.provider_api_keys or {})
    data = update.model_dump(exclude_unset=True)
    for field, slug in LEGACY_API_KEY_FIELDS.items():
        if field in data:
            merged[slug] = data[field] or ""
    return merged


async def _resolve_model_after_provider_change(
    *,
    session: AsyncSession,
    user_id: uuid.UUID,
    provider_slug: str,
    model: str | None,
    current_model: str,
) -> str:
    if model is not None:
        return model
    catalog = await ai_catalog.get_models_catalog(session=session, user_id=user_id)
    entry = next((p for p in catalog.providers if p.slug == provider_slug), None)
    if not entry:
        return current_model
    known_models = {m.id for m in entry.models}
    if current_model not in known_models:
        return entry.default_model
    return current_model


async def update_ai_config(
    *, session: AsyncSession, user_id: uuid.UUID, update: AIAgentConfigUpdate
) -> AIAgentConfigPublic:
    config = await get_or_create_ai_config(session=session, user_id=user_id)
    data = update.model_dump(exclude_unset=True)
    provider_api_keys = _merge_provider_api_keys(update)
    ollama_base_url = data.pop("ollama_base_url", None)
    for field in (*LEGACY_API_KEY_FIELDS, "provider_api_keys"):
        data.pop(field, None)

    if "provider" in data and isinstance(data["provider"], str):
        data["provider"] = _normalize_provider_slug(data["provider"])

    if "provider" in data:
        valid_slugs = await ai_catalog.list_text_provider_slugs(
            session=session, user_id=user_id
        )
        if data["provider"] not in valid_slugs:
            raise HTTPException(
                status_code=400,
                detail=f"Provider '{data['provider']}' is not available.",
            )

    new_provider = data.get("provider", _normalize_provider_slug(config.provider))
    if "provider" in data and "model" not in data:
        data["model"] = await _resolve_model_after_provider_change(
            session=session,
            user_id=user_id,
            provider_slug=new_provider,
            model=None,
            current_model=config.model,
        )

    for key, value in data.items():
        setattr(config, key, value)

    for slug, key_value in provider_api_keys.items():
        await ai_catalog.upsert_user_api_key(
            session=session,
            user_id=user_id,
            provider_slug=slug,
            api_key=key_value or None,
        )
        legacy_column = ai_catalog.LEGACY_PROVIDER_KEY_COLUMNS.get(slug)
        if legacy_column:
            setattr(config, legacy_column, None)

    if ollama_base_url is not None:
        await ai_catalog.upsert_user_ollama_base_url(
            session=session,
            user_id=user_id,
            base_url=ollama_base_url or None,
        )

    config.text_model_id = await ai_catalog.resolve_text_model_id(
        session=session,
        provider_slug=_normalize_provider_slug(config.provider),
        model_key=config.model,
    )
    config.cover_model_id = await ai_catalog.resolve_cover_model_id(
        session=session, cover_image_model=config.cover_image_model
    )

    config.updated_at = datetime.now(UTC)
    session.add(config)
    await session.commit()
    await session.refresh(config)
    return await _ai_public(session=session, config=config)


async def get_provider_api_key(
    *, session: AsyncSession, config: AIAgentConfig, provider_slug: str
) -> str | None:
    legacy_column = ai_catalog.LEGACY_PROVIDER_KEY_COLUMNS.get(provider_slug)
    legacy_encrypted = getattr(config, legacy_column) if legacy_column else None
    return await ai_catalog.get_user_api_key(
        session=session,
        user_id=config.user_id,
        provider_slug=provider_slug,
        legacy_encrypted=legacy_encrypted,
    )
