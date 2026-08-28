import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserCreate


@pytest.mark.asyncio
async def test_create_user_already_exists(client: AsyncClient, superuser_token: str):
    email = "existing_user@example.com"
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
    assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_read_user_by_id_not_found(client: AsyncClient, superuser_token: str):
    response = await client.get(
        f"/api/v1/users/byID/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {superuser_token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_read_user_by_email_not_found(client: AsyncClient, superuser_token: str):
    response = await client.get(
        "/api/v1/users/byEmail/nonexistent@example.com",
        headers={"Authorization": f"Bearer {superuser_token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_user_not_found(client: AsyncClient, superuser_token: str):
    response = await client.patch(
        f"/api/v1/users/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {superuser_token}"},
        json={"full_name": "New Name"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_user_not_found(client: AsyncClient, superuser_token: str):
    response = await client.delete(
        f"/api/v1/users/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {superuser_token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_user_forbidden(
    client: AsyncClient, normal_user_token: str, session: AsyncSession
):
    from app.crud import user as user_crud

    other_user = await user_crud.create_user(
        session=session,
        user_create=UserCreate(
            email="other_forb@example.com",
            password="password123",
            full_name="Other",  # noqa: S106
        ),
    )
    response = await client.patch(
        f"/api/v1/users/{other_user.id}",
        headers={"Authorization": f"Bearer {normal_user_token}"},
        json={"full_name": "Hacked"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_read_users_forbidden(client: AsyncClient, normal_user_token: str):
    response = await client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {normal_user_token}"},
    )
    assert response.status_code == 403
