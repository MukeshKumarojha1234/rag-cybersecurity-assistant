"""Node 3 entry point."""
from __future__ import annotations

from src.preprocessing.models import Chunk

from .embedder import Embedder, FastEmbedEmbedder
from .hybrid_index import HybridIndex


def build_index(chunks: list[Chunk], embedder: Embedder | None = None) -> HybridIndex:
    """Embed and index every chunk from node 2 into a hybrid vector + keyword index."""
    return HybridIndex.build(chunks, embedder or FastEmbedEmbedder())
