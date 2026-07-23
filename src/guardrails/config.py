"""Node 6 configuration."""
import os

HIGH_CONFIDENCE_THRESHOLD = float(os.environ.get("GUARDRAIL_HIGH_CONFIDENCE", "0.6"))
MEDIUM_CONFIDENCE_THRESHOLD = float(os.environ.get("GUARDRAIL_MEDIUM_CONFIDENCE", "0.3"))
THIN_CONTEXT_THRESHOLD = int(os.environ.get("GUARDRAIL_THIN_CONTEXT", "1"))

# Cap on how many of a session upload's chunks (after cross-encoder scoring)
# get prepended to the main index results — an upload can split into far
# more pieces than top_k, and dumping all of them in would drown out the
# indexed corpus and bloat the prompt.
MAX_EXTRA_CHUNKS = int(os.environ.get("GUARDRAIL_MAX_EXTRA_CHUNKS", "3"))

REFUSAL_MESSAGE = (
    "I can't help with generating exploit code, malware, or step-by-step attack "
    "instructions. I can explain the underlying vulnerability, its impact, and "
    "defensive mitigations instead — try rephrasing your question that way."
)
