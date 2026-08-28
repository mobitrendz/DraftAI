import uuid
from datetime import UTC, datetime

import structlog
from arq.worker import Retry
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import settings
from app.crud import publish_job as publish_job_crud
from app.crud import settings as settings_crud
from app.models.content import (
    ContentDraft,
    ContentDraftDetailPublic,
    ContentDraftStatus,
    CoverImage,
    CoverImagePlatform,
    DevtoArticle,
    LinkedinPost,
    PublishJob,
    PublishJobPublic,
    PublishJobStatus,
    PublishStatusPublic,
)
from app.models.platform_config import PlatformConfig
from app.services.arq_queue import (
    cancel_publish_job,
    enqueue_publish_job,
    is_publish_job_in_progress,
)
from app.services.platforms.cover_urls import resolve_devto_publish_cover_url
from app.services.platforms.devto import DevtoPublishError, publish_article
from app.services.platforms.linkedin import (
    LinkedinPublishError,
    publish_post,
    resolve_author_urn_for_publish,
)

logger = structlog.get_logger(__name__)

EDITABLE_DRAFT_STATUSES = frozenset(
    {ContentDraftStatus.DRAFT, ContentDraftStatus.APPROVED}
)


def build_linkedin_clipboard_text(
    *, teaser_text: str, article_url: str | None
) -> str:
    teaser = teaser_text.strip()
    if not article_url:
        return teaser
    if article_url in teaser:
        return teaser
    return f"{teaser}\n\n{article_url}".strip()


def _publish_job_public(job: PublishJob) -> PublishJobPublic:
    return PublishJobPublic.model_validate(job)


async def _load_owned_draft(
    *, session: AsyncSession, user_id: uuid.UUID, draft_id: uuid.UUID
) -> ContentDraft | None:
    draft = await session.get(ContentDraft, draft_id)
    if not draft or draft.user_id != user_id:
        return None
    return draft


async def _get_platform_config(
    *, session: AsyncSession, user_id: uuid.UUID
) -> PlatformConfig:
    return await settings_crud.get_or_create_platform_config(
        session=session, user_id=user_id
    )


def _require_devto_key_if_needed(
    *, platform_config: PlatformConfig, devto_article: DevtoArticle | None
) -> None:
    if not platform_config.devto_enabled or devto_article is None:
        return
    if not settings_crud.get_devto_api_key(platform_config):
        raise HTTPException(
            status_code=400,
            detail="DEV.to API key required. Add your key in Settings → Platforms.",
        )


async def get_publish_status(
    *, session: AsyncSession, user_id: uuid.UUID, draft_id: uuid.UUID
) -> PublishStatusPublic | None:
    draft = await _load_owned_draft(
        session=session, user_id=user_id, draft_id=draft_id
    )
    if not draft:
        return None

    job = await publish_job_crud.get_latest_publish_job(
        session=session, draft_id=draft_id
    )
    linkedin = (
        await session.execute(
            select(LinkedinPost).where(LinkedinPost.content_draft_id == draft_id)
        )
    ).scalars().first()

    clipboard_text = None
    if linkedin:
        clipboard_text = build_linkedin_clipboard_text(
            teaser_text=linkedin.teaser_text,
            article_url=linkedin.article_url,
        )

    return PublishStatusPublic(
        draft_status=draft.status,
        publish_job=_publish_job_public(job) if job else None,
        linkedin_clipboard_text=clipboard_text,
    )


async def approve_draft(
    *, session: AsyncSession, user_id: uuid.UUID, draft_id: uuid.UUID
) -> ContentDraftDetailPublic | None:
    draft = await _load_owned_draft(
        session=session, user_id=user_id, draft_id=draft_id
    )
    if not draft:
        return None

    if draft.status != ContentDraftStatus.DRAFT:
        raise HTTPException(
            status_code=400,
            detail=f"Only drafts in '{ContentDraftStatus.DRAFT}' status can be approved.",
        )

    platform_config = await _get_platform_config(session=session, user_id=user_id)
    devto = (
        await session.execute(
            select(DevtoArticle).where(DevtoArticle.content_draft_id == draft_id)
        )
    ).scalars().first()
    linkedin = (
        await session.execute(
            select(LinkedinPost).where(LinkedinPost.content_draft_id == draft_id)
        )
    ).scalars().first()

    if platform_config.devto_enabled and devto is None:
        raise HTTPException(
            status_code=400,
            detail="Cannot approve: DEV.to is enabled but this draft has no article.",
        )
    if platform_config.linkedin_enabled and linkedin is None:
        raise HTTPException(
            status_code=400,
            detail="Cannot approve: LinkedIn is enabled but this draft has no teaser.",
        )
    if not platform_config.devto_enabled and not platform_config.linkedin_enabled:
        raise HTTPException(
            status_code=400,
            detail="Enable at least one platform in Settings before approving.",
        )

    draft.status = ContentDraftStatus.APPROVED
    draft.updated_at = datetime.now(UTC)
    session.add(draft)
    await session.commit()
    from app.services.content import get_draft_detail

    return await get_draft_detail(session=session, user_id=user_id, draft_id=draft_id)


def _normalize_schedule_time(scheduled_at: datetime | None) -> datetime:
    now = datetime.now(UTC)
    run_at = scheduled_at or now
    if run_at.tzinfo is None:
        run_at = run_at.replace(tzinfo=UTC)
    return run_at


async def _reschedule_pending_job(
    *,
    session: AsyncSession,
    user_id: uuid.UUID,
    draft_id: uuid.UUID,
    draft: ContentDraft,
    job: PublishJob,
    scheduled_at: datetime | None,
) -> PublishStatusPublic:
    if job.status == PublishJobStatus.RUNNING or await is_publish_job_in_progress(
        draft_id=draft_id
    ):
        raise HTTPException(
            status_code=409,
            detail="Publish is already in progress and cannot be rescheduled.",
        )

    now = datetime.now(UTC)
    run_at = _normalize_schedule_time(scheduled_at)

    job.scheduled_at = run_at
    job.updated_at = now
    draft.updated_at = now
    session.add(job)
    session.add(draft)
    await session.commit()

    await cancel_publish_job(draft_id=draft_id)
    defer_by = max(0.0, (run_at - now).total_seconds())
    await enqueue_publish_job(draft_id=draft_id, defer_by=defer_by)

    status = await get_publish_status(
        session=session, user_id=user_id, draft_id=draft_id
    )
    assert status is not None
    return status


async def schedule_draft(
    *,
    session: AsyncSession,
    user_id: uuid.UUID,
    draft_id: uuid.UUID,
    scheduled_at: datetime | None,
) -> PublishStatusPublic | None:
    draft = await _load_owned_draft(
        session=session, user_id=user_id, draft_id=draft_id
    )
    if not draft:
        return None

    if draft.status not in (
        ContentDraftStatus.APPROVED,
        ContentDraftStatus.SCHEDULED,
        ContentDraftStatus.FAILED,
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Only approved drafts can be scheduled. "
                f"Current status: {draft.status.value}."
            ),
        )

    active_job = await publish_job_crud.get_active_publish_job(
        session=session, draft_id=draft_id
    )
    if active_job:
        if active_job.status == PublishJobStatus.RUNNING or await is_publish_job_in_progress(
            draft_id=draft_id
        ):
            raise HTTPException(
                status_code=409,
                detail="Publish is already in progress.",
            )
        if draft.status == ContentDraftStatus.SCHEDULED:
            return await _reschedule_pending_job(
                session=session,
                user_id=user_id,
                draft_id=draft_id,
                draft=draft,
                job=active_job,
                scheduled_at=scheduled_at,
            )
        return await get_publish_status(
            session=session, user_id=user_id, draft_id=draft_id
        )

    platform_config = await _get_platform_config(session=session, user_id=user_id)
    devto = (
        await session.execute(
            select(DevtoArticle).where(DevtoArticle.content_draft_id == draft_id)
        )
    ).scalars().first()
    _require_devto_key_if_needed(
        platform_config=platform_config, devto_article=devto
    )

    now = datetime.now(UTC)
    run_at = _normalize_schedule_time(scheduled_at)

    job = await publish_job_crud.create_publish_job(
        session=session,
        draft_id=draft_id,
        scheduled_at=run_at,
    )
    draft.status = ContentDraftStatus.SCHEDULED
    draft.updated_at = now
    session.add(draft)
    await session.commit()

    defer_by = max(0.0, (run_at - now).total_seconds())
    await enqueue_publish_job(draft_id=draft_id, defer_by=defer_by)

    status = await get_publish_status(
        session=session, user_id=user_id, draft_id=draft_id
    )
    assert status is not None
    if status.publish_job is None:
        status.publish_job = _publish_job_public(job)
    return status


async def reschedule_draft(
    *,
    session: AsyncSession,
    user_id: uuid.UUID,
    draft_id: uuid.UUID,
    scheduled_at: datetime,
) -> PublishStatusPublic | None:
    draft = await _load_owned_draft(
        session=session, user_id=user_id, draft_id=draft_id
    )
    if not draft:
        return None

    if draft.status != ContentDraftStatus.SCHEDULED:
        raise HTTPException(
            status_code=400,
            detail="Only scheduled drafts can be rescheduled.",
        )

    active_job = await publish_job_crud.get_active_publish_job(
        session=session, draft_id=draft_id
    )
    if not active_job:
        raise HTTPException(
            status_code=400,
            detail="No pending publish job found for this draft.",
        )

    return await _reschedule_pending_job(
        session=session,
        user_id=user_id,
        draft_id=draft_id,
        draft=draft,
        job=active_job,
        scheduled_at=scheduled_at,
    )


async def retry_publish(
    *, session: AsyncSession, user_id: uuid.UUID, draft_id: uuid.UUID
) -> PublishStatusPublic | None:
    draft = await _load_owned_draft(
        session=session, user_id=user_id, draft_id=draft_id
    )
    if not draft:
        return None

    if draft.status != ContentDraftStatus.FAILED:
        raise HTTPException(
            status_code=400,
            detail="Only failed drafts can be retried.",
        )

    active_job = await publish_job_crud.get_active_publish_job(
        session=session, draft_id=draft_id
    )
    if active_job:
        return await get_publish_status(
            session=session, user_id=user_id, draft_id=draft_id
        )

    platform_config = await _get_platform_config(session=session, user_id=user_id)
    devto = (
        await session.execute(
            select(DevtoArticle).where(DevtoArticle.content_draft_id == draft_id)
        )
    ).scalars().first()
    _require_devto_key_if_needed(
        platform_config=platform_config, devto_article=devto
    )

    now = datetime.now(UTC)
    job = await publish_job_crud.create_publish_job(
        session=session,
        draft_id=draft_id,
        scheduled_at=now,
    )
    draft.status = ContentDraftStatus.SCHEDULED
    draft.updated_at = now
    session.add(draft)
    await session.commit()

    await enqueue_publish_job(draft_id=draft_id)
    return await get_publish_status(
        session=session, user_id=user_id, draft_id=draft_id
    )


async def _resolve_cover_image_url(
    *,
    session: AsyncSession,
    draft_id: uuid.UUID,
    cover_image_id: uuid.UUID | None,
) -> str | None:
    cover: CoverImage | None = None
    if cover_image_id:
        cover = await session.get(CoverImage, cover_image_id)
    if cover is None:
        cover = (
            await session.execute(
                select(CoverImage).where(
                    CoverImage.content_draft_id == draft_id,
                    CoverImage.platform == CoverImagePlatform.DEVTO,
                )
            )
        ).scalars().first()
    try:
        return await resolve_devto_publish_cover_url(draft_id=draft_id, cover=cover)
    except ValueError as exc:
        raise DevtoPublishError(str(exc), retryable=False) from exc


async def execute_publish_job(*, session: AsyncSession, draft_id: uuid.UUID) -> None:
    """Run the publish pipeline for a scheduled draft (called from ARQ worker)."""
    draft = await session.get(ContentDraft, draft_id)
    if not draft:
        logger.warning("Publish job skipped — draft not found", draft_id=str(draft_id))
        return

    job = await publish_job_crud.get_active_publish_job(
        session=session, draft_id=draft_id
    )
    if not job:
        job = await publish_job_crud.get_latest_publish_job(
            session=session, draft_id=draft_id
        )
    if not job:
        logger.warning("Publish job skipped — no job record", draft_id=str(draft_id))
        return

    if job.status not in (PublishJobStatus.PENDING, PublishJobStatus.RUNNING):
        logger.info(
            "Publish job skipped — already finished",
            draft_id=str(draft_id),
            status=job.status.value,
        )
        return

    job.status = PublishJobStatus.RUNNING
    job.updated_at = datetime.now(UTC)
    session.add(job)
    await session.commit()

    platform_config = await _get_platform_config(
        session=session, user_id=draft.user_id
    )
    devto_article = (
        await session.execute(
            select(DevtoArticle).where(DevtoArticle.content_draft_id == draft_id)
        )
    ).scalars().first()
    linkedin_post = (
        await session.execute(
            select(LinkedinPost).where(LinkedinPost.content_draft_id == draft_id)
        )
    ).scalars().first()

    devto_url: str | None = job.devto_url
    devto_published = bool(devto_url)
    devto_attempted = False
    linkedin_enabled = platform_config.linkedin_enabled and linkedin_post is not None
    linkedin_published = False
    linkedin_attempted = False

    try:
        if platform_config.devto_enabled and devto_article and not devto_published:
            devto_attempted = True
            api_key = settings_crud.get_devto_api_key(platform_config)
            if not api_key:
                raise DevtoPublishError(
                    "DEV.to API key missing for this user.",
                    retryable=False,
                )
            cover_url = await _resolve_cover_image_url(
                session=session,
                draft_id=draft_id,
                cover_image_id=devto_article.cover_image_id,
            )
            devto_url = await publish_article(
                api_key=api_key,
                title=devto_article.title,
                body_markdown=devto_article.body_markdown,
                tags=devto_article.tags,
                main_image=cover_url,
            )
            job.devto_url = devto_url
            devto_published = True

        if linkedin_post and devto_url:
            linkedin_post.article_url = devto_url
            session.add(linkedin_post)

        if linkedin_enabled:
            linkedin_text = build_linkedin_clipboard_text(
                teaser_text=linkedin_post.teaser_text,
                article_url=devto_url,
            )
            linkedin_post.teaser_text = linkedin_text
            session.add(linkedin_post)

            if settings.LINKEDIN_ACCESS_TOKEN:
                linkedin_attempted = True
                author_urn = await resolve_author_urn_for_publish(
                    access_token=settings.LINKEDIN_ACCESS_TOKEN,
                    author_urn=settings.LINKEDIN_AUTHOR_URN,
                )
                await publish_post(
                    access_token=settings.LINKEDIN_ACCESS_TOKEN,
                    author_urn=author_urn,
                    post_text=linkedin_text,
                    article_url=devto_url,
                )
                linkedin_published = True
            else:
                logger.info(
                    "LinkedIn auto-publish skipped; credentials not configured",
                    draft_id=str(draft_id),
                )

        now = datetime.now(UTC)
        draft.updated_at = now
        job.updated_at = now

        devto_enabled = platform_config.devto_enabled and devto_article is not None

        if devto_enabled and devto_published and linkedin_enabled and linkedin_published:
            draft.status = ContentDraftStatus.PUBLISHED
            job.status = PublishJobStatus.COMPLETED
        elif devto_enabled and devto_published and linkedin_enabled:
            draft.status = ContentDraftStatus.PARTIALLY_PUBLISHED
            job.status = PublishJobStatus.PARTIAL
        elif devto_enabled and devto_published:
            draft.status = ContentDraftStatus.PUBLISHED
            job.status = PublishJobStatus.COMPLETED
        elif not devto_enabled and linkedin_enabled and linkedin_published:
            draft.status = ContentDraftStatus.PUBLISHED
            job.status = PublishJobStatus.COMPLETED
        elif not devto_enabled and linkedin_enabled and linkedin_attempted and not linkedin_published:
            raise LinkedinPublishError("LinkedIn post did not complete.", retryable=True)
        elif not devto_enabled and linkedin_enabled:
            draft.status = ContentDraftStatus.PARTIALLY_PUBLISHED
            job.status = PublishJobStatus.PARTIAL
        elif devto_attempted and not devto_published:
            raise DevtoPublishError(
                "DEV.to publish did not complete.",
                retryable=True,
            )
        else:
            draft.status = ContentDraftStatus.PUBLISHED
            job.status = PublishJobStatus.COMPLETED

        session.add(draft)
        session.add(job)
        await session.commit()
        logger.info(
            "Publish job completed",
            draft_id=str(draft_id),
            draft_status=draft.status.value,
            devto_url=devto_url,
        )
    except DevtoPublishError as exc:
        await _fail_publish_job(
            session=session,
            draft=draft,
            job=job,
            error_message=str(exc),
            retryable=exc.retryable,
        )
    except LinkedinPublishError as exc:
        await _fail_publish_job(
            session=session,
            draft=draft,
            job=job,
            error_message=str(exc),
            retryable=exc.retryable,
        )
    except Exception as exc:
        logger.exception("Publish job failed", draft_id=str(draft_id))
        await _fail_publish_job(
            session=session,
            draft=draft,
            job=job,
            error_message=f"Publish failed: {exc}",
            retryable=True,
        )


async def _fail_publish_job(
    *,
    session: AsyncSession,
    draft: ContentDraft,
    job: PublishJob,
    error_message: str,
    retryable: bool,
) -> None:
    job.retry_count += 1
    job.error_message = error_message
    job.updated_at = datetime.now(UTC)

    if retryable and job.retry_count < settings.PUBLISH_MAX_RETRIES:
        job.status = PublishJobStatus.PENDING
        session.add(job)
        await session.commit()
        defer = min(600, 30 * (2 ** (job.retry_count - 1)))
        logger.warning(
            "Publish job will retry",
            draft_id=str(draft.id),
            retry_count=job.retry_count,
            defer_seconds=defer,
        )
        raise Retry(defer=defer)

    job.status = PublishJobStatus.FAILED
    draft.status = ContentDraftStatus.FAILED
    draft.updated_at = datetime.now(UTC)
    session.add(job)
    session.add(draft)
    await session.commit()
    logger.error(
        "Publish job failed permanently",
        draft_id=str(draft.id),
        error=error_message,
    )


def assert_draft_editable(status: ContentDraftStatus) -> None:
    if status not in EDITABLE_DRAFT_STATUSES:
        raise HTTPException(
            status_code=400,
            detail="Cannot edit a draft after it has been scheduled for publishing.",
        )
