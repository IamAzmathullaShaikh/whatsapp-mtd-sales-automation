"""Memory facade: one entry point over short-term (session) + long-term (JSON)."""

from __future__ import annotations

from .long_term import JsonMemory
from .short_term import SessionMemory


class MemoryStore:
    def __init__(self, long_term: JsonMemory | None = None):
        self.session = SessionMemory()
        self.long_term = long_term  # None = long-term memory disabled

    @property
    def available(self) -> bool:
        return self.long_term is not None

    def remember(self, key: str, value: str, metadata: dict | None = None,
                 approved: bool = False) -> bool:
        """Persist to long-term memory only when explicitly approved."""
        if self.long_term is None or not approved:
            return False
        self.long_term.save(key, value, metadata)
        return True

    def recall(self, query: str, top_k: int = 5) -> list[dict]:
        if self.long_term is None:
            return []
        return self.long_term.search(query, top_k)
