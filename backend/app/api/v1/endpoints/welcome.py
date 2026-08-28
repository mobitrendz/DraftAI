from fastapi import APIRouter, HTTPException
from sqlmodel import select

from app.core.config import settings
from app.db.database import SessionDependency

router = APIRouter()


@router.get("/checkDBConnection", response_model=dict[str, str])
async def check_database_connection(session: SessionDependency) -> dict[str, str]:
    try:
        await session.execute(select(1))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Database connection failed: {str(e)}"
        ) from e


@router.get("/getEnvironment", response_model=dict[str, str])
def get_env_settings() -> dict[str, str]:
    return {
        "Environment": settings.ENVIRONMENT,
        "ai_text_generation_timeout_seconds": str(
            settings.AI_TEXT_GENERATION_TIMEOUT_SECONDS
        ),
        "ai_draft_generation_max_seconds": str(
            settings.AI_DRAFT_GENERATION_MAX_SECONDS
        ),
    }


@router.get("/{user_name}", response_model=dict[str, str])
def get_custom_welcome_message(user_name: str) -> dict[str, str]:
    return {"message": "Welcome " + user_name + "!"}


@router.get("/", response_model=dict[str, str])
def get_welcome_message() -> dict[str, str]:
    return {"message": "Welcome User!"}
