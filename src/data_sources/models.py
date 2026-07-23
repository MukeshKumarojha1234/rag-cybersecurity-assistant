"""Data models shared by every node-1 data source."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

SourceType = Literal["cve_nvd", "mitre_attack", "ics_cert", "internal_sop"]


class RawDocument(BaseModel):
    """A single unprocessed document handed off to node 2 (preprocessing & chunking)."""

    id: str
    source_type: SourceType
    title: str
    content: str
    url: str | None = None
    published_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
