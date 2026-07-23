"""Node 7 entry point: run the golden test set through the live pipeline and score it."""
from __future__ import annotations

from src.embedding_indexing import HybridIndex
from src.generation.generator import Generator
from src.generation.pipeline import generate_answer
from src.guardrails.intent_classifier import HeuristicIntentClassifier, IntentClassifier
from src.retrieval.cross_encoder import CrossEncoderReranker
from src.retrieval.pipeline import retrieve

from . import config
from .golden_set import GOLDEN_SET, GoldenExample
from .metrics import EvaluationReport, GenerationResult, RetrievalResult, score_generation, score_retrieval


def evaluate(
    index: HybridIndex,
    reranker: CrossEncoderReranker,
    generator: Generator,
    classifier: IntentClassifier | None = None,
    examples: list[GoldenExample] | None = None,
    top_k: int = config.DEFAULT_TOP_K,
) -> EvaluationReport:
    """Retrieve + generate for every golden example, scoring both stages.

    Runs the intent classifier too (node 6) so a false-positive block on a
    legitimate golden query shows up as a metric rather than silently
    skewing the generation scores.
    """
    classifier = classifier or HeuristicIntentClassifier()
    examples = examples if examples is not None else GOLDEN_SET

    retrieval_results: list[RetrievalResult] = []
    generation_results: list[GenerationResult] = []

    for example in examples:
        results = retrieve(example.query, index, reranker, filters=example.filters, top_k=top_k)
        retrieved_doc_ids = _dedupe([r.chunk.doc_id for r in results])
        retrieval_results.append(score_retrieval(example, retrieved_doc_ids))

        if classifier.classify(example.query).blocked:
            generation_results.append(
                score_generation(example, answer_text="", cited_doc_ids=[], grounded=False, blocked=True)
            )
            continue

        answer = generate_answer(example.query, results, generator)
        cited_doc_ids = [c.doc_id for c in answer.citations]
        generation_results.append(
            score_generation(example, answer.answer, cited_doc_ids, answer.grounded, blocked=False)
        )

    return EvaluationReport(retrieval=retrieval_results, generation=generation_results)


def _dedupe(doc_ids: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped = []
    for doc_id in doc_ids:
        if doc_id not in seen:
            seen.add(doc_id)
            deduped.append(doc_id)
    return deduped
