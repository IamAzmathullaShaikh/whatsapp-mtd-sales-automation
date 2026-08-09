"""Shell tool: execute a command, capture stdout/stderr/exit code.

Permission is decided by the policy's command patterns (safe read-only/test
commands vs destructive ones) — see config/permissions.toml.
"""

from __future__ import annotations

import subprocess

from .base import Permission, Tool, ToolResult, require


class RunCommand(Tool):
    name = "shell.run"
    description = "Execute a shell command and capture stdout/stderr/exit code."
    parameters = {
        "command": {"type": "string", "description": "shell command line", "required": True},
        "cwd": {"type": "string", "description": "working directory (workspace-relative)", "required": False},
        "timeout": {"type": "integer", "description": "seconds, default 30", "required": False},
    }
    permission = Permission.APPROVAL  # narrowed by policy patterns

    def __init__(self, ws, default_timeout: int = 60):
        self.ws = ws
        self.timeout = default_timeout

    def dry_run(self, args):
        return f"[dry-run] shell.run would execute: {args.get('command')}"

    def run(self, args):
        def fn(args):
            missing = require(args, "command")
            if missing:
                return ToolResult(tool=self.name, ok=False, error=f"missing args: {missing}")
            cwd = self.ws.resolve(args.get("cwd", ".")) if args.get("cwd") else self.ws.root
            timeout = float(args.get("timeout") or self.timeout)
            try:
                proc = subprocess.run(
                    args["command"], shell=True, cwd=cwd, capture_output=True,
                    text=True, timeout=timeout)
            except subprocess.TimeoutExpired:
                return ToolResult(tool=self.name, ok=False,
                                  error=f"command timed out after {timeout}s")
            stdout = (proc.stdout or "").strip()
            stderr = (proc.stderr or "").strip()
            if proc.returncode != 0:
                return ToolResult(
                    tool=self.name, ok=False,
                    error=f"exit code {proc.returncode}",
                    output="\n".join(x for x in (stdout, stderr) if x))
            return "\n".join(x for x in (stdout, stderr) if x) or "(no output)"
        return self._execute(fn, args)
