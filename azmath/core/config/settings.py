"""Centralized configuration for the azmath agent platform.

Loads ``config/agent.toml`` (platform) and ``config/permissions.toml``
(policy) via the stdlib ``tomllib`` — no third-party dependencies. Every
platform key can be overridden by an ``AZMATH_<SECTION>_<KEY>`` environment
variable, so the same checkout behaves differently in CI vs interactive use
without editing files.
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_AGENT_CONFIG = ROOT / "config" / "agent.toml"
DEFAULT_PERMISSIONS_CONFIG = ROOT / "config" / "permissions.toml"

# (section, key, envvar) — the complete list of env-overridable keys.
ENV_OVERRIDES = (
    ("model", "provider", "AZMATH_MODEL_PROVIDER"),
    ("model", "name", "AZMATH_MODEL_NAME"),
    ("model", "host", "AZMATH_HOST"),
    ("model", "temperature", "AZMATH_TEMPERATURE"),
    ("model", "num_ctx", "AZMATH_NUM_CTX"),
    ("model", "max_tokens", "AZMATH_MAX_TOKENS"),
    ("model", "simple_max_tokens", "AZMATH_SIMPLE_MAX_TOKENS"),
    ("model", "think", "AZMATH_THINK"),
    ("model", "timeout", "AZMATH_MODEL_TIMEOUT"),
    ("loop", "max_iterations", "AZMATH_MAX_ITERATIONS"),
    ("loop", "tool_timeout", "AZMATH_TOOL_TIMEOUT"),
    ("loop", "verify", "AZMATH_VERIFY"),
    ("tools", "approval_mode", "AZMATH_APPROVAL_MODE"),
    ("memory", "path", "AZMATH_MEMORY_PATH"),
    ("observability", "log_level", "AZMATH_LOG_LEVEL"),
    ("observability", "events_file", "AZMATH_EVENTS_FILE"),
)


def _coerce(value: str):
    """Best-effort scalar coercion for env overrides."""
    v = value.strip()
    low = v.lower()
    if low in ("true", "yes", "on"):
        return True
    if low in ("false", "no", "off"):
        return False
    if low in ("none", "null"):
        return None
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        pass
    return v


def _apply_env(data: dict, env: dict | None = None) -> dict:
    """Deep-merge AZMATH_* environment variables into the loaded dict."""
    env = os.environ if env is None else env
    merged = {k: dict(v) for k, v in data.items()}
    for section, key, var in ENV_OVERRIDES:
        if var in env:
            merged.setdefault(section, {})[key] = _coerce(env[var])
    return merged


def load_toml(path: Path) -> dict:
    with open(path, "rb") as fh:
        return tomllib.load(fh)


class Settings:
    """Dict-backed, env-aware configuration with section accessors."""

    def __init__(self, data: dict, permissions: dict, source: str):
        self._data = data
        self.permissions = permissions
        self.source = source

    # -- accessors -----------------------------------------------------------
    def section(self, name: str) -> dict:
        return self._data.get(name, {})

    def get(self, section: str, key: str, default=None):
        return self._data.get(section, {}).get(key, default)

    def __getitem__(self, section: str) -> dict:
        return self._data[section]

    # -- convenience ---------------------------------------------------------
    @property
    def model(self) -> dict:
        return self.section("model")

    @property
    def loop(self) -> dict:
        return self.section("loop")

    @property
    def tools_cfg(self) -> dict:
        return self.section("tools")

    @property
    def memory_cfg(self) -> dict:
        return self.section("memory")

    @property
    def observability(self) -> dict:
        return self.section("observability")

    def expand(self, value: str) -> str:
        """Expand ~ and $HOME in a configured path."""
        return os.path.expanduser(os.path.expandvars(value))


def load_settings(agent_config: Path = DEFAULT_AGENT_CONFIG,
                  permissions_config: Path = DEFAULT_PERMISSIONS_CONFIG,
                  env: dict | None = None) -> Settings:
    """Load + merge platform and permission configuration."""
    data = _apply_env(load_toml(agent_config), env)
    permissions = load_toml(permissions_config)
    return Settings(data, permissions, str(agent_config))
