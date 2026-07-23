"""Node 8 configuration."""
import os
from pathlib import Path

HOST = os.environ.get("API_HOST", "0.0.0.0")
PORT = int(os.environ.get("API_PORT", "8001"))

# The static frontend is opened from file:// or a local dev server on a
# different port — both need explicit CORS origins (or "*" for local dev).
CORS_ORIGINS = os.environ.get("API_CORS_ORIGINS", "*").split(",")

LOG_DB_PATH = Path(os.environ.get("QUERY_LOG_DB", Path(__file__).resolve().parents[2] / "data" / "query_log.sqlite3"))

# Frontend display labels (app.js source-toggle values) <-> internal source_type.
FRONTEND_SOURCE_LABELS = {
    "CVE/NVD": "cve_nvd",
    "MITRE ATT&CK": "mitre_attack",
    "ICS-CERT": "ics_cert",
    "Internal SOP": "internal_sop",
}

MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # matches the frontend's own limit

# Drift check: how many of the most recent queries to compare against the
# node 7 baseline mean confidence.
DRIFT_WINDOW = int(os.environ.get("DRIFT_WINDOW", "20"))
DRIFT_DROP_THRESHOLD = float(os.environ.get("DRIFT_DROP_THRESHOLD", "0.2"))
