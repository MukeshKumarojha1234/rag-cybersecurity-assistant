"""Retrieval and generation metrics computed over the golden test set."""
from __future__ import annotations

from pydantic import BaseModel

from .golden_set import GoldenExample


class RetrievalResult(BaseModel):
    query: str
    relevant_doc_ids: list[str]
    retrieved_doc_ids: list[str]  # rank order, deduped to doc level
    hit_rank: int | None  # 1-indexed rank of the first relevant doc found, None if missed
    precision: float
    recall: float


class GenerationResult(BaseModel):
    query: str
    grounded: bool
    keyword_hits: list[str]
    keyword_misses: list[str]
    faithfulness: float  # fraction of expected_keywords found in the answer text
    citation_correct: bool  # at least one citation points at a relevant_doc_id
    blocked_unexpectedly: bool  # every golden example is a legitimate query; a block here is a false positive


class EvaluationReport(BaseModel):
    retrieval: list[RetrievalResult]
    generation: list[GenerationResult]

    @property
    def mean_recall(self) -> float:
        return _mean(r.recall for r in self.retrieval)

    @property
    def mean_precision(self) -> float:
        return _mean(r.precision for r in self.retrieval)

    @property
    def mrr(self) -> float:
        """Mean reciprocal rank — the primary retrieval signal here, since most
        golden examples have exactly one correct doc (precision@k is
        structurally low in that case regardless of quality)."""
        return _mean((1.0 / r.hit_rank) if r.hit_rank else 0.0 for r in self.retrieval)

    @property
    def mean_faithfulness(self) -> float:
        return _mean(g.faithfulness for g in self.generation)

    @property
    def citation_accuracy(self) -> float:
        return _mean(1.0 if g.citation_correct else 0.0 for g in self.generation)

    @property
    def false_block_rate(self) -> float:
        return _mean(1.0 if g.blocked_unexpectedly else 0.0 for g in self.generation)


def _mean(values) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def score_retrieval(example: GoldenExample, retrieved_doc_ids: list[str]) -> RetrievalResult:
    relevant = set(example.relevant_doc_ids)
    retrieved_set = set(retrieved_doc_ids)

    hit_rank = next((i + 1 for i, doc_id in enumerate(retrieved_doc_ids) if doc_id in relevant), None)
    true_positives = len(relevant & retrieved_set)

    return RetrievalResult(
        query=example.query,
        relevant_doc_ids=example.relevant_doc_ids,
        retrieved_doc_ids=retrieved_doc_ids,
        hit_rank=hit_rank,
        precision=true_positives / len(retrieved_doc_ids) if retrieved_doc_ids else 0.0,
        recall=true_positives / len(relevant) if relevant else 0.0,
    )


def score_generation(
    example: GoldenExample,
    answer_text: str,
    cited_doc_ids: list[str],
    grounded: bool,
    blocked: bool,
) -> GenerationResult:
    lowered = answer_text.lower()
    hits = [kw for kw in example.expected_keywords if kw.lower() in lowered]
    misses = [kw for kw in example.expected_keywords if kw.lower() not in lowered]
    faithfulness = len(hits) / len(example.expected_keywords) if example.expected_keywords else 1.0

    return GenerationResult(
        query=example.query,
        grounded=grounded,
        keyword_hits=hits,
        keyword_misses=misses,
        faithfulness=faithfulness,
        citation_correct=any(doc_id in example.relevant_doc_ids for doc_id in cited_doc_ids),
        blocked_unexpectedly=blocked,
    )
