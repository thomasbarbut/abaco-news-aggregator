from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "abaco_news",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
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
    beat_schedule={
        "sync-all-sources": {
            "task": "app.tasks.sync_tasks.sync_all_sources",
            "schedule": crontab(minute=f"*/{settings.SYNC_INTERVAL_MINUTES}"),
        },
    },
)
