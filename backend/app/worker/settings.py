from arq.connections import RedisSettings

from app.core.config import settings
from app.worker import tasks


class WorkerSettings:
    """ARQ worker configuration for DraftAI publish jobs."""

    functions = [tasks.publish_draft_job, tasks.worker_healthcheck]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    on_startup = tasks.on_startup
    on_shutdown = tasks.on_shutdown
    max_jobs = 10
    job_timeout = settings.ARQ_JOB_TIMEOUT_SECONDS
