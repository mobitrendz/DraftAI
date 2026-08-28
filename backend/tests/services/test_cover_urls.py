import uuid

import pytest

from app.models.content import CoverImagePlatform
from app.services.platforms.cover_urls import (
    build_public_cover_url,
    is_devto_reachable_image_url,
    resolve_devto_cover_image_url,
    resolve_devto_publish_cover_url,
)
from app.models.content import CoverImage


def test_build_public_cover_url():
    draft_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    url = build_public_cover_url(
        draft_id=draft_id,
        platform=CoverImagePlatform.DEVTO,
        extension="png",
    )
    assert url is None

    from app.core.config import settings

    original = settings.PUBLIC_API_BASE_URL
    settings.PUBLIC_API_BASE_URL = "https://api.example.com"
    try:
        url = build_public_cover_url(
            draft_id=draft_id,
            platform=CoverImagePlatform.DEVTO,
            extension="png",
        )
        assert (
            url
            == "https://api.example.com/api/v1/public/covers/"
            "00000000-0000-0000-0000-000000000001/devto.png"
        )
    finally:
        settings.PUBLIC_API_BASE_URL = original


def test_is_devto_reachable_image_url_rejects_local_hosts():
    assert is_devto_reachable_image_url("http://localhost:9000/cover.png") is False
    assert is_devto_reachable_image_url("http://minio:9000/cover.png") is False
    assert (
        is_devto_reachable_image_url("https://cdn.example.com/cover.png") is True
    )


def test_resolve_devto_cover_image_url_prefers_public_proxy(monkeypatch):
    draft_id = uuid.uuid4()
    cover = CoverImage(
        content_draft_id=draft_id,
        platform=CoverImagePlatform.DEVTO,
        storage_key=f"covers/{draft_id}/devto.png",
    )

    from app.core.config import settings

    settings.PUBLIC_API_BASE_URL = "https://api.example.com"
    url = resolve_devto_cover_image_url(draft_id=draft_id, cover=cover)
    assert url == (
        f"https://api.example.com/api/v1/public/covers/{draft_id}/devto.png"
    )


def test_resolve_devto_cover_image_url_returns_none_for_private_presigned(
    monkeypatch,
):
    draft_id = uuid.uuid4()
    cover = CoverImage(
        content_draft_id=draft_id,
        platform=CoverImagePlatform.DEVTO,
        storage_key=f"covers/{draft_id}/devto.png",
    )

    from app.core.config import settings

    settings.PUBLIC_API_BASE_URL = None

    def fake_presigned(key: str) -> str:
        return "http://localhost:9000/draftai-covers/cover.png?sig=abc"

    monkeypatch.setattr(
        "app.services.storage.storage.get_presigned_url",
        fake_presigned,
    )
    assert resolve_devto_cover_image_url(draft_id=draft_id, cover=cover) is None


@pytest.mark.asyncio
async def test_resolve_devto_publish_cover_url_requires_public_base():
    draft_id = uuid.uuid4()
    cover = CoverImage(
        content_draft_id=draft_id,
        platform=CoverImagePlatform.DEVTO,
        storage_key=f"covers/{draft_id}/devto.png",
    )

    from app.core.config import settings

    settings.PUBLIC_API_BASE_URL = None
    with pytest.raises(ValueError, match="PUBLIC_API_BASE_URL"):
        await resolve_devto_publish_cover_url(draft_id=draft_id, cover=cover)
