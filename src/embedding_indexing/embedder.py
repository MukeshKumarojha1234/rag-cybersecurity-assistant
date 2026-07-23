"""Embedding generation for node 3.

Wraps whichever embedding backend is configured behind a single interface,
so the vector index doesn't care where embeddings come from. The default
backend is fastembed (ONNX runtime) rather than sentence-transformers
(torch) — on this machine, a Windows Application Control policy blocks
torch's native DLLs from loading, while onnxruntime's are unaffected. A
torch-based backend would be a reasonable addition on a host without that
restriction.
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod

import numpy as np


class Embedder(ABC):
    """Turns text into L2-normalized dense vectors."""

    model_name: str
    dimension: int

    @abstractmethod
    def embed(self, texts: list[str]) -> np.ndarray:
        """Return an (len(texts), dimension) float32 array of L2-normalized embeddings."""


class FastEmbedEmbedder(Embedder):
    """Local, offline embedder via onnxruntime — no API key, no torch."""

    def __init__(self, model_name: str | None = None, batch_size: int = 64):
        from . import config

        self.model_name = model_name or config.EMBEDDING_MODEL_NAME
        self.batch_size = batch_size
        self._model = self._load_model(self.model_name)
        self.dimension = len(next(self._model.embed(["dimension probe"])))

    @staticmethod
    def _load_model(model_name: str):
        """Load the model, preferring the local cache over a Hub round-trip.

        huggingface_hub normally re-checks the Hub for updates even when a
        model is already cached, and that freshness check has been observed
        to stall for minutes on this host's network. Force offline mode
        first (fast, uses the cache); only fall back to a real download if
        nothing is cached yet.
        """
        from fastembed import TextEmbedding

        previous = os.environ.get("HF_HUB_OFFLINE")
        os.environ["HF_HUB_OFFLINE"] = "1"
        try:
            return TextEmbedding(model_name=model_name)
        except Exception:
            if previous is None:
                os.environ.pop("HF_HUB_OFFLINE", None)
            else:
                os.environ["HF_HUB_OFFLINE"] = previous
            return TextEmbedding(model_name=model_name)

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)

        embeddings = np.asarray(list(self._model.embed(texts, batch_size=self.batch_size)), dtype=np.float32)

        # Guard cosine-similarity-via-dot-product regardless of whether the
        # configured model already outputs unit-norm vectors.
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return embeddings / norms
