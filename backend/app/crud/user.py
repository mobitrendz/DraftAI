import uuid
from typing import Any, cast

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.security import hash_password, verify_password
from app.models.user import (
    PasswordHistoriesPublic,
    PasswordHistory,
    UpdatePassword,
    User,
    UserCreate,
    UsersPublic,
    UserUpdate,
)


# CRUD operations for User model
async def create_user(*, session: AsyncSession, user_create: UserCreate) -> User:
    user = User.model_validate(
        user_create, update={"hashed_password": hash_password(user_create.password)}
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


# Read operations for users
async def get_users(*, session: AsyncSession) -> UsersPublic:
    statement = select(User)
    result = await session.execute(statement)
    users = result.scalars().all()
    return UsersPublic(data=users, count=len(users))


async def get_user_by_id(*, session: AsyncSession, id: uuid.UUID) -> User | None:
    return await session.get(User, id)


async def get_user_by_email(*, session: AsyncSession, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    result = await session.execute(statement)
    return result.scalars().first()


async def update_user(
    *, session: AsyncSession, id: uuid.UUID, user_update: UserUpdate
) -> User | None:
    user = await get_user_by_id(session=session, id=id)

    if not user:
        return None

    update_data = user_update.model_dump(exclude_unset=True)
    user.sqlmodel_update(update_data)

    session.add(user)
    await session.commit()
    await session.refresh(user)

    return user


async def delete_user(*, session: AsyncSession, id: uuid.UUID) -> bool:
    user = await get_user_by_id(session=session, id=id)

    if not user:
        return False

    await session.delete(user)
    await session.commit()

    return True


# Dummy hash for timing attack prevention
DUMMY_HASH = "$argon2id$v=19$m=65536,t=3,p=4$MjQyZWE1MzBjYjJlZTI0Yw$YTU4NGM5ZTZmYjE2NzZlZjY0ZWY3ZGRkY2U2OWFjNjk"


async def authenticate_user(
    *, session: AsyncSession, email: str, password: str
) -> User | None:
    db_user = await get_user_by_email(session=session, email=email)
    if not db_user:
        verify_password(password, DUMMY_HASH)
        return None
    verified = verify_password(password, db_user.hashed_password)
    if not verified:
        return None
    else:
        return db_user


# Update operation for changing a user's password, which requires verification of the current password.
async def update_password(
    *, session: AsyncSession, updatePassword: UpdatePassword, current_user: User
) -> bool:

    verified = verify_password(
        updatePassword.current_password, current_user.hashed_password
    )

    if not verified:
        raise HTTPException(status_code=400, detail="Incorrect password")
    if updatePassword.current_password == updatePassword.new_password:
        raise HTTPException(
            status_code=400, detail="New password cannot be the same as the current one"
        )

    # Save current password to history before updating
    password_history = PasswordHistory(
        user_id=current_user.id, hashed_password=current_user.hashed_password
    )
    session.add(password_history)

    hashed_password = hash_password(updatePassword.new_password)
    current_user.hashed_password = hashed_password
    session.add(current_user)
    await session.commit()

    return True


async def get_password_history(
    *, session: AsyncSession, user_id: uuid.UUID
) -> PasswordHistoriesPublic:
    statement = (
        select(PasswordHistory)
        .where(PasswordHistory.user_id == user_id)
        .order_by(cast(Any, PasswordHistory.created_at).desc())
        .limit(5)
    )
    result = await session.execute(statement)
    history = result.scalars().all()
    return PasswordHistoriesPublic(data=list(history), count=len(history))
