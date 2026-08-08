"""Tests for the local-agent layer: Ollama client, solver composition, Modelfile."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from agent.modelfile import render_modelfile
from agent.ollama_client import (OllamaUnavailable, build_generate_payload,
                                 ollama_generate, ollama_tags)
from agent.solver import (classify_complexity, compose_chat_prompt,
                          compose_task_prompt, load_skill_excerpts, trim_history)


# ---------------------------------------------------------------------------
# pure composition
# ---------------------------------------------------------------------------

def test_compose_task_prompt_with_skills():
    skills = [{"name": "xlsx", "source": "anthropics/skills",
               "description": "Use when spreadsheet",
               "body_excerpt": "openpyxl rules..."}]
    prompt = compose_task_prompt(skills, "edit my workbook")
    assert "## Selected skills" in prompt
    assert "### skill: xlsx [anthropics/skills]" in prompt
    assert "**When to use:** Use when spreadsheet" in prompt
    assert "openpyxl rules..." in prompt
    assert prompt.rstrip().endswith("edit my workbook")


def test_compose_task_prompt_without_skills():
    prompt = compose_task_prompt([], "hello")
    assert "## Selected skills" not in prompt
    assert prompt.rstrip().endswith("hello")


def test_load_skill_excerpts_truncates(tmp_path):
    norm = tmp_path / "normalized" / "acme__skills" / "big"
    norm.mkdir(parents=True)
    (norm / "body.md").write_text("x" * 5000)
    hits = [{"name": "big", "source": "acme/skills", "description": "desc"}]
    excerpts = load_skill_excerpts(hits, {"normalized": tmp_path / "normalized"}, 100)
    assert excerpts[0]["body_excerpt"] == "x" * 100
    assert excerpts[0]["description"] == "desc"


def test_load_skill_excerpts_skips_missing_body(tmp_path):
    hits = [{"name": "nope", "source": "acme/skills", "description": ""}]
    assert load_skill_excerpts(hits, {"normalized": tmp_path / "normalized"}, 100) == []


# ---------------------------------------------------------------------------
# chat / history
# ---------------------------------------------------------------------------

def test_trim_history_keeps_last_turns():
    history = [(r, f"{r}-{i}") for i in range(10) for r in ("user", "assistant")]
    trimmed = trim_history(history, max_turns=4)
    assert len(trimmed) == 8  # 4 turns * 2 entries
    assert trimmed[0] == ("user", "user-6")
    assert trimmed[-1] == ("assistant", "assistant-9")


def test_trim_history_empty_and_nonpositive():
    assert trim_history(None, 6) == []
    assert trim_history([("user", "x")], 0) == []


def test_compose_chat_prompt_with_history():
    skills = [{"name": "xlsx", "source": "anthropics/skills",
               "description": "Use when spreadsheet", "body_excerpt": "openpyxl rules"}]
    history = [("user", "edit my workbook"), ("assistant", "sure")]
    prompt = compose_chat_prompt(skills, history, "now add a formula")
    assert "## Conversation so far" in prompt
    assert "user: edit my workbook" in prompt
    assert "assistant: sure" in prompt
    assert "### skill: xlsx [anthropics/skills]" in prompt
    assert prompt.rstrip().endswith("now add a formula")


def test_classify_complexity():
    for simple in ("hello", "Hi there", "thanks for the help", "good morning",
                   "what's up", "who are you", "okay", "hey", "thank you!"):
        assert classify_complexity(simple) == "simple", simple
    for complex_ in ("refactor the fastapi dependency injection",
                     "what command runs the test suite",
                     "why is my dispatch failing", "", "hello world"):
        assert classify_complexity(complex_) == "complex", complex_


def test_compose_chat_prompt_without_history_matches_task_prompt():
    skills = [{"name": "xlsx", "source": "a/skills", "description": "d",
               "body_excerpt": "b"}]
    assert compose_chat_prompt(skills, [], "hi") == compose_task_prompt(skills, "hi")
    assert "## Conversation so far" not in compose_chat_prompt(skills, [], "hi")


def test_load_skill_excerpts_reads_curated_skills(tmp_path):
    """Curated skills (source 'curated/local') load from .agents/skills, not normalized."""
    curated = tmp_path / "curated"
    (curated / "running-tests" / "SKILL.md").parent.mkdir(parents=True)
    (curated / "running-tests" / "SKILL.md").write_text(
        "---\nname: running-tests\n---\n# body\nuse .venv/bin/python -m pytest")
    hits = [{"name": "running-tests", "source": "curated/local", "description": "d"}]
    excerpts = load_skill_excerpts(hits, {"normalized": tmp_path / "normalized"},
                                   200, curated_dir=curated)
    assert len(excerpts) == 1
    assert "pytest" in excerpts[0]["body_excerpt"]
    # without a curated dir they are skipped, not crashed on
    assert load_skill_excerpts(hits, {"normalized": tmp_path / "normalized"},
                               200) == []


def test_render_modelfile():
    text = render_modelfile("You are an agent.", model="qwen3:4b",
                            temperature=0.2, num_ctx=32768)
    assert text.startswith("FROM qwen3:4b")
    assert "PARAMETER temperature 0.2" in text
    assert "PARAMETER num_ctx 32768" in text
    assert "You are an agent." in text


# ---------------------------------------------------------------------------
# ollama client
# ---------------------------------------------------------------------------

def test_build_generate_payload():
    p = build_generate_payload("qwen3:4b", "hi", system="sys", temperature=0.1,
                               num_ctx=4096, think=False)
    assert p["model"] == "qwen3:4b"
    assert p["system"] == "sys"
    assert p["think"] is False
    assert p["options"] == {"temperature": 0.1, "num_ctx": 4096}


_CAPTURED_BODIES = []  # last POST bodies, for asserting what was sent


class _StubOllama(BaseHTTPRequestHandler):
    def do_GET(self):  # /api/tags
        body = json.dumps({"models": [{"name": "qwen3:4b"}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):  # /api/generate (streamed NDJSON)
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        _CAPTURED_BODIES.append(raw.decode("utf-8"))
        chunks = [
            json.dumps({"response": "use "}),
            json.dumps({"response": ".venv/bin/python -m pytest"}),
            json.dumps({"response": "", "done": True}),
        ]
        body = ("\n".join(chunks) + "\n").encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.fixture
def stub_ollama():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _StubOllama)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host = f"http://127.0.0.1:{server.server_address[1]}"
    yield host
    server.shutdown()


def test_ollama_tags_with_stub(stub_ollama):
    assert ollama_tags(stub_ollama) == ["qwen3:4b"]


def test_ollama_generate_with_stub(stub_ollama):
    response = ollama_generate(stub_ollama, "qwen3:4b", "how do I test?",
                               system="sys", timeout=10)
    assert "pytest" in response


def test_ollama_generate_unreachable():
    with pytest.raises(OllamaUnavailable):
        ollama_generate("http://127.0.0.1:1", "qwen3:4b", "hi", timeout=3)


def test_solve_threads_and_caps_history(stub_ollama, tmp_path, monkeypatch):
    """solve() keeps the last N turns in the prompt and injects curated skills."""
    from agent.solver import solve
    monkeypatch.setattr(
        "agent.solver.route",
        lambda *a, **k: ([{"name": "s1", "source": "curated/local",
                           "description": "d"}], None))
    curated = tmp_path / "curated"
    (curated / "s1" / "SKILL.md").parent.mkdir(parents=True)
    (curated / "s1" / "SKILL.md").write_text("---\nname: s1\n---\n# body\nuse pytest")
    monkeypatch.setattr("agent.solver.CURATED_DIR", curated)

    _CAPTURED_BODIES.clear()
    # 12 turns of history; only the last 3 may be sent
    history = [(r, f"{r}-{i}") for i in range(12) for r in ("user", "assistant")]
    response, used, info = solve("last question", model="qwen3:4b", host=stub_ollama,
                                 top_k=2, history=history, max_history_turns=3)
    assert response == "use .venv/bin/python -m pytest"
    assert used == ["s1"]
    sent = _CAPTURED_BODIES[-1]
    assert "user-9" in sent and "assistant-11" in sent  # newest turns kept
    assert "user-6" not in sent  # older turns trimmed
    assert "### skill: s1 [curated/local]" in sent


def test_solve_auto_tier_picks_budget_by_query(stub_ollama, tmp_path, monkeypatch):
    """think="auto": greetings get the small cap, technical gets the full cap,
    and think stays True in both (think=False leaks narration on this build)."""
    from agent.solver import solve
    monkeypatch.setattr("agent.solver.route", lambda *a, **k: ([], None))
    monkeypatch.setattr("agent.solver.CURATED_DIR", tmp_path / "curated")

    _CAPTURED_BODIES.clear()
    _, _, info_simple = solve("hello", model="qwen3:4b", host=stub_ollama,
                              think="auto")
    simple = json.loads(_CAPTURED_BODIES[-1])
    assert info_simple == {"tier": "simple", "think": True, "max_tokens": 200}
    assert simple["think"] is True
    assert simple["options"]["num_predict"] == 200

    _, _, info_complex = solve("refactor the fastapi dependency injection",
                               model="qwen3:4b", host=stub_ollama, think="auto")
    complex_ = json.loads(_CAPTURED_BODIES[-1])
    assert info_complex == {"tier": "complex", "think": True, "max_tokens": 1600}
    assert complex_["options"]["num_predict"] == 1600


def test_solve_fixed_think_false_respected(stub_ollama, tmp_path, monkeypatch):
    """An explicit think=False bypasses auto and is sent as-is."""
    from agent.solver import solve
    monkeypatch.setattr("agent.solver.route", lambda *a, **k: ([], None))
    monkeypatch.setattr("agent.solver.CURATED_DIR", tmp_path / "curated")
    _CAPTURED_BODIES.clear()
    solve("hello", model="qwen3:4b", host=stub_ollama, think=False)
    body = json.loads(_CAPTURED_BODIES[-1])
    assert body["think"] is False
    assert body["options"]["num_predict"] == 1600  # full cap in fixed mode
