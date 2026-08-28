import httpx
import structlog

logger = structlog.get_logger(__name__)

DEVTO_API_BASE = "https://dev.to/api"
DEVTO_PUBLISH_TIMEOUT_SECONDS = 60


class DevtoPublishError(Exception):
    def __init__(self, message: str, *, retryable: bool = True) -> None:
        super().__init__(message)
        self.retryable = retryable


def _parse_tags(tags: str) -> list[str]:
    return [tag.strip() for tag in tags.split(",") if tag.strip()][:4]


def prepare_devto_body_markdown(*, title: str, body_markdown: str) -> str:
    """Remove a leading H1 that duplicates the article title (DEV.to shows title separately)."""
    body = body_markdown.strip()
    if not body:
        return body

    lines = body.splitlines()
    first_line = lines[0].strip()
    if not first_line.startswith("# "):
        return body

    heading = first_line[2:].strip()
    if heading.lower() != title.strip().lower():
        return body

    remaining = lines[1:]
    while remaining and not remaining[0].strip():
        remaining = remaining[1:]
    return "\n".join(remaining).strip()


async def publish_article(
    *,
    api_key: str,
    title: str,
    body_markdown: str,
    tags: str,
    main_image: str | None = None,
) -> str:
    """Create a published DEV.to article and return its canonical URL."""
    article: dict[str, object] = {
        "title": title,
        "body_markdown": prepare_devto_body_markdown(
            title=title,
            body_markdown=body_markdown,
        ),
        "published": True,
        "tags": _parse_tags(tags),
    }
    if main_image:
        article["main_image"] = main_image
        logger.info("Publishing DEV.to article with cover image", main_image=main_image)

    async with httpx.AsyncClient(timeout=float(DEVTO_PUBLISH_TIMEOUT_SECONDS)) as client:
        response = await client.post(
            f"{DEVTO_API_BASE}/articles",
            headers={
                "api-key": api_key,
                "Content-Type": "application/json",
                "User-Agent": "DraftAI",
            },
            json={"article": article},
        )

    if response.status_code in (401, 403):
        raise DevtoPublishError(
            "DEV.to API key rejected. Check your key in Settings → Platforms.",
            retryable=False,
        )
    if response.status_code == 422:
        raise DevtoPublishError(
            f"DEV.to rejected the article: {response.text[:300]}",
            retryable=False,
        )
    if response.status_code not in (200, 201):
        logger.error(
            "DEV.to publish failed",
            status=response.status_code,
            body=response.text[:500],
        )
        raise DevtoPublishError(
            f"DEV.to publish failed ({response.status_code}): {response.text[:200]}",
            retryable=response.status_code >= 500 or response.status_code == 429,
        )

    payload = response.json()
    url = payload.get("url")
    if isinstance(url, str) and url.strip():
        return url.strip()
    path = payload.get("path")
    if isinstance(path, str) and path.strip():
        return f"https://dev.to{path}"
    raise DevtoPublishError(
        "DEV.to publish succeeded but returned no article URL.",
        retryable=False,
    )
