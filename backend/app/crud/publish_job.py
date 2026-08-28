import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.content import PublishJob, PublishJobStatus


async def get_latest_publish_job(
    *, session: AsyncSession, draft_id: uuid.UUID
) -> PublishJob | None:
    statement = (
        select(PublishJob)
        .where(PublishJob.content_draft_id == draft_id)
        .order_by(PublishJob.created_at.desc())  # type: ignore[attr-defined]
    )
    result = await session.execute(statement)
    return result.scalars().first()


async def get_active_publish_job(
    *, session: AsyncSession, draft_id: uuid.UUID
) -> PublishJob | None:
    statement = (
        select(PublishJob)
        .where(PublishJob.content_draft_id == draft_id)
        .where(
            PublishJob.status.in_(
                [PublishJobStatus.PENDING, PublishJobStatus.RUNNING]
            )
        )
        .order_by(PublishJob.created_at.desc())  # type: ignore[attr-defined]
    )
    result = await session.execute(statement)
    return result.scalars().first()


async def create_publish_job(
    *,
    session: AsyncSession,
    draft_id: uuid.UUID,
    scheduled_at: datetime | None,
) -> PublishJob:
    now = datetime.now(UTC)
    job = PublishJob(
        content_draft_id=draft_id,
        status=PublishJobStatus.PENDING,
        scheduled_at=scheduled_at or now,
    )
    session.add(job)
    await session.flush()
    return job
