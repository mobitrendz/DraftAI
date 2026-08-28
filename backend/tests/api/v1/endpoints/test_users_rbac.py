import pytest
from httpx import AsyncClient

from app.models.user import UserRole


@pytest.mark.asyncio
async def test_admin_cannot_create_super_user(
    client: AsyncClient, admin_user_token: str
):
    response = await client.post(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {admin_user_token}"},
        json={
            "full_name": "New Super",
            "email": "newsuper@example.com",
            "password": "password123",
            "role": UserRole.SUPER,
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Admins can only create regular users."


@pytest.mark.asyncio
async def test_admin_cannot_create_another_admin(
    client: AsyncClient, admin_user_token: str
):
    response = await client.post(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {admin_user_token}"},
        json={
            "full_name": "New Admin",
            "email": "newadmin@example.com",
            "password": "password123",
            "role": UserRole.ADMIN,
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Admins can only create regular users."


@pytest.mark.asyncio
async def test_admin_can_create_regular_user(
    client: AsyncClient, admin_user_token: str
):
    import secrets

    email = f"user_{secrets.randbelow(9000) + 1000}@example.com"
    response = await client.post(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {admin_user_token}"},
        json={
            "full_name": "Regular User",
            "email": email,
            "password": "password123",
            "role": UserRole.USER,
        },
    )
    assert response.status_code == 200
    assert response.json()["email"] == email


@pytest.mark.asyncio
async def test_admin_cannot_see_super_user_by_id(
    client: AsyncClient, admin_user_token: str, superuser_token: str
):
    # Get superuser id
    me_response = await client.get(
        "/api/v1/login/current-user",
        headers={"Authorization": f"Bearer {superuser_token}"},
    )
    superuser_id = me_response.json()["id"]

    response = await client.get(
        f"/api/v1/users/byID/{superuser_id}",
        headers={"Authorization": f"Bearer {admin_user_token}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Not enough permissions"


@pytest.mark.asyncio
async def test_admin_cannot_see_super_user_by_email(
    client: AsyncClient, admin_user_token: str, superuser_token: str
):
    # Get superuser email
    me_response = await client.get(
        "/api/v1/login/current-user",
        headers={"Authorization": f"Bearer {superuser_token}"},
    )
    superuser_email = me_response.json()["email"]

    response = await client.get(
        f"/api/v1/users/byEmail/{superuser_email}",
        headers={"Authorization": f"Bearer {admin_user_token}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Not enough permissions"


@pytest.mark.asyncio
async def test_admin_cannot_update_super_user(
    client: AsyncClient, admin_user_token: str, superuser_token: str
):
    me_response = await client.get(
        "/api/v1/login/current-user",
        headers={"Authorization": f"Bearer {superuser_token}"},
    )
    superuser_id = me_response.json()["id"]

    response = await client.patch(
        f"/api/v1/users/{superuser_id}",
        headers={"Authorization": f"Bearer {admin_user_token}"},
        json={"full_name": "Hacked"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Admins can only manage regular users."


@pytest.mark.asyncio
async def test_admin_cannot_delete_super_user(
    client: AsyncClient, admin_user_token: str, superuser_token: str
):
    me_response = await client.get(
        "/api/v1/login/current-user",
        headers={"Authorization": f"Bearer {superuser_token}"},
    )
    superuser_id = me_response.json()["id"]

    response = await client.delete(
        f"/api/v1/users/{superuser_id}",
        headers={"Authorization": f"Bearer {admin_user_token}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Admins can only delete regular users."


@pytest.mark.asyncio
async def test_user_cannot_update_own_role(client: AsyncClient, normal_user_token: str):
    me_response = await client.get(
        "/api/v1/login/current-user",
        headers={"Authorization": f"Bearer {normal_user_token}"},
    )
    user_id = me_response.json()["id"]

    response = await client.patch(
        f"/api/v1/users/{user_id}",
        headers={"Authorization": f"Bearer {normal_user_token}"},
        json={"role": UserRole.SUPER},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Cannot change your own role or active status"


@pytest.mark.asyncio
async def test_user_cannot_update_own_active_status(
    client: AsyncClient, normal_user_token: str
):
    me_response = await client.get(
        "/api/v1/login/current-user",
        headers={"Authorization": f"Bearer {normal_user_token}"},
    )
    user_id = me_response.json()["id"]

    response = await client.patch(
        f"/api/v1/users/{user_id}",
        headers={"Authorization": f"Bearer {normal_user_token}"},
        json={"is_active": False},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Cannot change your own role or active status"
