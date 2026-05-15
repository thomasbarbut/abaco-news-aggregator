import os

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

# Dev mode: run tasks inline (no Redis broker needed). Reads
# CELERY_TASK_ALWAYS_EAGER from env, defaults to True when DEBUG is on.
_eager = os.environ.get("CELERY_TASK_ALWAYS_EAGER", "true" if settings.DEBUG else "false").lower() in ("1", "true", "yes")

celery_app = Celery(
    "abaco_news",
    broker=settings.REDIS_URL if not _eager else "memory://",
    backend=settings.REDIS_URL if not _eager else "cache+memory://",
    include=["app.tasks.sync_tasks", "app.tasks.email_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Bucharest",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_always_eager=_eager,
    task_eager_propagates=_eager,
    beat_schedule={
        "sync-all-sources": {
            "task": "app.tasks.sync_tasks.sync_all_sources",
            "schedule": crontab(minute=f"*/{settings.SYNC_INTERVAL_MINUTES}"),
        },
    },
)
