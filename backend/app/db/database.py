from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

engine = create_async_engine(
    str(settings.SQLALCHEMY_DATABASE_URI),
    pool_pre_ping=True,
)

async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


# Database session management using SQLModel and FastAPI dependencies. This module sets up the database connection using SQLAlchemy's create_async_engine function with the database URI from the settings. It defines a get_session function that creates a new database session for each request and ensures that the session is properly closed after the request is completed. The SessionDependency is an annotated type that can be used in API endpoints to inject the database session as a dependency, allowing for easy access to the database in CRUD operations and other interactions with the User model and related data. This approach promotes clean and efficient database management throughout the application, ensuring that resources are properly managed and that database connections are not left open unnecessarily.
# The use of an async generator function for get_session allows for the use of the with statement to ensure that the session is properly closed after use, even if an error occurs during the request. This promotes better resource management and helps prevent issues with database connections being left open. The SessionDependency can be easily used in any API endpoint that requires access to the database, making it a convenient and reusable way to manage database sessions across the application.
async def get_session() -> AsyncGenerator[AsyncSession]:
    async with async_session_maker() as session:
        yield session


# The SessionDependency is an annotated type that can be used in API endpoints to inject the database session as a dependency, allowing for easy access to the database in CRUD operations and other interactions with the User model and related data. This promotes clean and efficient database management throughout the application, ensuring that resources are properly managed and that database connections are not left open unnecessarily.
SessionDependency = Annotated[AsyncSession, Depends(get_session)]
