from unittest.mock import MagicMock, patch

from app.services.storage import StorageService


def test_upload_bytes_puts_object():
    service = StorageService()
    mock_client = MagicMock()
    service._client = mock_client

    with patch.object(service, "ensure_bucket"):
        key = service.upload_bytes(
            key="covers/draft-1/shared.png",
            data=b"image-data",
            content_type="image/png",
        )

    assert key == "covers/draft-1/shared.png"
    mock_client.put_object.assert_called_once()


def test_get_presigned_url_returns_none_for_empty_key():
    service = StorageService()
    assert service.get_presigned_url("") is None
