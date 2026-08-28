# Gemini CLI Mandates - FastAPI Backend Template

This document provides foundational mandates and architectural guidance for the FastAPI Backend Template project. These rules take precedence over general defaults.

## 🚀 Project Identity & Tech Stack
- **Framework**: FastAPI (Python 3.12+)
- **ORM/Schema**: SQLModel (SQLAlchemy + Pydantic integration)
- **Database**: PostgreSQL 18 (using `psycopg3`)
- **Migrations**: Alembic
- **Auth**: OAuth2 with JWT (HS256) & Argon2 password hashing
- **Dependency Management**: `uv`
- **Orchestration**: Docker Compose (API, DB, pgAdmin, Seeder)

## 🏗️ Architectural Patterns
The project follows a **Layered Modular Architecture**:
1. **API Layer (`app/api/v1`)**: Versioned endpoints using `APIRouter`. Controllers for request handling.
2. **Service Layer (`app/services`)**: Business logic that orchestrates multiple CRUD operations or external integrations.
3. **CRUD Layer (`app/crud`)**: Reusable, atomic database operations.
4. **Model Layer (`app/models`)**: SQLModel definitions (Table models and DTOs like Create/Update/Read).
5. **Core Layer (`app/core`)**: Cross-cutting concerns: Security, Config (Pydantic Settings), and Database Engine.

## 🛠️ Coding Standards & Mandates

### 1. SQLModel & Database
- **Unification**: Always use `SQLModel` for both database tables and Pydantic schemas.
- **Async-Ready**: While current implementation uses synchronous `Session` via `engine`, keep logic decoupled for future async transition.
- **UUIDs**: Use `uuid.UUID` (v4) for primary keys in new models.
- **Timestamps**: Use `DateTime(timezone=True)` with `datetime.now(timezone.utc)` for all temporal fields.

### 2. Migrations (Alembic)
- **Always Migrate**: Never use `SQLModel.metadata.create_all()`. Use Alembic for all schema changes.
- **Autogenerate**: Use `uv run alembic revision --autogenerate -m "description"` to generate migrations.
- **Imports**: Ensure new models are imported in `alembic/env.py` to be detected by autogenerate.

### 3. API & Validation
- **Versioning**: All new endpoints must be registered under `app/api/v1/router.py`.
- **DTOs**: Explicitly use `Read`, `Create`, and `Update` models for API input/output to avoid leaking sensitive fields (like `hashed_password`).
- **Dependencies**: Use `Annotated` with `Depends` for clean dependency injection (e.g., `SessionDependency`).

### 4. Security
- **Hashing**: Always use `app.core.security.hash_password` (Argon2) for passwords.
- **Auth**: Protect sensitive routes with JWT authentication. Use `authenticate_user` to prevent timing attacks.

## 🧪 Testing & Validation
- **Framework**: `pytest`
- **Coverage**: Maintain high coverage (target 90%+). Run with `uv run pytest --cov=app`.
- **Isolation**: Use a test database or transaction-based rollbacks for integration tests.

## 📦 Deployment & Workflow
- **uv**: Use `uv sync` for local dev. Add dependencies via `uv add`.
- **Docker**: Always validate changes against the multi-stage `Dockerfile`.
- **Seeding**: Use the `lifespan` event in `app/main.py` or the `seeder` service for idempotent initial data.
