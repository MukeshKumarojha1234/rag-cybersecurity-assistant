"""Cross-encoder re-ranking via onnxruntime + tokenizers — no torch.

Scores (query, passage) pairs jointly (unlike the bi-encoder in node 3,
which scores them independently), which is slower per-pair but far more
accurate — the reason it only runs over a small hybrid-search candidate
set rather than the whole corpus.
"""
from __future__ import annotations

import os

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

from . import config


class CrossEncoderReranker:
    def __init__(self, model_name: str | None = None, max_length: int | None = None):
        self.model_name = model_name or config.CROSS_ENCODER_MODEL_NAME
        self.max_length = max_length or config.CROSS_ENCODER_MAX_LENGTH

        tokenizer_path, model_path = self._resolve_files(self.model_name)

        self._tokenizer = Tokenizer.from_file(tokenizer_path)
        self._tokenizer.enable_truncation(max_length=self.max_length)
        self._tokenizer.enable_padding(pad_id=0, pad_token="[PAD]")

        self._session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])

    @staticmethod
    def _resolve_files(model_name: str) -> tuple[str, str]:
        """Download (or find cached) tokenizer + ONNX weights.

        Same offline-first pattern as node 3's embedder: HF Hub's
        freshness check has been observed to stall for minutes on this
        host even when the files are already cached.
        """
        def _download():
            from huggingface_hub import hf_hub_download

            tokenizer_path = hf_hub_download(model_name, "tokenizer.json")
            model_path = hf_hub_download(model_name, config.CROSS_ENCODER_ONNX_FILE)
            return tokenizer_path, model_path

        previous = os.environ.get("HF_HUB_OFFLINE")
        os.environ["HF_HUB_OFFLINE"] = "1"
        try:
            return _download()
        except Exception:
            if previous is None:
                os.environ.pop("HF_HUB_OFFLINE", None)
            else:
                os.environ["HF_HUB_OFFLINE"] = previous
            return _download()

    def score(self, query: str, passages: list[str]) -> list[float]:
        """Return a relevance score per passage — sigmoid of the model's raw
        logit, so scores land in (0, 1) and higher means more relevant.
        Monotonic, so ranking order is unaffected by the sigmoid."""
        if not passages:
            return []

        encodings = self._tokenizer.encode_batch([(query, passage) for passage in passages])
        input_ids = np.array([e.ids for e in encodings], dtype=np.int64)
        attention_mask = np.array([e.attention_mask for e in encodings], dtype=np.int64)
        token_type_ids = np.array([e.type_ids for e in encodings], dtype=np.int64)

        (logits,) = self._session.run(
            None,
            {"input_ids": input_ids, "attention_mask": attention_mask, "token_type_ids": token_type_ids},
        )
        logits = logits.reshape(-1).astype(np.float64)
        return (1.0 / (1.0 + np.exp(-logits))).tolist()
