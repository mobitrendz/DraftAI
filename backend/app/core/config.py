from pathlib import Path
from typing import Annotated, Any, Self

from pydantic import (
    AnyUrl,
    BeforeValidator,
    EmailStr,
    PostgresDsn,
    computed_field,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

# Application configuration settings using Pydantic's BaseSettings. This class defines all the necessary configuration parameters for the application, including database connection details, JWT settings, and superuser credentials. The settings are loaded from environment variables, allowing for easy configuration in different environments (development, testing, production).
# The SQLALCHEMY_DATABASE_URI is computed based on the individual database connection parameters, providing a convenient way to access the full database URI for use in database connections. The use of BaseSettings allows for validation and type checking of the configuration parameters, ensuring that the application is configured correctly before it starts. The settings can be easily extended in the future to include additional configuration parameters as needed, and the use of environment variables allows for secure management of sensitive information like database credentials and secret keys without hardcoding them in the source code.


def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",") if i.strip()]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


# The Settings class is instantiated at the end of the module, creating a global settings object that can be imported and used throughout the application to access configuration values. This promotes a centralized and consistent way to manage configuration across the entire codebase.
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )

    FRONTEND_HOST: str
    ENVIRONMENT: str

    PROJECT_NAME: str
    STACK_NAME: str

    API_V1_STR: str

    BACKEND_CORS_ORIGINS: Annotated[
        list[AnyUrl] | str, BeforeValidator(parse_cors)
    ] = []

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        return [str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS] + [
            self.FRONTEND_HOST
        ]

    SECRET_KEY: str
    CREDENTIALS_ENCRYPTION_KEY: str | None = None
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    SMTP_TLS: bool = False
    SMTP_SSL: bool = False
    SMTP_PORT: int = 1025
    SMTP_HOST: str | None = None
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAILS_FROM_EMAIL: EmailStr | None = None
    EMAILS_FROM_NAME: str | None = None

    @model_validator(mode="after")
    def _set_default_emails_from(self) -> Self:
        if not self.EMAILS_FROM_NAME:
            self.EMAILS_FROM_NAME = self.PROJECT_NAME
        return self

    EMAIL_RESET_TOKEN_EXPIRE_HOURS: int

    SENTRY_DSN: str | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def emails_enabled(self) -> bool:
        return bool(self.SMTP_HOST and self.EMAILS_FROM_EMAIL)

    SUPER_USER_NAME: str
    SUPER_USER_EMAIL: str
    SUPER_USER_PASSWORD: str

    POSTGRES_SERVER: str
    POSTGRES_PORT: int
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_SSLMODE: str = "prefer"

    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    S3_ENDPOINT_URL: str = "http://minio:9000"
    S3_PUBLIC_ENDPOINT_URL: str | None = None
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET_NAME: str = "draftai-covers"
    S3_REGION: str = "us-east-1"
    S3_PRESIGNED_URL_EXPIRE_SECONDS: int = 3600

    # Public API base URL reachable by DEV.to when fetching cover images (no trailing slash).
    # Required for DEV.to cover images unless object storage is on a public HTTPS URL.
    PUBLIC_API_BASE_URL: str | None = None
    # Optional LinkedIn publishing config (required for auto-posting to LinkedIn feed).
    LINKEDIN_ACCESS_TOKEN: str | None = None
    LINKEDIN_AUTHOR_URN: str | None = None

    GEMINI_IMAGE_ASPECT_RATIO: str = "16:9"

    # Outbound HTTP timeouts (seconds) for AI provider calls
    AI_TEXT_GENERATION_TIMEOUT_SECONDS: int = 120
    AI_GEMINI_IMAGE_GENERATION_TIMEOUT_SECONDS: int = 180
    AI_OPENAI_IMAGE_GENERATION_TIMEOUT_SECONDS: int = 120
    AI_OPENAI_IMAGE_DOWNLOAD_TIMEOUT_SECONDS: int = 60
    AI_MODEL_DISCOVERY_TIMEOUT_SECONDS: int = 15
    AI_OLLAMA_TIMEOUT_SECONDS: int = 10
    ARQ_JOB_TIMEOUT_SECONDS: int = 600
    PUBLISH_MAX_RETRIES: int = 3

    # Minimum context window for text models shown on Create Content (800–1500 word drafts)
    AI_MIN_TEXT_CONTEXT_WINDOW_TOKENS: int = 16384

    COVER_TEMPLATE_FALLBACK_ENABLED: bool = True
    COVER_TEMPLATE_WIDTH: int = 1280
    COVER_TEMPLATE_HEIGHT: int = 720
    COVER_UPLOAD_MAX_BYTES: int = 5_242_880

    # Ollama on the host when backend runs in Docker (native: http://localhost:11434/v1)
    OLLAMA_BASE_URL: str = "http://host.docker.internal:11434/v1"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def AI_DRAFT_GENERATION_MAX_SECONDS(self) -> int:
        """Upper bound for sync draft generate (article text + per-platform covers)."""
        return (
            self.AI_TEXT_GENERATION_TIMEOUT_SECONDS
            + self.AI_GEMINI_IMAGE_GENERATION_TIMEOUT_SECONDS * 2
        )

    @model_validator(mode="after")
    def _normalize_local_service_hosts(self) -> Self:
        in_docker = Path("/.dockerenv").exists()
        if not in_docker:
            if self.S3_ENDPOINT_URL.rstrip("/") == "http://minio:9000":
                self.S3_ENDPOINT_URL = "http://localhost:9000"
            if self.S3_PUBLIC_ENDPOINT_URL is None:
                self.S3_PUBLIC_ENDPOINT_URL = "http://localhost:9000"
            if self.REDIS_HOST == "redis":
                self.REDIS_HOST = "localhost"
        elif self.S3_PUBLIC_ENDPOINT_URL is None:
            self.S3_PUBLIC_ENDPOINT_URL = "http://localhost:9000"
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        return PostgresDsn.build(
            scheme="postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=f"{self.POSTGRES_DB}?sslmode={self.POSTGRES_SSLMODE}",
        )


settings = Settings()  # ty:ignore[missing-argument]
