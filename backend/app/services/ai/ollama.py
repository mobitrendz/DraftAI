import structlog
import httpx

from app.core.config import settings
from app.models.ai_agent_config import AIModelOption

logger = structlog.get_logger(__name__)


def normalize_ollama_base_url(base_url: str) -> str:
    """Ensure OpenAI-compatible chat base URL ends with /v1."""
    url = base_url.strip().rstrip("/")
    if not url.endswith("/v1"):
        url = f"{url}/v1"
    return url


def ollama_api_root(base_url: str) -> str:
    """Root URL for Ollama native APIs (e.g. /api/tags)."""
    url = normalize_ollama_base_url(base_url)
    return url[: -len("/v1")]


def _format_model_size(size_bytes: int | None) -> str | None:
    if not size_bytes:
        return None
    gb = size_bytes / (1024**3)
    if gb >= 1:
        return f"{gb:.1f} GB local"
    mb = size_bytes / (1024**2)
    return f"{mb:.0f} MB local"


async def list_ollama_models(*, base_url: str) -> list[AIModelOption]:
    """Fetch installed models from a local Ollama instance."""
    root = ollama_api_root(base_url)
    url = f"{root}/api/tags"
    async with httpx.AsyncClient(
        timeout=float(settings.AI_OLLAMA_TIMEOUT_SECONDS)
    ) as client:
        response = await client.get(url)
    if response.status_code != 200:
        logger.warning(
            "Ollama tags API error",
            status=response.status_code,
            body=response.text[:200],
            url=url,
        )
        raise httpx.HTTPStatusError(
            f"Ollama returned {response.status_code}",
            request=response.request,
            response=response,
        )
    payload = response.json()
    models = payload.get("models") or []
    options: list[AIModelOption] = []
    for entry in models:
        name = entry.get("name") or entry.get("model")
        if not name:
            continue
        options.append(
            AIModelOption(
                id=name,
                label=name,
                description=_format_model_size(entry.get("size")),
            )
        )
    return options
