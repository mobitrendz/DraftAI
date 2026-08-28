import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import settings
from app.crud import user as user_crud
from app.db import database
from app.models.user import User, UserCreate, UserRole

logger = structlog.get_logger(__name__)


# Initial data creation for the database, including creating a superuser if it does not already exist.
# This function is designed to be run during application startup to ensure that the necessary initial data is present in the database.
# It checks for the existence of a user with the email specified in the settings (SUPER_USER_EMAIL) and creates a new user with admin privileges if one does not already exist.
# This allows for easy setup of an initial admin user for managing the application without needing to manually insert data into the database.
# The function uses the user_crud.create_user function to create the user, ensuring that the password is properly hashed and that all necessary fields are set according to the UserCreate model.
# The logging statements provide feedback on whether the initial data was created or if it already exists, helping with debugging and monitoring during application startup.
# This approach promotes a smooth initial setup process for the application, allowing developers to quickly get started with a pre-configured admin user.
async def init_db(session: AsyncSession) -> None:
    # Tables should be created with Alembic migrations
    # But if you don't want to use migrations, create
    # the tables un-commenting the next lines
    # from sqlmodel import SQLModel

    # This works because the models are already imported and registered from app.models
    # SQLModel.metadata.create_all(engine)

    logger.info("Creating initial data")

    statement = select(User).where(User.email == settings.SUPER_USER_EMAIL)
    result = await session.execute(statement)
    user = result.scalars().first()

    if not user:
        user_in = UserCreate(
            full_name=settings.SUPER_USER_NAME,
            email=settings.SUPER_USER_EMAIL,
            password=settings.SUPER_USER_PASSWORD,
            role=UserRole.SUPER,
        )
        user = await user_crud.create_user(session=session, user_create=user_in)
        logger.info("Initial data created")
    else:
        logger.info("Initial data already present")


async def init() -> None:
    async with database.async_session_maker() as session:
        await init_db(session)


async def main() -> None:
    await init()
