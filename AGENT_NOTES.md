# Agent Notes

Running log of decisions, gotchas, and lessons learned by stokowski-dispatched
agents working on this repo.

**Read this file BEFORE starting any work.**
**Append your notes BEFORE finishing.**

The point: every new agent inherits the lessons of every prior agent. Don't
make the same mistakes twice. Don't re-derive what's already been figured out.

---

## Environment constraints (this dev machine)

- **Docker Desktop is NOT installed.** Do not attempt `docker compose up` —
  it will fail. Use native development (uvicorn for backend, Vite for
  frontend, SQLite for dev DB).
- **Microsoft Entra ID is NOT configured.** `MICROSOFT_*` env vars in `.env`
  are placeholders. Protected routes will return 401. Stub the auth dependency
  or document that login flows don't work locally. Do not block on getting
  Entra ID working unless the ticket explicitly asks for it.
- **Python 3.11.9 is installed.** Project's `pyproject.toml` targets 3.12+
  but 3.11 is compatible. Don't try to upgrade Python.
- **Node v24 + npm 11.** Frontend builds without issues.
- **GitHub CLI (`gh`) is authenticated** as `thomasbarbut`. `git push` and
  `gh pr create` work normally. Use them.

## Repo layout (canonical)

```
abaco-news-aggregator/
├── backend/         FastAPI / SQLAlchemy async / Celery worker + scheduler
├── frontend/        React 18 / Vite / TypeScript / Tailwind / shadcn-ui
├── nginx/           Production reverse proxy
│   ├── conf.d/abaco-news.conf   Prod (TLS, news.abaco.ro)
│   └── local.conf               Local dev (HTTP only, mounted by override)
├── docker-compose.yml             Prod stack
├── docker-compose.override.yml    Local dev override (no SSL, exposes :8080/:8000)
├── .env / .env.example            Secrets. .env is gitignored.
└── CLAUDE.md                      Project conventions for Claude Code.
```

## Local dev URLs (target)

- `http://localhost:5173` — Vite dev server (frontend, hot reload)
- `http://localhost:8000` — FastAPI backend
- `http://localhost:8000/docs` — Swagger UI

Vite must proxy `/api/*` → `http://localhost:8000` so the frontend's
`axios.create({ baseURL: '/api' })` works without CORS hacks.

## Conventions

- Frontend API base: relative `/api` only. Same-origin via proxy in dev,
  via nginx in prod. Never hardcode `http://localhost:8000` in frontend code.
- Database in dev: SQLite (`./dev.db`). In prod: Postgres. Code should not
  depend on Postgres-specific features.
- Celery in dev: eager mode (`CELERY_TASK_ALWAYS_EAGER=True`) so Redis isn't
  required to run the server.
- Commits: conventional commit style (`feat:`, `fix:`, `chore:`, etc.).
- Branches: `<issue-id-lower>-<short-description>` (e.g. `cla-2-native-dev`).

## Decisions log (newest first)

### CLA-2 — 2026-05-15 — Native dev pivot
- Pivoted from Docker to native dev because Docker Desktop isn't installed.
- Created `dev.ps1` to start backend + frontend in parallel.
- Configured Vite proxy `/api` → `:8000` in `vite.config.ts`.
- Switched backend dev DB to SQLite via `DATABASE_URL=sqlite+aiosqlite:///./dev.db`.
- Added `aiosqlite` to backend deps.

### CLA-1 — 2026-05-15 — Initial scaffold
- Built the full stack as a production-ready system targeting `news.abaco.ro`.
- Stack: FastAPI + SQLAlchemy 2.0 async + Celery + React/Vite + nginx + Let's Encrypt.
- Auth: Microsoft Entra ID (OAuth2/OIDC + JWT).
- Scrapers: feedparser (RSS) + Playwright + BeautifulSoup for HTML.
- See `CLAUDE.md` for the deep architecture notes.

---

## How to use this file

**Reading (at session start):**
1. Open this file first, before reading anything else.
2. Pay attention to "Environment constraints" — they explain why obvious
   approaches won't work on this machine.
3. Check "Decisions log" for context on past work that might inform yours.

**Writing (before finishing):**
1. If you made a non-trivial decision, add an entry under "Decisions log"
   with: `### <ISSUE-ID> — <date> — <one-line summary>` and 3–6 bullets.
2. If you discovered a new constraint (e.g. "Postgres extension X is required"),
   add it under "Environment constraints".
3. If you established a new convention, add it under "Conventions".
4. **Commit the change with your other commits.** Don't make a separate commit
   just for this file unless your other changes are unrelated.

**What NOT to write here:**
- Detailed implementation history (that's what `git log` is for).
- One-shot tactical info (that's what the Linear workpad is for).
- Sensitive values (no API keys, secrets, internal URLs).
