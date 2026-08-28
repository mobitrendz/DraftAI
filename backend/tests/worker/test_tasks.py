import pytest

from app.worker import tasks


@pytest.mark.asyncio
async def test_worker_healthcheck():
    result = await tasks.worker_healthcheck({})
    assert result == "ok"


@pytest.mark.asyncio
async def test_publish_draft_job_calls_execute_publish_job():
    from unittest.mock import AsyncMock, patch

    with patch(
        "app.worker.tasks.execute_publish_job",
        new_callable=AsyncMock,
    ) as mock_execute:
        result = await tasks.publish_draft_job(
            {},
            draft_id="00000000-0000-0000-0000-000000000001",
        )
    mock_execute.assert_awaited_once()
    assert result == "published"


@pytest.mark.asyncio
async def test_worker_startup_shutdown():
    ctx: dict = {}
    await tasks.on_startup(ctx)
    await tasks.on_shutdown(ctx)
