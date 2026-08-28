from fastapi import APIRouter

from .endpoints import (
    activities,
    content,
    login,
    public_covers,
    settings,
    users,
    welcome,
)

api_router = APIRouter()

api_router.include_router(welcome.router, prefix="", tags=["Welcome"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(login.router, prefix="/login", tags=["Login"])
api_router.include_router(
    activities.router, prefix="/activities", tags=["User Activities"]
)
api_router.include_router(
    settings.router, prefix="/settings", tags=["Settings"]
)
api_router.include_router(
    content.router, prefix="/content/drafts", tags=["Content Drafts"]
)
api_router.include_router(
    public_covers.router, prefix="/public", tags=["Public"]
)
