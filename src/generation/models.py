"""Data models produced by node 5."""
from __future__ import annotations

from pydantic import BaseModel

from src.data_sources.models import SourceType


class Citation(BaseModel):
    """One [n] marker in the answer text, resolved back to its source chunk."""

    marker: int
    chunk_id: str  # e.g. "CVE-2021-44228::chunk-0" — the exact retrieved chunk
    doc_id: str  # e.g. "CVE-2021-44228" — the clean source ID for display
    source_type: SourceType
    title: str
    url: str | None = None


class GeneratedAnswer(BaseModel):
    query: str
    answer: str  # raw text with inline [n] citation markers, as the model wrote it
    citations: list[Citation]
    grounded: bool  # False if the model produced no citations (or there was no context at all)
    context_chunk_count: int
