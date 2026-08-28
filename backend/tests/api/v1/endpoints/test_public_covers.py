import io
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from app.services.ai.template_cover import generate_template_cover_bytes


@pytest.mark.asyncio
async def test_public_cover_image_endpoint_returns_png(
    client: AsyncClient, normal_user_token: str
):
    from unittest.mock import AsyncMock

    ai_patch = patch(
        "app.services.content.generate_json_content",
        new_callable=AsyncMock,
        return_value={
            "devto_title": "Cover proxy test",
            "devto_body_markdown": "# Hello",
            "devto_tags": "python",
            "linkedin_teaser": "Teaser",
            "cover_image_prompt": "Abstract",
        },
    )
    image_patch = patch(
        "app.services.content.generate_cover_image",
        new_callable=AsyncMock,
        return_value=None,
    )
    png_bytes = generate_template_cover_bytes(title="Cover proxy test", width=1000, height=420)

    with ai_patch, image_patch, patch(
        "app.services.content.storage.upload_bytes"
    ), patch(
        "app.services.content.storage.get_presigned_url",
        return_value="http://localhost:9000/cover.png",
    ):
        await client.patch(
            "/api/v1/settings/ai",
            headers={"Authorization": f"Bearer {normal_user_token}"},
            json={"provider": "openai", "openai_api_key": "sk-test"},
        )
        create_response = await client.post(
            "/api/v1/content/drafts/generate",
            headers={"Authorization": f"Bearer {normal_user_token}"},
            json={"topic": "Cover proxy test"},
        )
    assert create_response.status_code == 201
    draft_id = create_response.json()["id"]

    with patch(
        "app.services.storage.storage.get_object_bytes",
        return_value=(png_bytes, "image/png"),
    ):
        response = await client.get(
            f"/api/v1/public/covers/{draft_id}/devto.png",
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/png")
    assert response.content.startswith(b"\x89PNG")
