import base64
import json
import re
from dataclasses import dataclass

import httpx
import structlog
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.crud import ai_catalog
from app.models.content import CoverImagePlatform
from app.services.ai.cover_resize import resize_cover_image_bytes
from app.services.ai.cover_specs import get_cover_spec

logger = structlog.get_logger(__name__)

DALLE_SIZE = "1792x1024"


def _gemini_image_generation_config(model: str, *, aspect_ratio: str) -> dict:
    """Build generationConfig for Gemini image models."""
    image_config: dict[str, str] = {
        "aspectRatio": aspect_ratio,
    }
    if model.startswith("gemini-3"):
        image_config["imageSize"] = "1K"
    return {
        "responseModalities": ["IMAGE"],
        "imageConfig": image_config,
    }


def _extract_gemini_error_message(body: str) -> str:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return body
    error = payload.get("error")
    if isinstance(error, dict):
        message = error.get("message")
        if isinstance(message, str) and message.strip():
            return message
    return body


def _format_image_error(*, status_code: int, body: str) -> str:
    message = _extract_gemini_error_message(body)
    body_lower = f"{body} {message}".lower()

    if status_code == 429:
        if "free_tier" in body_lower and "limit: 0" in body_lower:
            return (
                "Gemini cover image generation is not available on your API key's free "
                "tier (image quota is 0). Enable billing on your Google AI / Cloud "
                "project, or upload a custom cover image on Edit draft."
            )
        retry_match = re.search(r"retry in ([0-9.]+)s", message, flags=re.IGNORECASE)
        if retry_match:
            seconds = max(1, int(float(retry_match.group(1))))
            return (
                f"Gemini cover image rate limit reached. Wait about {seconds} seconds "
                "and try again, or upload a custom cover image on Edit draft."
            )
        if "resource_exhausted" in body_lower or "quota" in body_lower:
            return (
                "Gemini cover image quota or rate limit reached. Check usage at "
                "https://ai.dev/rate-limit, wait for reset, or upload a custom cover "
                "image on Edit draft."
            )
        return (
            "Gemini cover image request was throttled. Try again shortly, or upload a "
            "custom cover image on Edit draft."
        )
    if status_code in (401, 403):
        return "Cover image API key rejected. Check your Gemini or OpenAI key in Settings → AI Providers."
    if status_code == 404 and "model" in body_lower:
        return "Cover image model not found. Pick another model under Settings → AI Providers."
    if status_code == 400 and "aspect_ratio" in body_lower:
        return (
            "Cover image aspect ratio rejected by Gemini for this platform. "
            "Try another cover image model in Settings → AI Providers."
        )
    return f"Cover image generation failed: {body[:200]}"


def _gemini_image_provider_label(model: str) -> str:
    return f"google-{model}"


def _openai_image_provider_label(model: str) -> str:
    return f"openai-{model}"


async def resolve_cover_image_model(
    *, session: AsyncSession, model: str | None
) -> str:
    if model:
        meta = await ai_catalog.get_image_model_meta(session=session, model_key=model)
        if meta:
            return meta.id
        return model
    return await ai_catalog.get_default_cover_image_model_key(session=session)


@dataclass(frozen=True)
class GeneratedCoverImage:
    data: bytes
    provider: str
    content_type: str = "image/png"


async def _generate_openai_cover_image_bytes(
    *,
    api_key: str,
    prompt: str,
    model: str,
    base_url: str = "https://api.openai.com/v1",
) -> bytes:
    async with httpx.AsyncClient(
        timeout=float(settings.AI_OPENAI_IMAGE_GENERATION_TIMEOUT_SECONDS)
    ) as client:
        response = await client.post(
            f"{base_url.rstrip('/')}/images/generations",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "prompt": prompt,
                "n": 1,
                "size": DALLE_SIZE,
                "response_format": "b64_json",
            },
        )
    if response.status_code != 200:
        logger.error(
            "DALL-E API error",
            status=response.status_code,
            body=response.text,
        )
        raise HTTPException(
            status_code=502,
            detail=f"Image generation error: {response.text[:300]}",
        )
    payload = response.json()
    images = payload.get("data") or []
    if not images:
        raise HTTPException(status_code=502, detail="Image generation returned no data.")
    b64_data = images[0].get("b64_json")
    if not b64_data:
        image_url = images[0].get("url")
        if not image_url:
            raise HTTPException(
                status_code=502, detail="Image generation returned no image data."
            )
        async with httpx.AsyncClient(
            timeout=float(settings.AI_OPENAI_IMAGE_DOWNLOAD_TIMEOUT_SECONDS)
        ) as client:
            image_response = await client.get(image_url)
        if image_response.status_code != 200:
            raise HTTPException(
                status_code=502, detail="Failed to download generated image."
            )
        return image_response.content
    return base64.b64decode(b64_data)


async def _generate_gemini_cover_image_bytes(
    *,
    api_key: str,
    prompt: str,
    model: str,
    aspect_ratio: str,
    base_url: str = "https://generativelanguage.googleapis.com/v1beta",
) -> tuple[bytes, str]:
    url = f"{base_url.rstrip('/')}/models/{model}:generateContent"
    generation_config = _gemini_image_generation_config(
        model, aspect_ratio=aspect_ratio
    )
    async with httpx.AsyncClient(
        timeout=float(settings.AI_GEMINI_IMAGE_GENERATION_TIMEOUT_SECONDS)
    ) as client:
        response = await client.post(
            url,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": api_key,
            },
            json={
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": prompt}],
                    }
                ],
                "generationConfig": generation_config,
            },
        )
    if response.status_code != 200:
        logger.error(
            "Gemini image API error",
            status=response.status_code,
            body=response.text,
            model=model,
        )
        raise HTTPException(
            status_code=502,
            detail=_format_image_error(
                status_code=response.status_code,
                body=response.text,
            ),
        )
    payload = response.json()
    candidates = payload.get("candidates") or []
    if not candidates:
        raise HTTPException(
            status_code=502, detail="Image generation returned no candidates."
        )
    parts = candidates[0].get("content", {}).get("parts") or []
    for part in parts:
        inline_data = part.get("inlineData") or part.get("inline_data")
        if not inline_data:
            continue
        b64_data = inline_data.get("data")
        if not b64_data:
            continue
        mime_type = inline_data.get("mimeType") or inline_data.get("mime_type") or "image/png"
        return base64.b64decode(b64_data), mime_type
    raise HTTPException(
        status_code=502, detail="Image generation returned no image data."
    )


def _platform_cover_prompt(*, prompt: str, platform: CoverImagePlatform) -> str:
    spec = get_cover_spec(platform)
    return (
        f"{prompt.strip()}\n\n"
        f"Create a professional cover image for {spec.label} "
        f"({spec.width}x{spec.height} pixels, wide banner layout). "
        "Include one short, bold headline phrase inspired by the prompt with "
        "clear, legible typography. Do not add URLs or watermarks."
    )


async def generate_cover_image(
    *,
    session: AsyncSession,
    prompt: str,
    cover_image_model: str,
    provider_api_keys: dict[str, str | None],
    platform: CoverImagePlatform,
) -> GeneratedCoverImage | None:
    spec = get_cover_spec(platform)
    model = await resolve_cover_image_model(
        session=session, model=cover_image_model
    )
    meta = await ai_catalog.get_image_model_meta(session=session, model_key=model)
    key_provider = meta.key_provider if meta else "gemini"

    provider_row = await ai_catalog.get_system_provider(
        session=session, slug=key_provider
    )
    api_key = provider_api_keys.get(key_provider)
    if not api_key:
        return None

    base_url = provider_row.base_url if provider_row else ""
    platform_prompt = _platform_cover_prompt(prompt=prompt, platform=platform)

    if key_provider == "openai":
        image_bytes = await _generate_openai_cover_image_bytes(
            api_key=api_key,
            prompt=platform_prompt,
            model=model,
            base_url=base_url or "https://api.openai.com/v1",
        )
        content_type = "image/png"
        provider = _openai_image_provider_label(model)
    else:
        gemini_base = base_url or "https://generativelanguage.googleapis.com/v1beta"
        image_bytes, content_type = await _generate_gemini_cover_image_bytes(
            api_key=api_key,
            prompt=platform_prompt,
            model=model,
            aspect_ratio=spec.gemini_aspect_ratio,
            base_url=gemini_base,
        )
        provider = _gemini_image_provider_label(model)

    resized_bytes, resized_type = resize_cover_image_bytes(
        image_bytes,
        width=spec.width,
        height=spec.height,
        content_type=content_type,
    )
    return GeneratedCoverImage(
        data=resized_bytes,
        provider=provider,
        content_type=resized_type,
    )
