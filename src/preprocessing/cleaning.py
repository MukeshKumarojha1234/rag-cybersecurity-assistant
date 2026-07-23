"""Text cleaning shared by every source type before chunking."""
from __future__ import annotations

import html
import re
import unicodedata

_TAG_RE = re.compile(r"<[^>]+>")
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_INLINE_WHITESPACE_RE = re.compile(r"[ \t\f\v]+")
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")


def strip_html(text: str) -> str:
    """Remove HTML tags (does not attempt to preserve block structure)."""
    return _TAG_RE.sub(" ", text)


def clean_text(text: str) -> str:
    """Decode entities, strip markup/control chars, and normalize whitespace.

    Idempotent and safe to run on already-clean plaintext (e.g. MITRE ATT&CK
    descriptions), so every source type is passed through it uniformly.
    """
    if not text:
        return ""

    text = html.unescape(text)
    text = strip_html(text)
    text = unicodedata.normalize("NFKC", text)
    text = _CONTROL_CHAR_RE.sub("", text)
    text = _INLINE_WHITESPACE_RE.sub(" ", text)
    text = _MULTI_NEWLINE_RE.sub("\n\n", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    return text.strip()
