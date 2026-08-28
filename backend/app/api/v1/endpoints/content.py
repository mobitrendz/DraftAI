import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.api.deps import CurrentUser
from app.db.database import SessionDependency
from app.models.content import (
    ContentDraftDetailPublic,
    ContentDraftsPublic,
    GenerateDraftRequest,
    PublishStatusPublic,
    RegenerateCoverImageRequest,
    RescheduleDraftRequest,
    ScheduleDraftRequest,
    UpdateDraftRequest,
)
from app.services import content as content_service
from app.services import publish as publish_service

router = APIRouter()


@router.get("/", response_model=ContentDraftsPublic)
async def list_content_drafts(
    session: SessionDependency, current_user: CurrentUser
) -> ContentDraftsPublic:
    return await content_service.list_drafts(
        session=session, user_id=current_user.id
    )


@router.get("/{draft_id}", response_model=ContentDraftDetailPublic)
async def get_content_draft(
    session: SessionDependency,
    current_user: CurrentUser,
    draft_id: uuid.UUID,
) -> ContentDraftDetailPublic:
    draft = await content_service.get_draft_detail(
        session=session, user_id=current_user.id, draft_id=draft_id
    )
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


@router.post("/generate", response_model=ContentDraftDetailPublic, status_code=201)
async def generate_content_draft(
    session: SessionDependency,
    current_user: CurrentUser,
    body: GenerateDraftRequest,
) -> ContentDraftDetailPublic:
    return await content_service.generate_draft(
        session=session, user_id=current_user.id, request=body
    )


@router.patch("/{draft_id}", response_model=ContentDraftDetailPublic)
async def update_content_draft(
    session: SessionDependency,
    current_user: CurrentUser,
    draft_id: uuid.UUID,
    body: UpdateDraftRequest,
) -> ContentDraftDetailPublic:
    draft = await content_service.update_draft(
        session=session,
        user_id=current_user.id,
        draft_id=draft_id,
        update=body,
    )
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


@router.post("/{draft_id}/covers/{cover_id}/image", response_model=ContentDraftDetailPublic)
async def upload_content_draft_cover_image(
    session: SessionDependency,
    current_user: CurrentUser,
    draft_id: uuid.UUID,
    cover_id: uuid.UUID,
    file: UploadFile = File(...),
) -> ContentDraftDetailPublic:
    data = await file.read()
    draft = await content_service.upload_draft_cover_image(
        session=session,
        user_id=current_user.id,
        draft_id=draft_id,
        cover_id=cover_id,
        data=data,
        content_type=file.content_type or "application/octet-stream",
    )
    if not draft:
        raise HTTPException(status_code=404, detail="Draft or cover image not found")
    return draft


@router.post(
    "/{draft_id}/covers/{cover_id}/regenerate",
    response_model=ContentDraftDetailPublic,
)
async def regenerate_content_draft_cover_image(
    session: SessionDependency,
    current_user: CurrentUser,
    draft_id: uuid.UUID,
    cover_id: uuid.UUID,
    body: RegenerateCoverImageRequest,
) -> ContentDraftDetailPublic:
    draft = await content_service.regenerate_draft_cover_image(
        session=session,
        user_id=current_user.id,
        draft_id=draft_id,
        cover_id=cover_id,
        prompt=body.prompt,
    )
    if not draft:
        raise HTTPException(status_code=404, detail="Draft or cover image not found")
    return draft


@router.post("/{draft_id}/approve", response_model=ContentDraftDetailPublic)
async def approve_content_draft(
    session: SessionDependency,
    current_user: CurrentUser,
    draft_id: uuid.UUID,
) -> ContentDraftDetailPublic:
    draft = await publish_service.approve_draft(
        session=session,
        user_id=current_user.id,
        draft_id=draft_id,
    )
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


@router.post("/{draft_id}/schedule", response_model=PublishStatusPublic)
async def schedule_content_draft(
    session: SessionDependency,
    current_user: CurrentUser,
    draft_id: uuid.UUID,
    body: ScheduleDraftRequest | None = None,
) -> PublishStatusPublic:
    scheduled_at = body.scheduled_at if body else None
    status = await publish_service.schedule_draft(
        session=session,
        user_id=current_user.id,
        draft_id=draft_id,
        scheduled_at=scheduled_at,
    )
    if not status:
        raise HTTPException(status_code=404, detail="Draft not found")
    return status


@router.patch("/{draft_id}/schedule", response_model=PublishStatusPublic)
async def reschedule_content_draft(
    session: SessionDependency,
    current_user: CurrentUser,
    draft_id: uuid.UUID,
    body: RescheduleDraftRequest,
) -> PublishStatusPublic:
    status = await publish_service.reschedule_draft(
        session=session,
        user_id=current_user.id,
        draft_id=draft_id,
        scheduled_at=body.scheduled_at,
    )
    if not status:
        raise HTTPException(status_code=404, detail="Draft not found")
    return status


@router.get("/{draft_id}/publish-status", response_model=PublishStatusPublic)
async def get_content_draft_publish_status(
    session: SessionDependency,
    current_user: CurrentUser,
    draft_id: uuid.UUID,
) -> PublishStatusPublic:
    status = await publish_service.get_publish_status(
        session=session,
        user_id=current_user.id,
        draft_id=draft_id,
    )
    if not status:
        raise HTTPException(status_code=404, detail="Draft not found")
    return status


@router.post("/{draft_id}/retry-publish", response_model=PublishStatusPublic)
async def retry_content_draft_publish(
    session: SessionDependency,
    current_user: CurrentUser,
    draft_id: uuid.UUID,
) -> PublishStatusPublic:
    status = await publish_service.retry_publish(
        session=session,
        user_id=current_user.id,
        draft_id=draft_id,
    )
    if not status:
        raise HTTPException(status_code=404, detail="Draft not found")
    return status


@router.delete("/{draft_id}", status_code=204)
async def delete_content_draft(
    session: SessionDependency,
    current_user: CurrentUser,
    draft_id: uuid.UUID,
) -> None:
    deleted = await content_service.delete_draft(
        session=session,
        user_id=current_user.id,
        draft_id=draft_id,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Draft not found")
