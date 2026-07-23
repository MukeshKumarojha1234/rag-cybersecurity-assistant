"""Node 3 — Embedding & indexing.

Generates dense embeddings for chunks from node 2 and builds a hybrid
vector + keyword (BM25) index — the retrieval-ready store that node 4
(retrieval & re-ranking) queries.
"""
from .embedder import Embedder, FastEmbedEmbedder
from .hybrid_index import HybridIndex, SearchResult, reciprocal_rank_fusion
from .pipeline import build_index

__all__ = [
    "Embedder",
    "FastEmbedEmbedder",
    "HybridIndex",
    "SearchResult",
    "build_index",
    "reciprocal_rank_fusion",
]
