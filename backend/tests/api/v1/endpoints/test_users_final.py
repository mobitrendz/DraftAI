import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_users_api_full_coverage(client: AsyncClient, superuser_token: str):
    # 1. Create User (Line 45-46)
    email = f"final_cov_{uuid.uuid4().hex[:8]}@example.com"
    response = await client.post(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {superuser_token}"},
        json={"email": email, "password": "password123", "full_name": "Final User"},
    )
    assert response.status_code == 200
    user_id = response.json()["id"]

    # 2. Read Users (Line 54)
    response = await client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {superuser_token}"},
    )
    assert response.status_code == 200

    # 3. Read User by ID (Line 67-69)
    response = await client.get(
        f"/api/v1/users/byID/{user_id}",
        headers={"Authorization": f"Bearer {superuser_token}"},
    )
    assert response.status_code == 200

    # 4. Read User by Email (Line 78-80)
    response = await client.get(
        f"/api/v1/users/byEmail/{email}",
        headers={"Authorization": f"Bearer {superuser_token}"},
    )
    assert response.status_code == 200

    # 5. Update User (Line 118-120)
    response = await client.patch(
        f"/api/v1/users/{user_id}",
        headers={"Authorization": f"Bearer {superuser_token}"},
        json={"full_name": "Updated Final"},
    )
    assert response.status_code == 200

    # 6. Delete User (Line 130-133)
    response = await client.delete(
        f"/api/v1/users/{user_id}",
        headers={"Authorization": f"Bearer {superuser_token}"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_role_checker_via_api(client: AsyncClient, normal_user_token: str):
    # Try to access admin-only endpoint
    response = await client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {normal_user_token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_users_api_admin_restrictions(client: AsyncClient, admin_user_token: str):
    from app.core.config import settings
    from app.models.user import UserRole

    # 1. Admin cannot create SUPER
    response = await client.post(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {admin_user_token}"},
        json={
            "email": "bad_admin@example.com",
            "password": "password123",
            "role": UserRole.SUPER,
            "full_name": "Bad",
        },
    )
    assert response.status_code == 403

    # 2. Admin cannot read SUPER by email
    response = await client.get(
        f"/api/v1/users/byEmail/{settings.SUPER_USER_EMAIL}",
        headers={"Authorization": f"Bearer {admin_user_token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_users_api_duplicate_error(client: AsyncClient, superuser_token: str):
    email = "duplicate_user@example.com"
    # Create first
    await client.post(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {superuser_token}"},
        json={"email": email, "password": "password123", "full_name": "First"},
    )
    # Create second
    response = await client.post(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {superuser_token}"},
        json={"email": email, "password": "password123", "full_name": "Second"},
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_update_user_self_restricted(
    client: AsyncClient, normal_user_token: str, session: AsyncSession
):
    from app.crud import user as user_crud
    from app.models.user import UserRole

    user = await user_crud.get_user_by_email(
        session=session, email="test_user@example.com"
    )
    assert user is not None

    # User cannot change their own role
    response = await client.patch(
        f"/api/v1/users/{user.id}",
        headers={"Authorization": f"Bearer {normal_user_token}"},
        json={"role": UserRole.ADMIN},
    )
    assert response.status_code == 403
    assert "Cannot change your own role" in response.json()["detail"]


@pytest.mark.asyncio
async def test_update_user_self_active_restricted(
    client: AsyncClient, normal_user_token: str, session: AsyncSession
):
    from app.crud import user as user_crud

    user = await user_crud.get_user_by_email(
        session=session, email="test_user@example.com"
    )
    assert user is not None

    # User cannot change their own active status
    response = await client.patch(
        f"/api/v1/users/{user.id}",
        headers={"Authorization": f"Bearer {normal_user_token}"},
        json={"is_active": False},
    )

    assert response.status_code == 403
    assert "Cannot change your own role or active status" in response.json()["detail"]


@pytest.mark.asyncio
async def test_read_password_history(client: AsyncClient, normal_user_token: str):
    response = await client.get(
        "/api/v1/users/me/password-history",
        headers={"Authorization": f"Bearer {normal_user_token}"},
    )
    assert response.status_code == 200
    assert "data" in response.json()


@pytest.mark.asyncio
async def test_update_other_admin_by_admin(
    client: AsyncClient, admin_user_token: str, session: AsyncSession
):
    from app.crud import user as user_crud
    from app.models.user import UserCreate, UserRole

    # Create another admin
    other_admin_in = UserCreate(
        email="other_admin@example.com",
        password="password123",
        full_name="Other Admin",
        role=UserRole.ADMIN,
    )
    other_admin = await user_crud.create_user(
        session=session, user_create=other_admin_in
    )

    # Admin tries to update other admin
    response = await client.patch(
        f"/api/v1/users/{other_admin.id}",
        headers={"Authorization": f"Bearer {admin_user_token}"},
        json={"full_name": "Should Fail"},
    )
    assert response.status_code == 403
    assert "Admins can only manage regular users" in response.json()["detail"]


@pytest.mark.asyncio
async def test_delete_admin_by_admin(
    client: AsyncClient, admin_user_token: str, session: AsyncSession
):
    from app.crud import user as user_crud
    from app.models.user import UserCreate, UserRole

    # Create another admin
    other_admin_in = UserCreate(
        email="del_admin@example.com",
        password="password123",
        full_name="Del Admin",
        role=UserRole.ADMIN,
    )
    other_admin = await user_crud.create_user(
        session=session, user_create=other_admin_in
    )

    # Admin tries to delete other admin
    response = await client.delete(
        f"/api/v1/users/{other_admin.id}",
        headers={"Authorization": f"Bearer {admin_user_token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_create_admin_forbidden(client: AsyncClient, admin_user_token: str):
    from app.models.user import UserRole

    response = await client.post(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {admin_user_token}"},
        json={
            "email": "new_admin@example.com",
            "password": "password123",
            "role": UserRole.ADMIN,
            "full_name": "New Admin",
        },
    )
    assert response.status_code == 403
    assert "Admins can only create regular users" in response.json()["detail"]


@pytest.mark.asyncio
async def test_admin_read_users_list(client: AsyncClient, admin_user_token: str):
    response = await client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {admin_user_token}"},
    )
    assert response.status_code == 200
    assert "items" in response.json()


@pytest.mark.asyncio
async def test_read_user_by_id_unauthorized(
    client: AsyncClient, normal_user_token: str, session: AsyncSession
):
    from app.crud import user as user_crud
    from app.models.user import UserCreate, UserRole

    # Create another user
    other_user_in = UserCreate(
        email="other_normal@example.com",
        password="password123",
        full_name="Other Normal",
        role=UserRole.USER,
    )
    other_user = await user_crud.create_user(session=session, user_create=other_user_in)

    # Normal user tries to read other user
    response = await client.get(
        f"/api/v1/users/byID/{other_user.id}",
        headers={"Authorization": f"Bearer {normal_user_token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_read_user_by_email_not_found(client: AsyncClient, superuser_token: str):
    response = await client.get(
        "/api/v1/users/byEmail/nonexistent@example.com",
        headers={"Authorization": f"Bearer {superuser_token}"},
    )
    assert response.status_code == 404
