"""Node 4 — Retrieval & re-ranking.

Filters node 3's index by metadata, runs hybrid search over what's left,
and re-ranks the survivors with a cross-encoder — producing the grounded
context node 5 (generation) will cite.
"""
from .cross_encoder import CrossEncoderReranker
from .filters import MetadataFilter
from .pipeline import RankedResult, retrieve

__all__ = ["CrossEncoderReranker", "MetadataFilter", "RankedResult", "retrieve"]
