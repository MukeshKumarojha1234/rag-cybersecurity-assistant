"""Node 4 entry point: metadata filtering -> hybrid search -> cross-encoder re-rank."""
from __future__ import annotations

from pydantic import BaseModel

from src.embedding_indexing import HybridIndex, reciprocal_rank_fusion
from src.preprocessing.models import Chunk

from . import config
from .cross_encoder import CrossEncoderReranker
from .filters import MetadataFilter, matching_indices


class RankedResult(BaseModel):
    chunk: Chunk
    rerank_score: float
    hybrid_score: float
    vector_score: float | None = None
    keyword_score: float | None = None


def retrieve(
    query: str,
    index: HybridIndex,
    reranker: CrossEncoderReranker,
    filters: MetadataFilter | None = None,
    candidate_k: int = config.DEFAULT_CANDIDATE_K,
    top_k: int = config.DEFAULT_TOP_K,
) -> list[RankedResult]:
    """Filter by metadata, run hybrid search over what's left, then re-rank with a cross-encoder."""
    allowed = matching_indices(index.chunks, filters)
    if allowed is not None and not allowed:
        return []  # nothing in the corpus matches the filter

    candidates = _hybrid_candidates(index, query, allowed, candidate_k)
    if not candidates:
        return []

    passages = [_passage_text(index.chunks[idx]) for idx, *_ in candidates]
    rerank_scores = reranker.score(query, passages)

    ranked = sorted(zip(candidates, rerank_scores), key=lambda pair: pair[1], reverse=True)[:top_k]
    return [
        RankedResult(
            chunk=index.chunks[idx],
            rerank_score=rerank_score,
            hybrid_score=hybrid_score,
            vector_score=vector_score,
            keyword_score=keyword_score,
        )
        for (idx, hybrid_score, vector_score, keyword_score), rerank_score in ranked
    ]


def _passage_text(chunk: Chunk) -> str:
    """Text shown to the cross-encoder: title (and section, if chunked by heading) plus body.

    A chunk's body alone can omit the words that actually signal relevance
    — e.g. an internal SOP's numbered procedure steps don't repeat its own
    title, so scoring on body text alone can badly underrate an otherwise
    obvious match. Node 5's generation prompt already includes the title
    for the same reason; this keeps the two consistent.
    """
    parts = [chunk.title]
    if chunk.section and chunk.section != chunk.title:
        parts.append(chunk.section)
    parts.append(chunk.text)
    return "\n".join(parts)


def _hybrid_candidates(
    index: HybridIndex, query: str, allowed: list[int] | None, candidate_k: int
) -> list[tuple[int, float, float | None, float | None]]:
    """Vector + BM25 + RRF, restricted to `allowed` row indices when a filter is active.

    When filtering, both branches search the *whole* corpus rather than an
    arbitrary top-N, so a small eligible subset isn't lost before the filter
    even gets applied — the corpus here is small enough (thousands of
    chunks) that this costs milliseconds.
    """
    search_k = len(index.chunks) if allowed is not None else max(candidate_k * 4, 20)

    query_embedding = index.embedder.embed([query])[0]
    vector_hits = index.vector_index.search(query_embedding, search_k)
    keyword_hits = index.keyword_index.search(query, search_k)

    if allowed is not None:
        allowed_set = set(allowed)
        vector_hits = [(i, s) for i, s in vector_hits if i in allowed_set]
        keyword_hits = [(i, s) for i, s in keyword_hits if i in allowed_set]

    vector_lookup = dict(vector_hits)
    keyword_lookup = dict(keyword_hits)
    fused = reciprocal_rank_fusion([vector_hits, keyword_hits])

    top = sorted(fused.items(), key=lambda kv: kv[1], reverse=True)[:candidate_k]
    return [(idx, score, vector_lookup.get(idx), keyword_lookup.get(idx)) for idx, score in top]
