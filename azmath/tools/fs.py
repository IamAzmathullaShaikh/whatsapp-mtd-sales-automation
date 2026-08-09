"""Filesystem tools. All paths resolve inside a workspace root; escapes are
rejected (a security boundary, not a convenience)."""

from __future__ import annotations

import fnmatch
import os
import re
import shutil
import stat as stat_mod
import time
from pathlib import Path

from .base import Permission, Tool, ToolResult, require


class Workspace:
    """Resolves tool paths relative to a root, blocking ``..`` escapes."""

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()

    def resolve(self, path: str) -> Path:
        p = (self.root / str(path)).resolve()
        if not p.is_relative_to(self.root):
            raise ValueError(f"path escapes workspace root {self.root}: {path!r}")
        return p


class ListDir(Tool):
    name = "fs.list"
    description = "List entries of a directory (name, type, size)."
    parameters = {"path": {"type": "string", "description": "directory, default '.'", "required": False}}
    permission = Permission.SAFE

    def __init__(self, ws: Workspace):
        self.ws = ws

    def run(self, args):
        def fn(args):
            d = self.ws.resolve(args.get("path", "."))
            if not d.is_dir():
                return ToolResult(tool=self.name, ok=False, error=f"not a directory: {d}")
            lines = []
            for entry in sorted(d.iterdir(), key=lambda e: e.name.lower()):
                kind = "dir " if entry.is_dir() else "file"
                size = "" if entry.is_dir() else f" {entry.stat().st_size:>10d} B"
                lines.append(f"{kind} {entry.name}{size}")
            return "\n".join(lines) or "(empty)"
        return self._execute(fn, args)


class ReadFile(Tool):
    name = "fs.read"
    description = "Read a file's text content."
    parameters = {
        "path": {"type": "string", "description": "file path", "required": True},
        "max_chars": {"type": "integer", "description": "cap on returned characters", "required": False},
    }
    permission = Permission.SAFE

    def __init__(self, ws: Workspace):
        self.ws = ws

    def run(self, args):
        def fn(args):
            p = self.ws.resolve(args["path"])
            if not p.is_file():
                return ToolResult(tool=self.name, ok=False, error=f"not a file: {p}")
            max_chars = int(args.get("max_chars") or 20000)
            text = p.read_text(encoding="utf-8", errors="replace")
            if len(text) > max_chars:
                text = text[:max_chars] + f"\n... [truncated at {max_chars} chars]"
            return text
        return self._execute(fn, args)


class WriteFile(Tool):
    name = "fs.write"
    description = "Create or overwrite a file with text content."
    parameters = {
        "path": {"type": "string", "description": "file path", "required": True},
        "content": {"type": "string", "description": "full text to write", "required": True},
    }
    permission = Permission.APPROVAL

    def __init__(self, ws: Workspace):
        self.ws = ws

    def dry_run(self, args):
        return f"[dry-run] fs.write would write {len(str(args.get('content','')))} chars to {args.get('path')}"

    def run(self, args):
        def fn(args):
            missing = require(args, "path", "content")
            if missing:
                return ToolResult(tool=self.name, ok=False, error=f"missing args: {missing}")
            p = self.ws.resolve(args["path"])
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(args["content"], encoding="utf-8")
            return f"wrote {len(args['content'])} chars to {p}"
        return self._execute(fn, args)


class Mkdir(Tool):
    name = "fs.mkdir"
    description = "Create a directory (and parents)."
    parameters = {"path": {"type": "string", "description": "directory path", "required": True}}
    permission = Permission.APPROVAL

    def __init__(self, ws: Workspace):
        self.ws = ws

    def run(self, args):
        def fn(args):
            p = self.ws.resolve(args["path"])
            p.mkdir(parents=True, exist_ok=True)
            return f"created {p}"
        return self._execute(fn, args)


class Move(Tool):
    name = "fs.move"
    description = "Move or rename a file/directory."
    parameters = {
        "src": {"type": "string", "description": "source path", "required": True},
        "dst": {"type": "string", "description": "destination path", "required": True},
    }
    permission = Permission.APPROVAL

    def __init__(self, ws: Workspace):
        self.ws = ws

    def run(self, args):
        def fn(args):
            src, dst = self.ws.resolve(args["src"]), self.ws.resolve(args["dst"])
            if not src.exists():
                return ToolResult(tool=self.name, ok=False, error=f"missing source: {src}")
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            return f"moved {src} -> {dst}"
        return self._execute(fn, args)


class Copy(Tool):
    name = "fs.copy"
    description = "Copy a file or directory tree."
    parameters = {
        "src": {"type": "string", "description": "source path", "required": True},
        "dst": {"type": "string", "description": "destination path", "required": True},
    }
    permission = Permission.APPROVAL

    def __init__(self, ws: Workspace):
        self.ws = ws

    def run(self, args):
        def fn(args):
            src, dst = self.ws.resolve(args["src"]), self.ws.resolve(args["dst"])
            if not src.exists():
                return ToolResult(tool=self.name, ok=False, error=f"missing source: {src}")
            if src.is_dir():
                shutil.copytree(src, dst)
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
            return f"copied {src} -> {dst}"
        return self._execute(fn, args)


class Delete(Tool):
    name = "fs.delete"
    description = "Delete a file or empty directory tree. Irreversible."
    parameters = {"path": {"type": "string", "description": "path to delete", "required": True}}
    permission = Permission.APPROVAL

    def __init__(self, ws: Workspace):
        self.ws = ws

    def dry_run(self, args):
        return f"[dry-run] fs.delete would remove {args.get('path')}"

    def run(self, args):
        def fn(args):
            p = self.ws.resolve(args["path"])
            if not p.exists():
                return ToolResult(tool=self.name, ok=False, error=f"missing: {p}")
            if p.is_dir() and any(p.iterdir()):
                return ToolResult(tool=self.name, ok=False,
                                  error=f"directory not empty: {p} (delete entries first)")
            (shutil.rmtree if p.is_dir() else p.unlink)(p)
            return f"deleted {p}"
        return self._execute(fn, args)


class SearchFiles(Tool):
    name = "fs.search"
    description = "Find files by filename glob pattern (e.g. '*.py')."
    parameters = {
        "pattern": {"type": "string", "description": "glob pattern", "required": True},
        "dir": {"type": "string", "description": "start directory, default '.'", "required": False},
        "max_results": {"type": "integer", "description": "cap, default 100", "required": False},
    }
    permission = Permission.SAFE

    def __init__(self, ws: Workspace):
        self.ws = ws

    def run(self, args):
        def fn(args):
            base = self.ws.resolve(args.get("dir", "."))
            pat = args["pattern"]
            limit = int(args.get("max_results") or 100)
            hits = []
            for root, dirs, files in os.walk(base):
                dirs[:] = [d for d in dirs if not d.startswith((".git", "__pycache__", ".venv"))]
                for name in sorted(files):
                    if fnmatch.fnmatch(name, pat):
                        hits.append(str(Path(root).relative_to(self.ws.root) / name))
                        if len(hits) >= limit:
                            return "\n".join(hits)
            return "\n".join(hits) or "(no matches)"
        return self._execute(fn, args)


class Grep(Tool):
    name = "fs.grep"
    description = "Regex search inside file contents. Returns matching lines."
    parameters = {
        "pattern": {"type": "string", "description": "regular expression", "required": True},
        "dir": {"type": "string", "description": "directory, default '.'", "required": False},
        "glob": {"type": "string", "description": "filename filter, e.g. '*.py'", "required": False},
        "max_results": {"type": "integer", "description": "cap, default 50", "required": False},
    }
    permission = Permission.SAFE

    def __init__(self, ws: Workspace):
        self.ws = ws

    def run(self, args):
        def fn(args):
            base = self.ws.resolve(args.get("dir", "."))
            limit = int(args.get("max_results") or 50)
            try:
                rx = re.compile(args["pattern"])
            except re.error as exc:
                return ToolResult(tool=self.name, ok=False, error=f"bad regex: {exc}")
            glob_pat = args.get("glob")
            out, count = [], 0
            for root, dirs, files in os.walk(base):
                dirs[:] = [d for d in dirs if not d.startswith((".git", "__pycache__", ".venv"))]
                for name in sorted(files):
                    if glob_pat and not fnmatch.fnmatch(name, glob_pat):
                        continue
                    p = Path(root) / name
                    try:
                        for i, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                            if rx.search(line):
                                rel = str(p.relative_to(self.ws.root))
                                out.append(f"{rel}:{i}: {line.strip()[:200]}")
                                count += 1
                                if count >= limit:
                                    return "\n".join(out)
                    except (OSError, UnicodeError):
                        continue
            return "\n".join(out) or "(no matches)"
        return self._execute(fn, args)


class Metadata(Tool):
    name = "fs.metadata"
    description = "Inspect a file/directory: size, type, mtime, permissions."
    parameters = {"path": {"type": "string", "description": "path", "required": True}}
    permission = Permission.SAFE

    def __init__(self, ws: Workspace):
        self.ws = ws

    def run(self, args):
        def fn(args):
            p = self.ws.resolve(args["path"])
            if not p.exists():
                return ToolResult(tool=self.name, ok=False, error=f"missing: {p}")
            st = p.stat()
            return (
                f"path: {p}\n"
                f"type: {'directory' if p.is_dir() else 'file'}\n"
                f"size: {st.st_size} bytes\n"
                f"modified: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(st.st_mtime))}\n"
                f"mode: {oct(stat_mod.S_IMODE(st.st_mode))}"
            )
        return self._execute(fn, args)


def register_fs(registry, ws: Workspace) -> None:
    for tool in (ListDir(ws), ReadFile(ws), WriteFile(ws), Mkdir(ws), Move(ws),
                 Copy(ws), Delete(ws), SearchFiles(ws), Grep(ws), Metadata(ws)):
        registry.register(tool)
