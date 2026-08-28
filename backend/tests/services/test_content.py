import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import settings as settings_crud
from app.models.ai_agent_config import AIAgentConfigUpdate
from app.models.content import (
    ContentDraft,
    ContentDraftStatus,
    CoverImage,
    DevtoArticle,
    GenerateDraftRequest,
    LinkedinPost,
    UpdateDraftRequest,
)
from app.models.platform_config import PlatformConfigUpdate
from app.models.user import User
from app.services import content as content_service

from app.services.ai.images import GeneratedCoverImage

MOCK_AI_RESPONSE = {
    "devto_title": "Test Article Title",
    "devto_body_markdown": "# Hello\n\nThis is test content.",
    "devto_tags": "python,fastapi",
    "linkedin_teaser": "Check out this new article on FastAPI!",
    "cover_image_prompt": "Abstract tech illustration",
}

MOCK_IMAGE_BYTES = b"\x89PNG\r\n\x1a\nfake-image"


def _mock_ai_and_images():
    return (
        patch(
            "app.services.content.generate_json_content",
            new_callable=AsyncMock,
            return_value=MOCK_AI_RESPONSE,
        ),
        patch(
            "app.services.content.generate_cover_image",
            new_callable=AsyncMock,
            return_value=GeneratedCoverImage(
                data=MOCK_IMAGE_BYTES,
                provider="openai-dall-e-3",
                content_type="image/png",
            ),
        ),
        patch(
            "app.services.content.storage.upload_bytes",
            return_value="covers/test/shared.png",
        ),
        patch(
            "app.services.content.storage.get_presigned_url",
            return_value="http://localhost:9000/presigned-url",
        ),
    )


@pytest.mark.asyncio
async def test_list_drafts_empty(session: AsyncSession, isolated_user: User):
    result = await content_service.list_drafts(
        session=session, user_id=isolated_user.id
    )
    assert result.count == 0
    assert result.data == []


@pytest.mark.asyncio
async def test_generate_draft_creates_assets(
    session: AsyncSession, normal_user: User
):
    ai_patch, image_patch, upload_patch, url_patch = _mock_ai_and_images()
    with ai_patch as mock_ai, image_patch, upload_patch as mock_upload, url_patch:
        await settings_crud.update_ai_config(
            session=session,
            user_id=normal_user.id,
            update=AIAgentConfigUpdate(
                provider="openai",
                openai_api_key="sk-test",
                cover_image_model="dall-e-3",
            ),
        )
        await settings_crud.update_platform_config(
            session=session,
            user_id=normal_user.id,
            update=PlatformConfigUpdate(devto_enabled=True, linkedin_enabled=True),
        )

        detail = await content_service.generate_draft(
            session=session,
            user_id=normal_user.id,
            request=GenerateDraftRequest(
                topic="Async APIs with FastAPI",
                user_prompt="Keep examples concise",
            ),
        )

        mock_ai.assert_called_once()
        assert mock_upload.call_count == 2
        assert detail.topic == "Async APIs with FastAPI"
        assert detail.status == ContentDraftStatus.DRAFT
        assert detail.devto_article is not None
        assert detail.devto_article.title == "Test Article Title"
        assert detail.linkedin_post is not None
        assert detail.linkedin_post.teaser_text == "Check out this new article on FastAPI!"
        assert len(detail.cover_images) == 2
        assert all(c.storage_key for c in detail.cover_images)
        assert all(c.provider == "openai-dall-e-3" for c in detail.cover_images)


@pytest.mark.asyncio
async def test_generate_draft_respects_disabled_platforms(
    session: AsyncSession, normal_user: User
):
    ai_patch, image_patch, upload_patch, url_patch = _mock_ai_and_images()
    with ai_patch as mock_ai, image_patch, upload_patch, url_patch:
        await settings_crud.update_ai_config(
            session=session,
            user_id=normal_user.id,
            update=AIAgentConfigUpdate(
                provider="openai",
                openai_api_key="sk-test",
                cover_image_model="dall-e-3",
            ),
        )
        await settings_crud.update_platform_config(
            session=session,
            user_id=normal_user.id,
            update=PlatformConfigUpdate(devto_enabled=False, linkedin_enabled=True),
        )

        detail = await content_service.generate_draft(
            session=session,
            user_id=normal_user.id,
            request=GenerateDraftRequest(topic="LinkedIn only topic"),
        )

        assert detail.devto_article is None
        assert detail.linkedin_post is not None
        assert len(detail.cover_images) == 1
        mock_ai.assert_called_once()


@pytest.mark.asyncio
async def test_generate_draft_with_ollama_no_api_key(
    session: AsyncSession, isolated_user: User
):
    ai_patch, image_patch, upload_patch, url_patch = _mock_ai_and_images()
    with ai_patch as mock_ai, image_patch, upload_patch, url_patch:
        await settings_crud.update_ai_config(
            session=session,
            user_id=isolated_user.id,
            update=AIAgentConfigUpdate(
                provider="ollama",
                model="qwen3:8b",
                ollama_base_url="http://localhost:11434/v1",
            ),
        )
        await settings_crud.update_platform_config(
            session=session,
            user_id=isolated_user.id,
            update=PlatformConfigUpdate(devto_enabled=True, linkedin_enabled=False),
        )

        detail = await content_service.generate_draft(
            session=session,
            user_id=isolated_user.id,
            request=GenerateDraftRequest(topic="Local Ollama topic"),
        )

        mock_ai.assert_called_once()
        assert mock_ai.call_args.kwargs["auth_style"] == "none"
        assert mock_ai.call_args.kwargs["api_key"] == ""
        assert mock_ai.call_args.kwargs["provider_label"] == "ollama"
        assert detail.topic == "Local Ollama topic"


@pytest.mark.asyncio
async def test_generate_draft_requires_openai_key(
    session: AsyncSession, isolated_user: User
):
    with pytest.raises(HTTPException) as exc_info:
        await content_service.generate_draft(
            session=session,
            user_id=isolated_user.id,
            request=GenerateDraftRequest(topic="No key topic"),
        )
    assert exc_info.value.status_code == 400
    assert "OpenAI API key required" in exc_info.value.detail


@pytest.mark.asyncio
async def test_generate_draft_with_anthropic(
    session: AsyncSession, normal_user: User
):
    ai_patch, image_patch, upload_patch, url_patch = _mock_ai_and_images()
    with ai_patch as mock_ai, image_patch, upload_patch, url_patch:
        await settings_crud.update_ai_config(
            session=session,
            user_id=normal_user.id,
            update=AIAgentConfigUpdate(
                provider="anthropic",
                anthropic_api_key="sk-ant-test",
            ),
        )

        detail = await content_service.generate_draft(
            session=session,
            user_id=normal_user.id,
            request=GenerateDraftRequest(topic="Anthropic topic"),
        )

        mock_ai.assert_called_once()
        assert mock_ai.call_args.kwargs["api_adapter"] == "anthropic_messages"
        assert mock_ai.call_args.kwargs["provider_label"] == "anthropic"
        assert detail.topic == "Anthropic topic"


@pytest.mark.asyncio
async def test_generate_draft_with_gemini(
    session: AsyncSession, normal_user: User
):
    ai_patch, image_patch, upload_patch, url_patch = _mock_ai_and_images()
    with ai_patch as mock_ai, image_patch, upload_patch, url_patch:
        await settings_crud.update_ai_config(
            session=session,
            user_id=normal_user.id,
            update=AIAgentConfigUpdate(
                provider="gemini",
                model="gemini-2.0-flash",
                gemini_api_key="gemini-test-key",
            ),
        )
        await settings_crud.update_platform_config(
            session=session,
            user_id=normal_user.id,
            update=PlatformConfigUpdate(devto_enabled=True, linkedin_enabled=True),
        )

        detail = await content_service.generate_draft(
            session=session,
            user_id=normal_user.id,
            request=GenerateDraftRequest(topic="Gemini generated topic"),
        )

        mock_ai.assert_called_once()
        assert mock_ai.call_args.kwargs["api_adapter"] == "gemini"
        assert mock_ai.call_args.kwargs["provider_label"] == "gemini"
        assert detail.topic == "Gemini generated topic"
        assert detail.devto_article is not None


@pytest.mark.asyncio
async def test_generate_draft_fills_missing_linkedin_teaser(
    session: AsyncSession, normal_user: User,
):
    ai_patch, image_patch, upload_patch, url_patch = _mock_ai_and_images()
    partial_response = {
        **MOCK_AI_RESPONSE,
        "linkedin_teaser": "",
    }
    with ai_patch as mock_ai, image_patch, upload_patch, url_patch:
        mock_ai.return_value = partial_response
        await settings_crud.update_ai_config(
            session=session,
            user_id=normal_user.id,
            update=AIAgentConfigUpdate(
                provider="gemini",
                model="gemini-2.5-flash",
                gemini_api_key="gemini-test-key",
            ),
        )
        await settings_crud.update_platform_config(
            session=session,
            user_id=normal_user.id,
            update=PlatformConfigUpdate(devto_enabled=True, linkedin_enabled=True),
        )

        detail = await content_service.generate_draft(
            session=session,
            user_id=normal_user.id,
            request=GenerateDraftRequest(topic="Gemini teaser fallback"),
        )

        assert detail.linkedin_post is not None
        assert detail.linkedin_post.teaser_text.startswith(
            "Just published: Test Article Title"
        )


def test_normalize_generated_draft_maps_camel_case():
    normalized = content_service._normalize_generated_draft(
        {
            "devtoTitle": "My Article",
            "devtoBodyMarkdown": "# Hello",
            "devtoTags": "ai",
            "linkedinTeaser": "Read this on DEV.to",
        },
        topic="Fallback topic",
    )
    assert normalized["devto_title"] == "My Article"
    assert normalized["linkedin_teaser"] == "Read this on DEV.to"


@pytest.mark.asyncio
async def test_generate_draft_with_groq(
    session: AsyncSession, normal_user: User
):
    ai_patch, image_patch, upload_patch, url_patch = _mock_ai_and_images()
    with ai_patch as mock_ai, image_patch, upload_patch, url_patch:
        await settings_crud.update_ai_config(
            session=session,
            user_id=normal_user.id,
            update=AIAgentConfigUpdate(
                provider="groq",
                model="llama-3.3-70b-versatile",
                groq_api_key="gsk-test",
            ),
        )

        detail = await content_service.generate_draft(
            session=session,
            user_id=normal_user.id,
            request=GenerateDraftRequest(topic="Groq topic"),
        )

        mock_ai.assert_called_once()
        assert mock_ai.call_args.kwargs["api_adapter"] == "openai_compatible"
        assert mock_ai.call_args.kwargs["provider_label"] == "groq"
        assert detail.topic == "Groq topic"


@pytest.mark.asyncio
async def test_generate_draft_with_openrouter(
    session: AsyncSession, normal_user: User
):
    ai_patch, image_patch, upload_patch, url_patch = _mock_ai_and_images()
    with ai_patch as mock_ai, image_patch, upload_patch, url_patch:
        await settings_crud.update_ai_config(
            session=session,
            user_id=normal_user.id,
            update=AIAgentConfigUpdate(
                provider="openrouter",
                model="meta-llama/llama-3.3-70b-instruct:free",
                openrouter_api_key="sk-or-test",
            ),
        )

        detail = await content_service.generate_draft(
            session=session,
            user_id=normal_user.id,
            request=GenerateDraftRequest(topic="OpenRouter topic"),
        )

        mock_ai.assert_called_once()
        assert mock_ai.call_args.kwargs["api_adapter"] == "openai_compatible"
        assert mock_ai.call_args.kwargs["provider_label"] == "openrouter"
        assert detail.topic == "OpenRouter topic"


@pytest.mark.asyncio
async def test_generate_draft_prefers_gemini_for_cover_images(
    session: AsyncSession, isolated_user: User
):
    ai_patch, image_patch, upload_patch, url_patch = _mock_ai_and_images()
    with ai_patch, image_patch as mock_image, upload_patch, url_patch:
        mock_image.return_value = GeneratedCoverImage(
            data=MOCK_IMAGE_BYTES,
            provider="google-gemini-3-pro-image",
            content_type="image/png",
        )
        await settings_crud.update_ai_config(
            session=session,
            user_id=isolated_user.id,
            update=AIAgentConfigUpdate(
                provider="gemini",
                gemini_api_key="gemini-test-key",
                openai_api_key="sk-test",
            ),
        )
        await settings_crud.update_platform_config(
            session=session,
            user_id=isolated_user.id,
            update=PlatformConfigUpdate(devto_enabled=True, linkedin_enabled=True),
        )

        detail = await content_service.generate_draft(
            session=session,
            user_id=isolated_user.id,
            request=GenerateDraftRequest(topic="Gemini cover topic"),
        )

        mock_image.assert_called()
        assert mock_image.call_count == 2
        assert mock_image.call_args.kwargs["provider_api_keys"]["gemini"] == "gemini-test-key"
        assert mock_image.call_args.kwargs["cover_image_model"] == "gemini-2.5-flash-image"
        assert len(detail.cover_images) == 2
        assert all(
            c.provider == "google-gemini-3-pro-image" for c in detail.cover_images
        )


@pytest.mark.asyncio
async def test_generate_draft_uses_template_cover_without_image_keys(
    session: AsyncSession, isolated_user: User
):
    ai_patch, image_patch, upload_patch, url_patch = _mock_ai_and_images()
    with ai_patch, image_patch as mock_image, upload_patch as mock_upload, url_patch:
        await settings_crud.update_ai_config(
            session=session,
            user_id=isolated_user.id,
            update=AIAgentConfigUpdate(
                provider="groq",
                groq_api_key="gsk-test",
            ),
        )
        await settings_crud.update_platform_config(
            session=session,
            user_id=isolated_user.id,
            update=PlatformConfigUpdate(devto_enabled=True, linkedin_enabled=True),
        )

        detail = await content_service.generate_draft(
            session=session,
            user_id=isolated_user.id,
            request=GenerateDraftRequest(topic="No image API keys"),
        )

        mock_image.assert_not_called()
        assert mock_upload.call_count == 2
        assert len(detail.cover_images) == 2
        assert all(c.storage_key for c in detail.cover_images)
        assert all(c.provider == "pillow-template" for c in detail.cover_images)
        assert detail.cover_image_warning is not None
        assert "template cover image" in detail.cover_image_warning.lower()


@pytest.mark.asyncio
async def test_generate_draft_uses_template_cover_when_api_fails(
    session: AsyncSession, isolated_user: User
):
    ai_patch, image_patch, upload_patch, url_patch = _mock_ai_and_images()
    with ai_patch, image_patch as mock_image, upload_patch as mock_upload, url_patch:
        mock_image.side_effect = HTTPException(
            status_code=502,
            detail="Cover image quota exceeded.",
        )
        await settings_crud.update_ai_config(
            session=session,
            user_id=isolated_user.id,
            update=AIAgentConfigUpdate(
                provider="gemini",
                gemini_api_key="gemini-test-key",
            ),
        )
        await settings_crud.update_platform_config(
            session=session,
            user_id=isolated_user.id,
            update=PlatformConfigUpdate(devto_enabled=True, linkedin_enabled=True),
        )

        detail = await content_service.generate_draft(
            session=session,
            user_id=isolated_user.id,
            request=GenerateDraftRequest(topic="API cover failure"),
        )

        mock_image.assert_called()
        assert mock_image.call_count == 2
        assert all(c.provider == "pillow-template" for c in detail.cover_images)
        assert detail.cover_image_warning is not None
        assert "quota exceeded" in detail.cover_image_warning.lower()
        assert "template cover image" in detail.cover_image_warning.lower()


@pytest.mark.asyncio
async def test_generate_draft_skips_images_when_template_fallback_disabled(
    session: AsyncSession, isolated_user: User, monkeypatch
):
    monkeypatch.setattr(
        "app.services.content.settings.COVER_TEMPLATE_FALLBACK_ENABLED",
        False,
    )
    ai_patch, image_patch, upload_patch, url_patch = _mock_ai_and_images()
    with ai_patch, image_patch as mock_image, upload_patch as mock_upload, url_patch:
        await settings_crud.update_ai_config(
            session=session,
            user_id=isolated_user.id,
            update=AIAgentConfigUpdate(
                provider="groq",
                groq_api_key="gsk-test",
            ),
        )
        await settings_crud.update_platform_config(
            session=session,
            user_id=isolated_user.id,
            update=PlatformConfigUpdate(devto_enabled=True, linkedin_enabled=True),
        )

        detail = await content_service.generate_draft(
            session=session,
            user_id=isolated_user.id,
            request=GenerateDraftRequest(topic="No image API keys"),
        )

        mock_image.assert_not_called()
        mock_upload.assert_not_called()
        assert len(detail.cover_images) == 2
        assert all(c.storage_key is None for c in detail.cover_images)
        assert detail.cover_image_warning is not None
        assert "Gemini API key required" in detail.cover_image_warning


@pytest.mark.asyncio
async def test_update_draft(session: AsyncSession, normal_user: User):
    ai_patch, image_patch, upload_patch, url_patch = _mock_ai_and_images()
    with ai_patch, image_patch, upload_patch, url_patch:
        await settings_crud.update_ai_config(
            session=session,
            user_id=normal_user.id,
            update=AIAgentConfigUpdate(
                provider="openai",
                openai_api_key="sk-test",
                cover_image_model="dall-e-3",
            ),
        )
        detail = await content_service.generate_draft(
            session=session,
            user_id=normal_user.id,
            request=GenerateDraftRequest(topic="Editable draft"),
        )

    updated = await content_service.update_draft(
        session=session,
        user_id=normal_user.id,
        draft_id=detail.id,
        update=UpdateDraftRequest(
            devto_title="Updated title",
            devto_body_markdown="# Updated body",
            linkedin_teaser="Updated teaser",
        ),
    )
    assert updated is not None
    assert updated.devto_article is not None
    assert updated.devto_article.title == "Updated title"
    assert updated.devto_article.body_markdown == "# Updated body"
    assert updated.linkedin_post is not None
    assert updated.linkedin_post.teaser_text == "Updated teaser"


@pytest.mark.asyncio
async def test_get_draft_detail_enforces_ownership(
    session: AsyncSession, normal_user: User
):
    ai_patch, image_patch, upload_patch, url_patch = _mock_ai_and_images()
    with ai_patch as mock_ai, image_patch, upload_patch, url_patch:
        await settings_crud.update_ai_config(
            session=session,
            user_id=normal_user.id,
            update=AIAgentConfigUpdate(
                provider="openai",
                openai_api_key="sk-test",
                cover_image_model="dall-e-3",
            ),
        )
        detail = await content_service.generate_draft(
            session=session,
            user_id=normal_user.id,
            request=GenerateDraftRequest(topic="Owned draft"),
        )

        other_detail = await content_service.get_draft_detail(
            session=session, user_id=uuid.uuid4(), draft_id=detail.id
        )
        assert other_detail is None
        mock_ai.assert_called_once()


@pytest.mark.asyncio
async def test_delete_draft_removes_related_records(
    session: AsyncSession, normal_user: User
):
    ai_patch, image_patch, upload_patch, url_patch = _mock_ai_and_images()
    with ai_patch, image_patch, upload_patch, url_patch:
        await settings_crud.update_ai_config(
            session=session,
            user_id=normal_user.id,
            update=AIAgentConfigUpdate(
                provider="openai",
                openai_api_key="sk-test",
                cover_image_model="dall-e-3",
            ),
        )
        await settings_crud.update_platform_config(
            session=session,
            user_id=normal_user.id,
            update=PlatformConfigUpdate(devto_enabled=True, linkedin_enabled=True),
        )
        detail = await content_service.generate_draft(
            session=session,
            user_id=normal_user.id,
            request=GenerateDraftRequest(topic="Delete me"),
        )

    draft_id = detail.id
    with patch("app.services.content.storage.delete_object") as mock_delete:
        deleted = await content_service.delete_draft(
            session=session,
            user_id=normal_user.id,
            draft_id=draft_id,
        )

    assert deleted is True
    assert await session.get(ContentDraft, draft_id) is None
    devto = await session.get(DevtoArticle, detail.devto_article.id)
    assert devto is None
    linkedin = await session.get(LinkedinPost, detail.linkedin_post.id)
    assert linkedin is None
    for cover in detail.cover_images:
        assert await session.get(CoverImage, cover.id) is None
    if any(cover.storage_key for cover in detail.cover_images):
        mock_delete.assert_called()
