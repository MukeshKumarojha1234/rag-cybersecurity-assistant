"""Node 7 — Evaluation.

Runs a golden test set (queries with known-correct sources, reproducible
regardless of when it's run) through the live pipeline (nodes 3-6) and
scores retrieval precision/recall/MRR and generation faithfulness/citation
correctness.
"""
from .golden_set import GOLDEN_SET, GoldenExample, build_eval_corpus
from .metrics import EvaluationReport, GenerationResult, RetrievalResult
from .pipeline import evaluate

__all__ = [
    "GOLDEN_SET",
    "GoldenExample",
    "build_eval_corpus",
    "EvaluationReport",
    "GenerationResult",
    "RetrievalResult",
    "evaluate",
]
