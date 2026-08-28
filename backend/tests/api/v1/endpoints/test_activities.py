import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import activity as activity_crud


@pytest.mark.asyncio
async def test_read_my_activities(
    client: AsyncClient, normal_user_token: str, session: AsyncSession
):
    # Get user to create some activities for them
    from app.crud import user as user_crud

    user = await user_crud.get_user_by_email(
        session=session, email="test_user@example.com"
    )
    assert user is not None

    # Create an activity
    await activity_crud.create_activity(
        session=session,
        user_id=user.id,
        method="GET",
        path="/api/v1/users/me",
        status_code=200,
        ip_address="127.0.0.1",
        user_agent="Pytest",
    )

    response = await client.get(
        "/api/v1/activities/me",
        headers={"Authorization": f"Bearer {normal_user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["count"] >= 1
    assert data["data"][0]["method"] == "GET"
    assert data["data"][0]["path"] == "/api/v1/users/me"


@pytest.mark.asyncio
async def test_read_all_activities_superuser(
    client: AsyncClient, superuser_token: str, session: AsyncSession
):
    # Create an activity for someone
    await activity_crud.create_activity(
        session=session,
        user_id=None,  # System activity or anonymous
        method="POST",
        path="/api/v1/login",
        status_code=200,
        ip_address="127.0.0.1",
        user_agent="Pytest",
    )

    response = await client.get(
        "/api/v1/activities/", headers={"Authorization": f"Bearer {superuser_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_read_all_activities_forbidden(
    client: AsyncClient, normal_user_token: str
):
    response = await client.get(
        "/api/v1/activities/", headers={"Authorization": f"Bearer {normal_user_token}"}
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "You do not have the necessary permissions."
