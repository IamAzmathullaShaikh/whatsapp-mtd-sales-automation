"""M4 — the agent loop, driven by a stub provider.

Acceptance coverage from the master prompt:
  A. "hello"            -> direct answer, ZERO tool calls
  B. inspect directory  -> filesystem tool actually used
  I. destructive op     -> permission system blocks it
plus termination (iteration cap), dry-run, and unknown-tool handling.
"""

import pytest

from azmath.core.agent import AgentLoop
from azmath.tools import ApprovalHandler, Policy, ToolRegistry, build_default_registry
from azmath.tools.fs import Workspace


class StubProvider:
    """Scripted responses; emits a tool call JSON or a plain answer."""

    name = "stub"

    def __init__(self, *responses, model="stub"):
        self.responses = list(responses)
        self.model = model
        self.generations = 0

    def generate(self, prompt, **kwargs):
        self.generations += 1
        return self.responses.pop(0) if self.responses else "stub final answer"

    def health(self):
        return True

    def metadata(self):
        return {"provider": "stub"}


def _loop(tmp_path, provider, *, mode="allow", dry_run=False, max_iterations=8,
          verify=True):
    ws = Workspace(tmp_path)
    settings = type("S", (), {"loop": {"verify": verify, "max_iterations": 8,
                                       "max_obs_chars": 8000},
                              "tools_cfg": {"enabled": []}})
    reg = build_default_registry(settings, ws)
    policy = Policy({})
    approver = ApprovalHandler(mode)
    return AgentLoop(provider, reg, policy, approver, settings=settings), ws


def test_hello_no_tool_calls(tmp_path):
    """Acceptance A: simple request -> direct answer, no analysis/tool calls."""
    provider = StubProvider("Hello! How can I help?")
    loop, _ = _loop(tmp_path, provider)
    result = loop.run("hello")
    assert result.ok and result.status == "completed"
    assert "Hello" in result.response
    assert result.tool_calls == []
    assert result.iterations == 0
    assert provider.generations == 1


def test_inspect_directory_uses_fs_tool(tmp_path):
    """Acceptance B: the model picks the filesystem tool, and it really runs."""
    (tmp_path / "alpha.py").write_text("x = 1", encoding="utf-8")
    provider = StubProvider(
        '{"tool": "fs.list", "args": {"path": "."}}',
        "I found alpha.py in the directory.")
    loop, ws = _loop(tmp_path, provider)
    result = loop.run("inspect this directory")
    assert result.ok
    assert result.tool_calls[0]["tool"] == "fs.list"
    assert result.tool_calls[0]["ok"] is True
    assert "alpha.py" in result.tool_calls[0]["output"]
    assert "alpha.py" in result.response
    assert result.iterations == 1
    assert provider.generations == 2


def test_destructive_op_blocked_and_file_survives(tmp_path):
    """Acceptance I: destructive operation is blocked, not silently executed."""
    victim = tmp_path / "important.txt"
    victim.write_text("keep me", encoding="utf-8")
    provider = StubProvider(
        '{"tool": "fs.delete", "args": {"path": "important.txt"}}',
        "I cannot delete important.txt: permission not granted.")
    loop, _ = _loop(tmp_path, provider, mode="deny")
    result = loop.run("delete important.txt")
    assert victim.exists()  # untouched
    call = result.tool_calls[0]
    assert call["ok"] is False
    assert call["level"] == "approval"
    assert "not permitted" in call["error"]
    # the model was told the truth and adapted
    assert "cannot delete" in result.response
    # verifier flags the denial honestly
    assert result.verification is not None
    assert not result.verification.ok
    assert any("not permitted" in i for i in result.verification.issues)


def test_unknown_tool_is_denied(tmp_path):
    provider = StubProvider('{"tool": "no.such.tool", "args": {}}', "done")
    loop, _ = _loop(tmp_path, provider)
    result = loop.run("whatever")
    assert not result.tool_calls[0]["ok"]
    assert "unknown tool" in result.tool_calls[0]["error"]


def test_iteration_cap_terminates(tmp_path):
    always_tool = StubProvider()
    always_tool.responses = None  # force default below

    class AlwaysTool(StubProvider):
        def generate(self, prompt, **kwargs):
            return '{"tool": "fs.list", "args": {"path": "."}}'

    loop, _ = _loop(tmp_path, AlwaysTool(), max_iterations=3)
    result = loop.run("keep going", max_iterations=3)
    assert result.status == "tool_limit"
    assert result.iterations == 3


def test_model_failure_reported(tmp_path):
    class Broken(StubProvider):
        def generate(self, prompt, **kwargs):
            raise RuntimeError("provider exploded")

    loop, _ = _loop(tmp_path, Broken())
    result = loop.run("do a thing")
    assert result.status == "error"
    assert "provider exploded" in result.error


def test_empty_generation_is_error_not_completion(tmp_path):
    """An empty model response must never be reported as a completed run."""
    class Empty(StubProvider):
        def generate(self, prompt, **kwargs):
            return ""

    loop, _ = _loop(tmp_path, Empty())
    result = loop.run("do a thing")
    assert result.status == "error"
    assert "empty response" in result.error


def test_dry_run_does_not_write(tmp_path):
    provider = StubProvider(
        '{"tool": "fs.write", "args": {"path": "new.txt", "content": "hi"}}',
        "wrote new.txt")
    loop, _ = _loop(tmp_path, provider, dry_run=True, mode="deny")
    result = loop.run("create new.txt", dry_run=True)
    assert result.ok
    assert result.tool_calls[0]["dry_run"] is True
    assert not (tmp_path / "new.txt").exists()
    # denied approval mode does not block dry-runs (they are side-effect free)
    assert result.tool_calls[0]["ok"] is True


def test_system_prompt_keeps_reasoning_hidden(tmp_path):
    from azmath.core.agent import build_system_prompt
    system = build_system_prompt("You are Azmath Agent.")
    assert "untrusted" in system.lower()
    assert "never claim" in system.lower()


def test_progress_reports_actions(tmp_path):
    lines = []
    provider = StubProvider('{"tool": "fs.list", "args": {}}', "done")
    loop, _ = _loop(tmp_path, provider)
    loop.progress = lines.append
    loop.run("go")
    joined = " ".join(lines).lower()
    assert "tool: fs.list" in joined
    assert "thinking" not in joined
