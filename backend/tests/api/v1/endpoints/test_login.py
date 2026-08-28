import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.config import settings


@pytest.mark.asyncio
async def test_login_access_token(client: AsyncClient, superuser_token: str):  # noqa: ARG001
    # superuser_token fixture already ensures superuser exists
    response = await client.post(
        "/api/v1/login/access-token",
        data={
            "username": settings.SUPER_USER_EMAIL,
            "password": settings.SUPER_USER_PASSWORD,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"  # noqa: S105


@pytest.mark.asyncio
async def test_login_access_token_incorrect_password(client: AsyncClient):
    response = await client.post(
        "/api/v1/login/access-token",
        data={
            "username": settings.SUPER_USER_EMAIL,
            "password": "wrongpassword",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Incorrect email or password"


@pytest.mark.asyncio
async def test_login_access_token_inactive(client: AsyncClient, session: AsyncSession):
    # Use the inactive user created in another test or create a new one
    email = "inactive_login@example.com"
    from app.crud import user as user_crud
    from app.models.user import UserCreate

    user_in = UserCreate(
        full_name="Inactive Login",
        email=email,
        password="password123",  # noqa: S106
        is_active=False,
    )
    await user_crud.create_user(session=session, user_create=user_in)

    response = await client.post(
        "/api/v1/login/access-token",
        data={
            "username": email,
            "password": "password123",  # noqa: S106
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Inactive user"


@pytest.mark.asyncio
async def test_read_secure_data(client: AsyncClient, normal_user_token: str):
    response = await client.get(
        "/api/v1/login/secure-data",
        headers={"Authorization": f"Bearer {normal_user_token}"},
    )
    assert response.status_code == 200
    assert "token" in response.json()


@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient, normal_user_token: str):
    response = await client.get(
        "/api/v1/login/current-user",
        headers={"Authorization": f"Bearer {normal_user_token}"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == "test_user@example.com"


@pytest.mark.asyncio
async def test_get_current_user_invalid_token(client: AsyncClient):
    response = await client.get(
        "/api/v1/login/current-user",
        headers={"Authorization": "Bearer invalidtoken"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_not_found(client: AsyncClient, session: AsyncSession):  # noqa: ARG001
    # Create a token for a non-existent user
    import uuid

    token = security.create_access_token(str(uuid.uuid4()))
    response = await client.get(
        "/api/v1/login/current-user",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_current_user_inactive(client: AsyncClient, session: AsyncSession):
    # Create an inactive user
    from app.crud import user as user_crud
    from app.models.user import UserCreate

    email = "inactive@example.com"
    user_in = UserCreate(
        full_name="Inactive User",
        email=email,
        password="password123",  # noqa: S106
        is_active=False,
    )
    user = await user_crud.create_user(session=session, user_create=user_in)

    token = security.create_access_token(str(user.id))
    response = await client.get(
        "/api/v1/login/current-user",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Inactive user"


@pytest.mark.asyncio
async def test_authenticate_user_not_found(client: AsyncClient):
    response = await client.post(
        "/api/v1/login/access-token",
        data={
            "username": "nonexistent@example.com",
            "password": "somepassword",
        },
    )
    assert response.status_code == 400
