"""Node 2 configuration — chunking strategy per source type."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChunkConfig:
    max_words: int
    overlap_words: int = 0
    min_words: int = 30
    split_by_heading: bool = False


# CVE/NVD entries are already short, structured, single-purpose paragraphs —
# splitting one apart would just fragment a single citeable fact, so it maps
# to None (never chunked; the whole cleaned document becomes one chunk).
CHUNK_CONFIGS: dict[str, ChunkConfig | None] = {
    "cve_nvd": None,
    "mitre_attack": ChunkConfig(max_words=220, overlap_words=40),
    "ics_cert": ChunkConfig(max_words=220, overlap_words=40),
    "internal_sop": ChunkConfig(max_words=180, overlap_words=30, split_by_heading=True),
}
