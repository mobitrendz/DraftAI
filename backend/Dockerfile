# Stage 1: Build dependencies
FROM python:3.12-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./

ARG UV_SYNC_ARGS="--no-dev"
RUN uv sync --frozen --no-install-project ${UV_SYNC_ARGS}

# Stage 2: Runtime
FROM python:3.12-slim-bookworm

WORKDIR /app

# Install curl, libpq, fonts for Pillow cover templates, and uv
RUN apt-get update && apt-get install -y --no-install-recommends curl libpq5 fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set environment paths
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# Copy virtual env from builder
COPY --from=builder /app/.venv /app/.venv

# Copy project files
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY scripts/ ./scripts/
COPY alembic.ini ./

# Ensure the script is executable
RUN chmod +x /app/scripts/prestart.sh

# Default command runs migrations then starts the API
CMD ["sh", "-c", "alembic upgrade head && fastapi run app/main.py --host 0.0.0.0 --port 8000"]
