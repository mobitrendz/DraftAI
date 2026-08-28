import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models.user import get_datetime_utc


class ContentDraftStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    PARTIALLY_PUBLISHED = "partially_published"
    FAILED = "failed"


class CoverImagePlatform(StrEnum):
    DEVTO = "devto"
    LINKEDIN = "linkedin"


class PublishJobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class ContentDraftBase(SQLModel):
    topic: str = Field(max_length=500)
    user_prompt: str | None = Field(default=None, max_length=4000)
    status: ContentDraftStatus = Field(default=ContentDraftStatus.DRAFT)


class ContentDraft(ContentDraftBase, table=True):
    __tablename__ = "content_draft"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", index=True, ondelete="CASCADE")
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class ContentDraftPublic(ContentDraftBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class CoverImage(SQLModel, table=True):
    __tablename__ = "cover_image"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    content_draft_id: uuid.UUID = Field(
        foreign_key="content_draft.id", index=True, ondelete="CASCADE"
    )
    platform: CoverImagePlatform
    storage_key: str | None = Field(default=None, max_length=1024)
    prompt_used: str | None = Field(default=None, max_length=2000)
    provider: str | None = Field(default=None, max_length=64)
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class CoverImagePublic(SQLModel):
    id: uuid.UUID
    platform: CoverImagePlatform
    storage_key: str | None
    prompt_used: str | None
    provider: str | None
    image_url: str | None = None


class DevtoArticle(SQLModel, table=True):
    __tablename__ = "devto_article"
    __table_args__ = (UniqueConstraint("content_draft_id"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    content_draft_id: uuid.UUID = Field(
        foreign_key="content_draft.id", index=True, ondelete="CASCADE"
    )
    title: str = Field(max_length=500)
    body_markdown: str
    tags: str = Field(default="", max_length=500)
    cover_image_id: uuid.UUID | None = Field(
        default=None, foreign_key="cover_image.id", ondelete="SET NULL"
    )


class DevtoArticlePublic(SQLModel):
    id: uuid.UUID
    title: str
    body_markdown: str
    tags: str
    cover_image_id: uuid.UUID | None


class LinkedinPost(SQLModel, table=True):
    __tablename__ = "linkedin_post"
    __table_args__ = (UniqueConstraint("content_draft_id"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    content_draft_id: uuid.UUID = Field(
        foreign_key="content_draft.id", index=True, ondelete="CASCADE"
    )
    teaser_text: str
    article_url: str | None = Field(default=None, max_length=2048)
    cover_image_id: uuid.UUID | None = Field(
        default=None, foreign_key="cover_image.id", ondelete="SET NULL"
    )


class LinkedinPostPublic(SQLModel):
    id: uuid.UUID
    teaser_text: str
    article_url: str | None
    cover_image_id: uuid.UUID | None


class PublishJob(SQLModel, table=True):
    __tablename__ = "publish_job"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    content_draft_id: uuid.UUID = Field(
        foreign_key="content_draft.id", index=True, ondelete="CASCADE"
    )
    status: PublishJobStatus = Field(default=PublishJobStatus.PENDING)
    retry_count: int = Field(default=0)
    devto_url: str | None = Field(default=None, max_length=2048)
    error_message: str | None = Field(default=None, max_length=2000)
    scheduled_at: datetime | None = Field(
        default=None, sa_type=DateTime(timezone=True)  # type: ignore
    )
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class PublishJobPublic(SQLModel):
    id: uuid.UUID
    status: PublishJobStatus
    retry_count: int
    devto_url: str | None
    error_message: str | None
    scheduled_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PublishStatusPublic(SQLModel):
    draft_status: ContentDraftStatus
    publish_job: PublishJobPublic | None = None
    linkedin_clipboard_text: str | None = None


class ScheduleDraftRequest(SQLModel):
    scheduled_at: datetime | None = Field(
        default=None,
        description="When to publish (UTC). Omit for immediate publish on first schedule.",
    )


class RescheduleDraftRequest(SQLModel):
    scheduled_at: datetime = Field(
        description="New publish time (UTC) for a scheduled draft.",
    )


class ContentDraftDetailPublic(ContentDraftPublic):
    devto_article: DevtoArticlePublic | None = None
    linkedin_post: LinkedinPostPublic | None = None
    cover_images: list[CoverImagePublic] = Field(default_factory=list)
    cover_image_warning: str | None = Field(
        default=None,
        description="Set when cover image generation was skipped or failed",
    )
    publish_job: PublishJobPublic | None = None
    linkedin_clipboard_text: str | None = Field(
        default=None,
        description="LinkedIn post text with live DEV.to URL when available",
    )


class GenerateDraftRequest(SQLModel):
    topic: str = Field(min_length=3, max_length=500)
    user_prompt: str | None = Field(default=None, max_length=4000)


class UpdateDraftRequest(SQLModel):
    devto_title: str | None = Field(default=None, max_length=500)
    devto_body_markdown: str | None = None
    devto_tags: str | None = Field(default=None, max_length=500)
    linkedin_teaser: str | None = None


class RegenerateCoverImageRequest(SQLModel):
    prompt: str = Field(min_length=1, max_length=2000)


class ContentDraftsPublic(SQLModel):
    data: list[ContentDraftPublic]
    count: int
