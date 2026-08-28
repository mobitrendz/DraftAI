import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_check_database_connection_failure(client: AsyncClient, mocker):
    # Mock session.execute to raise an exception
    # Need to find where Session.execute is called or mock the dependency
    mocker.patch(
        "app.api.v1.endpoints.welcome.select"
    )  # Mock select to fail? No, select(1) just creates a statement.

    # Mocking the session itself might be better
    from sqlalchemy.exc import SQLAlchemyError

    mocker.patch(
        "sqlalchemy.ext.asyncio.AsyncSession.execute",
        side_effect=SQLAlchemyError("Connection failed"),
    )

    response = await client.get("/api/v1/checkDBConnection")
    assert response.status_code == 500
    assert "Database connection failed" in response.json()["detail"]
