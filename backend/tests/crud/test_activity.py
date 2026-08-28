import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import activity as activity_crud
from app.crud import user as user_crud
from app.models.user import UserCreate, UserRole


@pytest.mark.asyncio
async def test_create_activity(session: AsyncSession):
    # Create a user first
    user_in = UserCreate(
        full_name="Activity User",
        email="activity_user@example.com",
        password="password123",
        role=UserRole.USER,
    )
    user = await user_crud.create_user(session=session, user_create=user_in)

    activity = await activity_crud.create_activity(
        session=session,
        user_id=user.id,
        method="GET",
        path="/api/v1/users/me",
        status_code=200,
        ip_address="127.0.0.1",
        user_agent="Pytest",
    )

    assert activity.user_id == user.id
    assert activity.method == "GET"
    assert activity.path == "/api/v1/users/me"
    assert activity.status_code == 200
    assert activity.ip_address == "127.0.0.1"
    assert activity.user_agent == "Pytest"
    assert activity.id is not None
    assert activity.created_at is not None


@pytest.mark.asyncio
async def test_get_user_activities(session: AsyncSession):
    # Create a user
    user_in = UserCreate(
        full_name="Activity Get User",
        email="activity_get@example.com",
        password="password123",
        role=UserRole.USER,
    )
    user = await user_crud.create_user(session=session, user_create=user_in)

    # Create multiple activities
    for i in range(5):
        await activity_crud.create_activity(
            session=session,
            user_id=user.id,
            method="GET",
            path=f"/path/{i}",
            status_code=200,
            ip_address="127.0.0.1",
            user_agent="Pytest",
        )

    activities = await activity_crud.get_user_activities(
        session=session, user_id=user.id
    )
    assert activities.count == 5
    assert len(activities.data) == 5
    # Should be ordered by created_at desc, so the last one created is first
    assert activities.data[0].path == "/path/4"
