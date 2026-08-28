import uuid

import structlog

from app.db.database import async_session_maker
from app.services.publish import execute_publish_job

logger = structlog.get_logger(__name__)


async def worker_healthcheck(_ctx: dict) -> str:
    logger.info("ARQ worker healthcheck")
    return "ok"


async def publish_draft_job(_ctx: dict, *, draft_id: str) -> str:
    """Publish a draft to DEV.to and prepare LinkedIn clipboard text."""
    logger.info("Starting publish job", draft_id=draft_id)
    async with async_session_maker() as session:
        await execute_publish_job(
            session=session, draft_id=uuid.UUID(draft_id)
        )
    return "published"


async def on_startup(ctx: dict) -> None:
    logger.info("DraftAI ARQ worker started")


async def on_shutdown(ctx: dict) -> None:
    logger.info("DraftAI ARQ worker shutting down")
