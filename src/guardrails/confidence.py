"""Confidence assessment — the "flag low-confidence answers" half of node 6.

Reuses signals already computed upstream rather than re-deriving relevance
from scratch: node 5's `grounded` flag (did the model cite anything at
all) and node 4's cross-encoder `rerank_score` for whichever chunks got
cited (was what it cited actually relevant).
"""
from __future__ import annotations

from src.generation.models import GeneratedAnswer
from src.retrieval.pipeline import RankedResult

from . import config
from .models import ConfidenceAssessment


def assess_confidence(answer: GeneratedAnswer, results: list[RankedResult]) -> ConfidenceAssessment:
    if not answer.grounded:
        return ConfidenceAssessment(score=0.0, label="low", flags=["ungrounded"])

    rerank_by_chunk_id = {r.chunk.id: r.rerank_score for r in results}
    cited_scores = [rerank_by_chunk_id[c.chunk_id] for c in answer.citations if c.chunk_id in rerank_by_chunk_id]

    if not cited_scores:
        return ConfidenceAssessment(score=0.0, label="low", flags=["ungrounded"])

    score = sum(cited_scores) / len(cited_scores)
    flags: list[str] = []

    if score >= config.HIGH_CONFIDENCE_THRESHOLD:
        label = "high"
    elif score >= config.MEDIUM_CONFIDENCE_THRESHOLD:
        label = "medium"
    else:
        label = "low"
        flags.append("low_relevance")

    if answer.context_chunk_count <= config.THIN_CONTEXT_THRESHOLD:
        flags.append("thin_context")

    return ConfidenceAssessment(score=score, label=label, flags=flags)
