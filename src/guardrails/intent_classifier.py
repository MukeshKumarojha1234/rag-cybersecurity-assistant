"""Query-intent classification — refuses exploit/attack requests before node 5 ever runs.

Checked at the query stage rather than post-hoc on the generated answer:
cheaper (no wasted LLM call) and doesn't rely on the generator alone to
resist a malicious request.
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod

from .models import IntentVerdict

# Patterns are whole-ish phrases, not single words like "exploit" or "hack"
# on their own — those are ordinary vocabulary in defensive security
# questions ("how does this exploit work", "who hacked X") and would
# false-positive constantly if matched alone.
_PATTERNS: dict[str, list[str]] = {
    "malware_generation": [
        r"\bwrite\s+(?:me\s+)?(?:a\s+)?(?:malware|virus|ransomware|worm|trojan|rootkit)\b",
        r"\b(?:create|generate|build)\s+(?:a\s+|me\s+a\s+)?(?:malware|virus|ransomware|worm|trojan)\b",
    ],
    "exploit_development": [
        r"\bwrite\s+(?:me\s+)?an?\s+exploit\b",
        r"\b(?:exploit|poc)\s+code\s+for\b",
        r"\bweaponi[sz]e\b",
    ],
    "attack_instructions": [
        r"\bhow\s+(?:do\s+i|to)\s+hack\b",
        r"\bstep[\s-]by[\s-]step\s+attack\b",
        r"\battack\s+plan\s+for\b",
    ],
    "evasion": [
        r"\bbypass\s+(?:antivirus|edr|detection)\b",
        r"\bevade\s+(?:edr|antivirus|detection)\b",
    ],
    "credential_theft": [
        r"\bdump\s+(?:credentials|passwords|hashes)\b",
        r"\bcrack\s+(?:the\s+)?password\b",
    ],
    "reverse_shell": [
        r"\breverse[\s-]shell\s+payload\s+for\b",
    ],
}

_COMPILED = {
    category: [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    for category, patterns in _PATTERNS.items()
}


class IntentClassifier(ABC):
    @abstractmethod
    def classify(self, query: str) -> IntentVerdict:
        """Return whether `query` should be refused, and why."""


class HeuristicIntentClassifier(IntentClassifier):
    """Fast, deterministic, no LLM call.

    Catches clear-cut phrasing; a paraphrased or obfuscated request may
    slip through. This is one layer of defense-in-depth, not the only one
    — node 5's system prompt also declines unsafe requests.
    """

    def classify(self, query: str) -> IntentVerdict:
        for category, patterns in _COMPILED.items():
            for pattern in patterns:
                if pattern.search(query):
                    return IntentVerdict(blocked=True, category=category, matched_pattern=pattern.pattern)
        return IntentVerdict(blocked=False)
