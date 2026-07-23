"""LLM backends for node 5."""
from __future__ import annotations

from abc import ABC, abstractmethod


class Generator(ABC):
    """Turns a (system prompt, user prompt) pair into a completion."""

    model_name: str
    # Set by generate() after each call, for node 8's cost tracking.
    # {"input_tokens": int, "output_tokens": int} or None if unavailable.
    last_usage: dict[str, int] | None = None

    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int | None = None) -> str:
        """Return the raw completion text.

        `max_tokens`, when given, overrides this generator's configured
        default for this call only (e.g. the frontend's response-length
        slider) — it never mutates instance state, since the generator is a
        single shared object reused across concurrent requests.
        """


class AnthropicGenerator(Generator):
    """Claude via the Anthropic API. Requires ANTHROPIC_API_KEY to be set."""

    def __init__(
        self,
        model_name: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        api_key: str | None = None,
    ):
        from anthropic import Anthropic

        from . import config

        self.model_name = model_name or config.GENERATION_MODEL
        self.max_tokens = max_tokens if max_tokens is not None else config.MAX_TOKENS
        self.temperature = temperature if temperature is not None else config.TEMPERATURE
        self._client = Anthropic(api_key=api_key)  # falls back to ANTHROPIC_API_KEY env var

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int | None = None) -> str:
        response = self._client.messages.create(
            model=self.model_name,
            max_tokens=max_tokens if max_tokens is not None else self.max_tokens,
            temperature=self.temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        self.last_usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
        return "".join(block.text for block in response.content if block.type == "text")


class GroqGenerator(Generator):
    """Free-tier alternative via the Groq API. Requires GROQ_API_KEY to be set."""

    def __init__(
        self,
        model_name: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        api_key: str | None = None,
    ):
        from groq import Groq

        from . import config

        self.model_name = model_name or config.GROQ_MODEL
        self.max_tokens = max_tokens if max_tokens is not None else config.MAX_TOKENS
        self.temperature = temperature if temperature is not None else config.TEMPERATURE
        self._client = Groq(api_key=api_key)  # falls back to GROQ_API_KEY env var

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int | None = None) -> str:
        response = self._client.chat.completions.create(
            model=self.model_name,
            max_tokens=max_tokens if max_tokens is not None else self.max_tokens,
            temperature=self.temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        self.last_usage = {
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
        }
        return response.choices[0].message.content or ""


class StubGenerator(Generator):
    """Deterministic, offline generator for testing the node 5 pipeline without an API key.

    Cites every excerpt it was given rather than actually reasoning about
    relevance — useful for verifying prompt construction, citation parsing,
    and wiring, not for judging answer quality.
    """

    model_name = "stub"

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int | None = None) -> str:
        context = user_prompt.split("Context:\n", 1)[-1].split("\n\nQuestion:")[0]
        markers = [int(line.split("]", 1)[0][1:]) for line in context.split("\n\n") if line.startswith("[")]
        citation_tail = "".join(f"[{m}]" for m in markers)
        self.last_usage = {"input_tokens": 0, "output_tokens": 0}
        return f"[stub answer — no LLM called] Relevant excerpts were retrieved {citation_tail}."
