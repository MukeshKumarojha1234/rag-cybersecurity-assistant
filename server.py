"""Unified entry point: serves the frontend and the node 8 API from one origin.

Run with `python server.py` from the project root, then open
http://localhost:8001 — the frontend's fetch("/api/query") hits the API on
the same origin, so no CORS configuration is needed for local use.

The API routes (defined in src/deployment/api.py) are registered on `app`
before the static-file mount below, so they take precedence: a request for
/api/query is handled by the API, and anything else falls through to the
frontend's static files (index.html, style.css, app.js).
"""
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # must run before the src.* imports below, which read env vars at import time

from fastapi.staticfiles import StaticFiles

from src.deployment import config
from src.deployment.api import app

FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"


class NoCacheStaticFiles(StaticFiles):
    """StaticFiles sends no Cache-Control header by default, so browsers fall
    back to heuristic caching and can keep serving a stale index.html/app.js/
    style.css indefinitely after an edit — force revalidation on every
    request instead, since this is a dev frontend that changes often.
    """

    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
        return response


app.mount("/", NoCacheStaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host=config.HOST, port=config.PORT, log_level="info")
