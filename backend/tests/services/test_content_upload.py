import io
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import (
    ContentDraft,
    ContentDraftStatus,
    CoverImage,
    CoverImagePlatform,
    DevtoArticle,
)
from app.services import content as content_service
from app.services.ai.images import GeneratedCoverImage


def _png_bytes() -> bytes:
    image = Image.new("RGB", (8, 8), color=(30, 64, 175))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_validate_cover_upload_rejects_unsupported_type():
    with pytest.raises(HTTPException) as exc_info:
        content_service._validate_cover_upload(
            data=_png_bytes(),
            content_type="application/pdf",
        )
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_upload_draft_cover_image_updates_cover(
    session: AsyncSession,
    isolated_user,
):
    draft = ContentDraft(
        user_id=isolated_user.id,
        topic="Upload cover topic",
        status=ContentDraftStatus.DRAFT,
    )
    session.add(draft)
    await session.flush()

    cover = CoverImage(
        content_draft_id=draft.id,
        platform=CoverImagePlatform.DEVTO,
        prompt_used="Prompt",
    )
    session.add(cover)
    await session.commit()

    png = _png_bytes()
    with (
        patch.object(content_service.storage, "upload_bytes", return_value="covers/test/devto.png"),
        patch.object(
            content_service.storage,
            "get_presigned_url",
            return_value="http://localhost:9000/presigned/devto.png",
        ),
    ):
        detail = await content_service.upload_draft_cover_image(
            session=session,
            user_id=isolated_user.id,
            draft_id=draft.id,
            cover_id=cover.id,
            data=png,
            content_type="image/png",
        )

    assert detail is not None
    assert len(detail.cover_images) == 1
    assert detail.cover_images[0].provider == "user-upload"
    assert detail.cover_images[0].storage_key == f"covers/{draft.id}/devto.png"
    assert detail.cover_images[0].image_url is not None
    assert detail.cover_images[0].image_url.startswith(
        f"/api/v1/public/covers/{draft.id}/devto.png?v="
    )


@pytest.mark.asyncio
async def test_upload_draft_cover_image_returns_none_for_other_user(
    session: AsyncSession,
    isolated_user,
    normal_user,
):
    draft = ContentDraft(
        user_id=isolated_user.id,
        topic="Private draft",
        status=ContentDraftStatus.DRAFT,
    )
    session.add(draft)
    await session.flush()

    cover = CoverImage(
        content_draft_id=draft.id,
        platform=CoverImagePlatform.LINKEDIN,
    )
    session.add(cover)
    await session.commit()

    detail = await content_service.upload_draft_cover_image(
        session=session,
        user_id=normal_user.id,
        draft_id=draft.id,
        cover_id=cover.id,
        data=_png_bytes(),
        content_type="image/png",
    )
    assert detail is None


@pytest.mark.asyncio
async def test_regenerate_draft_cover_image_updates_cover(
    session: AsyncSession,
    isolated_user,
):
    draft = ContentDraft(
        user_id=isolated_user.id,
        topic="Regenerate cover topic",
        status=ContentDraftStatus.DRAFT,
    )
    session.add(draft)
    await session.flush()

    cover = CoverImage(
        content_draft_id=draft.id,
        platform=CoverImagePlatform.DEVTO,
        prompt_used="Old prompt",
    )
    session.add(
        DevtoArticle(
            content_draft_id=draft.id,
            title="Article title for template",
            body_markdown="# Body",
            tags="devops",
            cover_image_id=cover.id,
        )
    )
    session.add(cover)
    await session.commit()

    generated = GeneratedCoverImage(
        data=_png_bytes(),
        provider="test-provider",
        content_type="image/png",
    )

    with (
        patch(
            "app.services.content.settings_crud.get_provider_api_key",
            new_callable=AsyncMock,
            return_value="test-api-key",
        ),
        patch(
            "app.services.content.generate_cover_image",
            new_callable=AsyncMock,
            return_value=generated,
        ),
        patch.object(content_service.storage, "upload_bytes", return_value="covers/test/devto.png"),
        patch.object(
            content_service.storage,
            "get_presigned_url",
            return_value="http://localhost:9000/presigned/devto.png",
        ),
    ):
        detail = await content_service.regenerate_draft_cover_image(
            session=session,
            user_id=isolated_user.id,
            draft_id=draft.id,
            cover_id=cover.id,
            prompt="New abstract illustration prompt",
        )

    assert detail is not None
    assert len(detail.cover_images) == 1
    assert detail.cover_images[0].provider == "test-provider"
    assert detail.cover_images[0].prompt_used == "New abstract illustration prompt"
    assert detail.cover_images[0].storage_key == f"covers/{draft.id}/devto.png"
    assert detail.cover_images[0].image_url.startswith(
        f"/api/v1/public/covers/{draft.id}/devto.png?v="
    )


@pytest.mark.asyncio
async def test_regenerate_draft_cover_image_blocks_scheduled_draft(
    session: AsyncSession,
    isolated_user,
):
    draft = ContentDraft(
        user_id=isolated_user.id,
        topic="Scheduled draft",
        status=ContentDraftStatus.SCHEDULED,
    )
    session.add(draft)
    await session.flush()

    cover = CoverImage(
        content_draft_id=draft.id,
        platform=CoverImagePlatform.LINKEDIN,
        prompt_used="Prompt",
    )
    session.add(cover)
    await session.commit()

    with pytest.raises(HTTPException) as exc_info:
        await content_service.regenerate_draft_cover_image(
            session=session,
            user_id=isolated_user.id,
            draft_id=draft.id,
            cover_id=cover.id,
            prompt="Updated prompt",
        )
    assert exc_info.value.status_code == 400
