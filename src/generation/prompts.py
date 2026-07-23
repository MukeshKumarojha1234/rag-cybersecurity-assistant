"""Prompt construction for node 5.

Deliberately scoped to grounding + citation behavior only. Refusing
exploit/attack requests and flagging low-confidence answers is node 6's
job ("Guardrails & safety") — this prompt doesn't duplicate that logic.
"""
from __future__ import annotations

from src.retrieval.pipeline import RankedResult

SYSTEM_PROMPT = """\
You are SentinelRAG, a cybersecurity assistant. Answer ONLY using the \
numbered source excerpts given in the context below — do not draw on \
outside or prior knowledge, and never invent a CVE ID, technique ID, \
advisory number, or fact that isn't present in the excerpts.

Rules:
- Support every factual claim with the bracketed source number(s) it came \
from, placed right after the claim, e.g. "...allows remote code execution [2]."
- A claim may cite more than one source if more than one supports it, e.g. [1][3].
- Excerpts marked "USER-UPLOADED DOCUMENT" were attached by the user for \
this specific question — when one of them is relevant to the question, \
prefer citing it over the general indexed corpus, since it's the source \
the user explicitly asked about.
- If the excerpts don't contain enough information to answer the question, \
say so plainly instead of guessing or filling gaps with general knowledge.
- Be concise and technically precise; the audience is security practitioners.\
"""


def build_context_block(results: list[RankedResult]) -> str:
    """Render retrieved chunks as numbered excerpts, in the order the model should cite them."""
    lines = []
    for i, result in enumerate(results, start=1):
        chunk = result.chunk
        label = "USER-UPLOADED DOCUMENT" if chunk.metadata.get("session_upload") else chunk.source_type
        lines.append(f"[{i}] ({label} — {chunk.id}) {chunk.title}\n{chunk.text}")
    return "\n\n".join(lines)


def build_user_prompt(query: str, results: list[RankedResult]) -> str:
    return f"Context:\n{build_context_block(results)}\n\nQuestion: {query}"
