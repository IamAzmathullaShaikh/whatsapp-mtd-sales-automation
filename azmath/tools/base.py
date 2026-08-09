"""Tool abstraction.

A Tool is a named, described, permission-classified capability. Tools are
discovered through the ToolRegistry and chosen by the model at runtime from
their serialized schemas — the loop contains no task-specific branches.

Permission levels: SAFE runs without approval; APPROVAL requires explicit user
consent (denied in non-interactive runs); DENIED never runs.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum


class Permission(str, Enum):
    SAFE = "safe"
    APPROVAL = "approval"
    DENIED = "denied"

    def __str__(self):
        return self.value


@dataclass
class ToolResult:
    """Outcome of one tool execution, fed back to the model as an observation."""

    tool: str
    ok: bool
    output: str = ""
    error: str | None = None
    permission: Permission = Permission.SAFE
    duration: float = 0.0
    dry_run: bool = False

    def observation(self, max_chars: int = 8000) -> str:
        """The text the model sees. Never includes arguments beyond output."""
        head = f"tool={self.tool} ok={self.ok}"
        if self.dry_run:
            head += " (dry-run)"
        body = self.output if self.ok else (self.error or "no output")
        body = (body or "")[:max_chars]
        return f"{head}\n{body}"

    def __bool__(self):
        return self.ok


class Tool(ABC):
    """Base class for every capability. Subclasses implement run()."""

    #: unique registry name, e.g. "fs.read"
    name: str = ""
    #: one-line description shown to the model
    description: str = ""
    #: param schema: {name: {"type": str, "description": str, "required": bool}}
    parameters: dict = {}
    #: default permission level (config/permissions.toml may override)
    permission: Permission = Permission.SAFE
    #: seconds; the executor enforces this
    timeout: float = 30.0

    def schema(self) -> dict:
        """Serialized capability metadata injected into the system prompt."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "permission": self.permission.value,
        }

    def dry_run(self, args: dict) -> str:
        """Describe what run() would do, without doing it."""
        return f"[dry-run] {self.name} would run with args {args}"

    @abstractmethod
    def run(self, args: dict) -> ToolResult:
        """Execute the tool. Must never raise; failures become ToolResult(ok=False)."""

    # -- helper for subclasses -----------------------------------------------
    def _execute(self, fn, args: dict) -> ToolResult:
        started = time.monotonic()
        try:
            result = fn(args)
            if isinstance(result, ToolResult):
                result.duration = time.monotonic() - started
                return result
            return ToolResult(tool=self.name, ok=True, output=str(result),
                              duration=time.monotonic() - started)
        except Exception as exc:  # tools must not crash the loop
            return ToolResult(tool=self.name, ok=False, error=str(exc),
                              duration=time.monotonic() - started)


def require(args: dict, *keys: str) -> list[str]:
    """Return the list of missing required argument names."""
    return [k for k in keys if not args.get(k)]
