import uuid
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ALLOW_ADMIN, get_current_user
from app.core import security
from app.crud import user as user_crud
from app.models.user import UpdatePassword, UserCreate, UserRole, UserUpdate


@pytest.mark.asyncio
async def test_get_users_crud(session: AsyncSession):
    users = await user_crud.get_users(session=session)
    assert users.count >= 1


@pytest.mark.asyncio
async def test_update_user_not_found_crud(session: AsyncSession):
    update_data = UserUpdate(full_name="New Name")
    result = await user_crud.update_user(
        session=session, id=uuid.uuid4(), user_update=update_data
    )
    assert result is None


@pytest.mark.asyncio
async def test_delete_user_not_found_crud(session: AsyncSession):
    result = await user_crud.delete_user(session=session, id=uuid.uuid4())
    assert result is False


@pytest.mark.asyncio
async def test_authenticate_user_incorrect_password_crud(session: AsyncSession):
    email = "auth_fail@example.com"
    user_in = UserCreate(
        full_name="Auth Fail",
        email=email,
        password="correctpassword",  # noqa: S106
        role=UserRole.USER,
    )
    await user_crud.create_user(session=session, user_create=user_in)

    user = await user_crud.authenticate_user(
        session=session, email=email, password="wrongpassword"
    )  # noqa: S106
    assert user is None


@pytest.mark.asyncio
async def test_update_password_incorrect_password(session: AsyncSession):
    email = "pass_fail@example.com"
    user_in = UserCreate(
        full_name="Pass Fail",
        email=email,
        password="oldpassword",  # noqa: S106
        role=UserRole.USER,
    )
    user = await user_crud.create_user(session=session, user_create=user_in)

    update_data = UpdatePassword(
        current_password="wrongpassword", new_password="newpassword"
    )  # noqa: S106
    with pytest.raises(HTTPException) as exc:
        await user_crud.update_password(
            session=session, updatePassword=update_data, current_user=user
        )
    assert exc.value.status_code == 400
    assert exc.value.detail == "Incorrect password"


@pytest.mark.asyncio
async def test_update_password_same_as_old(session: AsyncSession):
    email = "pass_same@example.com"
    user_in = UserCreate(
        full_name="Pass Same",
        email=email,
        password="password123",  # noqa: S106
        role=UserRole.USER,
    )
    user = await user_crud.create_user(session=session, user_create=user_in)

    update_data = UpdatePassword(
        current_password="password123", new_password="password123"
    )  # noqa: S106
    with pytest.raises(HTTPException) as exc:
        await user_crud.update_password(
            session=session, updatePassword=update_data, current_user=user
        )
    assert exc.value.status_code == 400
    assert exc.value.detail == "New password cannot be the same as the current one"


@pytest.mark.asyncio
async def test_role_checker_unauthorized(session: AsyncSession):
    user_in = UserCreate(
        full_name="Normal User",
        email="role_fail@example.com",
        password="password123",  # noqa: S106
        role=UserRole.USER,
    )
    user = await user_crud.create_user(session=session, user_create=user_in)

    checker = ALLOW_ADMIN
    with pytest.raises(HTTPException) as exc:
        checker(current_user=user)
    assert exc.value.status_code == 403
    assert exc.value.detail == "You do not have the necessary permissions."


@pytest.mark.asyncio
async def test_get_current_user_inactive_crud(session: AsyncSession):
    user_in = UserCreate(
        full_name="Inactive User",
        email="inactive_crud@example.com",
        password="password123",  # noqa: S106
        role=UserRole.USER,
        is_active=False,
    )
    user = await user_crud.create_user(session=session, user_create=user_in)

    token = security.create_access_token(str(user.id))
    mock_request = MagicMock()
    with pytest.raises(HTTPException) as exc:
        await get_current_user(request=mock_request, session=session, token=token)
    assert exc.value.status_code == 400
    assert exc.value.detail == "Inactive user"


@pytest.mark.asyncio
async def test_get_password_history_empty(session: AsyncSession):
    email = "pass_hist_empty@example.com"
    user_in = UserCreate(
        full_name="Hist User",
        email=email,
        password="password123",
        role=UserRole.USER,
    )
    user = await user_crud.create_user(session=session, user_create=user_in)

    history = await user_crud.get_password_history(session=session, user_id=user.id)
    assert history.count == 0
    assert len(history.data) == 0
