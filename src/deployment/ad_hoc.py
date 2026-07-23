"""Ad-hoc, session-scoped document handling for uploaded files.

Mirrors the frontend's "attach a document for this session" feature: an
uploaded file is chunked and scored against the query for that request only
(see src/guardrails/pipeline.py's `extra_chunks` param) — it's never written
into the persistent index node 3 built.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from src.preprocessing.chunker import chunk_by_words
from src.preprocessing.cleaning import clean_text
from src.preprocessing.models import Chunk

logger = logging.getLogger(__name__)

_TEXT_EXTENSIONS = {".txt", ".md", ".log", ".csv"}
_BINARY_READERS = {}  # populated below, after the reader functions are defined

# Matches node 2's mitre_attack/ics_cert chunking — a session upload is an
# arbitrary document of unknown structure, so a plain word-bounded split
# (no heading assumptions) is the safest default.
_MAX_WORDS = 220
_OVERLAP_WORDS = 40

# PDF/DOCX parsing has been observed to throw transient, non-reproducible
# I/O errors on Windows (large uploads get spooled to a temp file by
# python-multipart, which can race with e.g. antivirus scanning) — one retry
# clears these without masking a genuinely corrupt or unsupported upload.
_MAX_EXTRACT_ATTEMPTS = 2


def extract_text(filename: str, content: bytes) -> str | None:
    suffix = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""
    if suffix in _TEXT_EXTENSIONS:
        return content.decode("utf-8", errors="replace")

    reader = _BINARY_READERS.get(suffix)
    if reader is None:
        logger.warning("Unsupported uploaded file type: %s", filename)
        return None

    for attempt in range(1, _MAX_EXTRACT_ATTEMPTS + 1):
        try:
            return reader(content)
        except Exception:
            logger.exception(
                "Failed to extract text from uploaded file %s (attempt %d/%d)",
                filename, attempt, _MAX_EXTRACT_ATTEMPTS,
            )
    return None


def _read_pdf(content: bytes) -> str:
    import io

    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(content))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _read_docx(content: bytes) -> str:
    import io

    import docx

    document = docx.Document(io.BytesIO(content))
    return "\n".join(p.text for p in document.paragraphs)


_BINARY_READERS.update({".pdf": _read_pdf, ".docx": _read_docx})


@dataclass
class UploadOutcome:
    """What happened to a session upload — surfaced to the API response so a
    silently-dropped file (unsupported type, extraction error, no text) shows
    up as a visible warning instead of just quietly falling back to the
    persistent index, which looks identical to a normal low-confidence answer.
    """

    chunks: list[Chunk] = field(default_factory=list)
    status: str = "processed"  # "processed" | "unreadable" | "empty"


def build_ad_hoc_chunks(filename: str, content: bytes) -> UploadOutcome:
    """Turn an uploaded file into session-scoped Chunks, or an empty outcome if empty/unsupported.

    Split rather than kept as one chunk — a multi-page upload scored as a
    single passage would have its relevant section diluted (or truncated
    away entirely) by the cross-encoder reranker, which scores each extra
    chunk independently (see guardrails/pipeline.py's `extra_chunks`).
    """
    text = extract_text(filename, content)
    if not text:
        return UploadOutcome(status="unreadable")

    cleaned = clean_text(text)
    if not cleaned:
        return UploadOutcome(status="empty")

    pieces = chunk_by_words(cleaned, max_words=_MAX_WORDS, overlap_words=_OVERLAP_WORDS)
    chunks = [
        Chunk(
            id=f"{filename}::session-upload::{i}",
            doc_id=filename,
            source_type="internal_sop",
            title=filename,
            text=piece,
            chunk_index=i,
            total_chunks=len(pieces),
            metadata={"session_upload": True},
        )
        for i, piece in enumerate(pieces)
    ]
    return UploadOutcome(chunks=chunks, status="processed")
