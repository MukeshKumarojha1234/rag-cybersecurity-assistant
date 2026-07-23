"""Node 6 — Guardrails & safety.

Refuses exploit/attack-instruction requests before generation ever runs,
and flags low-confidence answers using signals already computed by nodes
4 and 5 (cross-encoder relevance, citation grounding). This is the outward
entry point for the whole pipeline — `answer_query()` wires nodes 4, 5,
and 6 together.
"""
from .confidence import assess_confidence
from .intent_classifier import HeuristicIntentClassifier, IntentClassifier
from .models import ConfidenceAssessment, GuardedAnswer, IntentVerdict
from .pipeline import answer_query

__all__ = [
    "assess_confidence",
    "HeuristicIntentClassifier",
    "IntentClassifier",
    "ConfidenceAssessment",
    "GuardedAnswer",
    "IntentVerdict",
    "answer_query",
]
