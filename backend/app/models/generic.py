from pydantic import Field
from sqlmodel import SQLModel


# Generic message
class Message(SQLModel):
    message: str = Field(..., description="A human-readable success or status message")


# Standard error detail for frontend parsing
class ErrorDetail(SQLModel):
    detail: str = Field(
        ..., description="A specific error message suitable for UI display"
    )


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None
