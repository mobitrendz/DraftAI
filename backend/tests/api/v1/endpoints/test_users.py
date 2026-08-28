import pytest
from httpx import AsyncClient

from app.core.config import settings


@pytest.mark.asyncio
async def test_create_user(client: AsyncClient, superuser_token: str):  # noqa: ARG001
    import secrets

    email = f"user_{secrets.randbelow(9000) + 1000}@example.com"
    response = await client.post(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {superuser_token}"},
        json={
            "full_name": "New User",
            "email": email,
            "password": "newpassword123",  # noqa: S106
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == email
    assert "id" in data


@pytest.mark.asyncio
async def test_create_user_not_admin(client: AsyncClient, normal_user_token: str):
    response = await client.post(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {normal_user_token}"},
        json={
            "full_name": "Another User",
            "email": "another@example.com",
            "password": "password123",  # noqa: S106
        },
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_read_users(client: AsyncClient, superuser_token: str):
    response = await client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {superuser_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_read_user_by_id(client: AsyncClient, superuser_token: str):
    # First get all users to find an ID
    response = await client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {superuser_token}"},
    )
    user_id = response.json()["items"][0]["id"]

    response = await client.get(
        f"/api/v1/users/byID/{user_id}",
        headers={"Authorization": f"Bearer {superuser_token}"},
    )
    assert response.status_code == 200
    assert response.json()["id"] == user_id


@pytest.mark.asyncio
async def test_update_user(client: AsyncClient, superuser_token: str):
    # Get a user ID
    response = await client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {superuser_token}"},
    )
    user_id = response.json()["items"][0]["id"]

    response = await client.patch(
        f"/api/v1/users/{user_id}",
        headers={"Authorization": f"Bearer {superuser_token}"},
        json={"full_name": "Updated Name"},
    )
    assert response.status_code == 200
    assert response.json()["full_name"] == "Updated Name"


@pytest.mark.asyncio
async def test_admin_can_update_user_role_and_active_status(
    client: AsyncClient, superuser_token: str
):
    import secrets

    email = f"role_update_{secrets.randbelow(9000) + 1000}@example.com"
    create_response = await client.post(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {superuser_token}"},
        json={
            "full_name": "Role Update",
            "email": email,
            "password": "password123",  # noqa: S106
        },
    )
    user_id = create_response.json()["id"]

    response = await client.patch(
        f"/api/v1/users/{user_id}",
        headers={"Authorization": f"Bearer {superuser_token}"},
        json={"role": "super", "is_active": False},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "super"
    assert data["is_active"] is False


@pytest.mark.asyncio
async def test_normal_user_cannot_update_role_or_active_status(
    client: AsyncClient, normal_user_token: str
):
    current_user_response = await client.get(
        "/api/v1/login/current-user",
        headers={"Authorization": f"Bearer {normal_user_token}"},
    )
    user_id = current_user_response.json()["id"]

    response = await client.patch(
        f"/api/v1/users/{user_id}",
        headers={"Authorization": f"Bearer {normal_user_token}"},
        json={"role": "admin", "is_active": False},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_user(client: AsyncClient, superuser_token: str):
    import secrets

    email = f"delete_{secrets.randbelow(9000) + 1000}@example.com"
    # Create a user to delete
    await client.post(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {superuser_token}"},
        json={
            "full_name": "Delete Me",
            "email": email,
            "password": "password123",  # noqa: S106
        },
    )

    # Get the ID
    response = await client.get(
        f"/api/v1/users/byEmail/{email}",
        headers={"Authorization": f"Bearer {superuser_token}"},
    )
    user_id = response.json()["id"]

    response = await client.delete(
        f"/api/v1/users/{user_id}",
        headers={"Authorization": f"Bearer {superuser_token}"},
    )
    assert response.status_code == 200
    assert response.json()["message"] == "User deleted successfully"


@pytest.mark.asyncio
async def test_get_user_by_email(client: AsyncClient, superuser_token: str):
    response = await client.get(
        f"/api/v1/users/byEmail/{settings.SUPER_USER_EMAIL}",
        headers={"Authorization": f"Bearer {superuser_token}"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == settings.SUPER_USER_EMAIL


@pytest.mark.asyncio
async def test_read_user_by_id_not_found(client: AsyncClient, superuser_token: str):
    import uuid

    random_id = uuid.uuid4()
    response = await client.get(
        f"/api/v1/users/byID/{random_id}",
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
    import uuid

    random_id = uuid.uuid4()
    response = await client.patch(
        f"/api/v1/users/{random_id}",
        headers={"Authorization": f"Bearer {superuser_token}"},
        json={"full_name": "Updated Name"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_user_not_found(client: AsyncClient, superuser_token: str):
    import uuid

    random_id = uuid.uuid4()
    response = await client.delete(
        f"/api/v1/users/{random_id}",
        headers={"Authorization": f"Bearer {superuser_token}"},
    )
    assert response.status_code == 404
