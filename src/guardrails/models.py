"""Data models produced by node 6."""
from __future__ import annotations

from pydantic import BaseModel

from src.generation.models import GeneratedAnswer


class IntentVerdict(BaseModel):
    blocked: bool
    category: str | None = None
    matched_pattern: str | None = None


class ConfidenceAssessment(BaseModel):
    score: float  # 0-1, mean rerank_score of the sources actually cited
    label: str  # "high" | "medium" | "low"
    flags: list[str]  # e.g. ["ungrounded"], ["low_relevance"], ["thin_context"]


class GuardedAnswer(BaseModel):
    query: str
    blocked: bool
    message: str  # the refusal text if blocked, else the generated answer text
    answer: GeneratedAnswer | None = None  # None if blocked
    confidence: ConfidenceAssessment | None = None  # None if blocked
    intent: IntentVerdict
