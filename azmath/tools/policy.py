"""Permission policy + approval handling.

Levels come from each tool's declared permission, overridden by
config/permissions.toml ([tools] map and [shell.patterns]). The ApprovalHandler
turns a level + args into a decision: safe runs, approval asks (interactive)
or denies (non-interactive), denied never runs.
"""

from __future__ import annotations

import re
import sys

from .base import Permission, Tool


class Policy:
    def __init__(self, permissions_config: dict):
        self._config = permissions_config
        self._tool_overrides = {
            k: Permission(v) for k, v in permissions_config.get("tools", {}).items()
        }
        self._shell_patterns = [
            (re.compile(p), Permission(level))
            for p, level in permissions_config.get("shell", {}).get("patterns", {}).items()
        ]

    def level_for(self, tool: Tool, args: dict | None = None) -> Permission:
        """Resolve the effective permission for one call."""
        if tool.name == "shell" and args and args.get("command"):
            for pattern, level in self._shell_patterns:
                if pattern.match(str(args["command"]).strip()):
                    return level
        return self._tool_overrides.get(tool.name, tool.permission)


class ApprovalHandler:
    """Decides whether an approval-level call may proceed.

    mode: "allow" (never ask) | "deny" (never approve) | "prompt" (ask when
    interactive, deny otherwise). ``input_fn`` is injectable for tests.
    """

    def __init__(self, mode: str = "prompt", input_fn=None):
        self.mode = mode
        self._input = input_fn

    def request(self, tool_name: str, description: str) -> bool:
        if self.mode == "allow":
            return True
        if self.mode == "deny":
            return False
        fn = self._input or self._prompt
        try:
            answer = fn(f"APPROVE {tool_name}? {description} [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return False
        return answer in ("y", "yes")

    @staticmethod
    def _prompt(text: str) -> str:
        if not sys.stdin.isatty():
            return "n"  # non-interactive: default deny
        return input(text)


def decide(tool: Tool, args: dict, policy: Policy, approver: ApprovalHandler,
           *, dry_run: bool = False) -> tuple[bool, str, Permission]:
    """Return (allowed, reason, level) for one call, applying dry-run first."""
    level = policy.level_for(tool, args)
    if dry_run:
        return True, f"dry-run requested for {tool.name} (level {level.value})", level
    if level is Permission.DENIED:
        return False, f"not permitted: {tool.name} is denied by policy", level
    if level is Permission.SAFE:
        return True, "safe: runs without approval", level
    # approval
    allowed = approver.request(tool.name, tool.description)
    reason = ("approved by user" if allowed else
              "not permitted: approval required and not granted")
    return allowed, reason, level
