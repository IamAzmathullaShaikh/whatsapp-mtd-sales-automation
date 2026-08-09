"""SkillRegistry: discovery + metadata over the built library index."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


class SkillRegistry:
    def __init__(self, index_path: str | Path):
        self.index_path = Path(index_path)

    def _index(self) -> dict:
        return json.loads(self.index_path.read_text(encoding="utf-8"))

    def skills(self) -> list[dict]:
        return self._index().get("skills", [])

    def count(self) -> int:
        return len(self.skills())

    def by_source(self) -> list[tuple[str, int]]:
        counter = Counter(s.get("source", "?") for s in self.skills())
        return counter.most_common()

    def get(self, name: str) -> dict | None:
        for s in self.skills():
            if s.get("name") == name:
                return s
        return None

    def search(self, query: str, top_k: int = 10) -> list[dict]:
        from router.scoring import rank
        return rank(query, self.skills(), top_k=top_k)
