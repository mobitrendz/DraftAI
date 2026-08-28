# DraftAI

Smart content assistant for developers and tech writers. Turn one topic into a DEV.to article, LinkedIn post, and cover image — then review, schedule, and publish.

## Monorepo structure

```text
DraftAI/
├── backend/       # FastAPI API + ARQ worker (forked from MobiTrendz template)
├── frontend/      # Vite + React 19 dashboard (forked from MobiTrendz template)
└── draftai-docs/  # Product & architecture documentation
```

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- [Node.js 22](https://nodejs.org/) (see `frontend/.nvmrc`)
- [uv](https://docs.astral.sh/uv/) for Python dependency management

## Quick start (Docker)

1. Copy environment files:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

2. Update `backend/.env` — at minimum set `SECRET_KEY`, `POSTGRES_PASSWORD`, and `SUPER_USER_PASSWORD`.

3. Start the full stack from the repo root:

```bash
docker compose up --build
```

| Service  | URL                        |
| -------- | -------------------------- |
| API      | http://localhost:8000/docs |
| Frontend | http://localhost:5173      |
| Postgres | localhost:5432             |
| Redis    | localhost:6379             |

Default superuser credentials come from `SUPER_USER_EMAIL` / `SUPER_USER_PASSWORD` in `backend/.env`.

## Local development (hybrid)

**Backend + worker + infra in Docker, frontend native:**

```bash
# Terminal 1 — API, worker, Postgres, Redis
docker compose up db redis prestart backend worker --build

# Terminal 2 — Vite dev server
cd frontend && npm install && npm run dev
```

**Fully native backend:**

```bash
cd backend
cp .env.example .env
# Set POSTGRES_SERVER=localhost and run Postgres/Redis via docker compose up db redis -d
uv sync
uv run alembic upgrade head
uv run fastapi dev --host 0.0.0.0
```

Regenerate the type-safe API client after backend schema changes:

```bash
cd frontend && npm run generate-client
```

## Publishing prerequisites

To publish DEV.to covers from local development and enable LinkedIn auto-posting:

```bash
# 1) Expose local backend to internet (for DEV.to cover fetch)
ngrok http 8000

# 2) backend/.env
PUBLIC_API_BASE_URL="https://<your-ngrok-subdomain>.ngrok-free.app"

# Optional: LinkedIn auto-post
LINKEDIN_ACCESS_TOKEN="<linkedin-oauth-access-token>"
LINKEDIN_AUTHOR_URN="urn:li:member:<your-numeric-member-id>"
```

If `LINKEDIN_*` values are not set, DraftAI falls back to copy-to-clipboard for manual LinkedIn posting.

## Running tests

Both suites require **Docker** for the backend (Postgres via Testcontainers). Copy `backend/.env.example` to `backend/.env` before running backend tests.

### Backend (pytest)

```bash
cd backend
cp .env.example .env   # first time only
POSTGRES_SERVER=localhost uv run pytest
```

Sprint 1 tests only:

```bash
cd backend
POSTGRES_SERVER=localhost uv run pytest \
  tests/core/test_encryption.py \
  tests/crud/test_settings.py \
  tests/services/test_content.py \
  tests/api/v1/endpoints/test_settings.py \
  tests/api/v1/endpoints/test_content.py \
  tests/worker/test_tasks.py
```

| File | Covers |
|------|--------|
| `tests/core/test_encryption.py` | Fernet encrypt/decrypt roundtrip, invalid token |
| `tests/crud/test_settings.py` | Platform & AI config CRUD, key encryption, per-user isolation |
| `tests/services/test_content.py` | Draft list/generate/update, platform toggles, ownership, images |
| `tests/services/test_storage.py` | S3 upload + presigned URL helpers |
| `tests/api/v1/endpoints/test_settings.py` | Settings API auth, defaults, PATCH |
| `tests/api/v1/endpoints/test_content.py` | Content API list/generate/get, tenancy |
| `tests/worker/test_tasks.py` | ARQ healthcheck, startup/shutdown |

**Expected:** ~175 tests pass (full suite).

### Frontend (Vitest)

```bash
cd frontend
npm run test:run      # CI mode — enforces coverage thresholds
npm test              # watch mode
npm run test:coverage # coverage report without threshold gate
```

Coverage thresholds (`test:run`): statements ≥ 92%, lines ≥ 92%, functions ≥ 85%, branches ≥ 80%.

| File | Covers |
|------|--------|
| `src/test/factories.ts` | Type-safe OpenAPI mock factories (settings, drafts) |
| `src/components/SettingsPage.test.tsx` | Loading, AI/Platforms tabs, save flows, errors |
| `src/components/Dashboard.test.tsx` | Generate UI, recent drafts, preview, error state |
| `src/components/DraftEditorPage.test.tsx` | Draft editor load + save |
| `src/components/layout/Sidebar.test.tsx` | Nav items including Settings link |
| `src/App.test.tsx` | Routes including `/settings` |

**Expected:** ~104 tests pass (full suite).

See [draftai-docs/sprints.md](draftai-docs/sprints.md) for manual test checklists and [draftai-docs/initial.md](draftai-docs/initial.md) for the full roadmap.

## Sprint status

- [x] Sprint 0: Monorepo bootstrap, demo cleanup, Redis + ARQ scaffold
- [x] Sprint 1: Content schema, encrypted config, generate-draft endpoint, automated tests
- [x] Sprint 2: AI factory, image generation, preview editor
- [x] Sprint 3: Scheduling & publishing (DEV.to publish, LinkedIn post/clipboard flow)

See [draftai-docs/initial.md](draftai-docs/initial.md) for the full roadmap.
