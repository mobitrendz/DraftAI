import io
import uuid

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch

from app.services.ai.images import GeneratedCoverImage

MOCK_AI_RESPONSE = {
    "devto_title": "Test Article Title",
    "devto_body_markdown": "# Hello\n\nThis is test content.",
    "devto_tags": "python,fastapi",
    "linkedin_teaser": "Check out this new article on FastAPI!",
    "cover_image_prompt": "Abstract tech illustration",
}


def _mock_generation():
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
                data=b"fake-image",
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
            return_value="http://localhost:9000/presigned",
        ),
    )


@pytest.mark.asyncio
async def test_list_content_drafts_unauthorized(client: AsyncClient):
    response = await client.get("/api/v1/content/drafts/")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_content_drafts_empty(
    client: AsyncClient, isolated_user_token: str
):
    response = await client.get(
        "/api/v1/content/drafts/",
        headers={"Authorization": f"Bearer {isolated_user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0
    assert data["data"] == []


@pytest.mark.asyncio
async def test_generate_content_draft(
    client: AsyncClient, normal_user_token: str
):
    ai_patch, image_patch, upload_patch, url_patch = _mock_generation()
    with ai_patch as mock_ai, image_patch, upload_patch, url_patch:
        await client.patch(
            "/api/v1/settings/ai",
            headers={"Authorization": f"Bearer {normal_user_token}"},
            json={"provider": "openai", "openai_api_key": "sk-test"},
        )
        await client.patch(
            "/api/v1/settings/platform",
            headers={"Authorization": f"Bearer {normal_user_token}"},
            json={"devto_enabled": True, "linkedin_enabled": True},
        )

        response = await client.post(
            "/api/v1/content/drafts/generate",
            headers={"Authorization": f"Bearer {normal_user_token}"},
            json={
                "topic": "Building with FastAPI",
                "user_prompt": "Include code samples",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["topic"] == "Building with FastAPI"
        assert data["status"] == "draft"
        assert data["devto_article"]["title"] == "Test Article Title"
        assert data["linkedin_post"]["teaser_text"] == MOCK_AI_RESPONSE["linkedin_teaser"]
        mock_ai.assert_called_once()


@pytest.mark.asyncio
async def test_generate_content_draft_without_api_key(
    client: AsyncClient, isolated_user_token: str
):
    response = await client.post(
        "/api/v1/content/drafts/generate",
        headers={"Authorization": f"Bearer {isolated_user_token}"},
        json={"topic": "Should fail without key"},
    )
    assert response.status_code == 400
    assert "OpenAI API key required" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_content_draft_by_id(
    client: AsyncClient, normal_user_token: str
):
    ai_patch, image_patch, upload_patch, url_patch = _mock_generation()
    with ai_patch as mock_ai, image_patch, upload_patch, url_patch:
        await client.patch(
            "/api/v1/settings/ai",
            headers={"Authorization": f"Bearer {normal_user_token}"},
            json={"provider": "openai", "openai_api_key": "sk-test"},
        )
        await client.patch(
            "/api/v1/settings/platform",
            headers={"Authorization": f"Bearer {normal_user_token}"},
            json={"devto_enabled": True, "linkedin_enabled": True},
        )
        create_response = await client.post(
            "/api/v1/content/drafts/generate",
            headers={"Authorization": f"Bearer {normal_user_token}"},
            json={"topic": "Draft detail test"},
        )
        draft_id = create_response.json()["id"]

        response = await client.get(
            f"/api/v1/content/drafts/{draft_id}",
            headers={"Authorization": f"Bearer {normal_user_token}"},
        )
        assert response.status_code == 200
        assert response.json()["id"] == draft_id
        mock_ai.assert_called_once()


@pytest.mark.asyncio
async def test_patch_content_draft(
    client: AsyncClient, normal_user_token: str
):
    ai_patch, image_patch, upload_patch, url_patch = _mock_generation()
    with ai_patch, image_patch, upload_patch, url_patch:
        await client.patch(
            "/api/v1/settings/ai",
            headers={"Authorization": f"Bearer {normal_user_token}"},
            json={"provider": "openai", "openai_api_key": "sk-test"},
        )
        create_response = await client.post(
            "/api/v1/content/drafts/generate",
            headers={"Authorization": f"Bearer {normal_user_token}"},
            json={"topic": "Patch test draft"},
        )
        draft_id = create_response.json()["id"]

    response = await client.patch(
        f"/api/v1/content/drafts/{draft_id}",
        headers={"Authorization": f"Bearer {normal_user_token}"},
        json={
            "devto_title": "Patched title",
            "devto_body_markdown": "# Patched",
            "linkedin_teaser": "Patched teaser",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["devto_article"]["title"] == "Patched title"
    assert data["devto_article"]["body_markdown"] == "# Patched"
    assert data["linkedin_post"]["teaser_text"] == "Patched teaser"


@pytest.mark.asyncio
async def test_get_content_draft_not_found_for_other_user(
    client: AsyncClient,
    normal_user_token: str,
    second_user_token: str,
):
    ai_patch, image_patch, upload_patch, url_patch = _mock_generation()
    with ai_patch as mock_ai, image_patch, upload_patch, url_patch:
        await client.patch(
            "/api/v1/settings/ai",
            headers={"Authorization": f"Bearer {normal_user_token}"},
            json={"provider": "openai", "openai_api_key": "sk-test"},
        )
        await client.patch(
            "/api/v1/settings/platform",
            headers={"Authorization": f"Bearer {normal_user_token}"},
            json={"devto_enabled": True, "linkedin_enabled": True},
        )
        create_response = await client.post(
            "/api/v1/content/drafts/generate",
            headers={"Authorization": f"Bearer {normal_user_token}"},
            json={"topic": "Private draft"},
        )
        draft_id = create_response.json()["id"]

        response = await client.get(
            f"/api/v1/content/drafts/{draft_id}",
            headers={"Authorization": f"Bearer {second_user_token}"},
        )
        assert response.status_code == 404
        mock_ai.assert_called_once()


@pytest.mark.asyncio
async def test_get_content_draft_invalid_uuid(
    client: AsyncClient, normal_user_token: str
):
    response = await client.get(
        f"/api/v1/content/drafts/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {normal_user_token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_content_draft(
    client: AsyncClient, normal_user_token: str
):
    ai_patch, image_patch, upload_patch, url_patch = _mock_generation()
    with ai_patch, image_patch, upload_patch, url_patch:
        await client.patch(
            "/api/v1/settings/ai",
            headers={"Authorization": f"Bearer {normal_user_token}"},
            json={"provider": "openai", "openai_api_key": "sk-test"},
        )
        await client.patch(
            "/api/v1/settings/platform",
            headers={"Authorization": f"Bearer {normal_user_token}"},
            json={"devto_enabled": True, "linkedin_enabled": True},
        )
        create_response = await client.post(
            "/api/v1/content/drafts/generate",
            headers={"Authorization": f"Bearer {normal_user_token}"},
            json={"topic": "Draft to delete"},
        )
        draft_id = create_response.json()["id"]

    delete_response = await client.delete(
        f"/api/v1/content/drafts/{draft_id}",
        headers={"Authorization": f"Bearer {normal_user_token}"},
    )
    assert delete_response.status_code == 204

    get_response = await client.get(
        f"/api/v1/content/drafts/{draft_id}",
        headers={"Authorization": f"Bearer {normal_user_token}"},
    )
    assert get_response.status_code == 404

    list_response = await client.get(
        "/api/v1/content/drafts/",
        headers={"Authorization": f"Bearer {normal_user_token}"},
    )
    assert list_response.status_code == 200
    assert list_response.json()["count"] == 0


def _minimal_png_bytes() -> bytes:
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), color=(20, 20, 20)).save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_upload_content_draft_cover_image(
    client: AsyncClient,
    normal_user_token: str,
):
    ai_patch, image_patch, upload_patch, url_patch = _mock_generation()
    with ai_patch, image_patch, upload_patch, url_patch:
        await client.patch(
            "/api/v1/settings/ai",
            headers={"Authorization": f"Bearer {normal_user_token}"},
            json={"provider": "openai", "openai_api_key": "sk-test"},
        )
        await client.patch(
            "/api/v1/settings/platform",
            headers={"Authorization": f"Bearer {normal_user_token}"},
            json={"devto_enabled": True, "linkedin_enabled": True},
        )
        create_response = await client.post(
            "/api/v1/content/drafts/generate",
            headers={"Authorization": f"Bearer {normal_user_token}"},
            json={"topic": "Cover upload draft"},
        )
        assert create_response.status_code == 201
        draft = create_response.json()
        cover_id = draft["cover_images"][0]["id"]

    with (
        patch(
            "app.services.content.storage.upload_bytes",
            return_value=f"covers/{draft['id']}/devto.png",
        ),
        patch(
            "app.services.content.storage.get_presigned_url",
            return_value="http://localhost:9000/presigned/devto.png",
        ),
    ):
        response = await client.post(
            f"/api/v1/content/drafts/{draft['id']}/covers/{cover_id}/image",
            headers={"Authorization": f"Bearer {normal_user_token}"},
            files={"file": ("cover.png", _minimal_png_bytes(), "image/png")},
        )

    assert response.status_code == 200
    payload = response.json()
    uploaded = next(item for item in payload["cover_images"] if item["id"] == cover_id)
    assert uploaded["provider"] == "user-upload"
    assert uploaded["image_url"].startswith(
        f"/api/v1/public/covers/{draft['id']}/devto.png?v="
    )


@pytest.mark.asyncio
async def test_regenerate_content_draft_cover_image(
    client: AsyncClient,
    normal_user_token: str,
):
    ai_patch, image_patch, upload_patch, url_patch = _mock_generation()
    with ai_patch, image_patch, upload_patch, url_patch:
        await client.patch(
            "/api/v1/settings/ai",
            headers={"Authorization": f"Bearer {normal_user_token}"},
            json={"provider": "openai", "openai_api_key": "sk-test"},
        )
        await client.patch(
            "/api/v1/settings/platform",
            headers={"Authorization": f"Bearer {normal_user_token}"},
            json={"devto_enabled": True, "linkedin_enabled": True},
        )
        create_response = await client.post(
            "/api/v1/content/drafts/generate",
            headers={"Authorization": f"Bearer {normal_user_token}"},
            json={"topic": "Cover regenerate draft"},
        )
        assert create_response.status_code == 201
        draft = create_response.json()
        cover_id = draft["cover_images"][0]["id"]

    with (
        patch(
            "app.services.content.settings_crud.get_provider_api_key",
            new_callable=AsyncMock,
            return_value="sk-test",
        ),
        patch(
            "app.services.content.generate_cover_image",
            new_callable=AsyncMock,
            return_value=GeneratedCoverImage(
                data=_minimal_png_bytes(),
                provider="openai-dall-e-3",
                content_type="image/png",
            ),
        ),
        patch(
            "app.services.content.storage.upload_bytes",
            return_value=f"covers/{draft['id']}/devto.png",
        ),
        patch(
            "app.services.content.storage.get_presigned_url",
            return_value="http://localhost:9000/presigned/devto-regenerated.png",
        ),
    ):
        response = await client.post(
            f"/api/v1/content/drafts/{draft['id']}/covers/{cover_id}/regenerate",
            headers={"Authorization": f"Bearer {normal_user_token}"},
            json={"prompt": "Minimal abstract tech cover art"},
        )

    assert response.status_code == 200
    payload = response.json()
    regenerated = next(item for item in payload["cover_images"] if item["id"] == cover_id)
    assert regenerated["provider"] == "openai-dall-e-3"
    assert regenerated["prompt_used"] == "Minimal abstract tech cover art"
    assert regenerated["image_url"].startswith(
        f"/api/v1/public/covers/{draft['id']}/devto.png?v="
    )


@pytest.mark.asyncio
async def test_delete_content_draft_not_found_for_other_user(
    client: AsyncClient,
    normal_user_token: str,
    second_user_token: str,
):
    ai_patch, image_patch, upload_patch, url_patch = _mock_generation()
    with ai_patch, image_patch, upload_patch, url_patch:
        await client.patch(
            "/api/v1/settings/ai",
            headers={"Authorization": f"Bearer {normal_user_token}"},
            json={"provider": "openai", "openai_api_key": "sk-test"},
        )
        create_response = await client.post(
            "/api/v1/content/drafts/generate",
            headers={"Authorization": f"Bearer {normal_user_token}"},
            json={"topic": "Private delete test"},
        )
        draft_id = create_response.json()["id"]

    response = await client.delete(
        f"/api/v1/content/drafts/{draft_id}",
        headers={"Authorization": f"Bearer {second_user_token}"},
    )
    assert response.status_code == 404
