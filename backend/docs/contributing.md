---
icon: lucide/hand-helping
---

# Contributing

We welcome contributions to this project! Whether you're reporting a bug, proposing a new feature, or improving documentation, your help is appreciated.

## 🛠 How to Contribute

### 1. Development Workflow
This project is built using **uv** for dependency management.
1. **Fork & Clone**: Fork the repository and clone your fork locally.
2. **Sync Dependencies**: `uv sync`
3. **Activate Environment**: `source .venv/bin/activate`
4. **Install Hooks**: `uv run prek install` (Required for automatic quality checks).

### 2. Code Standards
To ensure a high level of code quality, we maintain a strict toolchain:
- **Linting & Formatting**: `uv run ruff check .` and `uv run ruff format .`
- **Type Checking**: `uv run mypy .`
- **Security Scanning**: `uv run bandit -c pyproject.toml -r app`
- **Tests**: `uv run pytest`

Our `Prek` (pre-commit) hooks will automatically run these checks on every commit. If you encounter any issues, run `uv run prek run --all-files` to fix them before pushing your changes.

### 3. AI-Driven Assistance
We encourage the use of **Gemini CLI** and **Google Antigravity** to accelerate development.
- Please refer to `GEMINI.md` for architectural mandates and AI interaction guidelines.
- Always validate AI-generated code by running the project's test suite.

### 4. Pull Request Process
1. **Create a branch**: Use descriptive names (e.g., `feature/add-new-endpoint` or `fix/sentry-integration`).
2. **Run Tests**: Ensure all tests pass with `uv run pytest`.
3. **Commit**: Please write clear, concise commit messages.
4. **Open PR**: Submit your changes to the `develop` branch for review.

### 5. Documentation
We value clear documentation. If you modify any logic or add features, please update the corresponding `.md` file in the `docs/` folder.
