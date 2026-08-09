"""Provider registry: registration, discovery, lookup by name or alias."""

from __future__ import annotations

from .base import ModelProvider


class ProviderRegistry:
    """Maps provider names to ModelProvider instances."""

    def __init__(self):
        self._providers: dict[str, ModelProvider] = {}

    def register(self, provider: ModelProvider, alias: str | None = None) -> None:
        name = provider.name
        self._providers[name] = provider
        if alias:
            self._providers[alias] = provider

    def get(self, name: str) -> ModelProvider:
        try:
            return self._providers[name]
        except KeyError:
            raise KeyError(
                f"unknown model provider {name!r}; registered: {sorted(self._providers)}"
            ) from None

    def list(self) -> list[str]:
        return sorted({p.name for p in self._providers.values()})

    def available(self) -> list[str]:
        """Providers whose health check passes (best-effort, never raises)."""
        ok = []
        for name in sorted({p.name for p in self._providers.values()}):
            try:
                if self._providers[name].health():
                    ok.append(name)
            except Exception:
                continue
        return ok

    def __contains__(self, name: str) -> bool:
        return name in self._providers
