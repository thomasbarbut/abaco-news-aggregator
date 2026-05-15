import logging
import sys
from typing import Any

from pythonjsonlogger import jsonlogger

from app.core.config import settings

# ---------------------------------------------------------------------------
# Custom JSON formatter
# ---------------------------------------------------------------------------


class _AbacoJsonFormatter(jsonlogger.JsonFormatter):
    """Extends the base JSON formatter with app-level static fields."""

    def add_fields(
        self,
        log_record: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        super().add_fields(log_record, record, message_dict)
        log_record.setdefault("app", settings.APP_NAME)
        log_record.setdefault("env", "debug" if settings.DEBUG else "production")
        # Rename levelname → level for consistency with common log schemas
        if "levelname" in log_record:
            log_record["level"] = log_record.pop("levelname")


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

_LOG_FORMAT = "%(asctime)s %(name)s %(level)s %(message)s %(pathname)s %(lineno)d"
_LEVEL = logging.DEBUG if settings.DEBUG else logging.INFO


def setup_logging() -> None:
    """Configure the root logger and well-known uvicorn/sqlalchemy loggers.

    Call this once at application startup (e.g. inside the lifespan handler).
    """
    formatter = _AbacoJsonFormatter(fmt=_LOG_FORMAT)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # Root logger
    root = logging.getLogger()
    root.setLevel(_LEVEL)
    # Remove any handlers that may have been added by an earlier basicConfig call
    root.handlers.clear()
    root.addHandler(handler)

    # Tune noisy third-party loggers
    _set_level("uvicorn", logging.INFO)
    _set_level("uvicorn.error", logging.INFO)
    _set_level("uvicorn.access", logging.INFO)
    _set_level("sqlalchemy.engine", logging.WARNING if not settings.DEBUG else logging.INFO)
    _set_level("alembic", logging.INFO)
    _set_level("celery", logging.INFO)
    _set_level("httpx", logging.WARNING)
    _set_level("msal", logging.WARNING)

    # Propagate uvicorn loggers through the root so they use our formatter
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers.clear()
        lg.propagate = True


def _set_level(name: str, level: int) -> None:
    logging.getLogger(name).setLevel(level)


# ---------------------------------------------------------------------------
# Public helper
# ---------------------------------------------------------------------------


def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger.

    Usage::

        from app.core.logging import get_logger
        logger = get_logger(__name__)
        logger.info("Something happened", extra={"article_id": str(article_id)})
    """
    return logging.getLogger(name)
