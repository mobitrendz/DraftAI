import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import EmailStr
from sqlalchemy import DateTime
from sqlmodel import Field, Relationship, SQLModel


# Function to get the current UTC datetime
def get_datetime_utc() -> datetime:
    return datetime.now(UTC)


# User roles for role-based access control
class UserRole(StrEnum):
    SUPER = "super"
    ADMIN = "admin"
    EDITOR = "editor"
    PUBLISHER = "publisher"
    USER = "user"


# Base model for user, including common fields.
class UserBase(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = Field(default=True)
    role: UserRole = Field(default=UserRole.USER)


# UserCreate model for creating new users (used by SUPER/ADMIN)
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


# UserRegister model for public self-registration (defaults to USER role)
class UserRegister(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)


# UserUpdate model for standard profile updates (Self-service)
class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


# UserUpdateAdmin model for administrative actions (SUPER/ADMIN only)
class UserUpdateAdmin(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)
    is_active: bool | None = Field(default=None)
    role: UserRole | None = Field(default=None)


# Maintain UserUpdate as an alias or base for CRUD logic if needed,
# but API will use specialized ones.
class UserUpdate(UserUpdateAdmin):
    pass


# UpdatePassword model for changing a user's password
class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


# User model representing the database table
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    password_history: list["PasswordHistory"] = Relationship(back_populates="user")


# Password History model
class PasswordHistory(SQLModel, table=True):
    __tablename__: str = "password_history"  # type: ignore

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", index=True, ondelete="CASCADE")
    hashed_password: str
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )

    user: User = Relationship(back_populates="password_history")


# Properties to return via API for Password History
class PasswordHistoryPublic(SQLModel):
    id: uuid.UUID
    created_at: datetime


class PasswordHistoriesPublic(SQLModel):
    data: list[PasswordHistoryPublic]
    count: int


# Properties to return via API
class UserPublic(UserBase):
    id: uuid.UUID
    created_at: datetime | None = None


# Response model for list of users
class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int
