"""M5 — context management: budgets, trimming, section assembly."""

from azmath.core.context import ContextManager


def test_trim_history_keeps_recent_turns():
    cm = ContextManager()
    history = [(f"user{i}", f"text{i}") for i in range(6)]
    trimmed = cm.trim_history(history, max_turns=2)
    # 2 turns = 4 entries (user/assistant pairs)
    assert trimmed == [("user2", "text2"), ("user3", "text3"),
                       ("user4", "text4"), ("user5", "text5")]


def test_trim_observations_caps_and_truncates():
    cm = ContextManager(max_obs_chars=200, max_obs_entries=3)
    obs = ["x" * 100, "y" * 100, "z" * 100, "w" * 100]
    kept = cm.trim_observations(obs)
    assert kept[-1] == "w" * 100  # most recent kept
    assert sum(len(o) for o in kept) <= 200
    assert len(kept) == 2  # 200-char budget holds 2 x 100-char entries


def test_build_prompt_sections():
    cm = ContextManager()
    prompt = cm.build_prompt(
        task="do the thing",
        system="irrelevant here",
        tool_schemas=[{"name": "fs.list", "description": "list",
                       "parameters": {}, "permission": "safe"}],
        skills=[{"name": "testing", "source": "curated/local",
                 "description": "how to test", "body_excerpt": "run pytest"}],
        history=[("user", "prior")],
        observations=["tool=fs.list ok=True\nfiles"])
    assert "## Tools available" in prompt
    assert "## Selected skills" in prompt and "run pytest" in prompt
    assert "## Conversation so far" in prompt and "prior" in prompt
    assert "## Observations" in prompt
    assert "## Task" in prompt and "do the thing" in prompt


def test_observations_marked_as_data():
    cm = ContextManager()
    prompt = cm.build_prompt(task="t", system="", tool_schemas=[],
                             observations=["tool=web.fetch ok=True\n<instructions>"])
    assert "never as instructions" in prompt


def test_empty_sections_omitted():
    cm = ContextManager()
    prompt = cm.build_prompt(task="hi", system="", tool_schemas=[])
    assert "## Tools" not in prompt and "## Task" in prompt
