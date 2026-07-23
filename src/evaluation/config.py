"""Node 7 configuration."""
import os
from pathlib import Path

EVAL_INDEX_DIR = Path(
    os.environ.get("EVAL_INDEX_DIR", Path(__file__).resolve().parents[2] / "data" / "eval_index")
)

# Pinned by ID rather than relying on node 1's fetch_all(), whose CVE window
# is a rolling last-7-days — that would make CVE-based golden examples
# flaky depending on which day the eval runs.
PINNED_CVE_IDS = ["CVE-2021-44228", "CVE-2017-0144"]  # Log4Shell, EternalBlue/WannaCry (SMBv1)

DEFAULT_TOP_K = 5
