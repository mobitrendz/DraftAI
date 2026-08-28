from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from pydantic import ValidationError

from app.core.config import settings
from app.core.security import TokenDependency
from app.db.database import SessionDependency
from app.models.generic import TokenPayload
from app.models.user import User, UserRole


async def get_current_user(
    request: Request, session: SessionDependency, token: TokenDependency
) -> User:
    # fmt: off
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        ) from None
    except (InvalidTokenError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        ) from None
    # fmt: on
    user = await session.get(User, token_data.sub)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    # Store user in request state for middleware access
    request.state.user = user

    return user


class RoleChecker:
    def __init__(self, allowed_roles: list[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(
        self, current_user: Annotated[User, Depends(get_current_user)]
    ) -> User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have the necessary permissions.",
            )
        return current_user


# Current user dependency
CurrentUser = Annotated[User, Depends(get_current_user)]

# Access Control dependencies
ALLOW_ADMIN = RoleChecker([UserRole.ADMIN])
ALLOW_USER = RoleChecker([UserRole.USER])
ALLOW_ADMIN_AND_USER = RoleChecker([UserRole.ADMIN, UserRole.USER])

AllowSuper = Annotated[User, Depends(RoleChecker([UserRole.SUPER]))]
AllowAdmin = Annotated[User, Depends(ALLOW_ADMIN)]
AllowUser = Annotated[User, Depends(ALLOW_USER)]
AllowAdminAndUser = Annotated[User, Depends(ALLOW_ADMIN_AND_USER)]

# Combined roles
AllowSuperOrAdmin = Annotated[
    User, Depends(RoleChecker([UserRole.SUPER, UserRole.ADMIN]))
]
AllowAnyRole = Annotated[
    User, Depends(RoleChecker([UserRole.SUPER, UserRole.ADMIN, UserRole.USER]))
]

# Specifically for ToDo access (Allow all roles, but CRUD handles ownership)
AllowTodo = AllowAnyRole
