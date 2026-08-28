# DraftAI — Sprint Plan & Manual Testing Guide

This document is the operational companion to [initial.md](./initial.md). It defines **what each sprint delivers**, **how to run the stack locally**, **automated test commands**, and **step-by-step manual test checklists** to verify each sprint before moving on.

---

## Table of contents

1. [Prerequisites](#prerequisites)
2. [Local environment setup](#local-environment-setup)
3. [Automated tests](#automated-tests)
4. [Sprint 0 — Bootstrap & Cleanup](#sprint-0--bootstrap--cleanup)
5. [Sprint 1 — Schema, Config & First Generation](#sprint-1--schema-config--first-generation)
6. [Sprint 2 — Extensible Generation Engine](#sprint-2--extensible-generation-engine)
7. [Sprint 3 — Scheduling & Publishing](#sprint-3--scheduling--publishing)
8. [Sprint 4 — History Board](#sprint-4--history-board)
9. [Sprint 5 — QA Integration](#sprint-5--qa-integration)
10. [Appendix: Useful commands](#appendix-useful-commands)

---

## Prerequisites

| Tool | Version / notes |
|------|-----------------|
| Docker & Docker Compose | For Postgres, Redis, API, ARQ worker |
| Node.js | v22.x (see `frontend/.nvmrc`) |
| uv | Python package manager for backend |
| OpenAI API key | Required from Sprint 1 onward (BYOK) |
| DEV.to API key | Required from Sprint 3 onward (publishing) |

### Default local URLs

| Service | URL |
|---------|-----|
| Frontend (Vite) | `http://localhost:5173` (or next free port: 5174, 5175…) |
| API + OpenAPI | `http://localhost:8000` / `http://localhost:8000/docs` |
| Postgres | `localhost:5432` |
| Redis | `localhost:6379` |

### Default superuser (from `backend/.env`)

| Field | Typical value |
|-------|----------------|
| Email | `admin@example.com` |
| Password | Value of `SUPER_USER_PASSWORD` (e.g. `admin123`) |

---

## Local environment setup

Run once before testing any sprint.

```bash
# 1. Environment files
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
# Edit backend/.env: SECRET_KEY, POSTGRES_PASSWORD, SUPER_USER_PASSWORD

# 2. Infrastructure + API + worker
cd backend
docker compose up -d --build db redis prestart backend worker

# 3. Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

**Important:** Leave `VITE_API_URL` empty in `frontend/.env` so the Vite dev proxy handles API calls (avoids CORS when the dev port changes).

### Publishing config (DEV.to covers + LinkedIn auto-post)

For local publish tests, expose your backend publicly so DEV.to can fetch cover images:

```bash
ngrok http 8000
```

Then set these in `backend/.env`:

```env
PUBLIC_API_BASE_URL=https://<your-subdomain>.ngrok-free.app

# Optional LinkedIn auto-post (otherwise clipboard fallback is used)
LINKEDIN_ACCESS_TOKEN=<oauth-access-token>
LINKEDIN_AUTHOR_URN=urn:li:member:<numeric-member-id>
```

After backend schema changes:

```bash
cd frontend && npm run generate-client
```

---

## Automated tests

Sprint 1 introduced automated test suites for backend (pytest + Testcontainers Postgres) and frontend (Vitest + React Testing Library). Run these after code changes and before merging.

### Prerequisites

| Requirement | Notes |
|-------------|-------|
| Docker running | Backend tests spin up a Postgres 18 Testcontainer |
| `backend/.env` | Copy from `.env.example` — `POSTGRES_SERVER=localhost` is set automatically by the test command |
| `frontend` deps | `npm install` in `frontend/` |

### Backend — full suite

```bash
cd backend
cp .env.example .env          # first time only
POSTGRES_SERVER=localhost uv run pytest
```

**Expected:** all tests pass (~175 total, including template auth/user tests).

### Backend — Sprint 1 tests only

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

| File | What it tests |
|------|----------------|
| `tests/core/test_encryption.py` | Fernet encrypt/decrypt roundtrip; invalid token raises |
| `tests/crud/test_settings.py` | Platform & AI config CRUD; API key encryption; per-user isolation |
| `tests/services/test_content.py` | Draft list/generate; disabled platforms; missing key; ownership |
| `tests/api/v1/endpoints/test_settings.py` | Settings API auth, defaults, PATCH platform/AI |
| `tests/api/v1/endpoints/test_content.py` | Content API list/generate/get; tenancy; 404 cases |
| `tests/worker/test_tasks.py` | ARQ `worker_healthcheck`, startup/shutdown hooks |

**Fixtures** (in `tests/conftest.py`): `isolated_user` / `isolated_user_token` provide a fresh user per test to avoid settings/draft pollution across the shared Testcontainer database.

### Frontend — full suite (with coverage gate)

```bash
cd frontend
npm run test:run
```

**Expected:** all tests pass (~104 total). Coverage thresholds enforced:

| Metric | Minimum |
|--------|---------|
| Statements | 92% |
| Lines | 92% |
| Functions | 85% |
| Branches | 80% |

### Frontend — watch mode & coverage report

```bash
cd frontend
npm test              # interactive watch mode
npm run test:coverage # HTML/JSON coverage report (no threshold gate)
```

### Frontend — Sprint 1 test files

| File | What it tests |
|------|----------------|
| `src/test/factories.ts` | Type-safe mock factories aligned with OpenAPI types |
| `src/components/SettingsPage.test.tsx` | Loading spinner; AI/Platforms tabs; save flows; saved-key indicator; API errors |
| `src/components/Dashboard.test.tsx` | Generate form; disabled button; recent drafts; preview after generate; error display |
| `src/components/layout/Sidebar.test.tsx` | Nav items including **Settings** link |
| `src/App.test.tsx` | Protected `/settings` route |

### Quick verification checklist

| Step | Command | Pass criteria |
|------|---------|---------------|
| 1 | `cd backend && POSTGRES_SERVER=localhost uv run pytest` | Exit code 0 |
| 2 | `cd frontend && npm run test:run` | Exit code 0; coverage thresholds met |
| 3 | `cd frontend && npm run type-check` | No TypeScript errors |

---

## Sprint 0 — Bootstrap & Cleanup

**Status:** ✅ Complete

### Goals

- Monorepo scaffold from MobiTrendz templates (`/backend`, `/frontend`)
- Remove demo features (Todos, admin metrics dashboards)
- Add Redis + ARQ worker container (idle scaffold)
- Rebrand to DraftAI; fix architecture docs (Vite/React, not Next.js)

### Deliverables

| Area | Deliverable |
|------|-------------|
| Repo | `DraftAI/backend`, `DraftAI/frontend`, root `docker-compose.yml`, `README.md` |
| Backend | Auth, users, activities; no todo/admin-dashboard endpoints |
| Infra | Postgres 18, Redis 7, `draftai_api`, `draftai_worker` |
| Frontend | Login, home placeholder, profile, admin users/activity |

### Manual testing — Sprint 0

#### S0-T1: Stack health

| Step | Action | Expected result |
|------|--------|-----------------|
| 1 | `curl http://localhost:8000/health` | `{"status":"ok"}` |
| 2 | `docker ps` shows `draftai_postgres`, `draftai_redis`, `draftai_api`, `draftai_worker` | All running (worker may restart loop until Sprint 3 jobs exist — OK) |
| 3 | Open Vite URL in browser | Login page or redirect to `/login` |

**Pass criteria:** API healthy; frontend loads without a blank page.

---

#### S0-T2: Authentication

| Step | Action | Expected result |
|------|--------|-----------------|
| 1 | Go to `/login` | Login form visible |
| 2 | Sign in with superuser credentials | Redirect to home `/` |
| 3 | Refresh page | Still authenticated |
| 4 | Sign out | Redirect to `/login` |
| 5 | Open DevTools → Application → Local Storage | `auth_token` cleared after logout |

**Pass criteria:** Full login/logout cycle works; JWT persisted across refresh.

---

#### S0-T3: Demo features removed

| Step | Action | Expected result |
|------|--------|-----------------|
| 1 | Open `http://localhost:8000/docs` | No `/api/v1/todos` or `/api/v1/admin/dashboard` routes |
| 2 | Browse sidebar after login | No task/todo UI |
| 3 | Home page | DraftAI welcome (not MobiTrendz task board) |

**Pass criteria:** No todo or admin-metrics UI/API surface.

---

#### S0-T4: CORS / proxy

| Step | Action | Expected result |
|------|--------|-----------------|
| 1 | Start Vite on a non-5173 port (if 5173 busy) | Dev server starts on 5174/5175 |
| 2 | Login from that port | No CORS error in browser console |
| 3 | Network tab: login request | Goes to same origin `/api/v1/login/access-token` (proxied) |

**Pass criteria:** Login works regardless of Vite port.

---

## Sprint 1 — Schema, Config & First Generation

**Status:** ✅ Complete

### Goals

- Content schema (separate tables per asset)
- Encrypted per-user platform + AI settings (BYOK)
- Settings dashboard UI
- Generate draft via hardcoded **OpenAI** provider
- Alembic migration + OpenAPI client regeneration

### Deliverables

#### Database tables

| Table | Purpose |
|-------|---------|
| `platform_config` | DEV.to / LinkedIn toggles, profile URLs, encrypted DEV.to API key |
| `ai_agent_config` | Provider, model, temperature, system prompt, encrypted API keys |
| `content_draft` | Parent record, lifecycle status, topic, prompt |
| `devto_article` | Title, Markdown body, tags, cover image FK |
| `linkedin_post` | Teaser text, article URL (nullable), cover image FK |
| `cover_image` | Platform, storage key, prompt metadata (stub until Sprint 2) |
| `publish_job` | Schema only; used in Sprint 3 |

#### API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/settings/platform` | Read platform config (no secrets) |
| `PATCH` | `/api/v1/settings/platform` | Update toggles, URLs, DEV.to key |
| `GET` | `/api/v1/settings/ai` | Read AI config (no secrets) |
| `PATCH` | `/api/v1/settings/ai` | Update model, temperature, OpenAI key |
| `GET` | `/api/v1/content/drafts/` | List current user's drafts |
| `GET` | `/api/v1/content/drafts/{draft_id}` | Draft detail with nested assets |
| `POST` | `/api/v1/content/drafts/generate` | Generate draft from topic |

#### Frontend routes

| Route | Page |
|-------|------|
| `/` | Create content + generate draft + preview |
| `/settings` | AI Agent + Platforms configuration |
| `/profile` | Account settings |
| `/users` | Admin user management (ADMIN/SUPER) |

### Known limitations (Sprint 1)

- **OpenAI**, **Google Gemini**, **Groq**, and **OpenRouter** — generation works with BYOK API keys
- **Anthropic** — stored in settings; generation coming in Sprint 2
- **Cover images** — records created with `provider: pending_sprint2`; no actual image files
- **No edit/approve/schedule/publish** — drafts stay in `draft` status
- **Secrets** — API responses expose `has_*_api_key` flags only, never raw keys

### Manual testing — Sprint 1

#### S1-T1: Migration applied

| Step | Action | Expected result |
|------|--------|-----------------|
| 1 | `docker logs draftai_prestart 2>&1 \| tail -20` | Migration `sprint1_content_and_settings` applied |
| 2 | Connect to Postgres; `\dt` | Tables `platform_config`, `ai_agent_config`, `content_draft`, etc. exist |

**Pass criteria:** All Sprint 1 tables present.

---

#### S1-T2: Platform settings (API)

```bash
# Replace TOKEN with JWT from login
TOKEN="<access_token>"

curl -s http://localhost:8000/api/v1/settings/platform \
  -H "Authorization: Bearer $TOKEN" | jq
```

| Step | Action | Expected result |
|------|--------|-----------------|
| 1 | `GET /settings/platform` | `devto_enabled`, `linkedin_enabled` default `true`; `has_devto_api_key: false` |
| 2 | `PATCH` with `devto_api_key: "test-key-123"` | `has_devto_api_key: true`; key not in response body |
| 3 | `GET` again | Still `has_devto_api_key: true`; no plaintext key |

**Pass criteria:** Secrets encrypted at rest; never returned in API.

---

#### S1-T3: AI settings (API)

| Step | Action | Expected result |
|------|--------|-----------------|
| 1 | `GET /settings/ai` | `provider: openai`, `model: gpt-4o`, `temperature: 0.7` |
| 2 | `PATCH` with `openai_api_key`, `model: gpt-4o-mini`, `temperature: 0.5` | Updated values; `has_openai_api_key: true` |
| 3 | `PATCH` with empty `openai_api_key: ""` | Clears key; `has_openai_api_key: false` |

**Pass criteria:** AI config CRUD works; keys never leaked in responses.

---

#### S1-T4: Platform settings (UI)

| Step | Action | Expected result |
|------|--------|-----------------|
| 1 | Login → sidebar → **Settings** → **Platforms** tab | Form loads |
| 2 | Toggle DEV.to off, LinkedIn on | Checkboxes update |
| 3 | Enter DEV.to profile URL | Value persists after save |
| 4 | Enter DEV.to API key → **Save platform settings** | Green success message; `(saved)` next to key label |
| 5 | Refresh page | Toggles and URLs retained; key field empty (not re-displayed) |

**Pass criteria:** Platform settings round-trip through UI.

---

#### S1-T5: AI settings (UI)

| Step | Action | Expected result |
|------|--------|-----------------|
| 1 | **Settings** → **AI Agent** tab | Model, temperature slider, system prompt, OpenAI key fields |
| 2 | Paste valid OpenAI key → **Save AI settings** | Success toast/message |
| 3 | Adjust temperature → save | Value persists |

**Pass criteria:** OpenAI BYOK configured via UI.

---

#### S1-T6: Generate draft — happy path

**Prerequisite:** Valid OpenAI API key saved in Settings.

| Step | Action | Expected result |
|------|--------|-----------------|
| 1 | Go to **Home** (`/`) | Generate form visible |
| 2 | Enter topic: `Introduction to ARQ with FastAPI` | — |
| 3 | Optional: add instructions in textarea | — |
| 4 | Click **Generate draft** | Button shows loading (up to ~120s) |
| 5 | Wait for completion | Preview section appears |
| 6 | Verify **DEV.to article** block | Title, tags, Markdown body (substantial text) |
| 7 | Verify **LinkedIn post** block | LinkedIn-ready post text |
| 8 | **Recent drafts** list | New entry with topic; status `draft` |

**Pass criteria:** End-to-end text generation for enabled platforms.

---

#### S1-T7: Generate draft — error cases

| Step | Action | Expected result |
|------|--------|-----------------|
| 1 | Remove OpenAI key in Settings | — |
| 2 | Click **Generate draft** | Clear error: OpenAI API key required |
| 3 | Re-add invalid OpenAI key | Error from AI provider (502/400 with message) |
| 4 | Disable both platforms in Settings | Generate still works but only creates draft row (no platform assets) — *or* generates for whichever remain enabled |

**Pass criteria:** Actionable errors; no silent failures or blank UI.

---

#### S1-T8: Multi-tenant isolation

| Step | Action | Expected result |
|------|--------|-----------------|
| 1 | Register a second user via `/login` signup (if enabled) or admin creates user | Second account exists |
| 2 | User A generates a draft | Draft visible in User A's list |
| 3 | Login as User B | User B does not see User A's drafts |
| 4 | User B calls `GET /content/drafts/{user_a_draft_id}` | `404 Not found` |

**Pass criteria:** Drafts and settings scoped per `user_id`.

---

#### S1-T9: OpenAPI client sync

| Step | Action | Expected result |
|------|--------|-----------------|
| 1 | `cd frontend && npm run generate-client` | Completes without error |
| 2 | `npm run build` | TypeScript build passes |
| 3 | `npm run test:run` | All tests pass |

**Pass criteria:** Frontend contract aligned with backend OpenAPI.

---

#### S1-T10: Automated test suites (Sprint 1)

| Step | Command | Expected result |
|------|---------|---------------|
| 1 | `cd backend && POSTGRES_SERVER=localhost uv run pytest tests/core/test_encryption.py tests/crud/test_settings.py tests/services/test_content.py tests/api/v1/endpoints/test_settings.py tests/api/v1/endpoints/test_content.py tests/worker/test_tasks.py` | All Sprint 1 backend tests pass |
| 2 | `cd frontend && npm run test:run` | All tests pass; coverage ≥ 92% statements |
| 3 | `cd frontend && npm run type-check` | No TypeScript errors |

**Pass criteria:** Sprint 1 automated suites green locally. See [Automated tests](#automated-tests) for file-by-file coverage.

---

## Sprint 2 — Extensible Generation Engine

**Status:** ✅ Complete

### Goals

- Provider-agnostic **AI factory** (OpenAI, Anthropic, Gemini, Groq, OpenRouter BYOK)
- **Image generation** from article title/content (DALL-E 3 via OpenAI key)
- **Object storage** — MinIO locally, S3/Blob in production
- **Preview / refine editor** — edit DEV.to Markdown, LinkedIn post text, cover images before approval

### Deliverables

| Module | Details |
|--------|---------|
| `app/services/ai/` | `llm.py` (text generation), `images.py` (DALL-E covers) |
| Storage | `app/services/storage.py` — S3-compatible upload + presigned URLs |
| Docker | MinIO + `minio-init` bucket bootstrap in root `docker-compose.yml` |
| API | `PATCH /content/drafts/{id}` — update article/post |
| Frontend | `/drafts/:id` split-view editor; cover thumbnails; recent drafts link |
| Config | `S3_*` settings in `backend/.env` / `config.py` |

### Manual testing — Sprint 2

#### S2-T1: AI factory — Anthropic

| Step | Action | Expected result |
|------|--------|-----------------|
| 1 | Settings → set provider to **Anthropic**, save Anthropic API key | `has_anthropic_api_key: true` |
| 2 | Generate draft | Content produced via Claude (not OpenAI) |
| 3 | Switch provider to OpenAI | Generation uses OpenAI |

**Pass criteria:** Provider switch changes backend without code deploy.

---

#### S2-T2: Cover image generation

| Step | Action | Expected result |
|------|--------|-----------------|
| 1 | Generate draft with both platforms enabled | Cover image records have real `storage_key` |
| 2 | Open MinIO console or presigned URL | Image file exists; not ephemeral OpenAI URL |
| 3 | Preview UI | DEV.to and LinkedIn cover thumbnails visible |

**Pass criteria:** Images persisted; survive page refresh.

---

#### S2-T3: Preview editor

| Step | Action | Expected result |
|------|--------|-----------------|
| 1 | Open a draft from home or draft detail route | Editor loads with current content |
| 2 | Edit DEV.to Markdown body | — |
| 3 | Edit LinkedIn post text | — |
| 4 | Save | `PATCH` succeeds; reload shows edits |
| 5 | Regenerate single section (if implemented) | Only that section updates |

**Pass criteria:** User can refine AI output before approval.

---

#### S2-T4: Performance

| Step | Action | Expected result |
|------|--------|-----------------|
| 1 | Generate draft with text + images | Completes within **120 seconds** |
| 2 | If timeout | Clear error; partial draft handled per spec |

**Pass criteria:** Meets SRS performance target or fails gracefully.

---

## Sprint 3 — Scheduling & Publishing

**Status:** 🔲 Planned

### Goals

- ARQ publish pipeline: **DEV.to first** → extract live URL → inject into LinkedIn post
- Schedule datetime; worker executes jobs
- LinkedIn **auto-post when configured**, copy-to-clipboard fallback otherwise
- States: `APPROVED` → `SCHEDULED` → `PUBLISHED` \| `PARTIALLY_PUBLISHED` \| `FAILED`
- Retry with exponential backoff

### Planned deliverables

| Module | Details |
|--------|---------|
| Worker tasks | `publish_devto`, `publish_linkedin_or_clipboard` |
| API | `POST /content/drafts/{id}/approve`, `POST .../schedule`, `GET .../publish-status` |
| DEV.to client | API key auth; create article with cover image |
| Frontend | Approve + schedule UI; clipboard button for LinkedIn; job status indicator |

### Manual testing — Sprint 3

#### S3-T1: Approve flow

| Step | Action | Expected result |
|------|--------|-----------------|
| 1 | Open draft in `draft` status | Approve button available |
| 2 | Click **Approve** | Status → `approved` |
| 3 | Try to edit without un-approve (if restricted) | Blocked or warned per UX spec |

**Pass criteria:** Lifecycle transition `draft` → `approved`.

---

#### S3-T2: Schedule & DEV.to publish

**Prerequisite:** Valid DEV.to API key in Settings.

| Step | Action | Expected result |
|------|--------|-----------------|
| 1 | Approve draft → set schedule (near-future datetime) | Status → `scheduled` |
| 2 | Wait for worker (or trigger immediately) | ARQ job runs |
| 3 | Check `publish_job` / UI status | DEV.to step succeeds |
| 4 | Open live DEV.to URL | Article published with correct title/body |
| 5 | Draft status | `partially_published` or `published` depending on LinkedIn |

**Pass criteria:** Live DEV.to article exists; URL stored on draft/job.

---

#### S3-T3: LinkedIn link injection

| Step | Action | Expected result |
|------|--------|-----------------|
| 1 | After DEV.to publish | LinkedIn post contains live DEV.to URL |
| 2 | UI shows **Copy to clipboard** | Full post + link copied |
| 3 | Paste into LinkedIn manually | Formatted correctly |

**Pass criteria:** Zero manual link hunting; post ready to publish.

---

#### S3-T4: Failure & retry

| Step | Action | Expected result |
|------|--------|-----------------|
| 1 | Use invalid DEV.to API key | Job fails; status `failed`; error message stored |
| 2 | Fix key → retry job | DEV.to publish succeeds on retry |
| 3 | DEV.to succeeds, LinkedIn step fails | `partially_published`; clipboard fallback still available |

**Pass criteria:** Retry policy works; partial publish is recoverable.

---

#### S3-T5: Worker health

| Step | Action | Expected result |
|------|--------|-----------------|
| 1 | `docker logs draftai_worker` | Jobs picked up from Redis |
| 2 | Stop Redis briefly | Worker logs connection errors; recovers on restart |
| 3 | Duplicate schedule click | Idempotent — no double publish |

**Pass criteria:** Worker reliable under normal dev conditions.

---

## Sprint 4 — History Board

**Status:** 🔲 Planned

### Goals

- **Kanban** view by lifecycle state (`draft`, `approved`, `scheduled`, `published`, …)
- **Calendar** view by scheduled publish date
- **Edit & Repost** — clone published draft as new `draft` for iteration

### Planned deliverables

| Module | Details |
|--------|---------|
| Frontend | `/history` route with kanban + calendar tabs |
| API | `POST /content/drafts/{id}/clone` — copies assets to new draft |
| Filters | By status, date range, platform |

### Manual testing — Sprint 4

#### S4-T1: Kanban board

| Step | Action | Expected result |
|------|--------|-----------------|
| 1 | Create drafts in multiple statuses | — |
| 2 | Open **History** → Kanban | Cards in correct columns |
| 3 | Drag card to another column (if supported) | Status updates via API |
| 4 | Click card | Opens draft detail / editor |

**Pass criteria:** Visual pipeline matches database state.

---

#### S4-T2: Calendar view

| Step | Action | Expected result |
|------|--------|-----------------|
| 1 | Schedule 2 drafts on different days | — |
| 2 | Open Calendar tab | Events on correct dates |
| 3 | Click event | Navigates to draft |

**Pass criteria:** Scheduled publishes visible on calendar.

---

#### S4-T3: Edit & Repost (clone)

| Step | Action | Expected result |
|------|--------|-----------------|
| 1 | Open a `published` draft | **Edit & Repost** action visible |
| 2 | Click clone | New draft in `draft` status |
| 3 | Verify content | Title/body/post copied; new IDs |
| 4 | Edit clone → publish again | New DEV.to article (separate from original) |

**Pass criteria:** Clone does not mutate original published record.

---

## Sprint 5 — QA Integration

**Status:** 🔲 Planned (partial — Sprint 1 automated suites in place)

### Goals

- Expand automated test coverage for critical paths (publish pipeline, AI factory, history board)
- CI guard: OpenAPI change → `generate-client` required
- Backend pytest with Testcontainers ✅ (Sprint 1)
- Release checklist for AWS/Azure deployment

### Planned deliverables

| Area | Target |
|------|--------|
| Frontend | Vitest coverage ≥ 92% statements ✅ (Sprint 1 baseline) |
| Backend | pytest for auth, settings encryption, generate ✅; publish mocks (Sprint 3+) |
| CI | GitHub Actions: lint, test, API sync check |
| Docs | Deployment runbook update |

### Manual testing — Sprint 5

#### S5-T1: Automated test suites

| Step | Action | Expected result |
|------|--------|-----------------|
| 1 | `cd frontend && npm run test:run` | All pass; coverage thresholds met |
| 2 | `cd backend && uv run pytest` | All pass (Docker required for Testcontainers) |
| 3 | Break OpenAPI without regenerating client | CI fails on API sync check |

**Pass criteria:** CI green on `main`; local suites reproducible.

---

#### S5-T2: Full regression (smoke)

Run in order without skipping:

1. S0-T2 Authentication  
2. S1-T4 Platform settings UI  
3. S1-T5 AI settings UI  
4. S1-T6 Generate draft happy path  
5. S2-T3 Preview editor  
6. S3-T2 Schedule & DEV.to publish  
7. S3-T3 LinkedIn clipboard  
8. S4-T1 Kanban board  
9. S4-T3 Edit & Repost  

**Pass criteria:** Full user journey from topic → publish → history → repost works.

---

#### S5-T3: Production build smoke

| Step | Action | Expected result |
|------|--------|-----------------|
| 1 | `cd frontend && npm run build` | Static assets in `dist/` |
| 2 | `docker compose -f docker-compose.prod.yml up` (when added) | Stack healthy |
| 3 | Hit production URL `/health` | `ok` |

**Pass criteria:** Production artifacts build and start.

---

## Appendix: Useful commands

### Get JWT for API testing

```bash
curl -s -X POST http://localhost:8000/api/v1/login/access-token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=admin123" | jq -r .access_token
```

### Generate draft (curl)

```bash
TOKEN="<access_token>"

curl -s -X POST http://localhost:8000/api/v1/content/drafts/generate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"topic": "Testing DraftAI from curl", "user_prompt": "Keep it short"}' | jq
```

### Migrations

```bash
cd backend
POSTGRES_SERVER=localhost uv run alembic upgrade head
POSTGRES_SERVER=localhost uv run alembic revision --autogenerate -m "description"
```

### Rebuild backend after dependency changes

```bash
cd backend
docker compose build --no-cache backend
docker compose up -d backend worker
```

### Run automated tests

```bash
# Backend (Docker required for Testcontainers Postgres)
cd backend
cp .env.example .env
POSTGRES_SERVER=localhost uv run pytest

# Backend — Sprint 1 only
POSTGRES_SERVER=localhost uv run pytest \
  tests/core/test_encryption.py \
  tests/crud/test_settings.py \
  tests/services/test_content.py \
  tests/api/v1/endpoints/test_settings.py \
  tests/api/v1/endpoints/test_content.py \
  tests/worker/test_tasks.py

# Frontend (coverage thresholds enforced)
cd frontend && npm run test:run

# Frontend — watch mode
cd frontend && npm test
```

### Regenerate frontend API client

```bash
cd frontend
npm run generate-client
```

---

## Sprint status summary

| Sprint | Focus | Status |
|--------|-------|--------|
| 0 | Bootstrap & cleanup | ✅ Complete |
| 1 | Schema, config, first generation | ✅ Complete |
| 2 | AI factory, images, editor | 🔲 Planned |
| 3 | Schedule & publish | 🔲 Planned |
| 4 | History board & clone | 🔲 Planned |
| 5 | QA & CI hardening | 🔲 Planned |

---

*Last updated: June 2026 — align with [initial.md](./initial.md) for architecture and requirements.*
