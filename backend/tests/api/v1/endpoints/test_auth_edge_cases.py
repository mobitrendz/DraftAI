import jwt
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings


@pytest.mark.asyncio
async def test_get_current_user_malformed_token(client: AsyncClient):
    # Token with invalid signature
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.invalid_signature"  # noqa: S105
    response = await client.get(
        "/api/v1/login/current-user",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_validation_error(client: AsyncClient):
    # Token with valid signature but invalid type for 'sub' (expects string or None, we give dict)
    payload = {"sub": {"invalid": "type"}, "exp": 9999999999}
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    response = await client.get(
        "/api/v1/login/current-user",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"


@pytest.mark.asyncio
async def test_get_current_user_expired_token(client: AsyncClient):
    # Token that has expired
    payload = {"sub": "some-user-id", "exp": 1}  # Expired long ago
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    response = await client.get(
        "/api/v1/login/current-user",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Token expired"


@pytest.mark.asyncio
async def test_read_secure_data_endpoint(client: AsyncClient, normal_user_token: str):
    response = await client.get(
        "/api/v1/login/secure-data",
        headers={"Authorization": f"Bearer {normal_user_token}"},
    )
    assert response.status_code == 200
    assert "token" in response.json()


@pytest.mark.asyncio
async def test_get_current_user_not_found(client: AsyncClient):
    import uuid

    from app.core import security

    token = security.create_access_token(str(uuid.uuid4()))
    response = await client.get(
        "/api/v1/login/current-user",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


@pytest.mark.asyncio
async def test_get_current_user_inactive(client: AsyncClient, session: AsyncSession):
    from app.core import security
    from app.crud import user as user_crud
    from app.models.user import UserCreate

    email = "inactive_edge@example.com"
    user = await user_crud.create_user(
        session=session,
        user_create=UserCreate(
            email=email, password="password123", full_name="Inactive", is_active=False
        ),
    )
    token = security.create_access_token(str(user.id))
    response = await client.get(
        "/api/v1/login/current-user",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Inactive user"
