import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserCreate, UserRole


@pytest.mark.asyncio
async def test_signup_user_success(client: AsyncClient):
    import secrets

    email = f"signup_{secrets.randbelow(9000)}@example.com"
    response = await client.post(
        "/api/v1/login/signup",
        json={
            "email": email,
            "password": "password123",  # noqa: S106
            "full_name": "Signup User",
        },
    )
    assert response.status_code == 200
    assert response.json()["email"] == email


@pytest.mark.asyncio
async def test_recover_password_flow(
    client: AsyncClient, session: AsyncSession, mocker
):
    from app.crud import user as user_crud

    email = "recover_test@example.com"
    user_in = UserCreate(
        full_name="Recover User",
        email=email,
        password="password123",  # noqa: S106
        role=UserRole.USER,
    )
    await user_crud.create_user(session=session, user_create=user_in)

    mocker.patch(
        "app.api.v1.endpoints.login.security.render_email_template",
        return_value="<html>Reset</html>",
    )
    mock_send = mocker.patch("app.api.v1.endpoints.login.security.send_email")

    response = await client.post(f"/api/v1/login/password-recovery/{email}")
    assert response.status_code == 200
    assert "message" in response.json()
    mock_send.assert_called_once()


@pytest.mark.asyncio
async def test_login_access_token_inactive_coverage(
    client: AsyncClient, session: AsyncSession
):
    import secrets

    from app.crud import user as user_crud

    email = f"inactive_{secrets.randbelow(9000)}@example.com"
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
    assert response.json()["detail"] == "Inactive user"


@pytest.mark.asyncio
async def test_signup_user_duplicate(client: AsyncClient, session: AsyncSession):
    from app.crud import user as user_crud

    email = "duplicate@example.com"
    await user_crud.create_user(
        session=session,
        user_create=UserCreate(
            email=email,
            password="password123",
            full_name="Existing User",
        ),
    )
    response = await client.post(
        "/api/v1/login/signup",
        json={
            "email": email,
            "password": "password123",
            "full_name": "Signup User",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "User with this email already exists"


@pytest.mark.asyncio
async def test_recover_password_nonexistent(client: AsyncClient):
    # Should still return 200 to prevent enumeration
    response = await client.post(
        "/api/v1/login/password-recovery/nonexistent@example.com"
    )
    assert response.status_code == 200
    assert "message" in response.json()


@pytest.mark.asyncio
async def test_read_secure_data(client: AsyncClient, normal_user_token: str):
    response = await client.get(
        "/api/v1/login/secure-data",
        headers={"Authorization": f"Bearer {normal_user_token}"},
    )
    assert response.status_code == 200
    assert response.json()["token"] == normal_user_token
