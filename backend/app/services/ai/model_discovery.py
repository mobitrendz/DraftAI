import structlog
import httpx

from app.core.config import settings
from app.models.ai_agent_config import AIModelOption
from app.services.ai.ollama import list_ollama_models, normalize_ollama_base_url

logger = structlog.get_logger(__name__)

LIVE_MODEL_ADAPTERS = frozenset(
    {"openai_compatible", "ollama", "gemini", "anthropic_messages"}
)


def _auth_headers(
    *,
    api_key: str | None,
    auth_style: str,
    auth_header_name: str | None,
) -> dict[str, str]:
    headers: dict[str, str] = {}
    if not api_key:
        return headers
    if auth_style == "bearer":
        headers["Authorization"] = f"Bearer {api_key}"
    elif auth_style == "api_key_header" and auth_header_name:
        headers[auth_header_name] = api_key
    return headers


async def list_openai_compatible_models(
    *,
    base_url: str,
    api_key: str | None = None,
    auth_style: str = "bearer",
    auth_header_name: str | None = None,
) -> list[AIModelOption]:
    url = f"{base_url.rstrip('/')}/models"
    headers = _auth_headers(
        api_key=api_key,
        auth_style=auth_style,
        auth_header_name=auth_header_name,
    )
    async with httpx.AsyncClient(
        timeout=float(settings.AI_MODEL_DISCOVERY_TIMEOUT_SECONDS)
    ) as client:
        response = await client.get(url, headers=headers)
    if response.status_code != 200:
        logger.warning(
            "OpenAI-compatible models API error",
            status=response.status_code,
            body=response.text[:200],
            url=url,
        )
        raise httpx.HTTPStatusError(
            f"Provider returned {response.status_code}",
            request=response.request,
            response=response,
        )
    payload = response.json()
    entries = payload.get("data") or payload.get("models") or []
    options: list[AIModelOption] = []
    for entry in entries:
        if isinstance(entry, str):
            model_id = entry
        else:
            model_id = entry.get("id") or entry.get("name") or entry.get("model")
        if not model_id:
            continue
        options.append(
            AIModelOption(
                id=model_id,
                label=model_id,
                description=None,
            )
        )
    return options


def _gemini_model_id(raw_name: str) -> str:
    return raw_name.removeprefix("models/")


def _is_gemini_text_model(*, model_id: str, supported_methods: list[str] | None) -> bool:
    methods = supported_methods or []
    if "generateContent" not in methods:
        return False
    if model_id.endswith("-image") or "-image-" in model_id:
        return False
    return True


def _meets_min_context(context_window_tokens: int | None) -> bool:
    if context_window_tokens is None:
        return False
    return context_window_tokens >= settings.AI_MIN_TEXT_CONTEXT_WINDOW_TOKENS


async def list_gemini_models(*, base_url: str, api_key: str) -> list[AIModelOption]:
    url = f"{base_url.rstrip('/')}/models"
    async with httpx.AsyncClient(
        timeout=float(settings.AI_MODEL_DISCOVERY_TIMEOUT_SECONDS)
    ) as client:
        response = await client.get(url, params={"key": api_key})
    if response.status_code != 200:
        logger.warning(
            "Gemini models API error",
            status=response.status_code,
            body=response.text[:200],
            url=url,
        )
        raise httpx.HTTPStatusError(
            f"Provider returned {response.status_code}",
            request=response.request,
            response=response,
        )
    payload = response.json()
    options: list[AIModelOption] = []
    for entry in payload.get("models") or []:
        raw_name = entry.get("name") or ""
        model_id = _gemini_model_id(raw_name)
        if not model_id:
            continue
        if not _is_gemini_text_model(
            model_id=model_id,
            supported_methods=entry.get("supportedGenerationMethods"),
        ):
            continue
        context_window = entry.get("inputTokenLimit")
        if not _meets_min_context(context_window):
            continue
        options.append(
            AIModelOption(
                id=model_id,
                label=entry.get("displayName") or model_id,
                description=entry.get("description"),
                context_window_tokens=context_window,
            )
        )
    return options


async def list_anthropic_models(*, base_url: str, api_key: str) -> list[AIModelOption]:
    url = f"{base_url.rstrip('/')}/models"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }
    async with httpx.AsyncClient(
        timeout=float(settings.AI_MODEL_DISCOVERY_TIMEOUT_SECONDS)
    ) as client:
        response = await client.get(url, headers=headers)
    if response.status_code != 200:
        logger.warning(
            "Anthropic models API error",
            status=response.status_code,
            body=response.text[:200],
            url=url,
        )
        raise httpx.HTTPStatusError(
            f"Provider returned {response.status_code}",
            request=response.request,
            response=response,
        )
    payload = response.json()
    options: list[AIModelOption] = []
    for entry in payload.get("data") or []:
        model_id = entry.get("id")
        if not model_id:
            continue
        options.append(
            AIModelOption(
                id=model_id,
                label=entry.get("display_name") or model_id,
                description=entry.get("description"),
            )
        )
    return options


async def discover_provider_models(
    *,
    base_url: str,
    api_adapter: str,
    api_key: str | None = None,
    auth_style: str = "bearer",
    auth_header_name: str | None = None,
) -> list[AIModelOption]:
    if api_adapter == "ollama":
        return await list_ollama_models(base_url=normalize_ollama_base_url(base_url))
    if api_adapter == "openai_compatible":
        return await list_openai_compatible_models(
            base_url=base_url,
            api_key=api_key,
            auth_style=auth_style,
            auth_header_name=auth_header_name,
        )
    if api_adapter == "gemini":
        if not api_key:
            raise ValueError("Gemini model discovery requires an API key.")
        return await list_gemini_models(base_url=base_url, api_key=api_key)
    if api_adapter == "anthropic_messages":
        if not api_key:
            raise ValueError("Anthropic model discovery requires an API key.")
        return await list_anthropic_models(base_url=base_url, api_key=api_key)
    raise ValueError(f"Adapter '{api_adapter}' does not support live model discovery.")
