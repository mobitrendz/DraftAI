import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ALLOW_ADMIN
from app.crud import user as user_crud
from app.models.user import UserCreate, UserRole


@pytest.mark.asyncio
async def test_get_user_by_id_crud_none(session: AsyncSession):
    result = await user_crud.get_user_by_id(session=session, id=uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_get_user_by_email_crud_none(session: AsyncSession):
    result = await user_crud.get_user_by_email(
        session=session, email="none@example.com"
    )
    assert result is None


@pytest.mark.asyncio
async def test_delete_user_not_found_coverage(session: AsyncSession):
    result = await user_crud.delete_user(session=session, id=uuid.uuid4())
    assert result is False


@pytest.mark.asyncio
async def test_role_checker_success(session: AsyncSession):
    user_in = UserCreate(
        full_name="Admin User",
        email="admin_check@example.com",
        password="password123",  # noqa: S106
        role=UserRole.ADMIN,
    )
    user = await user_crud.create_user(session=session, user_create=user_in)

    checker = ALLOW_ADMIN
    res = checker(current_user=user)
    assert res.id == user.id
