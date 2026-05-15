# AGENT_NOTES

Cross-issue memory for autonomous agents working on this repo. Read in full at session start.

---

## Environment constraints

- **Docker Compose** is the standard way to run all services. `docker compose up -d` starts everything.
- **Local dev URLs (Docker):** `http://localhost:8080` (app via nginx-local), `http://localhost:8000/docs` (Swagger).
- **Local dev URL (Vite):** `http://localhost:5173` — only works when running `npm run dev` in `frontend/` while backend is on port 8000.
- **Tests** use SQLite in-memory (aiosqlite). No PostgreSQL or Redis needed to run the test suite.
- **`aiosqlite`** must be in `requirements.txt` for tests to work — it is NOT pulled in by SQLAlchemy's `asyncio` extra.
- **Microsoft Entra ID** is not configured in the local dev environment. Auth endpoints require placeholder credentials.
- **`CELERY_TASK_ALWAYS_EAGER=true`** makes Celery tasks run synchronously in tests/dev.

---

## Conventions

- Feature branches: `CLA-<issue>-<short-description>` off `main`.
- Conventional commits: `feat:`, `fix:`, `chore:`, etc.
- `docker-compose.override.yml` auto-loads on `docker compose up` and sets up local dev (no SSL, no domain). Production nginx/certbot are behind `--profile production`.
- Vite proxy target must be `http://localhost:8000` (not `http://backend:8000`) so `npm run dev` works from the host.

---

## Decisions log

### CLA-3 — 2026-05-15 — Fix Vite dev server connection refused on localhost:5173

- Root cause: `vite.config.ts` proxy target was `http://backend:8000` (Docker internal DNS), not resolvable from host when running `npm run dev` locally.
- Fixed proxy target to `http://localhost:8000` so the Vite dev server can reach the backend exposed by `docker-compose.override.yml`.
- Added `host: true` to Vite server config so the dev server binds on `0.0.0.0` (accessible from all network interfaces).
- Added `aiosqlite==0.20.0` to `requirements.txt` — missing but required by the test suite's in-memory SQLite setup.
- Updated `CLAUDE.md` Quick Start and Frontend sections to document correct dev URLs (Docker :8080 and Vite :5173).
- Created `frontend/src/lib/api.ts` and `frontend/src/lib/utils.ts` — referenced throughout the codebase but never committed; `api.ts` provides the axios instance + token helpers, `utils.ts` provides the `cn()` class merger.
- Created `frontend/eslint.config.js` (ESLint v9 flat config) — was missing; lint failed without it.
- Fixed unused `storeLogout` in `AppLayout.tsx` and `triggerSync(undefined)` in `AdminDashboard.tsx` for TypeScript strict mode.
