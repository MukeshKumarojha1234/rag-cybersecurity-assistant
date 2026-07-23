"""Brute-force cosine-similarity vector index.

The corpus here (low thousands of chunks) is small enough that a
brute-force numpy search is simpler and more portable than standing up
FAISS/HNSW, while still completing in milliseconds. Swap in an ANN library
here if the corpus grows past what brute force can serve interactively.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np


class VectorIndex:
    def __init__(self, embeddings: np.ndarray):
        self.embeddings = embeddings  # (N, dim), assumed L2-normalized

    @classmethod
    def build(cls, embeddings: np.ndarray) -> VectorIndex:
        return cls(embeddings)

    def search(self, query_embedding: np.ndarray, top_k: int) -> list[tuple[int, float]]:
        """Return up to `top_k` (row_index, cosine_similarity) pairs, best first."""
        if top_k <= 0 or self.embeddings.shape[0] == 0:
            return []
        scores = self.embeddings @ query_embedding
        top_k = min(top_k, len(scores))
        top_indices = np.argpartition(-scores, top_k - 1)[:top_k]
        top_indices = top_indices[np.argsort(-scores[top_indices])]
        return [(int(i), float(scores[i])) for i in top_indices]

    def save(self, path: Path | str) -> None:
        np.save(str(path), self.embeddings)

    @classmethod
    def load(cls, path: Path | str) -> VectorIndex:
        return cls(np.load(str(path)))
