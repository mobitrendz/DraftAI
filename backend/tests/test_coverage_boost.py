import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.crud import user as user_crud
from app.models.user import UpdatePassword, UserCreate, UserRole, UserUpdate


@pytest.mark.asyncio
async def test_authenticate_user_not_found_crud(session: AsyncSession):
    # This hits the DUMMY_HASH timing attack branch
    result = await user_crud.authenticate_user(
        session=session, email="nonexistent_boost@example.com", password="password"
    )  # noqa: S106
    assert result is None


@pytest.mark.asyncio
async def test_update_password_incorrect_password_crud(session: AsyncSession):
    user_in = UserCreate(
        full_name="Pass Fail",
        email="pass_fail_boost@example.com",
        password="oldpassword",  # noqa: S106
        role=UserRole.USER,
    )
    user = await user_crud.create_user(session=session, user_create=user_in)

    update_data = UpdatePassword(
        current_password="wrongpassword", new_password="newpassword"
    )  # noqa: S106
    with pytest.raises(HTTPException):  # Hits HTTPException in crud
        await user_crud.update_password(
            session=session, updatePassword=update_data, current_user=user
        )


@pytest.mark.asyncio
async def test_signup_already_exists_api(client: AsyncClient, session: AsyncSession):
    email = "signup_exists@example.com"
    await user_crud.create_user(
        session=session,
        user_create=UserCreate(
            email=email,
            password="password123",
            full_name="User 1",  # noqa: S106
        ),
    )

    response = await client.post(
        "/api/v1/login/signup",
        json={"email": email, "password": "password123", "full_name": "User 2"},  # noqa: S106
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_recover_password_user_exists_api(
    client: AsyncClient, session: AsyncSession, mocker
):
    email = "recover_exists@example.com"
    await user_crud.create_user(
        session=session,
        user_create=UserCreate(
            email=email,
            password="password123",
            full_name="Recover Me",  # noqa: S106
        ),
    )

    mocker.patch(
        "app.api.v1.endpoints.login.security.render_email_template", return_value="html"
    )
    mock_send = mocker.patch("app.api.v1.endpoints.login.security.send_email")

    response = await client.post(f"/api/v1/login/password-recovery/{email}")
    assert response.status_code == 200
    mock_send.assert_called_once()


@pytest.mark.asyncio
async def test_read_users_as_normal_user_api(
    client: AsyncClient, normal_user_token: str
):
    response = await client.get(
        "/api/v1/users/", headers={"Authorization": f"Bearer {normal_user_token}"}
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_user_role_as_normal_user_api(
    client: AsyncClient, normal_user_token: str
):
    current_user_res = await client.get(
        "/api/v1/login/current-user",
        headers={"Authorization": f"Bearer {normal_user_token}"},
    )
    user_id = current_user_res.json()["id"]

    response = await client.patch(
        f"/api/v1/users/{user_id}",
        headers={"Authorization": f"Bearer {normal_user_token}"},
        json={"role": "admin"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_login_inactive_user_api(client: AsyncClient, session: AsyncSession):
    email = "inactive_boost@example.com"
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
async def test_get_current_user_inactive_api(
    client: AsyncClient, session: AsyncSession
):
    email = "inactive_token@example.com"
    user = await user_crud.create_user(
        session=session,
        user_create=UserCreate(
            email=email,
            password="password123",
            full_name="Inactive Token",
            is_active=True,  # noqa: S106
        ),
    )
    token = security.create_access_token(str(user.id))

    # Deactivate user after token generation
    await user_crud.update_user(
        session=session, id=user.id, user_update=UserUpdate(is_active=False)
    )

    response = await client.get(
        "/api/v1/login/current-user", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Inactive user"
