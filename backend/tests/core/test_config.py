import pytest

from app.core.config import Settings, parse_cors


def test_parse_cors_list():
    assert parse_cors(["http://localhost"]) == ["http://localhost"]


def test_parse_cors_str_json():
    # pydantic might pass "[...]" if it's already a list-like string
    assert parse_cors('["http://localhost"]') == '["http://localhost"]'


def test_parse_cors_invalid():
    with pytest.raises(ValueError):
        parse_cors(123)


def test_emails_enabled():
    # Test with mock or temporary settings
    s = Settings(
        FRONTEND_HOST="http://localhost",
        ENVIRONMENT="dev",
        PROJECT_NAME="test",
        STACK_NAME="test",
        API_V1_STR="/v1",
        SECRET_KEY="test",  # noqa: S105, S106
        ALGORITHM="HS256",
        ACCESS_TOKEN_EXPIRE_MINUTES=60,
        EMAIL_RESET_TOKEN_EXPIRE_HOURS=1,
        SUPER_USER_NAME="admin",
        SUPER_USER_EMAIL="admin@example.com",
        SUPER_USER_PASSWORD="password",  # noqa: S106
        POSTGRES_SERVER="localhost",
        POSTGRES_PORT=5432,
        POSTGRES_DB="db",
        POSTGRES_USER="user",
        POSTGRES_PASSWORD="pass",  # noqa: S106
        SMTP_HOST="localhost",
        EMAILS_FROM_EMAIL="test@example.com",
    )
    assert s.emails_enabled is True

    s.SMTP_HOST = None
    assert s.emails_enabled is False
