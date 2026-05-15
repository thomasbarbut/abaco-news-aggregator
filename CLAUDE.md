# ABACO News Aggregation Platform

A production-ready news aggregation platform for Romanian business, legal, startup, and economic news. Runs at https://news.abaco.ro.

## Architecture

| Layer | Technology |
|-------|-----------|
| Backend API | Python 3.12+ / FastAPI / SQLAlchemy 2.0 async |
| Database | PostgreSQL 16 |
| Task Queue | Celery 5 + Redis 7 |
| Frontend | React 18 / TypeScript / Vite / TailwindCSS / shadcn-ui |
| Auth | Microsoft Entra ID (Azure AD) OAuth2/OIDC + JWT |
| Scrapers | feedparser (RSS) + Playwright + BeautifulSoup4 |
| Infrastructure | Docker Compose / NGINX / Let's Encrypt |

## Quick Start

```bash
cp .env.example .env
# Fill in required values (see .env.example comments)
docker compose up -d

# Run initial migration
docker compose exec backend alembic upgrade head

# Seed news sources
docker compose exec backend python -m app.scripts.seed_sources
```

After `docker compose up -d`, the local dev URLs are:
- `http://localhost:8080` — full app (frontend + API via nginx proxy)
- `http://localhost:8000/docs` — FastAPI Swagger UI

For frontend hot-reload development, run `npm run dev` in `frontend/` while the
backend is running on port 8000. Vite serves on `http://localhost:5173` and
proxies `/api/*` to `http://localhost:8000`.

## Project Structure

```
backend/
  app/
    api/          # FastAPI route handlers
    auth/         # Entra ID OAuth2, JWT, dependencies
    models/       # SQLAlchemy models (5 tables)
    schemas/      # Pydantic v2 request/response schemas
    services/     # Business logic layer
    scrapers/     # Scraper framework + 10 source implementations
    tasks/        # Celery tasks (sync scheduler, email alerts)
    core/         # Config, database, security, logging
  alembic/        # Database migrations
  tests/          # pytest test suite

frontend/
  src/
    api/          # TanStack Query hooks
    components/   # Reusable UI components
    hooks/        # Custom React hooks
    layouts/      # App & Admin layouts
    pages/        # Route pages
    store/        # Zustand state management
    types/        # TypeScript interfaces

nginx/            # NGINX reverse proxy config
docker-compose.yml
.env.example
```

## Development Commands

### Backend
```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Run migrations
alembic upgrade head

# Start dev server
uvicorn app.main:app --reload --port 8000

# Run tests
pytest tests/ -v

# Type check
mypy app/

# Lint
ruff check app/
```

### Frontend
```bash
cd frontend

# Install dependencies
npm install

# Start dev server on :5173 (proxies /api to localhost:8000 — backend must be running)
npm run dev

# Type check
npm run type-check

# Build
npm run build

# Lint
npm run lint
```

### Docker
```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f backend
docker compose logs -f worker

# Run migration
docker compose exec backend alembic upgrade head

# Trigger manual sync
docker compose exec backend python -m app.scripts.sync_now
```

## Coding Conventions

### Python (Backend)
- Python 3.12+, strict type hints throughout
- SQLAlchemy 2.0 mapped_column style (not Column())
- Async/await for all database operations (asyncpg driver)
- Pydantic v2 for all schemas (model_config, not Config class)
- Structured JSON logging via python-json-logger
- No print() statements — use logger = logging.getLogger(__name__)
- Secrets and config via environment variables only (never hardcode)
- pytest + pytest-asyncio for tests

### TypeScript (Frontend)
- Strict TypeScript with no `any` types
- TanStack Query v5 for all server state
- Zustand for client-only state (auth token, feed filters)
- All API calls go through src/lib/api.ts (axios instance)
- Tailwind utility classes + shadcn/ui components
- No inline styles

### Git
- Branch: `CLA-<issue>-<short-description>`
- Commits: conventional commits (feat:, fix:, chore:, etc.)
- Never commit .env files

## Key Prerequisites

Before the system can run end-to-end, these must be configured:

1. **Microsoft Entra ID App Registration** — needed for auth
   - App registration in Azure portal
   - Redirect URI: `https://news.abaco.ro/api/auth/callback`
   - API permissions: `User.Read` (delegated)
   - Client ID, Client Secret, Tenant ID → .env

2. **SMTP Credentials** — needed for sync failure alerts
   - SMTP server for notifications@abaco.ro
   - Credentials → .env

3. **DNS** — `news.abaco.ro` must point to the server IP

4. **SSL** — Run certbot for Let's Encrypt certificate
   ```bash
   docker compose run --rm certbot certonly --webroot -w /var/www/certbot -d news.abaco.ro --email thomas.barbut@abaco.ro --agree-tos
   ```

## News Sources

| Source | Strategy | RSS URL |
|--------|----------|---------|
| ZF (Ziarul Financiar) | RSS | zf.ro/rss |
| Profit.ro | RSS | profit.ro/rss |
| Curs de Guvernare | RSS | cursdeguvernare.ro/feed |
| Manager.ro | RSS | manager.ro/rss.php |
| StartupCafe.ro | RSS | startupcafe.ro/feed |
| Juridice.ro | RSS | juridice.ro/feed |
| Economedia | Playwright | (403 on RSS) |
| Wall-Street.ro | Playwright | (403 on RSS) |
| Forbes România | Playwright | (blocked) |
| Avocatnet.ro | Playwright | (403 on RSS) |
