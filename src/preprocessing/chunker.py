"""Source-agnostic text chunking primitives.

Chunk size is measured in words rather than tokens to avoid pulling in a
tokenizer dependency at this stage — node 3 (embedding) is where the actual
embedding model's tokenizer becomes relevant.
"""
from __future__ import annotations

import re

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)


def chunk_by_words(text: str, max_words: int, overlap_words: int = 0, min_words: int = 30) -> list[str]:
    """Split `text` into word-bounded chunks with a sliding overlap window.

    A trailing chunk shorter than `min_words` is merged into the previous
    one instead of being kept as a tiny, low-value fragment.
    """
    words = text.split()
    if not words:
        return []
    if len(words) <= max_words:
        return [text.strip()]

    step = max(max_words - overlap_words, 1)
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + max_words, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start += step

    if len(chunks) > 1 and len(chunks[-1].split()) < min_words:
        chunks[-2] = chunks[-2] + " " + chunks[-1]
        chunks.pop()

    return chunks


def split_markdown_sections(text: str) -> list[tuple[str | None, str]]:
    """Split markdown text into (heading, body) pairs by ATX (#) headings.

    Content before the first heading, if any, is returned with heading=None.
    Text with no headings at all is returned as a single (None, text) section.
    """
    matches = list(_HEADING_RE.finditer(text))
    if not matches:
        return [(None, text)] if text.strip() else []

    sections: list[tuple[str | None, str]] = []
    if matches[0].start() > 0:
        preamble = text[: matches[0].start()].strip()
        if preamble:
            sections.append((None, preamble))

    for i, match in enumerate(matches):
        heading = match.group(2).strip()
        body_start = match.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[body_start:body_end].strip()
        if body:
            sections.append((heading, body))

    return sections
