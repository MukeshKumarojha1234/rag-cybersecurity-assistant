"""Metadata filtering — the first stage of node 4, applied before hybrid search."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from src.data_sources.models import SourceType
from src.preprocessing.models import Chunk

_SEVERITY_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}


class MetadataFilter(BaseModel):
    """All set fields are combined with AND. Unset (None) fields impose no constraint."""

    source_types: list[SourceType] | None = None
    min_severity: str | None = None  # CVE/NVD only: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
    min_cvss_score: float | None = None  # CVE/NVD only
    tactics: list[str] | None = None  # MITRE ATT&CK only, e.g. ["initial-access"]
    published_after: datetime | None = None
    published_before: datetime | None = None

    def is_empty(self) -> bool:
        return not any(self.model_dump().values())


def _passes(chunk: Chunk, filt: MetadataFilter) -> bool:
    if filt.source_types is not None and chunk.source_type not in filt.source_types:
        return False

    if filt.min_severity is not None:
        severity = chunk.metadata.get("severity")
        threshold = _SEVERITY_ORDER.get(filt.min_severity.upper())
        if severity is None or threshold is None or _SEVERITY_ORDER.get(severity, -1) < threshold:
            return False

    if filt.min_cvss_score is not None:
        score = chunk.metadata.get("cvss_score")
        if score is None or score < filt.min_cvss_score:
            return False

    if filt.tactics is not None:
        chunk_tactics = set(chunk.metadata.get("tactics") or [])
        if not chunk_tactics.intersection(filt.tactics):
            return False

    if filt.published_after is not None and (chunk.published_at is None or chunk.published_at < filt.published_after):
        return False

    if filt.published_before is not None and (
        chunk.published_at is None or chunk.published_at > filt.published_before
    ):
        return False

    return True


def matching_indices(chunks: list[Chunk], filt: MetadataFilter | None) -> list[int] | None:
    """Row indices of chunks passing `filt`, or None if there's no filter to apply."""
    if filt is None or filt.is_empty():
        return None
    return [i for i, chunk in enumerate(chunks) if _passes(chunk, filt)]
