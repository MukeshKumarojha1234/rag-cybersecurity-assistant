"""Node 3 configuration."""
import os
from pathlib import Path

# BAAI/bge-small-en-v1.5: 384-dim, ONNX-quantized, runs via onnxruntime (no
# torch). Chosen specifically because this machine's Windows Application
# Control policy blocks torch's native DLLs — onnxruntime's are unaffected.
EMBEDDING_MODEL_NAME = os.environ.get("EMBEDDING_MODEL_NAME", "BAAI/bge-small-en-v1.5")

INDEX_DIR = Path(os.environ.get("INDEX_DIR", Path(__file__).resolve().parents[2] / "data" / "index"))

RRF_K = 60
DEFAULT_TOP_K = 10
