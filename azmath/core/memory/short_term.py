"""Short-term memory: current session/task state. Ephemeral by design — not
persisted, and never confused with long-term memory."""

from __future__ import annotations

import time


class SessionMemory:
    """A tiny key/value store scoped to one session."""

    def __init__(self, session_id: str | None = None):
        self.session_id = session_id or f"session-{int(time.time())}"
        self._data: dict = {}

    def set(self, key: str, value) -> None:
        self._data[key] = value

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def snapshot(self) -> dict:
        return dict(self._data)

    def clear(self) -> None:
        self._data.clear()
