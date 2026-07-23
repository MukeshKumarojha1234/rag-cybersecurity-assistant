"""Data model produced by node 2 and consumed by node 3 (embedding & indexing)."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.data_sources.models import SourceType


class Chunk(BaseModel):
    """A single retrievable unit: one slice of a cleaned, normalized RawDocument."""

    id: str
    doc_id: str
    source_type: SourceType
    title: str
    text: str
    section: str | None = None
    url: str | None = None
    published_at: datetime | None = None
    chunk_index: int
    total_chunks: int
    metadata: dict[str, Any] = Field(default_factory=dict)
