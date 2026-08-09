"""Model provider abstraction.

The agent runtime knows ``ModelProvider``, never a specific model or server.
Providers implement ``generate`` (streaming-capable) plus health/metadata, so
future providers (OpenAI-compatible, Gemini, Anthropic-compatible, other local
engines) slot in without touching the loop, tools, or CLI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@runtime_checkable
class ModelProvider(Protocol):
    """What the runtime requires from any model backend."""

    name: str

    def health(self) -> bool:
        """Reachability/availability check. Must not raise on failure."""

    def generate(self, prompt: str, *, system: str = "", temperature: float | None = None,
                 max_tokens: int | None = None, num_ctx: int | None = None,
                 think: bool | None = None) -> str:
        """Return the model's text for `prompt`. The trace/reasoning (if any)
        must never leak into the returned string."""

    def metadata(self) -> dict:
        """Model metadata: name, provider, context, token caps, capabilities."""


@dataclass
class ProviderError(Exception):
    """A provider call failed (unreachable, timeout, invalid request)."""

    message: str
    cause: Exception | None = field(default=None, repr=False)

    def __str__(self):
        return self.message
