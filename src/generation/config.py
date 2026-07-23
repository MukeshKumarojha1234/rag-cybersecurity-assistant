"""Node 5 configuration."""
import os

GENERATION_MODEL = os.environ.get("GENERATION_MODEL", "claude-sonnet-5")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
MAX_TOKENS = int(os.environ.get("GENERATION_MAX_TOKENS", "1024"))
TEMPERATURE = float(os.environ.get("GENERATION_TEMPERATURE", "0.0"))

# Frontend's 1-5 "response length" slider (Short..Detailed) -> max_tokens for
# that single call. Falls back to MAX_TOKENS above when the request doesn't
# send a value (e.g. an older client) or sends one outside 1-5.
RESPONSE_LENGTH_MAX_TOKENS = {1: 200, 2: 400, 3: 700, 4: 1200, 5: 2000}
