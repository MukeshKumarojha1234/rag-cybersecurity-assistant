"""Node 8 — Deployment & monitoring.

The FastAPI app (`api.py`) that the frontend's app.js already expects at
POST /api/query, plus SQLite query/retrieval logging and drift/cost
tracking. This is the outward-facing service wrapping nodes 1-7.
"""
from .api import app

__all__ = ["app"]
