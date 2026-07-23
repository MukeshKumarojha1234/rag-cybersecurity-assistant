"""Drift and freshness monitoring — the "drift and cost tracking" half of node 8."""
from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel

from src.embedding_indexing import HybridIndex

from . import config
from .query_log import recent_confidence_scores


class DriftReport(BaseModel):
    index_chunk_count: int
    index_age_days: float
    recent_mean_confidence: float | None
    baseline_mean_confidence: float | None
    drifted: bool


def index_freshness_days(index: HybridIndex) -> float:
    return (datetime.now(timezone.utc) - index.built_at).total_seconds() / 86400


def check_drift(index: HybridIndex, baseline_mean_confidence: float | None = None) -> DriftReport:
    """Compare recent live-query confidence against a baseline (e.g. node 7's eval mean).

    A drop of more than DRIFT_DROP_THRESHOLD (absolute) flags drift — a signal
    the index or retrieval quality may have degraded, worth re-running node 7's
    golden set to confirm.
    """
    recent_scores = recent_confidence_scores(config.DRIFT_WINDOW)
    recent_mean = sum(recent_scores) / len(recent_scores) if recent_scores else None

    drifted = (
        recent_mean is not None
        and baseline_mean_confidence is not None
        and (baseline_mean_confidence - recent_mean) > config.DRIFT_DROP_THRESHOLD
    )

    return DriftReport(
        index_chunk_count=len(index.chunks),
        index_age_days=index_freshness_days(index),
        recent_mean_confidence=recent_mean,
        baseline_mean_confidence=baseline_mean_confidence,
        drifted=drifted,
    )
