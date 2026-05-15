"""Entry point for running the backend directly with uvicorn.

Usage (development):
    uvicorn main:app --reload --host 0.0.0.0 --port 8000

The application factory lives in app/main.py; this module simply re-exports
the ``app`` object so that uvicorn can be pointed at ``main:app`` from the
repository root or the Docker CMD.
"""

from app.main import app  # noqa: F401 – re-export

__all__ = ["app"]
