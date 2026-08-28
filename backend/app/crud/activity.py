import uuid
from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.activity import UserActivitiesPublic, UserActivity


async def create_activity(
    *,
    session: AsyncSession,
    user_id: uuid.UUID | None,
    method: str,
    path: str,
    status_code: int,
    ip_address: str | None,
    user_agent: str | None,
) -> UserActivity:
    db_activity = UserActivity(
        user_id=user_id,
        method=method,
        path=path,
        status_code=status_code,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    session.add(db_activity)
    await session.commit()
    await session.refresh(db_activity)
    return db_activity


async def get_user_activities(
    *, session: AsyncSession, user_id: uuid.UUID
) -> UserActivitiesPublic:
    statement = (
        select(UserActivity)
        .where(UserActivity.user_id == user_id)
        .order_by(cast(Any, UserActivity.created_at).desc())
        .limit(20)
    )
    result = await session.execute(statement)
    activities = result.scalars().all()
    return UserActivitiesPublic(data=list(activities), count=len(activities))
