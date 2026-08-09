"""M4 — planner: tolerant tool-call parsing."""

from azmath.core.agent import parse_tool_call


def test_bare_json():
    assert parse_tool_call('{"tool": "fs.list", "args": {"path": "."}}') == {
        "tool": "fs.list", "args": {"path": "."}}


def test_prose_wrapped_json():
    text = 'The listing: {"tool": "fs.read", "args": {"path": "a.py"}} — done.'
    assert parse_tool_call(text)["tool"] == "fs.read"


def test_fenced_json():
    text = '```json\n{"tool": "shell.run", "args": {"command": "ls"}}\n```'
    assert parse_tool_call(text)["tool"] == "shell.run"


def test_plain_answer_is_not_a_call():
    assert parse_tool_call("Just a plain answer with {braces} but no tool.") is None
    assert parse_tool_call("Hello there.") is None


def test_missing_args_defaults_empty():
    assert parse_tool_call('{"tool": "fs.list"}') == {"tool": "fs.list", "args": {}}


def test_accepts_arguments_spelling():
    # qwen3:4b emitted {"arguments": ...} in live testing — must parse.
    assert parse_tool_call('{"tool": "fs.list", "arguments": {"path": "."}}') == {
        "tool": "fs.list", "args": {"path": "."}}


def test_invalid_json_ignored():
    assert parse_tool_call('{"tool": broken') is None
    assert parse_tool_call("") is None
