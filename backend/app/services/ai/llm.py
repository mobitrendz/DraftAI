import json

import httpx
import structlog
from fastapi import HTTPException

from app.core.config import settings

logger = structlog.get_logger(__name__)


def _format_provider_error(*, status_code: int, body: str, provider_label: str) -> str:
    body_lower = body.lower()
    if status_code == 429:
        if "quota" in body_lower and provider_label == "gemini":
            return (
                "Google Gemini quota exceeded. Article generation is a large request "
                "(800–1500 words). Try gemini-2.0-flash on Home, wait for your quota to reset, "
                "or review limits at https://ai.google.dev/gemini-api/docs/rate-limits"
            )
        if "quota" in body_lower:
            return (
                f"{provider_label} quota exceeded. Wait for your limit to reset and try again."
            )
        return f"{provider_label} rate limit exceeded. Wait a few minutes and try again."
    if status_code in (401, 403):
        return f"{provider_label} rejected the API key. Check Settings → AI Providers."
    return f"AI provider error: {body[:300]}"


async def call_openai_compatible(
    *,
    base_url: str,
    api_key: str,
    model: str,
    temperature: float,
    system_prompt: str,
    user_message: str,
    provider_label: str,
    extra_headers: dict[str, str] | None = None,
    auth_style: str = "bearer",
    auth_header_name: str | None = None,
) -> dict:
    headers: dict[str, str] = {"Content-Type": "application/json", **(extra_headers or {})}
    if auth_style == "bearer" and api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    elif auth_style == "api_key_header" and api_key and auth_header_name:
        headers[auth_header_name] = api_key

    async with httpx.AsyncClient(
        timeout=float(settings.AI_TEXT_GENERATION_TIMEOUT_SECONDS)
    ) as client:
        response = await client.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers=headers,
            json={
                "model": model,
                "temperature": temperature,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
            },
        )
    if response.status_code != 200:
        logger.error(
            f"{provider_label} API error",
            status=response.status_code,
            body=response.text,
        )
        raise HTTPException(
            status_code=502,
            detail=_format_provider_error(
                status_code=response.status_code,
                body=response.text,
                provider_label=provider_label,
            ),
        )
    payload = response.json()
    content = payload["choices"][0]["message"]["content"]
    return json.loads(content)


async def call_anthropic(
    *,
    base_url: str,
    api_key: str,
    model: str,
    temperature: float,
    system_prompt: str,
    user_message: str,
) -> dict:
    async with httpx.AsyncClient(
        timeout=float(settings.AI_TEXT_GENERATION_TIMEOUT_SECONDS)
    ) as client:
        response = await client.post(
            f"{base_url.rstrip('/')}/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": 8192,
                "temperature": temperature,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_message}],
            },
        )
    if response.status_code != 200:
        logger.error(
            "Anthropic API error",
            status=response.status_code,
            body=response.text,
        )
        raise HTTPException(
            status_code=502,
            detail=_format_provider_error(
                status_code=response.status_code,
                body=response.text,
                provider_label="Anthropic",
            ),
        )
    payload = response.json()
    content_blocks = payload.get("content") or []
    text_parts = [block["text"] for block in content_blocks if block.get("text")]
    if not text_parts:
        raise HTTPException(status_code=502, detail="AI provider returned empty content.")
    return json.loads(text_parts[0])


async def call_gemini(
    *,
    base_url: str,
    api_key: str,
    model: str,
    temperature: float,
    system_prompt: str,
    user_message: str,
) -> dict:
    url = f"{base_url.rstrip('/')}/models/{model}:generateContent"
    async with httpx.AsyncClient(
        timeout=float(settings.AI_TEXT_GENERATION_TIMEOUT_SECONDS)
    ) as client:
        response = await client.post(
            url,
            params={"key": api_key},
            headers={"Content-Type": "application/json"},
            json={
                "systemInstruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"role": "user", "parts": [{"text": user_message}]}],
                "generationConfig": {
                    "temperature": temperature,
                    "responseMimeType": "application/json",
                },
            },
        )
    if response.status_code != 200:
        logger.error("Gemini API error", status=response.status_code, body=response.text)
        raise HTTPException(
            status_code=502,
            detail=_format_provider_error(
                status_code=response.status_code,
                body=response.text,
                provider_label="gemini",
            ),
        )
    payload = response.json()
    candidates = payload.get("candidates") or []
    if not candidates:
        raise HTTPException(status_code=502, detail="AI provider returned no candidates.")
    parts = candidates[0].get("content", {}).get("parts") or []
    if not parts or "text" not in parts[0]:
        raise HTTPException(status_code=502, detail="AI provider returned empty content.")
    return json.loads(parts[0]["text"])


async def generate_json_content(
    *,
    api_adapter: str,
    base_url: str,
    api_key: str,
    model: str,
    temperature: float,
    system_prompt: str,
    user_message: str,
    auth_style: str = "bearer",
    auth_header_name: str | None = None,
    extra_headers: dict[str, str] | None = None,
    provider_label: str = "AI",
) -> dict:
    if api_adapter == "openai_compatible":
        return await call_openai_compatible(
            base_url=base_url,
            api_key=api_key,
            model=model,
            temperature=temperature,
            system_prompt=system_prompt,
            user_message=user_message,
            provider_label=provider_label,
            extra_headers=extra_headers,
            auth_style=auth_style,
            auth_header_name=auth_header_name,
        )
    if api_adapter == "anthropic_messages":
        return await call_anthropic(
            base_url=base_url,
            api_key=api_key,
            model=model,
            temperature=temperature,
            system_prompt=system_prompt,
            user_message=user_message,
        )
    if api_adapter == "gemini":
        return await call_gemini(
            base_url=base_url,
            api_key=api_key,
            model=model,
            temperature=temperature,
            system_prompt=system_prompt,
            user_message=user_message,
        )
    raise HTTPException(
        status_code=400,
        detail=f"API adapter '{api_adapter}' is not supported for generation.",
    )
