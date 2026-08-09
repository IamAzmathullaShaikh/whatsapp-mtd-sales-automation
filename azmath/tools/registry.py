"""ToolRegistry: registration, discovery, lookup, enable/disable."""

from __future__ import annotations

from .base import Tool


class ToolRegistry:
    """Holds every registered Tool. Enablement is decided per run."""

    def __init__(self, enabled: list[str] | None = None):
        self._tools: dict[str, Tool] = {}
        self._enabled: set[str] = set(enabled or ())

    def register(self, tool: Tool) -> None:
        if not tool.name:
            raise ValueError("tool must have a name")
        if tool.name in self._tools:
            raise ValueError(f"duplicate tool name: {tool.name}")
        self._tools[tool.name] = tool
        if tool.name in self._enabled:
            self._enabled.add(tool.name)  # keep explicit enablement

    def enable(self, name: str) -> None:
        if name not in self._tools:
            raise KeyError(f"unknown tool: {name}")
        self._enabled.add(name)

    def disable(self, name: str) -> None:
        self._enabled.discard(name)

    def enable_all(self) -> None:
        self._enabled = set(self._tools)

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError:
            raise KeyError(f"unknown tool {name!r}; available: {sorted(self._tools)}") from None

    def list(self) -> list[str]:
        return sorted(self._tools)

    def enabled(self) -> list[str]:
        """Enabled tool names (all when nothing is explicitly enabled)."""
        if not self._enabled:
            return sorted(self._tools)
        return sorted(self._enabled)

    def is_enabled(self, name: str) -> bool:
        return name in self._tools and (not self._enabled or name in self._enabled)

    def schemas(self) -> list[dict]:
        """Capability schemas for prompt injection (enabled tools only)."""
        return [self._tools[n].schema() for n in self.enabled()]

    def __contains__(self, name: str) -> bool:
        return name in self._tools
