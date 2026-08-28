import uuid
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core import security
from app.crud import user as user_crud
from app.models.user import UserCreate


@pytest.mark.asyncio
async def test_users_missing_branches(client: AsyncClient, superuser_token: str):
    # Line 40-46: User with this email already exists
    email = "already_92@example.com"
    await client.post(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {superuser_token}"},
        json={"email": email, "password": "password123", "full_name": "User 1"},  # noqa: S106
    )
    response = await client.post(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {superuser_token}"},
        json={"email": email, "password": "password123", "full_name": "User 2"},  # noqa: S106
    )
    assert response.status_code == 400
    assert "exists" in response.json()["detail"]

    # Line 67-69: read_user_by_id not found
    response = await client.get(
        f"/api/v1/users/byID/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {superuser_token}"},
    )
    assert response.status_code == 404

    # Line 78-80: read_user_by_email not found
    response = await client.get(
        "/api/v1/users/byEmail/nonexistent_92@example.com",
        headers={"Authorization": f"Bearer {superuser_token}"},
    )
    assert response.status_code == 404

    # Line 118-120: update_user not found
    response = await client.patch(
        f"/api/v1/users/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {superuser_token}"},
        json={"full_name": "New Name"},
    )
    assert response.status_code == 404

    # Line 130-133: delete_user not found
    response = await client.delete(
        f"/api/v1/users/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {superuser_token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_login_missing_branches(client: AsyncClient):
    # Line 38-40: Incorrect email or password
    response = await client.post(
        "/api/v1/login/access-token",
        data={"username": "wrong_92@example.com", "password": "wrongpassword"},  # noqa: S106
    )
    assert response.status_code == 400
    assert "Incorrect" in response.json()["detail"]


@pytest.mark.asyncio
async def test_signup_success_coverage(client: AsyncClient):
    import secrets

    email = f"signup_92_{secrets.randbelow(9999)}@example.com"
    response = await client.post(
        "/api/v1/login/signup",
        json={"email": email, "password": "password123", "full_name": "New User"},  # noqa: S106
    )
    assert response.status_code == 200
    assert response.json()["email"] == email


@pytest.mark.asyncio
async def test_login_inactive_user_coverage(client: AsyncClient, session: AsyncSession):
    email = "inactive_92@example.com"
    await user_crud.create_user(
        session=session,
        user_create=UserCreate(
            email=email,
            password="password123",
            full_name="Inactive",
            is_active=False,  # noqa: S106
        ),
    )
    response = await client.post(
        "/api/v1/login/access-token",
        data={"username": email, "password": "password123"},  # noqa: S106
    )
    assert response.status_code == 400
    assert "Inactive" in response.json()["detail"]


@pytest.mark.asyncio
async def test_crud_missing_branches(session: AsyncSession):
    # Line 102: authenticate_user user not found
    res = await user_crud.authenticate_user(
        session=session, email="none_92@example.com", password="any"
    )  # noqa: S106
    assert res is None

    # Line 128: get_current_user user not found
    mock_request = MagicMock()
    with pytest.raises(HTTPException) as exc:
        await get_current_user(
            request=mock_request,
            session=session,
            token=security.create_access_token(str(uuid.uuid4())),
        )
    assert exc.value.status_code == 404

    # Line 131: get_current_user inactive user
    user = await user_crud.create_user(
        session=session,
        user_create=UserCreate(
            email="inactive_crud_92@example.com",
            password="password123",
            full_name="Inactive",
            is_active=False,  # noqa: S106
        ),
    )
    token = security.create_access_token(str(user.id))
    with pytest.raises(HTTPException) as exc:
        await get_current_user(request=mock_request, session=session, token=token)
    assert exc.value.status_code == 400
