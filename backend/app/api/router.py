"""Central router that aggregates all sub-routers.

Each domain module (auth, articles, sources, admin …) registers its own
APIRouter and is included here. The main app then mounts this single router
under the /api prefix.
"""

from fastapi import APIRouter

# Use the full-featured router modules that live directly under app/api/
from app.api import articles, auth, sources, admin

api_router = APIRouter()

# Each sub-router already declares its own prefix; we include them without an
# additional prefix so that /api/auth/…, /api/articles/… etc. are correct.
api_router.include_router(auth.router)
api_router.include_router(articles.router)
api_router.include_router(sources.router)
api_router.include_router(admin.router)
