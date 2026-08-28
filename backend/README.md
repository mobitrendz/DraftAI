# FastAPI AI-Optimized Enterprise Backend Template

<a href="https://github.com/mobitrendz/fastapi-backend-template/actions/workflows/docker-compose-test.yml" target="_blank"><img src="https://github.com/mobitrendz/fastapi-backend-template/actions/workflows/docker-compose-test.yml/badge.svg?branch=develop" alt="Docker Validation"></a>
<a href="https://github.com/mobitrendz/fastapi-backend-template/actions/workflows/test-fastapi-backend-template.yml" target="_blank"><img src="https://github.com/mobitrendz/fastapi-backend-template/actions/workflows/test-fastapi-backend-template.yml/badge.svg?branch=develop" alt="Backend Code Quality"></a>
<a href="https://github.com/mobitrendz/fastapi-backend-template/actions/workflows/test-coverage.yml" target="_blank"><img src="coverage.svg" alt="Coverage"></a>

An evolving, enterprise-grade FastAPI template currently in active development. While designed for scalability and high performance, this project is in a rapid growth phase—continuously receiving new features and bug fixes. It provides a robust, modular foundation that integrates enterprise-grade security, comprehensive observability, and automated quality assurance workflows.

> [!IMPORTANT]
> This project is currently in **Active Development (Beta)**. We are adding new functionalities and fixing bugs. While it follows enterprise standards, it should be thoroughly evaluated before use in critical production environments.

## 🏗️ Architectural Pattern

This template follows a **Layered Modular Architecture** to ensure high maintainability and clear separation of concerns:

1.  **API Layer (`app/api`)**: Versioned controllers handling request validation and OpenAPI documentation.
2.  **Service Layer (`app/services`)**: Business logic orchestrating multiple CRUD operations or external integrations.
3.  **CRUD Layer (`app/crud`)**: Atomic, reusable database operations.
4.  **Model Layer (`app/models`)**: Unified SQLModel definitions for both DB tables and API DTOs (Data Transfer Objects).
5.  **Core Layer (`app/core`)**: Centralized security, configuration, and observability logic.

---

## 🔗 Related Projects

- **React Frontend Template**: A companion frontend built with React 19, Vite, and Tailwind CSS. It is pre-configured to consume this API and handle its standardized error formats. [Frontend Template](https://github.com/mobitrendz/react-frontend-template)

- **Expo Template**: [Expo Mobile App Template](https://github.com/mobitrendz/expo-mobile-template)

---

## 🌟 Key Features

*   **AI-Driven Development**: Optimized for **Google Antigravity** and **Gemini CLI** assisted engineering, refactoring, code review, and feature implementation.
*   **Python 3.12+ Runtime**: Leverages the latest interpreter performance enhancements.
*   **Enterprise Observability**: Structured JSON logging with **Structlog** and real-time metrics with **Prometheus**.
*   **API Standardization**: Integrated **Pagination** for uniform list responses and **Rate Limiting** via SlowAPI.
*   **Modern Dependency Management**: Powered by <a href="https://astral.sh" target="_blank">uv</a> for lightning-fast, reproducible builds.
*   **Full-Stack Orchestration**: Integrated **PostgreSQL 18**, **Traefik**, and development-only admin/email tooling.
*   **Enterprise Security**: Centralised OAuth2, JWT implementation, Argon2-based hashing, and automated **Security Scanning** via Bandit.
*   **Robust Health Monitoring**: Integrated Docker health checks ensuring zero-downtime dependency readiness.

## 🛠️ Tech Stack

| Tool Category | Key Dependencies | Core Benefits |
| :--- | :--- | :--- |
| **Core Framework** | `FastAPI`, `SQLModel` | High-performance, async-native API development with unified data modeling (Pydantic + SQLAlchemy). |
| **Data Persistence** | `PostgreSQL 18`, `Alembic`, `psycopg3` | The latest stable database engine with modern binary drivers and robust migration management. |
| **Security** | `pwdlib[argon2]`, `PyJWT`, `Bandit` | State-of-the-art password hashing, industry-standard authentication, and automated security linting. |
| **Observability** | `Structlog`, `Prometheus`, `Sentry`, `Rich` | Centralized JSON logging, real-time metrics, proactive error tracking, and beautiful local console output. |
| **Resilience** | `Tenacity`, `SlowAPI` | Automated retries for transient failures and built-in rate limiting to prevent API abuse. |
| **Testing** | `Pytest`, `Testcontainers`, `Hypothesis` | Isolated infrastructure testing, property-based edge-case detection, and high coverage standards. |
| **Optimization** | `py-spy`, `Scalene` | Deep profiling of CPU and memory usage to eliminate bottlenecks in production. |
| **Developer DX** | `uv`, `Ruff`, `Mypy`, `Prek`, `Zensical` | Lightning-fast dependency management, formatting, and strict type checking, all orchestrated via automated hooks. |

---

## 🛡️ Enterprise Security & RBAC

The template implements a robust **Role-Based Access Control (RBAC)** system using FastAPI dependencies.

### User Roles
- **SUPER**: Full system access (seeded via `.env`).
- **ADMIN**: Can manage users but cannot access system metrics or other admins.
- **USER**: Standard access to personal data (e.g., ToDo lists).

### Usage in Routes
Secure your endpoints using the provided dependencies:
```python
from app.api.deps import AllowSuper, AllowAdmin

@router.get("/admin-only")
async def secure_route(current_user: AllowAdmin):
    return {"message": "Hello, Admin!"}
```

---

## 📋 Prerequisites

Before you begin, ensure you have the following installed on your system:

### 📦 uv (Fastest Python Package Manager)
This project uses **uv** for high-performance dependency management.

- **macOS/Linux**:
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- **Windows**:
  ```powershell
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```
- **More info**: <a href="https://docs.astral.sh/uv/getting-started/installation/" target="_blank">uv Installation Guide</a>

### 🐳 Docker & Docker Compose
Used for full-stack orchestration and environmental parity.

- **Desktop (macOS/Windows/Linux)**: <a href="https://docs.docker.com/get-docker/" target="_blank">Install Docker Desktop</a>
- **Linux (Engine only)**: <a href="https://docs.docker.com/engine/install/" target="_blank">Install Docker Engine</a>

## 🏁 Getting Started

### 1. Clone the Repository
```bash
git clone git@github.com:mobitrendz/fastapi-backend-template.git
cd fastapi-backend-template
```

### 2. Environment Configuration

The application requires several environment variables for security, database connection, and email settings.

1.  **Copy the template**:
    ```bash
    cp .env.example .env
    ```
2.  **Configure variables**: Open the new `.env` file and update the values. At a minimum, you should update:
    - `SECRET_KEY`: Generate a secure key (e.g., `openssl rand -hex 32`).
    - `POSTGRES_PASSWORD`: Set a secure password for your local database.
    - `SUPER_USER_PASSWORD`: Set the password for the initial admin account.

For a detailed breakdown of all available variables, refer to the <a href="https://mobitrendz.github.io/fastapi-backend-template/development/#environment-configuration" target="_blank">Environment Configuration</a> section in the development documentation.

### 3. Orchestration Launch

Deploy the local development stack with a single command:
```bash
docker compose up --build
```

For a base stack without development-only pgAdmin and MailCatcher services, run:
```bash
docker compose -f docker-compose.yaml up --build
```

### 4. Documentation (Zensical)
The project documentation is built with **Zensical**, a high-performance, Rust-powered documentation generator. It serves as the primary resource for deep-dives into our architecture, development workflows, and deployment strategies.

#### Access & Build
- **Live Documentation**: [https://mobitrendz.github.io/fastapi-backend-template/](https://mobitrendz.github.io/fastapi-backend-template/)
- **Serve Locally**: `uv run zensical serve` (Available at: http://localhost:3000)
- **Build Static Site**: `uv run zensical build`

*For an in-depth understanding of the system, please explore the full [Documentation Portal](https://mobitrendz.github.io/fastapi-backend-template/).*

---

### 5. Local API Development (Hybrid Setup)

For developers who prefer running the database services via Docker while developing the FastAPI application natively on their host machine for faster iteration:

1. **Start Database Services only**:
   ```bash
   docker compose up -d db pgadmin mailcatcher
   ```

2. **Configure Local Environment**:
   Ensure your `.env` connects to the local Docker ports (e.g., `POSTGRES_SERVER=localhost` and `POSTGRES_PORT=5432`).

3. Run API Natively:
   ```bash
   # Sync environment and dependencies
   uv sync

   # Activate virtual environment
   source .venv/bin/activate

   # Start development server (Auto-reload enabled)
   # Use --host 0.0.0.0 to make the server accessible from outside the container or machine
   uv run fastapi dev --host 0.0.0.0
   ```

4. **Access Endpoints**:
   - API Documentation: http://localhost:8000/docs
   - Prometheus Metrics: http://localhost:8000/metrics
   - pgAdmin: http://localhost:5050
   - MailCatcher UI: http://localhost:1080
   - Health Status: http://localhost:8000/health

---

### 6. 🛠️ Local Development
Maintain system integrity and code quality with the integrated toolchain:

#### 🧹 Linting & Formatting (Ruff)
```bash
# Check for linting issues
uv run ruff check .

# Automatically fix fixable issues
uv run ruff check --fix .

# Format the code
uv run ruff format .
```

#### 🔍 Static Type Checking (Mypy)
```bash
# Run strict type checking
uv run mypy .
```

#### 🛡️ Security Analysis (Bandit)
```bash
# Run security scan
uv run bandit -c pyproject.toml -r app
```

#### ✅ Test Suite
```bash
# Run unit and integration tests
uv run pytest
```

---

### 🗄️ Database Migrations (Alembic)

This project uses **Alembic** for robust database schema management. All changes to the database structure must be performed via migration scripts.

#### 🏗️ Creating Migrations
When you modify your `SQLModel` definitions in `app/models/`, generate a new migration script:
```bash
# Generate a migration script automatically
uv run alembic revision --autogenerate -m "description of changes"
```

#### 🚀 Applying Migrations
To sync your database with the latest schema:
```bash
# Apply all pending migrations to the database
uv run alembic upgrade head
```

#### 🔄 Reverting Migrations
To roll back the last migration:
```bash
# Revert the database to the previous version
uv run alembic downgrade -1
```

*Note: Ensure your database container (`db` service) is running before executing migration commands.*

---

## 🤝 Contributing
We welcome contributions! Please see our [Contributing Guide](docs/contributing.md) for details on how to get involved. If you find a bug or have a feature request, please open an issue on GitHub.

## 📝 Release Notes
See the full <a href="release-notes.md" target="_blank">Release Notes</a> for a detailed history of changes.

## ⚖️ License
This project is licensed under the <a href="LICENSE" target="_blank">MIT License</a>.

## 💡 Inspiration
This project is heavily inspired by the official <a href="https://github.com/fastapi/full-stack-fastapi-template" target="_blank">full-stack-fastapi-template</a> in the FastAPI repository. It builds upon those foundational concepts, incorporating modern toolchain upgrades, enhanced observability, and AI-optimized developer workflows.
