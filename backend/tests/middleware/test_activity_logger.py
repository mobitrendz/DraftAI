import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.activity import UserActivity


@pytest.mark.asyncio
async def test_activity_logger_middleware_logged_in(
    client: AsyncClient, normal_user_token: str, session: AsyncSession
):
    # This request should be logged by the middleware
    response = await client.get(
        "/api/v1/login/current-user",
        headers={"Authorization": f"Bearer {normal_user_token}"},
    )
    assert response.status_code == 200

    # Check if activity was logged
    from app.crud import user as user_crud

    user = await user_crud.get_user_by_email(
        session=session, email="test_user@example.com"
    )
    assert user is not None

    statement = (
        select(UserActivity)
        .where(UserActivity.path == "/api/v1/login/current-user")
        .where(UserActivity.user_id == user.id)
        .order_by(UserActivity.created_at.desc())  # type: ignore
    )
    result = await session.execute(statement)
    activities = result.scalars().all()

    assert len(activities) >= 1
    assert activities[0].method == "GET"
    assert activities[0].status_code == 200


@pytest.mark.asyncio
async def test_activity_logger_middleware_anonymous(
    client: AsyncClient, session: AsyncSession
):
    # This request should be logged as anonymous
    response = await client.get("/health")
    assert response.status_code == 200

    statement = select(UserActivity).where(UserActivity.path == "/health")
    result = await session.execute(statement)
    activities = result.scalars().all()

    assert len(activities) >= 1
    assert activities[0].user_id is None
    assert activities[0].method == "GET"


@pytest.mark.asyncio
async def test_activity_logger_middleware_error(client: AsyncClient, mocker):
    # Mock create_activity to raise an exception
    mocker.patch(
        "app.middleware.activity_logger.create_activity",
        side_effect=Exception("Database error"),
    )

    # The request should still succeed even if logging fails
    response = await client.get("/health")
    assert response.status_code == 200
