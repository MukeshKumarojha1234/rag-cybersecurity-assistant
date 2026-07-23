"""BM25 keyword index (rank_bm25) — the lexical half of the hybrid search."""
from __future__ import annotations

import re

from rank_bm25 import BM25Okapi

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9\-_.]*")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


class KeywordIndex:
    def __init__(self, texts: list[str]):
        self.texts = texts
        tokenized = [tokenize(t) for t in texts]
        self._bm25 = BM25Okapi(tokenized) if tokenized else None

    @classmethod
    def build(cls, texts: list[str]) -> KeywordIndex:
        return cls(texts)

    def search(self, query: str, top_k: int) -> list[tuple[int, float]]:
        """Return up to `top_k` (row_index, bm25_score) pairs with score > 0, best first."""
        if self._bm25 is None or top_k <= 0:
            return []
        scores = self._bm25.get_scores(tokenize(query))
        top_k = min(top_k, len(scores))
        top_indices = scores.argsort()[::-1][:top_k]
        return [(int(i), float(scores[i])) for i in top_indices if scores[i] > 0]
