from fastapi import APIRouter
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import apaginate
from sqlmodel import select

from app.api.deps import AllowSuper, CurrentUser
from app.crud import activity as activity_crud
from app.db.database import SessionDependency
from app.models.activity import UserActivitiesPublic, UserActivity, UserActivityPublic

router = APIRouter()


@router.get("/me", response_model=UserActivitiesPublic)
async def read_my_activities(
    session: SessionDependency,
    current_user: CurrentUser,
) -> UserActivitiesPublic:
    """
    Retrieve the last 20 activities for the authenticated user.
    """
    return await activity_crud.get_user_activities(
        session=session, user_id=current_user.id
    )


@router.get("/", response_model=Page[UserActivityPublic])
async def read_all_activities(
    session: SessionDependency,
    _current_user: AllowSuper,
) -> Page[UserActivityPublic]:
    """
    Retrieve all system-wide activities (SUPER users only).
    """
    statement = select(UserActivity).order_by(UserActivity.created_at.desc())  # type: ignore
    return await apaginate(session, statement)  # type: ignore
