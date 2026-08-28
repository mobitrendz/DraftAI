import io
import uuid
from datetime import UTC, datetime

import structlog
from fastapi import HTTPException
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.crud import publish_job as publish_job_crud
from app.crud import ai_catalog
from app.crud import settings as settings_crud
from app.models.content import (
    ContentDraft,
    ContentDraftDetailPublic,
    ContentDraftPublic,
    ContentDraftStatus,
    ContentDraftsPublic,
    CoverImage,
    CoverImagePlatform,
    CoverImagePublic,
    DevtoArticle,
    DevtoArticlePublic,
    GenerateDraftRequest,
    LinkedinPost,
    LinkedinPostPublic,
    PublishJobPublic,
    UpdateDraftRequest,
)
from app.services.platforms.cover_urls import cover_extension_from_storage_key
from app.services.publish import assert_draft_editable, build_linkedin_clipboard_text
from app.models.platform_config import PlatformConfig
from app.core.config import settings
from app.services.ai.cover_specs import get_cover_spec
from app.services.ai.images import GeneratedCoverImage, generate_cover_image
from app.services.ai.template_cover import (
    TEMPLATE_PROVIDER,
    generate_template_cover_bytes,
)
from app.services.ai.llm import generate_json_content
from app.services.storage import storage

logger = structlog.get_logger(__name__)

USER_UPLOAD_PROVIDER = "user-upload"
ALLOWED_COVER_UPLOAD_TYPES = frozenset({"image/png", "image/jpeg", "image/webp"})
COVER_UPLOAD_EXTENSIONS = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
}

GENERATION_OUTPUT_SCHEMA = """Respond ONLY with valid JSON matching this schema:
{
  "devto_title": "string",
  "devto_body_markdown": "string (full technical article in Markdown, 800-1500 words)",
  "devto_tags": "comma-separated tags, max 4",
  "linkedin_teaser": "string (LinkedIn post text, 1-5 short paragraphs, no URL yet)",
  "cover_image_prompt": "string (describe a professional cover image for the article)"
}"""

DEFAULT_SYSTEM_PROMPT = f"""You are DraftAI, an expert technical writer for developers.
Generate publication-ready content from the user's topic.
{GENERATION_OUTPUT_SCHEMA}"""


def _resolve_system_prompt(custom_prompt: str | None) -> str:
    if not custom_prompt:
        return DEFAULT_SYSTEM_PROMPT
    return f"{custom_prompt.strip()}\n\n{GENERATION_OUTPUT_SCHEMA}"


def _normalize_generated_draft(generated: dict, *, topic: str) -> dict:
    normalized = dict(generated)
    aliases = {
        "devto_title": ("devtoTitle", "title", "article_title"),
        "devto_body_markdown": (
            "devtoBodyMarkdown",
            "body_markdown",
            "body",
            "article_body",
        ),
        "devto_tags": ("devtoTags", "tags"),
        "linkedin_teaser": ("linkedinTeaser", "linkedin_post", "teaser", "teaser_text"),
        "cover_image_prompt": ("coverImagePrompt", "cover_prompt", "image_prompt"),
    }
    for canonical, keys in aliases.items():
        if normalized.get(canonical):
            continue
        for key in keys:
            value = normalized.get(key)
            if value:
                normalized[canonical] = value
                break

    post_text = str(normalized.get("linkedin_teaser") or "").strip()
    if not post_text:
        title = str(normalized.get("devto_title") or topic).strip()
        normalized["linkedin_teaser"] = (
            f"Just published: {title}\n\n"
            "Here are the key takeaways and practical steps."
        )[:800]

    return normalized


def _provider_missing_key_message(provider_slug: str, label: str | None = None) -> str:
    name = label or provider_slug
    return f"{name} API key required. Add your key in Settings → AI Providers."


def _template_cover_warning(*, prior_detail: str | None = None) -> str:
    if prior_detail:
        detail = prior_detail.rstrip(".")
        return f"{detail}. A template cover image was saved instead."
    return "AI cover image unavailable. A template cover image was saved instead."


def _combine_cover_warnings(warnings: list[str]) -> str:
    unique: list[str] = []
    for warning in warnings:
        if warning not in unique:
            unique.append(warning)
    return " ".join(unique)


def _store_generated_cover(
    *,
    draft_id: uuid.UUID,
    platform: CoverImagePlatform,
    generated_image: GeneratedCoverImage,
) -> tuple[str, str]:
    ext = "png" if generated_image.content_type == "image/png" else "jpg"
    storage_key = f"covers/{draft_id}/{platform.value}.{ext}"
    storage.upload_bytes(
        key=storage_key,
        data=generated_image.data,
        content_type=generated_image.content_type,
    )
    return storage_key, generated_image.provider


def _build_template_cover(
    *,
    title: str,
    subtitle: str | None,
    platform: CoverImagePlatform,
) -> GeneratedCoverImage:
    spec = get_cover_spec(platform)
    return GeneratedCoverImage(
        data=generate_template_cover_bytes(
            title=title,
            subtitle=subtitle,
            width=spec.width,
            height=spec.height,
        ),
        provider=TEMPLATE_PROVIDER,
        content_type="image/png",
    )


def _try_template_cover_fallback(
    *,
    title: str,
    subtitle: str | None,
    prior_detail: str | None,
    platform: CoverImagePlatform,
) -> tuple[GeneratedCoverImage | None, str | None]:
    if not settings.COVER_TEMPLATE_FALLBACK_ENABLED:
        return None, prior_detail
    try:
        return _build_template_cover(
            title=title, subtitle=subtitle, platform=platform
        ), _template_cover_warning(prior_detail=prior_detail)
    except Exception as exc:
        logger.warning("Template cover generation failed", error=str(exc))
        if prior_detail:
            return None, prior_detail
        return None, f"Cover image could not be generated: {exc}"

def _cover_image_cache_version(updated_at: datetime) -> str:
    return str(int(updated_at.timestamp()))


def _build_cover_image_url(
    *,
    draft_id: uuid.UUID,
    cover: CoverImage,
    cache_version: str,
) -> str | None:
    if not cover.storage_key:
        return None
    extension = cover_extension_from_storage_key(cover.storage_key)
    filename = f"{cover.platform.value}.{extension}"
    return f"/api/v1/public/covers/{draft_id}/{filename}?v={cache_version}"


def _cover_image_public(
    cover: CoverImage,
    *,
    draft_id: uuid.UUID,
    cache_version: str,
) -> CoverImagePublic:
    public = CoverImagePublic.model_validate(cover)
    public.image_url = _build_cover_image_url(
        draft_id=draft_id,
        cover=cover,
        cache_version=cache_version,
    )
    return public


async def list_drafts(
    *, session: AsyncSession, user_id: uuid.UUID
) -> ContentDraftsPublic:
    statement = (
        select(ContentDraft)
        .where(ContentDraft.user_id == user_id)
        .order_by(ContentDraft.created_at.desc())  # type: ignore
    )
    result = await session.execute(statement)
    drafts = result.scalars().all()
    return ContentDraftsPublic(
        data=[ContentDraftPublic.model_validate(d) for d in drafts],
        count=len(drafts),
    )


async def get_draft_detail(
    *, session: AsyncSession, user_id: uuid.UUID, draft_id: uuid.UUID
) -> ContentDraftDetailPublic | None:
    draft = await session.get(ContentDraft, draft_id)
    if not draft or draft.user_id != user_id:
        return None

    devto = (
        await session.execute(
            select(DevtoArticle).where(DevtoArticle.content_draft_id == draft_id)
        )
    ).scalars().first()
    linkedin = (
        await session.execute(
            select(LinkedinPost).where(LinkedinPost.content_draft_id == draft_id)
        )
    ).scalars().first()
    covers = (
        await session.execute(
            select(CoverImage).where(CoverImage.content_draft_id == draft_id)
        )
    ).scalars().all()

    publish_job_row = await publish_job_crud.get_latest_publish_job(
        session=session, draft_id=draft_id
    )
    linkedin_clipboard_text = None
    if linkedin:
        linkedin_clipboard_text = build_linkedin_clipboard_text(
            teaser_text=linkedin.teaser_text,
            article_url=linkedin.article_url,
        )

    return ContentDraftDetailPublic(
        **ContentDraftPublic.model_validate(draft).model_dump(),
        devto_article=DevtoArticlePublic.model_validate(devto) if devto else None,
        linkedin_post=LinkedinPostPublic.model_validate(linkedin) if linkedin else None,
        cover_images=[
            _cover_image_public(
                c,
                draft_id=draft_id,
                cache_version=_cover_image_cache_version(draft.updated_at),
            )
            for c in covers
        ],
        publish_job=(
            PublishJobPublic.model_validate(publish_job_row)
            if publish_job_row
            else None
        ),
        linkedin_clipboard_text=linkedin_clipboard_text,
    )


async def _generate_and_store_single_cover(
    *,
    session: AsyncSession,
    draft_id: uuid.UUID,
    image: CoverImage,
    cover_prompt: str,
    cover_title: str,
    cover_image_model: str,
    provider_api_keys: dict[str, str | None],
) -> str | None:
    cover_meta = await ai_catalog.get_image_model_meta(
        session=session, model_key=cover_image_model
    )
    required_key_slug = cover_meta.key_provider if cover_meta else "gemini"
    has_cover_api_key = bool(provider_api_keys.get(required_key_slug))
    platform_warning: str | None = None
    generated_image: GeneratedCoverImage | None = None

    if not has_cover_api_key:
        provider_label = (
            "Gemini" if required_key_slug == "gemini" else required_key_slug
        )
        platform_warning = (
            f"{provider_label} API key required for cover images. "
            "Add it in Settings → AI Providers (cover images use a separate model from article text)."
        )
    else:
        try:
            generated_image = await generate_cover_image(
                session=session,
                prompt=cover_prompt,
                cover_image_model=cover_image_model,
                provider_api_keys=provider_api_keys,
                platform=image.platform,
            )
            if not generated_image:
                platform_warning = "Cover image generation returned no data."
        except HTTPException as exc:
            logger.warning(
                "Cover image generation failed",
                draft_id=str(draft_id),
                platform=image.platform.value,
                detail=exc.detail,
            )
            platform_warning = str(exc.detail)
        except Exception as exc:
            logger.warning(
                "Cover image generation failed",
                draft_id=str(draft_id),
                platform=image.platform.value,
                error=str(exc),
            )
            platform_warning = f"Cover image generation failed: {exc}"

    if not generated_image:
        generated_image, platform_warning = _try_template_cover_fallback(
            title=cover_title,
            subtitle=cover_prompt,
            prior_detail=platform_warning,
            platform=image.platform,
        )

    if generated_image:
        try:
            storage_key, image_provider = _store_generated_cover(
                draft_id=draft_id,
                platform=image.platform,
                generated_image=generated_image,
            )
            image.storage_key = storage_key
            image.provider = image_provider
        except Exception as exc:
            logger.warning(
                "Cover image storage failed",
                draft_id=str(draft_id),
                platform=image.platform.value,
                error=str(exc),
            )
            platform_warning = f"Cover image could not be saved to storage: {exc}"

    image.prompt_used = cover_prompt
    session.add(image)
    await session.flush()
    return platform_warning


async def _persist_cover_images(
    *,
    session: AsyncSession,
    draft_id: uuid.UUID,
    cover_images: list[CoverImage],
    cover_prompt: str,
    cover_title: str,
    cover_image_model: str,
    provider_api_keys: dict[str, str | None],
) -> str | None:
    if not cover_images:
        return None

    warnings: list[str] = []

    for image in cover_images:
        platform_warning = await _generate_and_store_single_cover(
            session=session,
            draft_id=draft_id,
            image=image,
            cover_prompt=cover_prompt,
            cover_title=cover_title,
            cover_image_model=cover_image_model,
            provider_api_keys=provider_api_keys,
        )
        if platform_warning:
            warnings.append(platform_warning)

    return _combine_cover_warnings(warnings) if warnings else None


async def generate_draft(
    *,
    session: AsyncSession,
    user_id: uuid.UUID,
    request: GenerateDraftRequest,
) -> ContentDraftDetailPublic:
    ai_config = await settings_crud.get_or_create_ai_config(
        session=session, user_id=user_id
    )
    platform_config = await settings_crud.get_or_create_platform_config(
        session=session, user_id=user_id
    )

    user_message = f"Topic: {request.topic}"
    if request.user_prompt:
        user_message += f"\n\nAdditional instructions:\n{request.user_prompt}"

    legacy_column = ai_catalog.LEGACY_PROVIDER_KEY_COLUMNS.get(ai_config.provider)
    legacy_encrypted = (
        getattr(ai_config, legacy_column) if legacy_column else None
    )
    try:
        generation = await ai_catalog.resolve_text_generation(
            session=session,
            user_id=user_id,
            provider_slug=ai_config.provider,
            model_key=ai_config.model,
            legacy_encrypted=legacy_encrypted,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if generation.auth_style != "none" and not generation.api_key:
        provider_row = await ai_catalog.get_system_provider(
            session=session, slug=ai_config.provider
        )
        raise HTTPException(
            status_code=400,
            detail=_provider_missing_key_message(
                ai_config.provider,
                provider_row.display_name if provider_row else None,
            ),
        )

    system_prompt = _resolve_system_prompt(ai_config.system_prompt)

    generated = await generate_json_content(
        api_adapter=generation.api_adapter,
        base_url=generation.base_url,
        api_key=generation.api_key,
        model=generation.model_key,
        temperature=ai_config.temperature,
        system_prompt=system_prompt,
        user_message=user_message,
        auth_style=generation.auth_style,
        auth_header_name=generation.auth_header_name,
        extra_headers=generation.extra_headers,
        provider_label=generation.provider_slug,
    )
    generated = _normalize_generated_draft(generated, topic=request.topic)

    now = datetime.now(UTC)
    draft = ContentDraft(
        user_id=user_id,
        topic=request.topic,
        user_prompt=request.user_prompt,
        status=ContentDraftStatus.DRAFT,
        created_at=now,
        updated_at=now,
    )
    session.add(draft)
    await session.flush()

    cover_images: list[CoverImage] = []
    cover_prompt = generated.get("cover_image_prompt", request.topic)

    if platform_config.devto_enabled:
        cover_images.append(
            CoverImage(
                content_draft_id=draft.id,
                platform=CoverImagePlatform.DEVTO,
                prompt_used=cover_prompt,
            )
        )
    if platform_config.linkedin_enabled:
        cover_images.append(
            CoverImage(
                content_draft_id=draft.id,
                platform=CoverImagePlatform.LINKEDIN,
                prompt_used=cover_prompt,
            )
        )

    cover_meta = await ai_catalog.get_image_model_meta(
        session=session, model_key=ai_config.cover_image_model
    )
    cover_key_provider = cover_meta.key_provider if cover_meta else "gemini"
    provider_api_keys: dict[str, str | None] = {
        cover_key_provider: await settings_crud.get_provider_api_key(
            session=session,
            config=ai_config,
            provider_slug=cover_key_provider,
        )
    }

    cover_image_warning = await _persist_cover_images(
        session=session,
        draft_id=draft.id,
        cover_images=cover_images,
        cover_prompt=cover_prompt,
        cover_title=str(generated.get("devto_title") or request.topic),
        cover_image_model=ai_config.cover_image_model,
        provider_api_keys=provider_api_keys,
    )

    devto_cover_id = next(
        (img.id for img in cover_images if img.platform == CoverImagePlatform.DEVTO),
        None,
    )
    linkedin_cover_id = next(
        (img.id for img in cover_images if img.platform == CoverImagePlatform.LINKEDIN),
        None,
    )

    if platform_config.devto_enabled:
        session.add(
            DevtoArticle(
                content_draft_id=draft.id,
                title=generated.get("devto_title", request.topic),
                body_markdown=generated.get("devto_body_markdown", ""),
                tags=generated.get("devto_tags", "devops,ai"),
                cover_image_id=devto_cover_id,
            )
        )

    if platform_config.linkedin_enabled:
        session.add(
            LinkedinPost(
                content_draft_id=draft.id,
                teaser_text=generated.get("linkedin_teaser", ""),
                cover_image_id=linkedin_cover_id,
            )
        )

    await session.commit()

    detail = await get_draft_detail(session=session, user_id=user_id, draft_id=draft.id)
    assert detail is not None
    if cover_image_warning:
        return detail.model_copy(update={"cover_image_warning": cover_image_warning})
    return detail


async def update_draft(
    *,
    session: AsyncSession,
    user_id: uuid.UUID,
    draft_id: uuid.UUID,
    update: UpdateDraftRequest,
) -> ContentDraftDetailPublic | None:
    draft = await session.get(ContentDraft, draft_id)
    if not draft or draft.user_id != user_id:
        return None

    assert_draft_editable(draft.status)

    data = update.model_dump(exclude_unset=True)
    if not data:
        return await get_draft_detail(
            session=session, user_id=user_id, draft_id=draft_id
        )

    devto = (
        await session.execute(
            select(DevtoArticle).where(DevtoArticle.content_draft_id == draft_id)
        )
    ).scalars().first()
    linkedin = (
        await session.execute(
            select(LinkedinPost).where(LinkedinPost.content_draft_id == draft_id)
        )
    ).scalars().first()

    if devto:
        if "devto_title" in data:
            devto.title = data["devto_title"]
        if "devto_body_markdown" in data:
            devto.body_markdown = data["devto_body_markdown"]
        if "devto_tags" in data:
            devto.tags = data["devto_tags"]
        session.add(devto)

    if linkedin and "linkedin_teaser" in data:
        linkedin.teaser_text = data["linkedin_teaser"]
        session.add(linkedin)

    draft.updated_at = datetime.now(UTC)
    session.add(draft)
    await session.commit()

    return await get_draft_detail(session=session, user_id=user_id, draft_id=draft_id)


def _validate_cover_upload(*, data: bytes, content_type: str) -> str:
    normalized_type = content_type.split(";", 1)[0].strip().lower()
    if normalized_type not in ALLOWED_COVER_UPLOAD_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Cover image must be PNG, JPEG, or WebP.",
        )
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Cover image file is empty.")
    if len(data) > settings.COVER_UPLOAD_MAX_BYTES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Cover image is too large. Maximum size is "
                f"{settings.COVER_UPLOAD_MAX_BYTES // (1024 * 1024)} MB."
            ),
        )
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is not a valid image.",
        ) from exc
    return normalized_type


async def upload_draft_cover_image(
    *,
    session: AsyncSession,
    user_id: uuid.UUID,
    draft_id: uuid.UUID,
    cover_id: uuid.UUID,
    data: bytes,
    content_type: str,
) -> ContentDraftDetailPublic | None:
    draft = await session.get(ContentDraft, draft_id)
    if not draft or draft.user_id != user_id:
        return None

    assert_draft_editable(draft.status)

    cover = await session.get(CoverImage, cover_id)
    if not cover or cover.content_draft_id != draft_id:
        return None

    normalized_type = _validate_cover_upload(data=data, content_type=content_type)
    extension = COVER_UPLOAD_EXTENSIONS[normalized_type]
    new_storage_key = f"covers/{draft_id}/{cover.platform.value}.{extension}"
    previous_storage_key = cover.storage_key

    storage.upload_bytes(
        key=new_storage_key,
        data=data,
        content_type=normalized_type,
    )

    cover.storage_key = new_storage_key
    cover.provider = USER_UPLOAD_PROVIDER
    session.add(cover)

    draft.updated_at = datetime.now(UTC)
    session.add(draft)
    await session.commit()

    if previous_storage_key and previous_storage_key != new_storage_key:
        try:
            storage.delete_object(key=previous_storage_key)
        except Exception:
            logger.warning(
                "Failed to delete replaced cover image",
                draft_id=str(draft_id),
                cover_id=str(cover_id),
                storage_key=previous_storage_key,
            )

    return await get_draft_detail(session=session, user_id=user_id, draft_id=draft_id)


async def regenerate_draft_cover_image(
    *,
    session: AsyncSession,
    user_id: uuid.UUID,
    draft_id: uuid.UUID,
    cover_id: uuid.UUID,
    prompt: str,
) -> ContentDraftDetailPublic | None:
    draft = await session.get(ContentDraft, draft_id)
    if not draft or draft.user_id != user_id:
        return None

    assert_draft_editable(draft.status)

    cover = await session.get(CoverImage, cover_id)
    if not cover or cover.content_draft_id != draft_id:
        return None

    cover_prompt = prompt.strip()
    if not cover_prompt:
        raise HTTPException(status_code=400, detail="Cover image prompt is required.")

    previous_storage_key = cover.storage_key

    ai_config = await settings_crud.get_or_create_ai_config(
        session=session, user_id=user_id
    )
    cover_meta = await ai_catalog.get_image_model_meta(
        session=session, model_key=ai_config.cover_image_model
    )
    cover_key_provider = cover_meta.key_provider if cover_meta else "gemini"
    provider_api_keys: dict[str, str | None] = {
        cover_key_provider: await settings_crud.get_provider_api_key(
            session=session,
            config=ai_config,
            provider_slug=cover_key_provider,
        )
    }

    devto = (
        await session.execute(
            select(DevtoArticle).where(DevtoArticle.content_draft_id == draft_id)
        )
    ).scalars().first()
    cover_title = devto.title if devto else draft.topic

    warning = await _generate_and_store_single_cover(
        session=session,
        draft_id=draft_id,
        image=cover,
        cover_prompt=cover_prompt,
        cover_title=cover_title,
        cover_image_model=ai_config.cover_image_model,
        provider_api_keys=provider_api_keys,
    )

    draft.updated_at = datetime.now(UTC)
    session.add(draft)
    await session.commit()

    if (
        previous_storage_key
        and cover.storage_key
        and previous_storage_key != cover.storage_key
    ):
        try:
            storage.delete_object(key=previous_storage_key)
        except Exception:
            logger.warning(
                "Failed to delete replaced cover image",
                draft_id=str(draft_id),
                cover_id=str(cover_id),
                storage_key=previous_storage_key,
            )

    detail = await get_draft_detail(session=session, user_id=user_id, draft_id=draft_id)
    if detail and warning:
        return detail.model_copy(update={"cover_image_warning": warning})
    return detail


async def delete_draft(
    *, session: AsyncSession, user_id: uuid.UUID, draft_id: uuid.UUID
) -> bool:
    draft = await session.get(ContentDraft, draft_id)
    if not draft or draft.user_id != user_id:
        return False

    covers = (
        await session.execute(
            select(CoverImage).where(CoverImage.content_draft_id == draft_id)
        )
    ).scalars().all()
    storage_keys = {cover.storage_key for cover in covers if cover.storage_key}

    await session.delete(draft)
    await session.commit()

    for key in storage_keys:
        try:
            storage.delete_object(key=key)
        except Exception:
            logger.warning(
                "Failed to delete cover image from storage",
                draft_id=str(draft_id),
                storage_key=key,
            )

    return True
