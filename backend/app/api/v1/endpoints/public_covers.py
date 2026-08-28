import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.database import SessionDependency
from app.models.content import CoverImage, CoverImagePlatform
from app.services.platforms.cover_urls import (
    is_public_cover_filename,
    platform_from_cover_filename,
)
from app.services.storage import storage

router = APIRouter()


@router.get("/covers/{draft_id}/{filename}")
async def get_public_cover_image(
    session: SessionDependency,
    draft_id: uuid.UUID,
    filename: str,
) -> Response:
    """Serve cover images on a public URL so DEV.to can fetch them at publish time."""
    if not is_public_cover_filename(filename):
        raise HTTPException(status_code=404, detail="Cover image not found")

    platform = platform_from_cover_filename(filename)
    if platform is None:
        raise HTTPException(status_code=404, detail="Cover image not found")

    cover = (
        await session.execute(
            select(CoverImage).where(
                CoverImage.content_draft_id == draft_id,
                CoverImage.platform == platform,
            )
        )
    ).scalars().first()
    if not cover or not cover.storage_key:
        raise HTTPException(status_code=404, detail="Cover image not found")

    try:
        data, content_type = storage.get_object_bytes(key=cover.storage_key)
    except Exception as exc:
        raise HTTPException(
            status_code=404, detail="Cover image not found."
        ) from exc

    return Response(
        content=data,
        media_type=content_type,
        headers={"Cache-Control": "private, no-cache, must-revalidate"},
    )
