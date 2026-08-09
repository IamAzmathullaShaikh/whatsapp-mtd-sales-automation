"""Controlled Python execution: the code runs in a subprocess with a timeout
and captured output. Approval-gated (executing arbitrary code is powerful)."""

from __future__ import annotations

import subprocess
import tempfile
import textwrap
from pathlib import Path

from .base import Permission, Tool, ToolResult, require


class ExecPython(Tool):
    name = "python.exec"
    description = "Execute a short Python program and return its stdout/stderr."
    parameters = {
        "code": {"type": "string", "description": "Python source code", "required": True},
        "cwd": {"type": "string", "description": "workspace-relative cwd, default '.'", "required": False},
    }
    permission = Permission.APPROVAL
    timeout = 60.0

    def __init__(self, ws, default_timeout: float = 60.0):
        self.ws = ws
        self.timeout = default_timeout

    def dry_run(self, args):
        n = len(str(args.get("code", "")))
        return f"[dry-run] python.exec would run {n} chars of Python in a subprocess"

    def run(self, args):
        def fn(a):
            missing = require(a, "code")
            if missing:
                return ToolResult(tool=self.name, ok=False, error=f"missing args: {missing}")
            code = textwrap.dedent(a["code"]).strip()
            cwd = self.ws.resolve(a.get("cwd", ".")) if a.get("cwd") else self.ws.root
            with tempfile.NamedTemporaryFile(
                    "w", suffix=".py", prefix="azmath_", delete=False, encoding="utf-8") as fh:
                fh.write(code)
                script = fh.name
            try:
                proc = subprocess.run(
                    ["python3", script], cwd=cwd, capture_output=True, text=True,
                    timeout=self.timeout)
            except subprocess.TimeoutExpired:
                return ToolResult(tool=self.name, ok=False,
                                  error=f"python.exec timed out after {self.timeout}s")
            finally:
                Path(script).unlink(missing_ok=True)
            stdout, stderr = (proc.stdout or "").strip(), (proc.stderr or "").strip()
            if proc.returncode != 0:
                return ToolResult(tool=self.name, ok=False,
                                  error=f"exit code {proc.returncode}\n{stderr[:4000]}",
                                  output=stdout[:4000])
            return "\n".join(x for x in (stdout, stderr) if x) or "(no output)"
        return self._execute(fn, args)
