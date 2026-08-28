---
icon: lucide/layers
---

# Tech Stack

This document provides a comprehensive overview of the technologies, tools, and infrastructure powering the FastAPI Enterprise Backend Template.

## 🏗️ Core Architecture
- 🐍 **Python 3.12+** — High-performance interpreter with advanced language features.
- ⚡ **FastAPI** — High-performance, production-ready web framework for building APIs.
- 📐 **Pydantic v2** — Modern data validation and settings management using type hints.
- 🔢 **FastAPI-Pagination** — Uniform pagination support for clean and consistent list responses.

## 🗄️ Persistence & Data
- 🐘 **PostgreSQL 18** — The world's most advanced open-source relational database.
- 🧬 **SQLModel** — Elegant unification of SQLAlchemy and Pydantic for data modeling.
- 🛠️ **Alembic** — Robust database migration management for versioned schema updates.
- 🔌 **psycopg3** — Modern, high-performance PostgreSQL adapter for Python.

## 🛡️ Security & Health
- 🔑 **OAuth2 + JWT** — Industry-standard secure authentication and authorization.
- 🔒 **Argon2** — State-of-the-art password hashing for maximum credential security.
- 🚦 **SlowAPI** — Advanced rate limiting to protect endpoints from automated abuse.
- 🛡️ **Bandit** — Automated security linting to identify and mitigate vulnerabilities.

## 📊 Observability & Resilience
- 🪵 **Structlog** — High-performance structured logging for deep system visibility.
- 📈 **Prometheus** — Real-time metrics instrumentation for monitoring system health.
- 🎯 **Sentry SDK** — Proactive error tracking and performance monitoring with native FastAPI integration.
- ✨ **Rich** — Beautiful console formatting and traceback visualization for local development.
- 🔄 **Tenacity** — Sophisticated retry logic for handling transient operational failures.

## 📧 Email & Templating
- ✉️ **Emails** — Simplifies sending emails with custom headers and attachments.
- 🎨 **Jinja2** — Modern and designer-friendly templating engine for Python.
- 🔍 **Email-Validator** — Robust validation for email addresses to ensure data integrity.

## 🛠️ Tooling & Infrastructure
- 📦 **uv** — Next-generation, lightning-fast Python package and project manager.
- 🐳 **Docker & Compose** — Full-stack container orchestration for environmental parity.
- 🧭 **Traefik** — Local reverse proxy for stable `.test` service URLs.
- 📥 **MailCatcher** — Instant SMTP server for capturing and inspecting emails during development.
- 🦀 **Zensical** — Ultra-fast, Rust-powered documentation generator for this project.
- 🤖 **Google Antigravity** — AI coding collaborator for implementation, review, documentation, and repository maintenance.
- 🤖 **Gemini CLI** — AI-powered autonomous agent for rapid, surgical engineering.

## 🧪 Quality Assurance
- 🧪 **Pytest & Coverage** — Mature testing framework with detailed coverage reporting.
- 🐳 **Testcontainers** — Isolated, containerized integration testing.
- 🧠 **Hypothesis** — Advanced property-based testing for edge-case identification.
- 🚀 **py-spy & Scalene** — Advanced performance profiling for CPU and memory optimization.
- 🧹 **Ruff** — Extremely fast, all-in-one Python linter and code formatter.
- 🔍 **Mypy** — Strict static type checking to eliminate runtime type errors.
- ⚓ **Prek** — Ultra-fast, Rust-powered Git hook manager for automated code quality checks.
