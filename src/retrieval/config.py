"""Node 4 configuration."""
import os

# ONNX conversion of cross-encoder/ms-marco-MiniLM-L-6-v2 — runs on
# onnxruntime, not torch, for the same reason node 3 uses fastembed: this
# host's Application Control policy blocks torch's native DLLs.
CROSS_ENCODER_MODEL_NAME = os.environ.get("CROSS_ENCODER_MODEL_NAME", "Xenova/ms-marco-MiniLM-L-6-v2")
CROSS_ENCODER_ONNX_FILE = os.environ.get("CROSS_ENCODER_ONNX_FILE", "onnx/model_quantized.onnx")
CROSS_ENCODER_MAX_LENGTH = 512

DEFAULT_CANDIDATE_K = 30  # hybrid-search hits fed into the cross-encoder
DEFAULT_TOP_K = 5  # re-ranked results returned to the caller
