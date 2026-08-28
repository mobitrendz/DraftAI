import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import settings as settings_crud
from app.models.ai_agent_config import AIAgentConfigUpdate
from app.models.platform_config import PlatformConfigUpdate
from app.models.user import User


@pytest.mark.asyncio
async def test_get_or_create_platform_config(session: AsyncSession, isolated_user: User):
    config = await settings_crud.get_or_create_platform_config(
        session=session, user_id=isolated_user.id
    )
    assert config.user_id == isolated_user.id
    assert config.devto_enabled is True
    assert config.linkedin_enabled is True


@pytest.mark.asyncio
async def test_update_platform_config_encrypts_api_key(
    session: AsyncSession, isolated_user: User
):
    updated = await settings_crud.update_platform_config(
        session=session,
        user_id=isolated_user.id,
        update=PlatformConfigUpdate(
            devto_profile_url="https://dev.to/tester",
            devto_api_key="devto-secret-key",
        ),
    )
    assert updated.has_devto_api_key is True
    assert updated.devto_profile_url == "https://dev.to/tester"

    raw_config = await settings_crud.get_or_create_platform_config(
        session=session, user_id=isolated_user.id
    )
    assert raw_config.devto_api_key_encrypted is not None
    assert "devto-secret-key" not in raw_config.devto_api_key_encrypted
    assert settings_crud.get_devto_api_key(raw_config) == "devto-secret-key"


@pytest.mark.asyncio
async def test_clear_platform_api_key(session: AsyncSession, isolated_user: User):
    await settings_crud.update_platform_config(
        session=session,
        user_id=isolated_user.id,
        update=PlatformConfigUpdate(devto_api_key="temporary-key"),
    )
    cleared = await settings_crud.update_platform_config(
        session=session,
        user_id=isolated_user.id,
        update=PlatformConfigUpdate(devto_api_key=""),
    )
    assert cleared.has_devto_api_key is False


@pytest.mark.asyncio
async def test_get_or_create_ai_config(session: AsyncSession, isolated_user: User):
    config = await settings_crud.get_or_create_ai_config(
        session=session, user_id=isolated_user.id
    )
    assert config.user_id == isolated_user.id
    assert config.provider == "openai"
    assert config.model == "gpt-4o"


@pytest.mark.asyncio
async def test_update_ai_config_encrypts_keys(session: AsyncSession, isolated_user: User):
    updated = await settings_crud.update_ai_config(
        session=session,
        user_id=isolated_user.id,
        update=AIAgentConfigUpdate(
            provider_api_keys={"openai": "sk-openai-test", "anthropic": "sk-ant-test"},
            temperature=0.3,
            model="gpt-4o-mini",
        ),
    )
    assert updated.saved_api_keys["openai"] is True
    assert updated.saved_api_keys["anthropic"] is True
    assert updated.temperature == 0.3
    assert updated.model == "gpt-4o-mini"

    raw = await settings_crud.get_or_create_ai_config(
        session=session, user_id=isolated_user.id
    )
    assert (
        await settings_crud.get_provider_api_key(
            session=session, config=raw, provider_slug="openai"
        )
        == "sk-openai-test"
    )
    assert raw.openai_api_key_encrypted is None


@pytest.mark.asyncio
async def test_update_ai_config_encrypts_gemini_key(
    session: AsyncSession, isolated_user: User
):
    updated = await settings_crud.update_ai_config(
        session=session,
        user_id=isolated_user.id,
        update=AIAgentConfigUpdate(
            provider="gemini",
            model="gemini-2.0-flash",
            provider_api_keys={"gemini": "gemini-secret"},
        ),
    )
    assert updated.saved_api_keys["gemini"] is True
    assert updated.provider == "gemini"

    raw = await settings_crud.get_or_create_ai_config(
        session=session, user_id=isolated_user.id
    )
    assert (
        await settings_crud.get_provider_api_key(
            session=session, config=raw, provider_slug="gemini"
        )
        == "gemini-secret"
    )


@pytest.mark.asyncio
async def test_update_ai_config_encrypts_groq_key(
    session: AsyncSession, isolated_user: User
):
    updated = await settings_crud.update_ai_config(
        session=session,
        user_id=isolated_user.id,
        update=AIAgentConfigUpdate(
            provider="groq",
            provider_api_keys={"groq": "gsk-secret"},
        ),
    )
    assert updated.saved_api_keys["groq"] is True
    raw = await settings_crud.get_or_create_ai_config(
        session=session, user_id=isolated_user.id
    )
    assert (
        await settings_crud.get_provider_api_key(
            session=session, config=raw, provider_slug="groq"
        )
        == "gsk-secret"
    )


@pytest.mark.asyncio
async def test_settings_are_per_user(
    session: AsyncSession, normal_user: User, isolated_user: User
):
    await settings_crud.update_platform_config(
        session=session,
        user_id=normal_user.id,
        update=PlatformConfigUpdate(devto_enabled=False),
    )
    other = await settings_crud.get_platform_config_public(
        session=session, user_id=isolated_user.id
    )
    assert other.devto_enabled is True
