import re
import uuid
from urllib.parse import urlparse

import httpx
import structlog

from app.core.config import settings
from app.models.content import CoverImage, CoverImagePlatform

logger = structlog.get_logger(__name__)

_PUBLIC_COVER_FILENAME = re.compile(
    r"^(devto|linkedin)\.(png|jpe?g|webp)$",
    flags=re.IGNORECASE,
)

_PRIVATE_HOSTS = frozenset(
    {"localhost", "127.0.0.1", "minio", "host.docker.internal", "0.0.0.0"}
)

COVER_PUBLISH_SETUP_MESSAGE = (
    "DEV.to cannot fetch your cover image from private storage. Set PUBLIC_API_BASE_URL "
    "in backend/.env to a publicly reachable HTTPS URL for this API "
    "(e.g. your production domain, or an ngrok/Cloudflare tunnel to port 8000 for local dev). "
    "Then republish the article."
)

_TUNNEL_VERIFY_HEADERS = {
    # ngrok free tier returns an HTML interstitial without this header.
    "ngrok-skip-browser-warning": "true",
    "User-Agent": "DraftAI-CoverVerify/1.0",
}


def _cover_url_verification_hint(*, status_code: int, content_type: str, url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    if "ngrok" in host and (status_code != 200 or content_type.startswith("text/html")):
        return (
            "The ngrok tunnel appears offline or returned HTML instead of an image. "
            "Run `ngrok http 8000` (or your reserved domain) and update PUBLIC_API_BASE_URL "
            "if the URL changed, then restart backend/worker."
        )
    if content_type.startswith("text/html"):
        return (
            "The configured PUBLIC_API_BASE_URL returned an HTML page instead of PNG/JPEG. "
            "Check the tunnel is running and points to port 8000."
        )
    return (
        "The configured PUBLIC_API_BASE_URL did not return a valid image "
        "(check the tunnel is running and returns PNG/JPEG, not an HTML page)."
    )


def is_public_cover_filename(filename: str) -> bool:
    return bool(_PUBLIC_COVER_FILENAME.match(filename))


def platform_from_cover_filename(filename: str) -> CoverImagePlatform | None:
    match = _PUBLIC_COVER_FILENAME.match(filename)
    if not match:
        return None
    platform_value = match.group(1).lower()
    if platform_value == "devto":
        return CoverImagePlatform.DEVTO
    return CoverImagePlatform.LINKEDIN


def cover_extension_from_storage_key(storage_key: str) -> str:
    return storage_key.rsplit(".", 1)[-1].lower()


def build_public_cover_url(
    *,
    draft_id: uuid.UUID,
    platform: CoverImagePlatform,
    extension: str,
) -> str | None:
    base_url = settings.PUBLIC_API_BASE_URL
    if not base_url:
        return None
    normalized_ext = extension.lower().lstrip(".")
    return (
        f"{base_url.rstrip('/')}/api/v1/public/covers/"
        f"{draft_id}/{platform.value}.{normalized_ext}"
    )


def is_devto_reachable_image_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    hostname = (parsed.hostname or "").lower()
    if not hostname:
        return False
    if hostname in _PRIVATE_HOSTS:
        return False
    if hostname.endswith(".local"):
        return False
    return True


def resolve_devto_cover_image_url(
    *,
    draft_id: uuid.UUID,
    cover: CoverImage | None,
) -> str | None:
    if not cover or not cover.storage_key:
        return None

    extension = cover_extension_from_storage_key(cover.storage_key)
    public_url = build_public_cover_url(
        draft_id=draft_id,
        platform=CoverImagePlatform.DEVTO,
        extension=extension,
    )
    if public_url:
        return public_url

    from app.services.storage import storage

    presigned = storage.get_presigned_url(cover.storage_key)
    if presigned and not is_devto_reachable_image_url(presigned):
        logger.warning(
            "DEV.to cannot fetch cover image from private storage URL. "
            "Set PUBLIC_API_BASE_URL to your publicly reachable API base "
            "(e.g. https://your-domain.com or an ngrok URL for local dev).",
            draft_id=str(draft_id),
            storage_key=cover.storage_key,
        )
        return None
    return presigned


def cover_publish_url_error() -> str:
    return COVER_PUBLISH_SETUP_MESSAGE


async def verify_public_image_url(url: str) -> bool:
    """Best-effort check that a URL returns image bytes (not HTML error pages)."""
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.head(url, headers=_TUNNEL_VERIFY_HEADERS)
            if response.status_code == 405:
                response = await client.get(url, headers=_TUNNEL_VERIFY_HEADERS)
            if response.status_code != 200:
                return False
            content_type = (
                response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
            )
            return content_type.startswith("image/")
    except Exception as exc:
        logger.warning("Cover image URL verification failed", url=url, error=str(exc))
        return False


async def explain_public_image_url_failure(url: str) -> str:
    """Return a user-facing hint when verify_public_image_url would fail."""
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.head(url, headers=_TUNNEL_VERIFY_HEADERS)
            if response.status_code == 405:
                response = await client.get(url, headers=_TUNNEL_VERIFY_HEADERS)
            content_type = (
                response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
            )
            hint = _cover_url_verification_hint(
                status_code=response.status_code,
                content_type=content_type,
                url=url,
            )
    except Exception as exc:
        logger.warning("Cover image URL verification failed", url=url, error=str(exc))
        hint = _cover_url_verification_hint(
            status_code=0,
            content_type="",
            url=url,
        )
    return f"{COVER_PUBLISH_SETUP_MESSAGE} {hint}"


async def resolve_devto_publish_cover_url(
    *,
    draft_id: uuid.UUID,
    cover: CoverImage | None,
) -> str | None:
    """Resolve a DEV.to-reachable cover URL or raise ValueError with setup instructions."""
    if not cover or not cover.storage_key:
        return None

    url = resolve_devto_cover_image_url(draft_id=draft_id, cover=cover)
    if not url:
        raise ValueError(cover_publish_url_error())

    if not is_devto_reachable_image_url(url):
        raise ValueError(cover_publish_url_error())

    if not await verify_public_image_url(url):
        raise ValueError(await explain_public_image_url_failure(url))

    return url
