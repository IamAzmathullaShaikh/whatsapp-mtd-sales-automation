"""Observer: records the execution trace fed back to the model each iteration."""

from __future__ import annotations

import time
import uuid


class Observer:
    """Owns the running trace: observations (for the prompt) + structured call
    records (for the verifier and observability)."""

    def __init__(self):
        self.observations: list[str] = []
        self.calls: list[dict] = []

    def record(self, *, tool: str, args: dict, ok: bool, output: str = "",
               error: str | None = None, duration: float = 0.0,
               level: str = "safe", reason: str = "", dry_run: bool = False) -> str:
        """Append an observation and a structured record; returns the observation."""
        obs = (
            f"tool={tool} ok={ok}"
            + (" dry-run" if dry_run else "")
            + (f" level={level}" if level != "safe" else "")
            + f" duration={duration:.2f}s"
            + (f"\n{output}" if output else "")
            + (f"\nERROR: {error}" if error else "")
        )
        self.observations.append(obs)
        self.calls.append({
            "id": str(uuid.uuid4())[:8],
            "tool": tool,
            "args": args,
            "ok": bool(ok),
            "output": (output or "")[:2000],
            "error": error,
            "duration": round(duration, 3),
            "level": level,
            "reason": reason,
            "dry_run": dry_run,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        })
        return obs

    def last(self) -> dict | None:
        return self.calls[-1] if self.calls else None

    def failed_calls(self) -> list[dict]:
        return [c for c in self.calls if not c["ok"]]

    def has_tool_use(self) -> bool:
        return bool(self.calls)
