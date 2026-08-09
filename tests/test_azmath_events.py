"""M6 — observability: event bus, JSONL trace, secret redaction."""

from azmath.core.events import EventBus, redact


def test_redact_secret_shaped_values():
    assert "ghp_" not in redact("token ghp_ABCDEFGHIJKLMNOPQRSTUVWX1234567890 end")
    assert "hunter2" not in redact("password='hunter2'")
    assert redact("plain text no secrets") == "plain text no secrets"


def test_emit_notifies_handlers():
    bus = EventBus()
    seen = []
    bus.subscribe(lambda e: seen.append(e))
    bus.emit("tool.called", task_id="t1", tool="fs.list", ok=True)
    assert seen[0]["type"] == "tool.called"
    assert seen[0]["tool"] == "fs.list"
    assert seen[0]["task_id"] == "t1"


def test_emit_writes_jsonl(tmp_path):
    path = tmp_path / "events.jsonl"
    bus = EventBus(str(path), session_id="sess1")
    bus.emit("task.finished", task_id="t9", status="completed")
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    import json
    event = json.loads(lines[0])
    assert event["session_id"] == "sess1" and event["status"] == "completed"


def test_content_field_is_redacted_in_event(tmp_path):
    path = tmp_path / "events.jsonl"
    bus = EventBus(str(path))
    bus.emit("tool.called", tool="fs.write", content="ghp_ABCDEFGHIJKLMNOPQRSTUVWX1234567890")
    import json
    event = json.loads(path.read_text(encoding="utf-8"))
    assert "ghp_" not in event["content"]
