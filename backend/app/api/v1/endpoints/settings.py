from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query
import uuid

from app.api.deps import CurrentUser
from app.crud import ai_catalog
from app.crud import settings as settings_crud
from app.db.database import SessionDependency
from app.models.ai_agent_config import (
    AIAgentConfigPublic,
    AIAgentConfigUpdate,
    AIModelsCatalogPublic,
    CustomAIProviderCreate,
    CustomAIProviderPublic,
    ProviderModelsRefreshPublic,
)
from app.models.platform_config import PlatformConfigPublic, PlatformConfigUpdate

router = APIRouter()


@router.get("/platform", response_model=PlatformConfigPublic)
async def read_platform_config(
    session: SessionDependency, current_user: CurrentUser
) -> PlatformConfigPublic:
    return await settings_crud.get_platform_config_public(
        session=session, user_id=current_user.id
    )


@router.patch("/platform", response_model=PlatformConfigPublic)
async def update_platform_config(
    session: SessionDependency,
    current_user: CurrentUser,
    body: PlatformConfigUpdate,
) -> PlatformConfigPublic:
    return await settings_crud.update_platform_config(
        session=session, user_id=current_user.id, update=body
    )


@router.get("/ai/models", response_model=AIModelsCatalogPublic)
async def read_ai_models_catalog(
    session: SessionDependency,
    current_user: CurrentUser,
    ollama_base_url: str | None = Query(default=None, max_length=2048),
) -> AIModelsCatalogPublic:
    return await ai_catalog.get_models_catalog(
        session=session,
        user_id=current_user.id,
        ollama_base_url=ollama_base_url,
    )


@router.get("/ai", response_model=AIAgentConfigPublic)
async def read_ai_config(
    session: SessionDependency, current_user: CurrentUser
) -> AIAgentConfigPublic:
    return await settings_crud.get_ai_config_public(
        session=session, user_id=current_user.id
    )


@router.patch("/ai", response_model=AIAgentConfigPublic)
async def update_ai_config(
    session: SessionDependency,
    current_user: CurrentUser,
    body: AIAgentConfigUpdate,
) -> AIAgentConfigPublic:
    return await settings_crud.update_ai_config(
        session=session, user_id=current_user.id, update=body
    )


@router.post("/ai/providers", response_model=CustomAIProviderPublic)
async def create_custom_ai_provider(
    session: SessionDependency,
    current_user: CurrentUser,
    body: CustomAIProviderCreate,
) -> CustomAIProviderPublic:
    try:
        return await ai_catalog.create_custom_provider(
            session=session,
            user_id=current_user.id,
            data=body,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/ai/providers/{provider_id}", status_code=204)
async def delete_custom_ai_provider(
    session: SessionDependency,
    current_user: CurrentUser,
    provider_id: uuid.UUID,
) -> None:
    provider = await ai_catalog.get_user_custom_provider_by_id(
        session=session, user_id=current_user.id, provider_id=provider_id
    )
    if not provider:
        raise HTTPException(status_code=404, detail="Custom provider not found.")

    config = await settings_crud.get_or_create_ai_config(
        session=session, user_id=current_user.id
    )
    if config.provider == provider.slug:
        config.provider = "openai"
        config.model = "gpt-4o"
        config.updated_at = datetime.now(UTC)
        session.add(config)

    await session.delete(provider)
    await session.commit()


@router.post(
    "/ai/providers/{provider_slug}/refresh-models",
    response_model=ProviderModelsRefreshPublic,
)
async def refresh_provider_models(
    session: SessionDependency,
    current_user: CurrentUser,
    provider_slug: str,
    ollama_base_url: str | None = Query(default=None, max_length=2048),
) -> ProviderModelsRefreshPublic:
    try:
        return await ai_catalog.refresh_provider_models(
            session=session,
            user_id=current_user.id,
            provider_slug=provider_slug,
            ollama_base_url=ollama_base_url,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
