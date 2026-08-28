import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_welcome_message(client: AsyncClient):
    response = await client.get("/api/v1/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome User!"}


@pytest.mark.asyncio
async def test_get_welcome_message_user(client: AsyncClient):
    response = await client.get("/api/v1/Sreeraj")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome Sreeraj!"}


@pytest.mark.asyncio
async def test_check_db_connection(client: AsyncClient):
    response = await client.get("/api/v1/checkDBConnection")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}


@pytest.mark.asyncio
async def test_get_environment(client: AsyncClient):
    response = await client.get("/api/v1/getEnvironment")
    assert response.status_code == 200
    payload = response.json()
    assert "Environment" in payload
    assert payload["ai_text_generation_timeout_seconds"] == "120"
    assert payload["ai_draft_generation_max_seconds"] == "300"
