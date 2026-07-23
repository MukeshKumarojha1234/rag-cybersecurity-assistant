"""Node 3 output: a hybrid vector + keyword index over a chunk corpus.

This is node 3's own retrieval primitive — plain hybrid search via
reciprocal rank fusion, with no metadata filtering or cross-encoder
re-ranking. Node 4 ("Retrieval & re-ranking") builds on top of this with
both.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel

from src.preprocessing.models import Chunk

from . import config
from .embedder import Embedder, FastEmbedEmbedder
from .keyword_index import KeywordIndex
from .vector_index import VectorIndex

logger = logging.getLogger(__name__)


def _index_text(chunk: Chunk) -> str:
    """Text embedded and BM25-indexed: title (and section, if present) plus body.

    IDs like a CVE or ATT&CK technique number often live only in the title,
    not the body — indexing body text alone makes those chunks unreachable
    by exact-ID queries. Mirrors node 4's own `_passage_text` used for
    re-ranking, so what gets retrieved and what gets scored stay consistent.
    """
    parts = [chunk.title]
    if chunk.section and chunk.section != chunk.title:
        parts.append(chunk.section)
    parts.append(chunk.text)
    return "\n".join(parts)


class SearchResult(BaseModel):
    chunk: Chunk
    score: float
    vector_score: float | None = None
    keyword_score: float | None = None


def reciprocal_rank_fusion(rankings: list[list[tuple[int, float]]], k: int = config.RRF_K) -> dict[int, float]:
    """score(d) = sum over rankings of 1 / (k + rank_in_that_ranking).

    RRF sidesteps having to calibrate cosine similarity against a BM25 score
    on the same scale — it only uses rank position from each ranker.
    """
    fused: dict[int, float] = {}
    for ranking in rankings:
        for rank, (idx, _score) in enumerate(ranking):
            fused[idx] = fused.get(idx, 0.0) + 1.0 / (k + rank + 1)
    return fused


class HybridIndex:
    def __init__(
        self,
        chunks: list[Chunk],
        vector_index: VectorIndex,
        keyword_index: KeywordIndex,
        embedder: Embedder,
        built_at: datetime | None = None,
    ):
        self.chunks = chunks
        self.vector_index = vector_index
        self.keyword_index = keyword_index
        self.embedder = embedder
        self.built_at = built_at or datetime.now(timezone.utc)

    @classmethod
    def build(cls, chunks: list[Chunk], embedder: Embedder) -> HybridIndex:
        texts = [_index_text(c) for c in chunks]
        embeddings = embedder.embed(texts)
        return cls(chunks, VectorIndex.build(embeddings), KeywordIndex.build(texts), embedder)

    def search(self, query: str, top_k: int = config.DEFAULT_TOP_K) -> list[SearchResult]:
        if not self.chunks or top_k <= 0:
            return []

        candidate_k = max(top_k * 4, 20)
        query_embedding = self.embedder.embed([query])[0]

        vector_hits = self.vector_index.search(query_embedding, candidate_k)
        keyword_hits = self.keyword_index.search(query, candidate_k)
        vector_lookup = dict(vector_hits)
        keyword_lookup = dict(keyword_hits)

        fused = reciprocal_rank_fusion([vector_hits, keyword_hits])
        ranked = sorted(fused.items(), key=lambda kv: kv[1], reverse=True)[:top_k]

        return [
            SearchResult(
                chunk=self.chunks[idx],
                score=score,
                vector_score=vector_lookup.get(idx),
                keyword_score=keyword_lookup.get(idx),
            )
            for idx, score in ranked
        ]

    def save(self, directory: Path | str | None = None) -> None:
        directory = Path(directory or config.INDEX_DIR)
        directory.mkdir(parents=True, exist_ok=True)

        self.vector_index.save(directory / "embeddings.npy")
        with open(directory / "chunks.jsonl", "w", encoding="utf-8") as f:
            for chunk in self.chunks:
                f.write(chunk.model_dump_json() + "\n")
        with open(directory / "meta.json", "w", encoding="utf-8") as f:
            json.dump({"embedder_model": self.embedder.model_name, "built_at": self.built_at.isoformat()}, f)

        logger.info("Saved hybrid index (%d chunks) to %s", len(self.chunks), directory)

    @classmethod
    def load(cls, directory: Path | str | None = None) -> HybridIndex:
        directory = Path(directory or config.INDEX_DIR)

        vector_index = VectorIndex.load(directory / "embeddings.npy")

        chunks = []
        with open(directory / "chunks.jsonl", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    chunks.append(Chunk.model_validate_json(line))

        with open(directory / "meta.json", encoding="utf-8") as f:
            meta = json.load(f)
        embedder = FastEmbedEmbedder(model_name=meta["embedder_model"])
        built_at = datetime.fromisoformat(meta["built_at"]) if "built_at" in meta else None

        keyword_index = KeywordIndex.build([_index_text(c) for c in chunks])
        logger.info("Loaded hybrid index (%d chunks) from %s", len(chunks), directory)
        return cls(chunks, vector_index, keyword_index, embedder, built_at=built_at)
