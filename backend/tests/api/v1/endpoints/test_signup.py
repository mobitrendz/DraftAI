import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import user as user_crud
from app.models.user import UserCreate, UserRole


@pytest.mark.asyncio
async def test_signup_success(client: AsyncClient):
    response = await client.post(
        "/api/v1/login/signup",
        json={
            "email": "newuser@example.com",
            "password": "password123",
            "full_name": "New User",
        },
    )
    assert response.status_code == 200
    assert response.json()["email"] == "newuser@example.com"


@pytest.mark.asyncio
async def test_signup_existing_email(client: AsyncClient, session: AsyncSession):
    # Ensure user exists with a unique email
    email = "existing-user@example.com"
    user_in = UserCreate(
        full_name="Existing User",
        email=email,
        password="password123",  # noqa: S106
        role=UserRole.USER,
    )
    await user_crud.create_user(session=session, user_create=user_in)

    # Attempt to sign up with the same email
    response = await client.post(
        "/api/v1/login/signup",
        json={
            "email": email,
            "password": "password123",
            "full_name": "New User",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "User with this email already exists"
