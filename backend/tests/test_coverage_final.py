import pytest
from httpx import AsyncClient

from app.db.database import get_session


@pytest.mark.asyncio
async def test_welcome_db_failure_coverage(client: AsyncClient, mocker):
    # We can override the dependency specifically for this test
    async def override_get_session_fail():
        mock_session = mocker.AsyncMock()
        mock_session.execute.side_effect = Exception("DB Fail")
        yield mock_session

    from app.main import app

    app.dependency_overrides[get_session] = override_get_session_fail

    response = await client.get("/api/v1/checkDBConnection")
    assert response.status_code == 500
    assert "Database connection failed" in response.json()["detail"]

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_main_sentry_coverage(mocker):
    mocker.patch("app.main.settings.SENTRY_DSN", "http://key@sentry.io/1")
    mock_init = mocker.patch("app.main.sentry_sdk.init")

    # We need to re-import or reload main to hit the init code
    import importlib

    import app.main

    importlib.reload(app.main)

    assert mock_init.called
