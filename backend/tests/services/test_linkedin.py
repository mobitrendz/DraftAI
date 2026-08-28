from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.platforms.linkedin import (
    LinkedinPublishError,
    _normalize_author_urn,
    resolve_author_urn_for_publish,
    resolve_author_urn_from_token,
)


def test_normalize_author_urn_accepts_person_urn():
    assert _normalize_author_urn("urn:li:person:8691m5m4fzx85u") == (
        "urn:li:person:8691m5m4fzx85u"
    )


def test_normalize_author_urn_accepts_organization_urn():
    assert _normalize_author_urn("urn:li:organization:67890") == (
        "urn:li:organization:67890"
    )


def test_normalize_author_urn_converts_member_urn_to_person():
    assert _normalize_author_urn("urn:li:member:12345") == "urn:li:person:12345"


def test_normalize_author_urn_converts_company_urn_to_organization():
    assert _normalize_author_urn("urn:li:company:67890") == "urn:li:organization:67890"


def test_normalize_author_urn_converts_numeric_id():
    assert _normalize_author_urn("12345") == "urn:li:person:12345"


def test_normalize_author_urn_strips_surrounding_quotes():
    assert _normalize_author_urn('"urn:li:organization:117255113"') == (
        "urn:li:organization:117255113"
    )


def test_normalize_author_urn_rejects_company_vanity_id():
    with pytest.raises(LinkedinPublishError, match="Invalid LINKEDIN_AUTHOR_URN"):
        _normalize_author_urn("urn:li:company:8691m5m4fzx85u")


@pytest.mark.asyncio
async def test_resolve_author_urn_from_token_uses_userinfo_sub():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"sub": "8691m5m4fzx85u"}

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get = AsyncMock(return_value=mock_response)

    with patch("app.services.platforms.linkedin.httpx.AsyncClient", return_value=mock_client):
        urn = await resolve_author_urn_from_token("token")

    assert urn == "urn:li:person:8691m5m4fzx85u"


@pytest.mark.asyncio
async def test_resolve_author_urn_for_publish_falls_back_to_token():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"sub": "abc123"}

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get = AsyncMock(return_value=mock_response)

    with patch("app.services.platforms.linkedin.httpx.AsyncClient", return_value=mock_client):
        urn = await resolve_author_urn_for_publish(
            access_token="token",
            author_urn="urn:li:company:8691m5m4fzx85u",
        )

    assert urn == "urn:li:person:abc123"
