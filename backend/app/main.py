"""FastAPI application factory for ABACO News Aggregation Platform."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import ensure_schema_additions, init_db
from app.core.logging import get_logger, setup_logging


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup
    setup_logging()
    logger = get_logger(__name__)
    logger.info(
        "Starting ABACO News backend",
        extra={
            "app": settings.APP_NAME,
            "debug": settings.DEBUG,
            "domain": settings.DOMAIN,
        },
    )
    if settings.DEBUG:
        # In development we create tables directly; in production Alembic handles this
        await init_db()
    # Apply additive schema fixes on every boot (safe in prod too).
    await ensure_schema_additions()

    # Background auto-sync loop. Runs in-process when no Celery worker/beat is
    # available (eager mode). When CELERY_TASK_ALWAYS_EAGER=true (or DEBUG=true)
    # we use this loop; otherwise assume Celery beat is running elsewhere and
    # skip the in-process loop.
    import asyncio as _asyncio
    import os as _os
    auto_sync_task = None
    _eager = _os.environ.get("CELERY_TASK_ALWAYS_EAGER", "").lower() in ("1", "true", "yes")
    if _eager or settings.DEBUG:
        from app.api.admin import auto_sync_loop
        auto_sync_task = _asyncio.create_task(auto_sync_loop())
        logger.info("In-process auto-sync loop started (eager mode)")

    yield

    # Shutdown
    if auto_sync_task is not None:
        auto_sync_task.cancel()
    logger.info("Shutting down ABACO News backend")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description="ABACO News Aggregation Platform – REST API",
        version="1.0.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    allowed_origins = [
        f"https://{settings.DOMAIN}",
        f"https://www.{settings.DOMAIN}",
    ]
    if settings.DEBUG:
        allowed_origins += [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────────────────────────
    from app.api.router import api_router

    app.include_router(api_router, prefix="/api")

    # ── Health endpoint ───────────────────────────────────────────────────────
    @app.get("/health", tags=["health"], summary="Liveness probe")
    async def health() -> JSONResponse:
        return JSONResponse({"status": "ok", "app": settings.APP_NAME})

    return app


app = create_app()
