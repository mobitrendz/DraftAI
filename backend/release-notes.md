# Release Notes

## [0.2.0] - 2026-05-07

### Added
- **Traefik Integration**: Implemented Traefik as the reverse proxy for all services, providing routing via `.test` domains.
  - API: `http://api.fastapi-template.test`
  - pgAdmin: `http://pgadmin.fastapi-template.test`
  - Mailcatcher: `http://mail.fastapi-template.test`
  - Traefik Dashboard: `http://traefik.fastapi-template.test:8080`
- **Signup Endpoint**: Added a new public registration endpoint `POST /api/v1/login/signup` for new users.
- **Improved Test Coverage**: Achieved 100% test coverage with additional integration and edge-case tests.
- **CI/CD Updates**: Updated all GitHub Actions workflows to Node.js 24 runtime compatibility.

### Changed
- **Development Environment**: Standardized local service access to use custom `.test` domains through Traefik instead of direct IP/localhost ports.
- **Linting & Tooling**:
  - Enabled `pre-commit` hooks via `prek` (requires manual `prek install` after update).
  - Temporarily disabled `bandit` due to Python 3.12 incompatibility.
  - Updated all GitHub Action workflows to use modern versions: `actions/checkout@v6`, `actions/setup-python@v6`, `astral-sh/setup-uv@v8.0.0`.

### Fixed
- Fixed linting errors (`ruff`, `S105`/`S106` warnings) in test files.
- Corrected CI/CD YAML syntax error in workflow configurations.
- Fixed `test_recover_password_existing_user` failure by ensuring test environment integrity.

---
## [0.1.0] - 2026-04-20
- Initial release of the FastAPI Backend Template.
- Core architecture (FastAPI, SQLModel, PostgreSQL, Alembic).
- Basic Auth (JWT).
- Docker Compose orchestration.
