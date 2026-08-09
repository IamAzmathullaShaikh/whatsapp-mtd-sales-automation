"""M5 — memory: session state + JSON long-term store + approval gating."""

from azmath.core.memory import JsonMemory, MemoryStore, SessionMemory


def test_session_memory(tmp_path):
    s = SessionMemory()
    s.set("workspace", "/tmp/x")
    assert s.get("workspace") == "/tmp/x"
    s.clear()
    assert s.get("workspace") is None


def test_json_memory_roundtrip(tmp_path):
    m = JsonMemory(tmp_path / "mem.json")
    m.save("t1", "the pipeline runs pytest", {"kind": "note"})
    m2 = JsonMemory(tmp_path / "mem.json")  # reload from disk
    assert m2.get("t1")["value"] == "the pipeline runs pytest"
    assert m2.search("pytest")[0]["key"] == "t1"
    assert m2.search("unrelated") == []
    assert m2.delete("t1") is True
    assert m2.get("t1") is None


def test_memory_store_gates_persistence(tmp_path):
    store = MemoryStore(JsonMemory(tmp_path / "mem.json"))
    assert store.remember("k", "v", approved=False) is False
    assert store.long_term.get("k") is None
    assert store.remember("k", "v", approved=True) is True
    assert store.long_term.get("k")["value"] == "v"
    assert store.recall("v")[0]["key"] == "k"


def test_memory_store_without_backend():
    store = MemoryStore(None)
    assert store.available is False
    assert store.recall("x") == []
    assert store.remember("k", "v", approved=True) is False
