import uuid

from fastapi import APIRouter, HTTPException
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import apaginate
from fastapi_pagination.utils import disable_installed_extensions_check
from sqlmodel import select

from app.api.deps import AllowAnyRole, AllowSuperOrAdmin, CurrentUser
from app.crud import user as user_crud
from app.db.database import SessionDependency
from app.models.generic import Message
from app.models.user import (
    PasswordHistoriesPublic,
    UpdatePassword,
    User,
    UserCreate,
    UserPublic,
    UserRole,
    UserUpdate,
    UserUpdateMe,
)

disable_installed_extensions_check()

router = APIRouter()


@router.post("/", response_model=UserPublic)
async def create_user(
    session: SessionDependency, current_user: AllowSuperOrAdmin, user_create: UserCreate
) -> UserPublic:
    # Validation: ADMIN cannot create SUPER or other ADMINs (only SUPER can)
    if current_user.role == UserRole.ADMIN:
        if user_create.role in [UserRole.SUPER, UserRole.ADMIN]:
            raise HTTPException(
                status_code=403, detail="Admins can only create regular users."
            )

    user = await user_crud.get_user_by_email(session=session, email=user_create.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="User with this email already exists",
        )
    user = await user_crud.create_user(session=session, user_create=user_create)
    return UserPublic.model_validate(user)


@router.get("/", response_model=Page[UserPublic])
async def read_users(
    session: SessionDependency, current_user: AllowSuperOrAdmin
) -> Page[UserPublic]:
    # ADMIN can see all but cannot see SUPER details (filter them out)
    if current_user.role == UserRole.ADMIN:
        statement = select(User).where(User.role != UserRole.SUPER)
        return await apaginate(session, statement)  # type: ignore

    return await apaginate(session, select(User))  # type: ignore


@router.get("/byID/{id}", response_model=UserPublic)
async def read_user_by_id(
    session: SessionDependency,
    current_user: AllowAnyRole,
    id: uuid.UUID,
) -> UserPublic:
    user = await user_crud.get_user_by_id(session=session, id=id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Logic:
    # 1. SUPER can see anyone.
    # 2. Any user can see themselves.
    # 3. ADMIN can see anyone EXCEPT SUPER.
    if current_user.role == UserRole.SUPER:
        return UserPublic.model_validate(user)

    if current_user.id == id:
        return UserPublic.model_validate(user)

    if current_user.role == UserRole.ADMIN:
        if user.role == UserRole.SUPER:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        return UserPublic.model_validate(user)

    raise HTTPException(status_code=403, detail="Not enough permissions")


@router.get("/byEmail/{email}", response_model=UserPublic)
async def read_user_by_email(
    session: SessionDependency, current_user: AllowSuperOrAdmin, email: str
) -> UserPublic:
    user = await user_crud.get_user_by_email(session=session, email=email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # ADMIN cannot see SUPER
    if current_user.role == UserRole.ADMIN and user.role == UserRole.SUPER:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    return UserPublic.model_validate(user)


@router.get("/me/password-history", response_model=PasswordHistoriesPublic)
async def read_password_history(
    session: SessionDependency,
    current_user: CurrentUser,
) -> PasswordHistoriesPublic:
    """
    Retrieve the last 5 password changes for the authenticated user.
    """
    return await user_crud.get_password_history(
        session=session, user_id=current_user.id
    )


@router.patch("/password", response_model=Message)
async def update_password(
    session: SessionDependency,
    update_password: UpdatePassword,
    current_user: CurrentUser,
) -> Message:
    password_updated = await user_crud.update_password(
        session=session, updatePassword=update_password, current_user=current_user
    )
    if password_updated:
        return Message(message="Password updated successfully")
    else:
        raise HTTPException(status_code=400, detail="Failed to update password")


@router.patch("/{id}", response_model=UserPublic)
async def update_user(
    session: SessionDependency,
    current_user: AllowAnyRole,
    id: uuid.UUID,
    user_update: UserUpdate,
) -> UserPublic:
    target_user = await user_crud.get_user_by_id(session=session, id=id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # 1. Access Control Logic (Who can edit whom)
    if current_user.id == id:
        # Users can edit themselves, but only SUPER can change roles or active status
        if current_user.role != UserRole.SUPER:
            if user_update.role is not None or user_update.is_active is not None:
                raise HTTPException(
                    status_code=403,
                    detail="Cannot change your own role or active status",
                )
    elif current_user.role == UserRole.SUPER:
        pass  # SUPER can update any field on any user
    elif current_user.role == UserRole.ADMIN:
        # ADMIN can manage regular USERS, but not other ADMINs or SUPERs
        if target_user.role in [UserRole.SUPER, UserRole.ADMIN]:
            raise HTTPException(
                status_code=403, detail="Admins can only manage regular users."
            )
        # ADMIN cannot modify the 'role' field (Only SUPER can)
        if user_update.role is not None:
            raise HTTPException(
                status_code=403,
                detail="Only SUPER users can modify roles.",
            )
        # ADMIN is allowed to modify 'is_active' and other fields for regular users
    else:
        # Regular users cannot edit other users
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # 2. Schema Gating (Mass Assignment Protection)
    # If not a privileged user, ensure only fields from UserUpdateMe are processed
    if current_user.role not in [UserRole.SUPER, UserRole.ADMIN]:
        # Convert to the restricted schema to strip unallowed fields
        # Crucial: Use exclude_unset=True to avoid setting missing fields to None
        restricted_data = UserUpdateMe.model_validate(
            user_update.model_dump(exclude_unset=True)
        )
        # Re-wrap into UserUpdate for the CRUD layer
        user_update = UserUpdate.model_validate(
            restricted_data.model_dump(exclude_unset=True)
        )

    user = await user_crud.update_user(session=session, id=id, user_update=user_update)
    return UserPublic.model_validate(user)


@router.delete("/{id}", response_model=Message)
async def delete_user(
    session: SessionDependency, current_user: AllowSuperOrAdmin, id: uuid.UUID
) -> Message:
    target_user = await user_crud.get_user_by_id(session=session, id=id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    if current_user.role == UserRole.ADMIN:
        if target_user.role in [UserRole.SUPER, UserRole.ADMIN]:
            raise HTTPException(
                status_code=403, detail="Admins can only delete regular users."
            )

    deleted = await user_crud.delete_user(session=session, id=id)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")

    return Message(message="User deleted successfully")
