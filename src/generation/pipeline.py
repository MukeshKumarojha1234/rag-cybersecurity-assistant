"""Node 5 entry point: retrieved chunks -> a grounded, cited answer."""
from __future__ import annotations

import re

from src.retrieval.pipeline import RankedResult

from .generator import Generator
from .models import Citation, GeneratedAnswer
from .prompts import SYSTEM_PROMPT, build_user_prompt

_CITATION_RE = re.compile(r"\[(\d+)\]")


def generate_answer(
    query: str,
    results: list[RankedResult],
    generator: Generator,
    max_tokens: int | None = None,
) -> GeneratedAnswer:
    """Generate an answer grounded in `results`, resolving inline [n] markers back to their chunks.

    Citations are only included for markers the model actually used and
    that resolve to a real result — a fabricated or out-of-range marker is
    silently dropped rather than crashing the pipeline.
    """
    if not results:
        return GeneratedAnswer(
            query=query,
            answer=(
                "I don't have any indexed sources that address this — try rephrasing the "
                "question or broadening the data sources."
            ),
            citations=[],
            grounded=False,
            context_chunk_count=0,
        )

    raw_answer = generator.generate(SYSTEM_PROMPT, build_user_prompt(query, results), max_tokens=max_tokens)

    used_markers = sorted({int(m) for m in _CITATION_RE.findall(raw_answer)})
    citations = [
        Citation(
            marker=marker,
            chunk_id=results[marker - 1].chunk.id,
            doc_id=results[marker - 1].chunk.doc_id,
            source_type=results[marker - 1].chunk.source_type,
            title=results[marker - 1].chunk.title,
            url=results[marker - 1].chunk.url,
        )
        for marker in used_markers
        if 1 <= marker <= len(results)
    ]

    return GeneratedAnswer(
        query=query,
        answer=raw_answer,
        citations=citations,
        grounded=len(citations) > 0,
        context_chunk_count=len(results),
    )
