from uuid import UUID

import structlog
from arq import create_pool
from arq.connections import ArqRedis, RedisSettings
from arq.constants import default_queue_name, in_progress_key_prefix, job_key_prefix, result_key_prefix

from app.core.config import settings

logger = structlog.get_logger(__name__)

_pool: ArqRedis | None = None

PUBLISH_JOB_ID_PREFIX = "publish-"


def publish_job_id(draft_id: UUID) -> str:
    return f"{PUBLISH_JOB_ID_PREFIX}{draft_id}"


async def get_arq_pool() -> ArqRedis:
    global _pool
    if _pool is None:
        _pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
    return _pool


async def close_arq_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def cancel_publish_job(*, draft_id: UUID) -> None:
    """Remove a queued (not yet running) publish job from Redis."""
    pool = await get_arq_pool()
    job_id = publish_job_id(draft_id)
    async with pool.pipeline(transaction=True) as pipe:
        pipe.zrem(default_queue_name, job_id)
        pipe.delete(job_key_prefix + job_id)
        pipe.delete(result_key_prefix + job_id)
        await pipe.execute()
    logger.info("Cancelled queued publish job", draft_id=str(draft_id))


async def is_publish_job_in_progress(*, draft_id: UUID) -> bool:
    pool = await get_arq_pool()
    job_id = publish_job_id(draft_id)
    return bool(await pool.exists(in_progress_key_prefix + job_id))


async def enqueue_publish_job(*, draft_id: UUID, defer_by: float = 0) -> None:
    pool = await get_arq_pool()
    job_id = publish_job_id(draft_id)
    kwargs: dict[str, object] = {"draft_id": str(draft_id)}
    if defer_by > 0:
        await pool.enqueue_job(
            "publish_draft_job",
            **kwargs,
            _job_id=job_id,
            _defer_by=int(defer_by),
        )
        logger.info(
            "Scheduled publish job",
            draft_id=str(draft_id),
            defer_by_seconds=int(defer_by),
        )
        return
    await pool.enqueue_job("publish_draft_job", **kwargs, _job_id=job_id)
    logger.info("Enqueued publish job", draft_id=str(draft_id))
