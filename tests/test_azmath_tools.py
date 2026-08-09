"""M3 — tool implementations against real temp workspaces."""

import subprocess

import pytest

from azmath.tools import Permission, Tool, ToolRegistry
from azmath.tools import build_default_registry
from azmath.tools.fs import Workspace
from azmath.tools.web import StdlibWebProvider


class FakeWebProvider:
    def search(self, query, max_results):
        return [{"title": "Fake Result", "url": "https://example.com"}]

    def fetch(self, url, max_chars):
        return "extracted text from " + url


def _ws(tmp_path):
    return Workspace(tmp_path)


def test_workspace_blocks_escape(tmp_path):
    ws = _ws(tmp_path)
    with pytest.raises(ValueError):
        ws.resolve("../outside")
    assert ws.resolve("sub/dir.txt").parent.name == "sub"


def test_fs_list_read_write(tmp_path):
    ws = _ws(tmp_path)
    (tmp_path / "a.txt").write_text("hello world", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    listing = ws_list = __import__("azmath.tools.fs", fromlist=["ListDir"]).ListDir(ws)
    res = listing.run({"path": "."})
    assert res.ok and "a.txt" in res.output and "sub" in res.output
    reader = __import__("azmath.tools.fs", fromlist=["ReadFile"]).ReadFile(ws)
    assert reader.run({"path": "a.txt"}).output == "hello world"
    writer = __import__("azmath.tools.fs", fromlist=["WriteFile"]).WriteFile(ws)
    assert writer.run({"path": "b.txt", "content": "x" * 100}).ok
    assert (tmp_path / "b.txt").read_text() == "x" * 100


def test_fs_write_rejects_missing_args(tmp_path):
    writer = __import__("azmath.tools.fs", fromlist=["WriteFile"]).WriteFile(_ws(tmp_path))
    res = writer.run({"path": "x.txt"})
    assert not res.ok and "missing" in res.error


def test_fs_grep_and_search(tmp_path):
    ws = _ws(tmp_path)
    (tmp_path / "mod.py").write_text("def foo():\n    pass\n", encoding="utf-8")
    grep = __import__("azmath.tools.fs", fromlist=["Grep"]).Grep(ws)
    res = grep.run({"pattern": "def foo", "glob": "*.py"})
    assert res.ok and "mod.py:1" in res.output
    search = __import__("azmath.tools.fs", fromlist=["SearchFiles"]).SearchFiles(ws)
    assert search.run({"pattern": "*.py"}).ok


def test_fs_delete_requires_approval_and_works(tmp_path):
    ws = _ws(tmp_path)
    (tmp_path / "junk.txt").write_text("junk", encoding="utf-8")
    deleter = __import__("azmath.tools.fs", fromlist=["Delete"]).Delete(ws)
    assert deleter.permission is Permission.APPROVAL
    assert deleter.run({"path": "junk.txt"}).ok
    assert not (tmp_path / "junk.txt").exists()


def test_shell_run_capture_and_timeout(tmp_path):
    shell = __import__("azmath.tools.shell", fromlist=["RunCommand"]).RunCommand(Workspace(tmp_path), 5)
    res = shell.run({"command": "echo hello; echo err >&2"})
    assert res.ok and "hello" in res.output and "err" in res.output
    bad = shell.run({"command": "exit 3"})
    assert not bad.ok and "3" in bad.error
    timed = shell.run({"command": "sleep 10", "timeout": 1})
    assert not timed.ok and "timed out" in timed.error


def test_git_tools_on_real_repo(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "T"], check=True)
    (tmp_path / "f.txt").write_text("x", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "init"], check=True)
    ws = Workspace(tmp_path)
    status = __import__("azmath.tools.git", fromlist=["Status"]).Status(ws)
    assert status.run({}).ok
    log = __import__("azmath.tools.git", fromlist=["Log"]).Log(ws)
    assert "init" in log.run({}).output
    branch = __import__("azmath.tools.git", fromlist=["Branch"]).Branch(ws)
    assert branch.run({}).ok


def test_web_search_and_fetch_with_fake_provider():
    from azmath.tools import web
    assert web.Search(FakeWebProvider()).run({"query": "x"}).ok
    assert "extracted" in web.Fetch(FakeWebProvider()).run({"url": "https://e.com"}).output


def test_web_fetch_rejects_bad_scheme():
    from azmath.tools import web
    res = web.Fetch(FakeWebProvider()).run({"url": "file:///etc/passwd"})
    assert not res.ok and "scheme" in res.error


def test_web_provider_unavailable_is_honest():
    class Broken:
        def search(self, q, n):
            raise ConnectionError("no network")
        def fetch(self, u, n):
            raise ConnectionError("no network")
    from azmath.tools import web
    res = web.Search(Broken()).run({"query": "x"})
    assert not res.ok and "capability unavailable" in res.error


def test_python_exec(tmp_path):
    ws = Workspace(tmp_path)
    execer = __import__("azmath.tools.python_exec", fromlist=["ExecPython"]).ExecPython(ws)
    res = execer.run({"code": "print(6 * 7)"})
    assert res.ok and "42" in res.output
    bad = execer.run({"code": "raise ValueError('boom')"})
    assert not bad.ok and "boom" in bad.error


def test_default_registry_builds_and_enables(tmp_path):
    settings = type("S", (), {"tools_cfg": {"enabled": ["fs", "shell"]},
                              "loop": {"tool_timeout": 30}})()
    reg = build_default_registry(settings, Workspace(tmp_path), FakeWebProvider())
    assert "fs.list" in reg and "shell.run" in reg and "web.fetch" in reg
    assert reg.is_enabled("fs.list") and reg.is_enabled("shell.run")
    assert not reg.is_enabled("web.fetch")
    assert reg.is_enabled("python.exec") is False
    assert len(reg.schemas()) > 0


def test_tool_run_never_raises(tmp_path):
    """A raising tool is caught by the executor, never the loop."""
    from azmath.core.agent.executor import ToolExecutor
    from azmath.tools import ApprovalHandler, Policy

    class Boom(Tool):
        name = "boom"
        description = "raises"
        permission = Permission.SAFE

        def run(self, args):
            raise RuntimeError("kaboom")

    reg = ToolRegistry()
    reg.register(Boom())
    executor = ToolExecutor(reg, Policy({}), ApprovalHandler("allow"))
    outcome = executor.execute("boom", {})
    assert outcome["result"].ok is False
    assert "kaboom" in outcome["result"].error
