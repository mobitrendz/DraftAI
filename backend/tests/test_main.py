import pytest
from httpx import AsyncClient

from app.main import app, lifespan


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get(
        "/api/v1/welcome/health"
    )  # Wait, health is at /health or /api/v1/health?
    # app.main has @app.get("/health")
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_lifespan(capsys):
    async with lifespan(app):
        pass
    captured = capsys.readouterr()
    assert "--- START SEEDING INITIAL DATA ---" in captured.out
    assert "--- SYSTEM SHUTDOWN ---" in captured.out


@pytest.mark.asyncio
async def test_lifespan_creates_superuser(mocker):
    # Mock user_crud.get_user_by_email or result of select
    mock_execute = mocker.patch("sqlalchemy.ext.asyncio.AsyncSession.execute")
    mock_result = mocker.Mock()
    mock_result.scalars.return_value.first.return_value = None
    mock_execute.return_value = mock_result

    mock_create = mocker.patch("app.crud.user.create_user")

    async with lifespan(app):
        pass

    mock_create.assert_called_once()


@pytest.mark.asyncio
async def test_lifespan_error(mocker, capsys):
    mocker.patch("app.db.initial_data.init", side_effect=Exception("Seeding failed"))
    async with lifespan(app):
        pass
    captured = capsys.readouterr()
    assert '"event": "Seeding failed"' in captured.out
    assert '"error": "Seeding failed"' in captured.out


@pytest.mark.asyncio
async def test_initial_data_main(mocker):
    from app.db import initial_data

    mock_init = mocker.patch("app.db.initial_data.init")
    # Simulate if __name__ == "__main__":
    await initial_data.main()
    mock_init.assert_called_once()
