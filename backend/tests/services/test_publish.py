import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import settings as settings_crud
from app.models.ai_agent_config import AIAgentConfigUpdate
from app.models.content import (
    ContentDraftStatus,
    GenerateDraftRequest,
    PublishJobStatus,
    UpdateDraftRequest,
)
from app.models.platform_config import PlatformConfigUpdate
from app.models.user import User
from app.services import content as content_service
from app.services import publish as publish_service

MOCK_AI_RESPONSE = {
    "devto_title": "Publish Test Article",
    "devto_body_markdown": "# Hello",
    "devto_tags": "python",
    "linkedin_teaser": "New article on Python",
    "cover_image_prompt": "Abstract",
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
            return_value=None,
        ),
        patch("app.services.content.storage.upload_bytes"),
        patch(
            "app.services.content.storage.get_presigned_url",
            return_value="http://localhost:9000/cover.png",
        ),
    )


async def _create_draft(session: AsyncSession, user: User):
    ai_patch, image_patch, upload_patch, url_patch = _mock_generation()
    with ai_patch, image_patch, upload_patch, url_patch:
        await settings_crud.update_ai_config(
            session=session,
            user_id=user.id,
            update=AIAgentConfigUpdate(
                provider="openai",
                openai_api_key="sk-test",
            ),
        )
        await settings_crud.update_platform_config(
            session=session,
            user_id=user.id,
            update=PlatformConfigUpdate(devto_enabled=True, linkedin_enabled=True),
        )
        return await content_service.generate_draft(
            session=session,
            user_id=user.id,
            request=GenerateDraftRequest(topic="Publish pipeline test"),
        )


@pytest.mark.asyncio
async def test_approve_draft_transitions_status(
    session: AsyncSession, isolated_user: User
):
    detail = await _create_draft(session, isolated_user)
    assert detail.status == ContentDraftStatus.DRAFT

    approved = await publish_service.approve_draft(
        session=session,
        user_id=isolated_user.id,
        draft_id=detail.id,
    )
    assert approved is not None
    assert approved.status == ContentDraftStatus.APPROVED


@pytest.mark.asyncio
async def test_approve_draft_rejects_non_draft_status(
    session: AsyncSession, isolated_user: User
):
    detail = await _create_draft(session, isolated_user)
    await publish_service.approve_draft(
        session=session,
        user_id=isolated_user.id,
        draft_id=detail.id,
    )
    with pytest.raises(HTTPException) as exc:
        await publish_service.approve_draft(
            session=session,
            user_id=isolated_user.id,
            draft_id=detail.id,
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_schedule_draft_requires_devto_key(
    session: AsyncSession, isolated_user: User
):
    detail = await _create_draft(session, isolated_user)
    await publish_service.approve_draft(
        session=session,
        user_id=isolated_user.id,
        draft_id=detail.id,
    )
    with pytest.raises(HTTPException) as exc:
        await publish_service.schedule_draft(
            session=session,
            user_id=isolated_user.id,
            draft_id=detail.id,
            scheduled_at=None,
        )
    assert exc.value.status_code == 400
    assert "DEV.to API key" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_schedule_draft_enqueues_job(
    session: AsyncSession, isolated_user: User
):
    detail = await _create_draft(session, isolated_user)
    await settings_crud.update_platform_config(
        session=session,
        user_id=isolated_user.id,
        update=PlatformConfigUpdate(devto_api_key="devto-test-key"),
    )
    await publish_service.approve_draft(
        session=session,
        user_id=isolated_user.id,
        draft_id=detail.id,
    )

    with patch(
        "app.services.publish.enqueue_publish_job",
        new_callable=AsyncMock,
    ) as mock_enqueue:
        status = await publish_service.schedule_draft(
            session=session,
            user_id=isolated_user.id,
            draft_id=detail.id,
            scheduled_at=None,
        )

    mock_enqueue.assert_awaited_once()
    assert status is not None
    assert status.draft_status == ContentDraftStatus.SCHEDULED
    assert status.publish_job is not None
    assert status.publish_job.status == PublishJobStatus.PENDING


@pytest.mark.asyncio
async def test_execute_publish_job_publishes_to_devto(
    session: AsyncSession, isolated_user: User
):
    detail = await _create_draft(session, isolated_user)
    await settings_crud.update_platform_config(
        session=session,
        user_id=isolated_user.id,
        update=PlatformConfigUpdate(devto_api_key="devto-test-key"),
    )
    await publish_service.approve_draft(
        session=session,
        user_id=isolated_user.id,
        draft_id=detail.id,
    )
    with patch("app.services.publish.enqueue_publish_job", new_callable=AsyncMock):
        await publish_service.schedule_draft(
            session=session,
            user_id=isolated_user.id,
            draft_id=detail.id,
            scheduled_at=None,
        )

    from app.core.config import settings

    settings.PUBLIC_API_BASE_URL = "https://api.example.com"
    settings.LINKEDIN_ACCESS_TOKEN = None
    settings.LINKEDIN_AUTHOR_URN = None
    try:
        with (
            patch(
                "app.services.platforms.cover_urls.verify_public_image_url",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "app.services.publish.publish_article",
                new_callable=AsyncMock,
                return_value="https://dev.to/user/live-article",
            ) as mock_publish,
        ):
            await publish_service.execute_publish_job(
                session=session, draft_id=detail.id
            )
    finally:
        settings.PUBLIC_API_BASE_URL = None
        settings.LINKEDIN_ACCESS_TOKEN = None
        settings.LINKEDIN_AUTHOR_URN = None

    mock_publish.assert_awaited_once()
    main_image = mock_publish.call_args.kwargs["main_image"]
    assert main_image is not None
    assert f"/api/v1/public/covers/{detail.id}/devto.png" in main_image

    refreshed = await content_service.get_draft_detail(
        session=session,
        user_id=isolated_user.id,
        draft_id=detail.id,
    )
    assert refreshed is not None
    assert refreshed.status == ContentDraftStatus.PARTIALLY_PUBLISHED
    assert refreshed.linkedin_post is not None
    assert refreshed.linkedin_post.article_url == "https://dev.to/user/live-article"
    assert "https://dev.to/user/live-article" in (refreshed.linkedin_clipboard_text or "")


@pytest.mark.asyncio
async def test_execute_publish_job_auto_posts_to_linkedin_when_configured(
    session: AsyncSession, isolated_user: User
):
    detail = await _create_draft(session, isolated_user)
    await settings_crud.update_platform_config(
        session=session,
        user_id=isolated_user.id,
        update=PlatformConfigUpdate(devto_api_key="devto-test-key"),
    )
    await publish_service.approve_draft(
        session=session,
        user_id=isolated_user.id,
        draft_id=detail.id,
    )
    with patch("app.services.publish.enqueue_publish_job", new_callable=AsyncMock):
        await publish_service.schedule_draft(
            session=session,
            user_id=isolated_user.id,
            draft_id=detail.id,
            scheduled_at=None,
        )

    from app.core.config import settings

    settings.PUBLIC_API_BASE_URL = "https://api.example.com"
    settings.LINKEDIN_ACCESS_TOKEN = "linkedin-token"
    settings.LINKEDIN_AUTHOR_URN = "urn:li:person:test-author"
    try:
        with (
            patch(
                "app.services.platforms.cover_urls.verify_public_image_url",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "app.services.publish.publish_article",
                new_callable=AsyncMock,
                return_value="https://dev.to/user/live-article",
            ),
            patch(
                "app.services.publish.publish_post",
                new_callable=AsyncMock,
                return_value="urn:li:share:123456",
            ) as mock_linkedin,
        ):
            await publish_service.execute_publish_job(
                session=session, draft_id=detail.id
            )
    finally:
        settings.PUBLIC_API_BASE_URL = None
        settings.LINKEDIN_ACCESS_TOKEN = None
        settings.LINKEDIN_AUTHOR_URN = None

    mock_linkedin.assert_awaited_once()
    refreshed = await content_service.get_draft_detail(
        session=session,
        user_id=isolated_user.id,
        draft_id=detail.id,
    )
    assert refreshed is not None
    assert refreshed.status == ContentDraftStatus.PUBLISHED


@pytest.mark.asyncio
async def test_reschedule_draft_updates_pending_job(
    session: AsyncSession, isolated_user: User
):
    detail = await _create_draft(session, isolated_user)
    await settings_crud.update_platform_config(
        session=session,
        user_id=isolated_user.id,
        update=PlatformConfigUpdate(devto_api_key="devto-test-key"),
    )
    await publish_service.approve_draft(
        session=session,
        user_id=isolated_user.id,
        draft_id=detail.id,
    )
    future = datetime.now(UTC) + timedelta(hours=2)
    with patch("app.services.publish.enqueue_publish_job", new_callable=AsyncMock):
        await publish_service.schedule_draft(
            session=session,
            user_id=isolated_user.id,
            draft_id=detail.id,
            scheduled_at=future,
        )

    new_time = datetime.now(UTC) + timedelta(hours=5)
    with (
        patch(
            "app.services.publish.cancel_publish_job",
            new_callable=AsyncMock,
        ) as mock_cancel,
        patch(
            "app.services.publish.enqueue_publish_job",
            new_callable=AsyncMock,
        ) as mock_enqueue,
        patch(
            "app.services.publish.is_publish_job_in_progress",
            new_callable=AsyncMock,
            return_value=False,
        ),
    ):
        status = await publish_service.reschedule_draft(
            session=session,
            user_id=isolated_user.id,
            draft_id=detail.id,
            scheduled_at=new_time,
        )

    mock_cancel.assert_awaited_once()
    mock_enqueue.assert_awaited_once()
    assert status is not None
    assert status.publish_job is not None
    assert status.publish_job.scheduled_at is not None
    assert abs(
        status.publish_job.scheduled_at.replace(tzinfo=UTC) - new_time
    ) < timedelta(seconds=1)


@pytest.mark.asyncio
async def test_schedule_draft_reschedules_via_post_when_already_scheduled(
    session: AsyncSession, isolated_user: User
):
    detail = await _create_draft(session, isolated_user)
    await settings_crud.update_platform_config(
        session=session,
        user_id=isolated_user.id,
        update=PlatformConfigUpdate(devto_api_key="devto-test-key"),
    )
    await publish_service.approve_draft(
        session=session,
        user_id=isolated_user.id,
        draft_id=detail.id,
    )
    with patch("app.services.publish.enqueue_publish_job", new_callable=AsyncMock):
        await publish_service.schedule_draft(
            session=session,
            user_id=isolated_user.id,
            draft_id=detail.id,
            scheduled_at=datetime.now(UTC) + timedelta(hours=1),
        )

    new_time = datetime.now(UTC) + timedelta(hours=3)
    with (
        patch("app.services.publish.cancel_publish_job", new_callable=AsyncMock),
        patch("app.services.publish.enqueue_publish_job", new_callable=AsyncMock) as mock_enqueue,
        patch(
            "app.services.publish.is_publish_job_in_progress",
            new_callable=AsyncMock,
            return_value=False,
        ),
    ):
        status = await publish_service.schedule_draft(
            session=session,
            user_id=isolated_user.id,
            draft_id=detail.id,
            scheduled_at=new_time,
        )

    mock_enqueue.assert_awaited_once()
    assert status is not None
    assert status.publish_job is not None
    assert status.publish_job.scheduled_at is not None


@pytest.mark.asyncio
async def test_reschedule_draft_rejects_non_scheduled_status(
    session: AsyncSession, isolated_user: User
):
    detail = await _create_draft(session, isolated_user)
    await publish_service.approve_draft(
        session=session,
        user_id=isolated_user.id,
        draft_id=detail.id,
    )
    with pytest.raises(HTTPException) as exc:
        await publish_service.reschedule_draft(
            session=session,
            user_id=isolated_user.id,
            draft_id=detail.id,
            scheduled_at=datetime.now(UTC) + timedelta(hours=1),
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_update_draft_blocked_after_schedule(
    session: AsyncSession, isolated_user: User
):
    detail = await _create_draft(session, isolated_user)
    await settings_crud.update_platform_config(
        session=session,
        user_id=isolated_user.id,
        update=PlatformConfigUpdate(devto_api_key="devto-test-key"),
    )
    await publish_service.approve_draft(
        session=session,
        user_id=isolated_user.id,
        draft_id=detail.id,
    )
    with patch("app.services.publish.enqueue_publish_job", new_callable=AsyncMock):
        await publish_service.schedule_draft(
            session=session,
            user_id=isolated_user.id,
            draft_id=detail.id,
            scheduled_at=None,
        )

    with pytest.raises(HTTPException) as exc:
        await content_service.update_draft(
            session=session,
            user_id=isolated_user.id,
            draft_id=detail.id,
            update=UpdateDraftRequest(devto_title="Changed"),
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_execute_publish_job_fails_without_public_cover_url(
    session: AsyncSession, isolated_user: User
):
    detail = await _create_draft(session, isolated_user)
    await settings_crud.update_platform_config(
        session=session,
        user_id=isolated_user.id,
        update=PlatformConfigUpdate(devto_api_key="devto-test-key"),
    )
    await publish_service.approve_draft(
        session=session,
        user_id=isolated_user.id,
        draft_id=detail.id,
    )
    with patch("app.services.publish.enqueue_publish_job", new_callable=AsyncMock):
        await publish_service.schedule_draft(
            session=session,
            user_id=isolated_user.id,
            draft_id=detail.id,
            scheduled_at=None,
        )

    from app.core.config import settings

    settings.PUBLIC_API_BASE_URL = None
    with patch(
        "app.services.publish.publish_article",
        new_callable=AsyncMock,
    ) as mock_publish:
        await publish_service.execute_publish_job(
            session=session, draft_id=detail.id
        )

    mock_publish.assert_not_awaited()
    refreshed = await content_service.get_draft_detail(
        session=session,
        user_id=isolated_user.id,
        draft_id=detail.id,
    )
    assert refreshed is not None
    assert refreshed.status == ContentDraftStatus.FAILED
    assert refreshed.publish_job is not None
    assert refreshed.publish_job.status == PublishJobStatus.FAILED
    assert "PUBLIC_API_BASE_URL" in (refreshed.publish_job.error_message or "")


@pytest.mark.asyncio
async def test_execute_publish_job_fails_without_public_cover_url(
    session: AsyncSession, isolated_user: User
):
    detail = await _create_draft(session, isolated_user)
    await settings_crud.update_platform_config(
        session=session,
        user_id=isolated_user.id,
        update=PlatformConfigUpdate(devto_api_key="devto-test-key"),
    )
    await publish_service.approve_draft(
        session=session,
        user_id=isolated_user.id,
        draft_id=detail.id,
    )
    with patch("app.services.publish.enqueue_publish_job", new_callable=AsyncMock):
        await publish_service.schedule_draft(
            session=session,
            user_id=isolated_user.id,
            draft_id=detail.id,
            scheduled_at=None,
        )

    from app.core.config import settings

    settings.PUBLIC_API_BASE_URL = None
    with patch(
        "app.services.publish.publish_article",
        new_callable=AsyncMock,
    ) as mock_publish:
        await publish_service.execute_publish_job(
            session=session, draft_id=detail.id
        )

    mock_publish.assert_not_awaited()
    refreshed = await content_service.get_draft_detail(
        session=session,
        user_id=isolated_user.id,
        draft_id=detail.id,
    )
    assert refreshed is not None
    assert refreshed.status == ContentDraftStatus.FAILED
    assert refreshed.publish_job is not None
    assert refreshed.publish_job.status == PublishJobStatus.FAILED
    assert "PUBLIC_API_BASE_URL" in (refreshed.publish_job.error_message or "")
