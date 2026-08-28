import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserCreate, UserRole


@pytest.mark.asyncio
async def test_update_password_success(client: AsyncClient, normal_user_token: str):
    response = await client.patch(
        "/api/v1/users/password",
        headers={"Authorization": f"Bearer {normal_user_token}"},
        json={"current_password": "password123", "new_password": "newpassword123"},
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Password updated successfully"


@pytest.mark.asyncio
async def test_update_password_incorrect_current(
    client: AsyncClient, normal_user_token: str
):
    response = await client.patch(
        "/api/v1/users/password",
        headers={"Authorization": f"Bearer {normal_user_token}"},
        json={"current_password": "wrongpassword", "new_password": "newpassword123"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Incorrect password"


@pytest.mark.asyncio
async def test_update_password_same_as_current(
    client: AsyncClient, session: AsyncSession
):
    from app.core import security
    from app.crud import user as user_crud

    # Create a fresh user for this test to avoid session issues
    email = f"samepass_{uuid.uuid4().hex[:6]}@example.com"
    user_in = UserCreate(
        full_name="Same Pass",
        email=email,
        password="password123",  # noqa: S106
        role=UserRole.USER,
    )
    user = await user_crud.create_user(session=session, user_create=user_in)
    token = security.create_access_token(str(user.id))

    response = await client.patch(
        "/api/v1/users/password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": "password123", "new_password": "password123"},
    )
    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "New password cannot be the same as the current one"
    )


@pytest.mark.asyncio
async def test_update_password_failure_mock(
    client: AsyncClient, normal_user_token: str, mocker
):
    mocker.patch(
        "app.api.v1.endpoints.users.user_crud.update_password", return_value=False
    )
    response = await client.patch(
        "/api/v1/users/password",
        headers={"Authorization": f"Bearer {normal_user_token}"},
        json={"current_password": "password123", "new_password": "newpassword123"},  # noqa: S106
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Failed to update password"


@pytest.mark.asyncio
async def test_read_user_by_id_forbidden(
    client: AsyncClient, normal_user_token: str, session: AsyncSession
):
    # Create another user
    from app.crud import user as user_crud

    other_user_in = UserCreate(
        full_name="Other User",
        email="other_forbidden@example.com",
        password="password123",  # noqa: S106
        role=UserRole.USER,
    )
    other_user = await user_crud.create_user(session=session, user_create=other_user_in)

    response = await client.get(
        f"/api/v1/users/byID/{other_user.id}",
        headers={"Authorization": f"Bearer {normal_user_token}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Not enough permissions"


@pytest.mark.asyncio
async def test_update_user_permissions_denied(
    client: AsyncClient, normal_user_token: str, session: AsyncSession
):
    # Create another user
    from app.crud import user as user_crud

    other_user_in = UserCreate(
        full_name="Other User",
        email=f"other_{uuid.uuid4().hex[:6]}@example.com",
        password="password123",  # noqa: S106
        role=UserRole.USER,
    )
    other_user = await user_crud.create_user(session=session, user_create=other_user_in)

    # Try to update other user as normal user
    response = await client.patch(
        f"/api/v1/users/{other_user.id}",
        headers={"Authorization": f"Bearer {normal_user_token}"},
        json={"full_name": "New Name"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_user_role_denied_for_normal_user(
    client: AsyncClient, normal_user_token: str, session: AsyncSession
):
    from app.crud import user as user_crud

    user = await user_crud.get_user_by_email(
        session=session, email="test_user@example.com"
    )
    assert user is not None

    response = await client.patch(
        f"/api/v1/users/{user.id}",
        headers={"Authorization": f"Bearer {normal_user_token}"},
        json={"role": UserRole.ADMIN},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_user_success(
    client: AsyncClient, superuser_token: str, session: AsyncSession
):
    from app.crud import user as user_crud

    user_in = UserCreate(
        full_name="To Delete",
        email=f"todelete_{uuid.uuid4().hex[:6]}@example.com",
        password="password123",  # noqa: S106
        role=UserRole.USER,
    )
    user = await user_crud.create_user(session=session, user_create=user_in)

    response = await client.delete(
        f"/api/v1/users/{user.id}",
        headers={"Authorization": f"Bearer {superuser_token}"},
    )
    assert response.status_code == 200
    assert response.json()["message"] == "User deleted successfully"


@pytest.mark.asyncio
async def test_create_user_existing_email(client: AsyncClient, superuser_token: str):
    email = "existing_admin@example.com"
    # Create user first
    await client.post(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {superuser_token}"},
        json={
            "full_name": "First User",
            "email": email,
            "password": "password123",
        },
    )
    # Try again
    response = await client.post(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {superuser_token}"},
        json={
            "full_name": "Second User",
            "email": email,
            "password": "password123",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "User with this email already exists"


@pytest.mark.asyncio
async def test_update_user_forbidden_sensitive_fields(
    client: AsyncClient, normal_user_token: str
):
    current_user_response = await client.get(
        "/api/v1/login/current-user",
        headers={"Authorization": f"Bearer {normal_user_token}"},
    )
    user_id = current_user_response.json()["id"]

    # Normal user trying to update their own role
    response = await client.patch(
        f"/api/v1/users/{user_id}",
        headers={"Authorization": f"Bearer {normal_user_token}"},
        json={"role": UserRole.ADMIN},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Cannot change your own role or active status"


@pytest.mark.asyncio
async def test_admin_cannot_manage_other_admins_or_super(
    client: AsyncClient, session: AsyncSession
):
    from app.core import security
    from app.crud import user as user_crud

    # Create an ADMIN user
    admin_email = f"admin_{uuid.uuid4().hex[:6]}@example.com"
    admin_in = UserCreate(
        full_name="Admin User",
        email=admin_email,
        password="password123",
        role=UserRole.ADMIN,
    )
    admin_user = await user_crud.create_user(session=session, user_create=admin_in)
    admin_token = security.create_access_token(str(admin_user.id))

    # Get SUPER user ID
    from app.core.config import settings

    super_user = await user_crud.get_user_by_email(
        session=session, email=settings.SUPER_USER_EMAIL
    )
    assert super_user is not None

    # ADMIN tries to view SUPER details -> 403
    response = await client.get(
        f"/api/v1/users/byID/{super_user.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 403

    # ADMIN tries to create another ADMIN -> 403
    response = await client.post(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "full_name": "Another Admin",
            "email": "another_admin@example.com",
            "password": "password123",
            "role": UserRole.ADMIN,
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Admins can only create regular users."


@pytest.mark.asyncio
async def test_read_user_by_email_not_found_coverage(
    client: AsyncClient, superuser_token: str
):
    response = await client.get(
        "/api/v1/users/byEmail/nonexistent_coverage@example.com",
        headers={"Authorization": f"Bearer {superuser_token}"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


@pytest.mark.asyncio
async def test_update_user_not_found_coverage(
    client: AsyncClient, superuser_token: str
):
    response = await client.patch(
        f"/api/v1/users/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {superuser_token}"},
        json={"full_name": "New Name"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"
