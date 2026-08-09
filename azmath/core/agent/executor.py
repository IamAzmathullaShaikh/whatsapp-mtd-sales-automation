"""Executor: run one tool call through policy + approval and return the result."""

from __future__ import annotations

from azmath.tools import ApprovalHandler, Permission, Policy, ToolResult, decide


class ToolExecutor:
    def __init__(self, registry, policy: Policy, approver: ApprovalHandler):
        self.registry = registry
        self.policy = policy
        self.approver = approver

    def execute(self, tool_name: str, args: dict, *, dry_run: bool = False) -> dict:
        """Run one call. Returns {result, allowed, reason, level}."""
        if tool_name not in self.registry:
            return {
                "result": ToolResult(tool=tool_name, ok=False,
                                     error=f"unknown tool: {tool_name}"),
                "allowed": False,
                "reason": f"unknown tool {tool_name!r}",
                "level": Permission.DENIED,
            }
        tool = self.registry.get(tool_name)
        if not self.registry.is_enabled(tool_name):
            return {
                "result": ToolResult(tool=tool_name, ok=False,
                                     error=f"tool disabled: {tool_name}"),
                "allowed": False,
                "reason": f"tool {tool_name!r} is disabled",
                "level": Permission.DENIED,
            }
        allowed, reason, level = decide(tool, args, self.policy, self.approver,
                                        dry_run=dry_run)
        if not allowed:
            result = ToolResult(tool=tool_name, ok=False,
                                error=f"not permitted: {reason}",
                                permission=level, dry_run=dry_run)
            return {"result": result, "allowed": False, "reason": reason, "level": level}
        try:
            result = tool.dry_run(args) if dry_run else tool.run(args)
        except Exception as exc:  # a tool must never crash the loop
            result = ToolResult(tool=tool.name, ok=False,
                                error=f"{type(exc).__name__}: {exc}")
        if not isinstance(result, ToolResult):
            result = ToolResult(tool=tool.name, ok=True, output=str(result),
                                dry_run=dry_run)
        result.permission = level
        result.dry_run = dry_run
        return {"result": result, "allowed": True, "reason": reason, "level": level}
