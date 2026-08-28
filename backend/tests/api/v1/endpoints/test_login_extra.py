import pytest
from httpx import AsyncClient

from app.core.config import settings


@pytest.mark.asyncio
@pytest.mark.usefixtures("superuser_token")
async def test_recover_password_existing_user(client: AsyncClient, mocker):
    mocker.patch(
        "app.api.v1.endpoints.login.security.render_email_template",
        return_value="<html>Reset</html>",
    )
    mock_send_email = mocker.patch("app.api.v1.endpoints.login.security.send_email")

    response = await client.post(
        f"/api/v1/login/password-recovery/{settings.SUPER_USER_EMAIL}"
    )
    assert response.status_code == 200
    assert (
        response.json()["message"]
        == "If that email is registered, we sent a password recovery link"
    )
    mock_send_email.assert_called_once()


@pytest.mark.asyncio
async def test_recover_password_non_existing_user(client: AsyncClient, mocker):
    mock_send_email = mocker.patch("app.api.v1.endpoints.login.security.send_email")
    mock_get_user = mocker.patch(
        "app.api.v1.endpoints.login.user_crud.get_user_by_email", return_value=None
    )

    response = await client.post(
        "/api/v1/login/password-recovery/nonexistent@example.com"
    )
    assert response.status_code == 200
    assert (
        response.json()["message"]
        == "If that email is registered, we sent a password recovery link"
    )
    mock_send_email.assert_not_called()
    mock_get_user.assert_called_once()


@pytest.mark.asyncio
async def test_test_email(client: AsyncClient, mocker):
    from app.core.security import EmailData

    mocker.patch(
        "app.main.generate_test_email",
        return_value=EmailData(html_content="<html>Test</html>", subject="Test"),
    )
    mock_send_email = mocker.patch("app.main.send_email")

    response = await client.post("/test-email/?email_to=test@example.com")
    assert response.status_code == 201
    assert response.json()["message"] == "Test email sent"
    mock_send_email.assert_called_once()
