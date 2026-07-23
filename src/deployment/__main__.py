"""CLI: `python -m src.deployment` starts the API server on http://localhost:8001."""
from dotenv import load_dotenv

load_dotenv()  # must run before the config/api imports below, which read env vars at import time

import uvicorn

from . import config

if __name__ == "__main__":
    uvicorn.run("src.deployment.api:app", host=config.HOST, port=config.PORT, log_level="info")
