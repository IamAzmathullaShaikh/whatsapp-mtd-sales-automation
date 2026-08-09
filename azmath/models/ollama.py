"""Ollama provider.

Wraps the existing, proven streaming REST client (``agent.ollama_client``)
behind the ModelProvider interface. All model-specific concerns live here —
nothing else in the platform knows about Ollama's API.
"""

from __future__ import annotations

from agent.ollama_client import (OllamaError, OllamaUnavailable, ollama_generate,
                                 ollama_tags)

from .base import ProviderError


class OllamaProvider:
    name = "ollama"

    def __init__(self, model: str, host: str = "http://localhost:11434",
                 temperature: float = 0.2, num_ctx: int = 16384,
                 max_tokens: int = 1600, simple_max_tokens: int = 200,
                 think="auto", timeout: int = 300):
        self.model = model
        self.host = host
        self.temperature = temperature
        self.num_ctx = num_ctx
        self.max_tokens = max_tokens
        self.simple_max_tokens = simple_max_tokens
        self.think = think  # "auto" | True | False
        self.timeout = timeout

    # -- ModelProvider -------------------------------------------------------
    def health(self) -> bool:
        """True when the server responds AND the configured model is local."""
        try:
            return self.model in self.models()
        except Exception:
            return False

    def generate(self, prompt: str, *, system: str = "", temperature: float | None = None,
                 max_tokens: int | None = None, num_ctx: int | None = None,
                 think: bool | None = None) -> str:
        """Streaming generate; reasoning never appears in the returned text."""
        # "auto" think tiers: greetings/small talk get a small budget; keep
        # think=True in BOTH tiers (verified: think=False makes qwen3 narrate).
        effective_think = think
        effective_max = max_tokens
        if effective_think is None:
            if self.think == "auto":
                effective_think = True
                if effective_max is None:
                    effective_max = self.simple_max_tokens if _is_small_talk(prompt) \
                        else self.max_tokens
            elif self.think is True or self.think is False:
                effective_think = self.think
                if effective_max is None:
                    effective_max = self.max_tokens
        try:
            return ollama_generate(
                self.host, self.model, prompt, system=system or None,
                temperature=temperature if temperature is not None else self.temperature,
                num_ctx=num_ctx or self.num_ctx,
                timeout=self.timeout, think=effective_think, max_tokens=effective_max)
        except (OllamaUnavailable, OllamaError, TimeoutError, OSError) as exc:
            raise ProviderError(
                f"ollama provider failed: {exc}", cause=exc) from exc

    def models(self) -> list[str]:
        return ollama_tags(self.host, timeout=min(self.timeout, 10))

    def metadata(self) -> dict:
        return {
            "provider": self.name,
            "model": self.model,
            "host": self.host,
            "num_ctx": self.num_ctx,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "think": self.think,
            "capabilities": ["text", "streaming", "reasoning-trace-hidden"],
        }


_SMALL_TALK = frozenset({
    "hello", "hi", "hey", "yo", "ok", "okay", "bye", "goodbye", "thanks",
    "thank you", "good morning", "good afternoon", "good evening",
})


def _is_small_talk(prompt: str) -> bool:
    q = " ".join(prompt.lower().split())
    if not q:
        return False
    if q in _SMALL_TALK:
        return True
    return any(p in q for p in ("hello there", "hi there", "hey there",
                                "what's up", "whats up", "how are you"))
