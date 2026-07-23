"""Node 2 entry point: RawDocument -> cleaned, normalized, tagged Chunks."""
from __future__ import annotations

import logging

from src.data_sources.models import RawDocument

from .chunker import chunk_by_words, split_markdown_sections
from .cleaning import clean_text
from .config import CHUNK_CONFIGS
from .cve_normalizer import normalize_cve_metadata
from .models import Chunk

logger = logging.getLogger(__name__)


def _chunk_text(source_type: str, text: str) -> list[tuple[str | None, str]]:
    """Return (section, chunk_text) pairs for a cleaned document body."""
    config = CHUNK_CONFIGS.get(source_type)
    if config is None:
        return [(None, text)] if text.strip() else []

    sections = split_markdown_sections(text) if config.split_by_heading else [(None, text)]

    pieces: list[tuple[str | None, str]] = []
    for heading, body in sections:
        for piece in chunk_by_words(body, config.max_words, config.overlap_words, config.min_words):
            pieces.append((heading, piece))
    return pieces


def preprocess_document(doc: RawDocument) -> list[Chunk]:
    """Clean, normalize, and chunk a single RawDocument."""
    cleaned = clean_text(doc.content)
    if not cleaned:
        logger.warning("%s %s has no content after cleaning; skipping.", doc.source_type, doc.id)
        return []

    metadata = normalize_cve_metadata(doc.metadata) if doc.source_type == "cve_nvd" else dict(doc.metadata)

    pieces = _chunk_text(doc.source_type, cleaned)
    total = len(pieces)

    return [
        Chunk(
            id=f"{doc.id}::chunk-{i}",
            doc_id=doc.id,
            source_type=doc.source_type,
            title=doc.title,
            text=piece_text,
            section=section,
            url=doc.url,
            published_at=doc.published_at,
            chunk_index=i,
            total_chunks=total,
            metadata=metadata,
        )
        for i, (section, piece_text) in enumerate(pieces)
    ]


def preprocess_documents(documents: list[RawDocument]) -> list[Chunk]:
    """Clean, normalize, and chunk every RawDocument from node 1.

    A failure on one document is isolated and logged so it doesn't drop the
    rest of the batch.
    """
    chunks: list[Chunk] = []
    for doc in documents:
        try:
            chunks.extend(preprocess_document(doc))
        except Exception:
            logger.exception("Failed to preprocess %s %s; skipping.", doc.source_type, doc.id)
    return chunks
