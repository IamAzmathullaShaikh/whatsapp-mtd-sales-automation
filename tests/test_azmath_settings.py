"""M1 — configuration: TOML load + AZMATH_* env overrides + coercion."""

import tomllib
from pathlib import Path

from azmath.core.config import load_settings


def test_loads_defaults(tmp_path):
    cfg = tmp_path / "agent.toml"
    cfg.write_text("[model]\nname = \"qwen3:4b\"\nhost = \"http://x:1\"\n"
                   "[loop]\nmax_iterations = 3\n", encoding="utf-8")
    perm = tmp_path / "permissions.toml"
    perm.write_text("[tools]\n\"fs.write\" = \"approval\"\n", encoding="utf-8")
    s = load_settings(cfg, perm)
    assert s.model["name"] == "qwen3:4b"
    assert s.loop["max_iterations"] == 3
    assert s.permissions["tools"]["fs.write"] == "approval"


def test_env_override_and_coercion(tmp_path):
    cfg = tmp_path / "agent.toml"
    cfg.write_text("[model]\nname = \"qwen3:4b\"\n[loop]\nmax_iterations = 8\n",
                   encoding="utf-8")
    perm = tmp_path / "permissions.toml"
    perm.write_text("", encoding="utf-8")
    env = {"AZMATH_MODEL_NAME": "qwen3:8b", "AZMATH_MAX_ITERATIONS": "3",
           "AZMATH_VERIFY": "false", "AZMATH_THINK": "false"}
    s = load_settings(cfg, perm, env=env)
    assert s.model["name"] == "qwen3:8b"
    assert s.loop["max_iterations"] == 3
    assert s.loop["verify"] is False
    assert s.model["think"] is False


def test_real_project_config_loads():
    s = load_settings()
    assert s.model["provider"] == "ollama"
    assert s.get("tools", "approval_mode") == "prompt"
    assert s.loop["max_iterations"] >= 1
    assert "shell" in s.permissions["tools"]
