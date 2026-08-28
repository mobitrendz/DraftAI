from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated, Any

import jwt
import structlog
from argon2 import PasswordHasher
from argon2.exceptions import Argon2Error
from emails.message import Message
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jinja2 import Template

from app.core.config import settings

logger = structlog.get_logger(__name__)

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)
TokenDependency = Annotated[str, Depends(oauth2_scheme)]

password_hash = PasswordHasher(
    time_cost=2,
    memory_cost=102400,
    parallelism=8,
    hash_len=32,
    salt_len=16,
)


# Security utilities for password hashing, token creation, and token decoding. This module provides functions to hash passwords using Argon2, verify passwords against their hashes, create JWT access tokens for authenticated users, and decode and validate JWT access tokens. These utilities are essential for implementing secure authentication and authorization in the application, ensuring that user credentials are protected and that access to API endpoints is properly controlled based on valid tokens. The use of environment variables for configuration allows for secure management of sensitive information like secret keys and database credentials without hardcoding them in the source code.
# The functions in this module are designed to be reusable across different parts of the application, promoting a consistent approach to security-related operations. The create_access_token and decode_access_token functions handle the creation and validation of JWT tokens, while the hash_password and verify_password functions ensure that user passwords are securely stored and verified during authentication processes. The use of Argon2 for password hashing provides strong security against brute-force attacks, and the JWT implementation allows for stateless authentication across the API.
# The get_current_user function is a dependency that can be used in API endpoints to retrieve the currently authenticated user based on the provided JWT token, ensuring that only valid and active users can access protected endpoints. This promotes a secure and robust authentication mechanism throughout the application.
# The code is organized to separate concerns, with security-related functions and dependencies centralized in this module, making it easier to maintain and update security features as needed. This structure also promotes scalability, allowing for the addition of new security features or changes to existing ones without affecting other parts of the application.
# The use of type annotations and Pydantic models for configuration and user data ensures that the code is type-safe and that input validation is handled effectively, reducing the likelihood of errors and improving the overall robustness of the application.


# Function to hash a password using Argon2 with a random salt. This function takes a plaintext password as input and returns the hashed version of the password, which can be safely stored in the database. The use of Argon2 provides strong security against brute-force attacks, and the random salt ensures that even identical passwords will have different hashes.
def hash_password(password: str) -> str:
    """Hash a password using Argon2 with a random salt."""
    if not password:
        raise ValueError("Password must not be empty")

    return password_hash.hash(password)


# Function to verify a plaintext password against an Argon2 hash. This function uses the verify method of the PasswordHasher to check if the provided password matches the stored hash. If the verification fails (e.g., due to an incorrect password or a hashing error), it catches the Argon2Error and returns False, allowing the calling code to handle authentication failures appropriately.
def verify_password(password: str, hashed_password: str) -> bool:
    """Validate a plaintext password against an Argon2 hash."""
    try:
        return password_hash.verify(hashed_password, password)
    except Argon2Error:
        return False


# Function to create a JWT access token for a subject (typically a user id or email). The token includes the subject, issued at time, and expiration time. The token is signed using the secret key and algorithm specified in the settings, ensuring that it can be securely verified when decoded.
def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token for a subject (typically a user id or email)."""
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# Function to decode and validate a JWT access token. This function attempts to decode the token using the secret key and algorithm specified in the settings. If the token is valid, it returns the decoded payload as a dictionary. If the token is invalid (e.g., expired, malformed, or signature verification fails), it returns None, allowing the calling code to handle authentication failures appropriately.
def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decode and validate a JWT access token."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None


def generate_password_reset_token(email: str) -> str:
    delta = timedelta(hours=settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS)
    now = datetime.now(UTC)
    expires = now + delta
    exp = expires.timestamp()
    encoded_jwt = jwt.encode(
        {"exp": exp, "nbf": now, "sub": email},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return encoded_jwt


@dataclass
class EmailData:
    html_content: str
    subject: str


def generate_test_email(email_to: str) -> EmailData:
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - Test email"
    html_content = render_email_template(
        template_name="test_email.html",
        context={"project_name": settings.PROJECT_NAME, "email": email_to},
    )
    return EmailData(html_content=html_content, subject=subject)


def generate_reset_password_email(email_to: str, email: str, token: str) -> EmailData:
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - Password recovery for user {email}"
    link = f"{settings.FRONTEND_HOST}/reset-password?token={token}"
    html_content = render_email_template(
        template_name="reset_password.html",
        context={
            "project_name": settings.PROJECT_NAME,
            "username": email,
            "email": email_to,
            "valid_hours": settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS,
            "link": link,
        },
    )
    return EmailData(html_content=html_content, subject=subject)


def render_email_template(*, template_name: str, context: dict[str, Any]) -> str:
    template_str = (
        Path(__file__).parent.parent / "email-templates" / "build" / template_name
    ).read_text()
    html_content = Template(template_str).render(context)
    return html_content


def send_email(
    *,
    email_to: str,
    subject: str = "",
    html_content: str = "",
) -> None:
    # assert settings.emails_enabled, "no provided configuration for email variables"
    message = Message(
        subject=subject,
        html=html_content,
        mail_from=(
            settings.EMAILS_FROM_NAME or "Admin",
            settings.EMAILS_FROM_EMAIL or "noreply@example.com",
        ),
    )
    smtp_options = {"host": settings.SMTP_HOST, "port": settings.SMTP_PORT}
    if settings.SMTP_TLS:
        smtp_options["tls"] = True
    elif settings.SMTP_SSL:
        smtp_options["ssl"] = True
    if settings.SMTP_USER:
        smtp_options["user"] = settings.SMTP_USER
    if settings.SMTP_PASSWORD:
        smtp_options["password"] = settings.SMTP_PASSWORD
    response = message.send(to=email_to, smtp=smtp_options)
    logger.info(f"send email result: {response}")
