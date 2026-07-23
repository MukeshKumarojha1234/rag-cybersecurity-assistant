"""Node 6 entry point — the full guarded pipeline: nodes 4, 5, and 6 wired together."""
from __future__ import annotations

from src.embedding_indexing import HybridIndex
from src.generation.generator import Generator
from src.generation.pipeline import generate_answer
from src.preprocessing.models import Chunk
from src.retrieval.cross_encoder import CrossEncoderReranker
from src.retrieval.filters import MetadataFilter
from src.retrieval.pipeline import RankedResult, retrieve

from . import config
from .confidence import assess_confidence
from .intent_classifier import HeuristicIntentClassifier, IntentClassifier
from .models import GuardedAnswer


def answer_query(
    query: str,
    index: HybridIndex,
    reranker: CrossEncoderReranker,
    generator: Generator,
    filters: MetadataFilter | None = None,
    classifier: IntentClassifier | None = None,
    top_k: int = 5,
    extra_chunks: list[Chunk] | None = None,
    max_tokens: int | None = None,
) -> GuardedAnswer:
    """Classify intent -> (node 4 retrieve -> node 5 generate) -> assess confidence.

    A blocked query never reaches retrieval or generation at all. `extra_chunks`
    (e.g. a session-scoped document upload) are scored against the query and
    the best-matching few are prepended to node 4's results — never written
    into the persistent index.
    """
    classifier = classifier or HeuristicIntentClassifier()

    intent = classifier.classify(query)
    if intent.blocked:
        return GuardedAnswer(query=query, blocked=True, message=config.REFUSAL_MESSAGE, intent=intent)

    results = retrieve(query, index, reranker, filters=filters, top_k=top_k)

    if extra_chunks:
        extra_scores = reranker.score(query, [c.text for c in extra_chunks])
        extra_results = sorted(
            (
                RankedResult(chunk=chunk, rerank_score=score, hybrid_score=1.0)
                for chunk, score in zip(extra_chunks, extra_scores)
            ),
            key=lambda r: r.rerank_score,
            reverse=True,
        )[:config.MAX_EXTRA_CHUNKS]
        results = extra_results + results

    answer = generate_answer(query, results, generator, max_tokens=max_tokens)
    confidence = assess_confidence(answer, results)

    return GuardedAnswer(
        query=query,
        blocked=False,
        message=answer.answer,
        answer=answer,
        confidence=confidence,
        intent=intent,
    )
