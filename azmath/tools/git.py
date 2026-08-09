"""Git tools — thin wrappers around the system git binary.

Inspection commands are safe; anything that mutates history, pushes, or clones
requires approval (config/permissions.toml can tighten this further).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from .base import Permission, Tool, ToolResult, require


def _git(args: list[str], cwd: Path, timeout: float = 60.0):
    proc = subprocess.run(["git", *args], cwd=cwd, capture_output=True,
                          text=True, timeout=timeout)
    if proc.returncode != 0:
        return ToolResult(tool="git", ok=False,
                          error=(proc.stderr or proc.stdout or "").strip()[:2000])
    return "\n".join(x for x in (proc.stdout, proc.stderr) if x.strip()).strip() or "(clean)"


class _GitTool(Tool):
    def __init__(self, ws):
        self.ws = ws

    def _repo(self, args):
        return self.ws.resolve(args.get("repo", "."))


class Status(_GitTool):
    name = "git.status"
    description = "Working-tree status (changed/untracked files)."
    parameters = {"repo": {"type": "string", "description": "repo dir, default '.'", "required": False}}
    permission = Permission.SAFE

    def run(self, args):
        return self._execute(lambda a: _git(["status", "--short"], self._repo(a)), args)


class Log(_GitTool):
    name = "git.log"
    description = "Recent commit history (one line per commit)."
    parameters = {
        "repo": {"type": "string", "description": "repo dir", "required": False},
        "n": {"type": "integer", "description": "number of commits, default 10", "required": False},
    }
    permission = Permission.SAFE

    def run(self, args):
        n = int(args.get("n") or 10)
        return self._execute(
            lambda a: _git(["log", f"-{n}", "--oneline"], self._repo(a)), args)


class Diff(_GitTool):
    name = "git.diff"
    description = "Uncommitted changes, or diff against a ref when 'ref' is given."
    parameters = {
        "repo": {"type": "string", "description": "repo dir", "required": False},
        "ref": {"type": "string", "description": "e.g. HEAD~1, optional", "required": False},
    }
    permission = Permission.SAFE

    def run(self, args):
        ref = args.get("ref")
        argv = ["diff", ref] if ref else ["diff"]
        return self._execute(lambda a: _git(argv, self._repo(a), timeout=90), args)


class Branch(_GitTool):
    name = "git.branch"
    description = "List branches and the current branch."
    parameters = {"repo": {"type": "string", "description": "repo dir", "required": False}}
    permission = Permission.SAFE

    def run(self, args):
        return self._execute(lambda a: _git(["branch", "-a"], self._repo(a)), args)


class Clone(_GitTool):
    name = "git.clone"
    description = "Clone a repository into a workspace directory."
    parameters = {
        "url": {"type": "string", "description": "repository URL", "required": True},
        "dest": {"type": "string", "description": "destination dir (workspace-relative)", "required": True},
    }
    permission = Permission.APPROVAL

    def dry_run(self, args):
        return f"[dry-run] git.clone would clone {args.get('url')} into {args.get('dest')}"

    def run(self, args):
        def fn(a):
            missing = require(a, "url", "dest")
            if missing:
                return ToolResult(tool=self.name, ok=False, error=f"missing args: {missing}")
            dest = self.ws.resolve(a["dest"])
            dest.parent.mkdir(parents=True, exist_ok=True)
            return _git(["clone", a["url"], str(dest)], self.ws.root, timeout=300)
        return self._execute(fn, args)


class Checkout(_GitTool):
    name = "git.checkout"
    description = "Switch branch or checkout a ref (can discard local edits)."
    parameters = {
        "repo": {"type": "string", "description": "repo dir", "required": False},
        "ref": {"type": "string", "description": "branch/tag/commit to check out", "required": True},
    }
    permission = Permission.APPROVAL

    def run(self, args):
        return self._execute(
            lambda a: _git(["checkout", a["ref"]], self._repo(a)), args)


class Push(_GitTool):
    name = "git.push"
    description = "Push local commits to the remote. Irreversible for the remote."
    parameters = {
        "repo": {"type": "string", "description": "repo dir", "required": False},
        "remote": {"type": "string", "description": "remote name, default origin", "required": False},
        "branch": {"type": "string", "description": "branch, default current", "required": False},
    }
    permission = Permission.APPROVAL

    def dry_run(self, args):
        return f"[dry-run] git.push would push {args.get('branch', 'current')} to {args.get('remote', 'origin')}"

    def run(self, args):
        def fn(a):
            argv = ["push"]
            if a.get("remote"):
                argv.append(a["remote"])
            if a.get("branch"):
                argv.append(a["branch"])
            return _git(argv, self._repo(a))
        return self._execute(fn, args)


def register_git(registry, ws) -> None:
    for tool in (Status(ws), Log(ws), Diff(ws), Branch(ws), Clone(ws),
                 Checkout(ws), Push(ws)):
        registry.register(tool)
