from datetime import timedelta

import pytest

from app.core import security
from app.core.config import settings


def test_hash_password():
    password = "testpassword"  # noqa: S105
    hashed = security.hash_password(password)
    assert hashed != password
    assert security.verify_password(password, hashed)
    assert not security.verify_password("wrongpassword", hashed)


def test_hash_password_empty():
    with pytest.raises(ValueError, match="Password must not be empty"):
        security.hash_password("")


def test_create_access_token():
    subject = "test@example.com"
    token = security.create_access_token(subject)
    decoded = security.decode_access_token(token)
    assert decoded["sub"] == subject


def test_create_access_token_expires():
    subject = "test@example.com"
    expires_delta = timedelta(minutes=10)
    token = security.create_access_token(subject, expires_delta=expires_delta)
    decoded = security.decode_access_token(token)
    assert decoded["sub"] == subject


def test_decode_access_token_invalid():
    assert security.decode_access_token("invalidtoken") is None


def test_generate_password_reset_token():
    email = "test@example.com"
    token = security.generate_password_reset_token(email)
    decoded = security.decode_access_token(token)
    assert decoded["sub"] == email


def test_generate_test_email(mocker):
    mocker.patch(
        "app.core.security.render_email_template", return_value="<html>Test</html>"
    )
    email_to = "test@example.com"
    email_data = security.generate_test_email(email_to)
    assert email_data.subject == f"{settings.PROJECT_NAME} - Test email"
    assert email_data.html_content == "<html>Test</html>"


def test_generate_reset_password_email(mocker):
    mocker.patch(
        "app.core.security.render_email_template", return_value="<html>Reset</html>"
    )
    email_to = "test@example.com"
    email = "test_user@example.com"
    token = "sometoken"  # noqa: S105
    email_data = security.generate_reset_password_email(email_to, email, token)
    assert (
        email_data.subject
        == f"{settings.PROJECT_NAME} - Password recovery for user {email}"
    )
    assert email_data.html_content == "<html>Reset</html>"


def test_send_email(mocker):
    # Mock emails.message.Message.send
    mock_send = mocker.patch("emails.message.Message.send")
    mock_send.return_value = "sent"

    security.send_email(
        email_to="test@example.com",
        subject="Test Subject",
        html_content="<h1>Test</h1>",
    )

    mock_send.assert_called_once()


def test_send_email_tls_ssl(mocker):
    # Test different SMTP settings
    mock_send = mocker.patch("emails.message.Message.send")

    # Force TLS
    original_tls = settings.SMTP_TLS
    settings.SMTP_TLS = True
    security.send_email(email_to="test@example.com")
    settings.SMTP_TLS = original_tls

    # Force SSL
    original_ssl = settings.SMTP_SSL
    settings.SMTP_SSL = True
    security.send_email(email_to="test@example.com")
    settings.SMTP_SSL = original_ssl

    # Force User/Pass
    original_user = settings.SMTP_USER
    original_pass = settings.SMTP_PASSWORD
    settings.SMTP_USER = "user"
    settings.SMTP_PASSWORD = "pass"  # noqa: S105
    security.send_email(email_to="test@example.com")
    settings.SMTP_USER = original_user
    settings.SMTP_PASSWORD = original_pass

    assert mock_send.call_count == 3
