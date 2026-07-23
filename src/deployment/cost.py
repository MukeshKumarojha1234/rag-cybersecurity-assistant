"""Cost estimation for node 8's usage tracking.

Pricing is USD per million tokens, snapshotted from Anthropic's published
rates as of 2026-06-24 (see https://platform.claude.com/docs/en/pricing for
current figures — prices do change; update PRICING below if they drift).
"""
from __future__ import annotations

PRICING: dict[str, dict[str, float]] = {
    "claude-fable-5": {"input": 10.00, "output": 50.00},
    "claude-mythos-5": {"input": 10.00, "output": 50.00},
    "claude-opus-4-8": {"input": 5.00, "output": 25.00},
    "claude-opus-4-7": {"input": 5.00, "output": 25.00},
    "claude-opus-4-6": {"input": 5.00, "output": 25.00},
    "claude-sonnet-5": {"input": 3.00, "output": 15.00},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-haiku-4-5": {"input": 1.00, "output": 5.00},
}


def estimate_cost_usd(model_name: str, input_tokens: int, output_tokens: int) -> float | None:
    """Return the estimated USD cost of a generation call, or None if the model isn't priced here."""
    rates = PRICING.get(model_name)
    if rates is None:
        return None
    return (input_tokens * rates["input"] + output_tokens * rates["output"]) / 1_000_000
