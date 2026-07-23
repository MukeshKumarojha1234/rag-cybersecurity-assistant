"""Node 5 — Grounded generation.

Takes node 4's filtered, re-ranked chunks and produces an answer that
cites its sources inline — the LLM is instructed to answer only from the
given excerpts, never from outside knowledge. Refusing exploit/attack
requests and flagging low-confidence answers is node 6's job, not this
one's.
"""
from .generator import AnthropicGenerator, Generator, GroqGenerator, StubGenerator
from .models import Citation, GeneratedAnswer
from .pipeline import generate_answer

__all__ = [
    "AnthropicGenerator",
    "Generator",
    "GroqGenerator",
    "StubGenerator",
    "Citation",
    "GeneratedAnswer",
    "generate_answer",
]
