from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import get_current_user as get_curr_user
from app.core import security
from app.core.config import settings
from app.core.limiter import limiter
from app.core.security import (
    oauth2_scheme,
)
from app.crud import user as user_crud
from app.db.database import SessionDependency
from app.models.generic import Message, Token
from app.models.user import UserCreate, UserPublic, UserRegister, UserRole

router = APIRouter()


# This endpoint allows users to log in and receive an access token for authentication in future requests.
@router.post("/access-token", response_model=Token)
@limiter.limit("5/minute")
async def login_access_token(
    request: Request,  # noqa: ARG001
    session: SessionDependency,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    """
    OAuth2 compatible token login, get an access token for future requests
    """

    user = await user_crud.authenticate_user(
        session=session, email=form_data.username, password=form_data.password
    )

    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    return Token(
        access_token=security.create_access_token(
            str(user.id), expires_delta=access_token_expires
        )
    )


# This endpoint allows authenticated users to retrieve their access token.
@router.get("/secure-data")
async def read_secure(token: str = Depends(oauth2_scheme)) -> dict[str, str]:
    return {"token": token}


# This endpoint allows authenticated users to retrieve their own user information using the access token.
@router.get("/current-user", response_model=UserPublic)
async def get_current_user(
    current_user: Annotated[UserPublic, Depends(get_curr_user)],
) -> UserPublic:
    return current_user


@router.post("/signup", response_model=UserPublic)
@limiter.limit("5/minute")
async def register_user(
    request: Request,  # noqa: ARG001
    session: SessionDependency,
    user_in: UserRegister,
) -> UserPublic:
    """
    Public signup endpoint for new users.
    """
    user = await user_crud.get_user_by_email(session=session, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="User with this email already exists",
        )

    user_create = UserCreate(
        email=user_in.email,
        password=user_in.password,
        full_name=user_in.full_name,
        role=UserRole.USER,
        is_active=True,
    )
    user = await user_crud.create_user(session=session, user_create=user_create)
    return UserPublic.model_validate(user)


@router.post("/password-recovery/{email}")
@limiter.limit("3/minute")
async def recover_password(
    request: Request,  # noqa: ARG001
    email: str,
    session: SessionDependency,
) -> Message:

    user = await user_crud.get_user_by_email(session=session, email=email)

    # Always return the same response to prevent email enumeration attacks
    # Only send email if user actually exists
    if user:
        password_reset_token = security.generate_password_reset_token(email=email)
        email_data = security.generate_reset_password_email(
            email_to=user.email, email=email, token=password_reset_token
        )
        security.send_email(
            email_to=user.email,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )
    return Message(
        message="If that email is registered, we sent a password recovery link"
    )
