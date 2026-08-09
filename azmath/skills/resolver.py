"""SkillResolver: route a task to relevant skills and load their bodies.

This is the "dynamic discovery" stage: only the selected skills are injected,
so a 4B model never carries the whole library in context.
"""

from __future__ import annotations

from pathlib import Path

from router.router import route

from .loader import load_excerpts


class SkillResolver:
    def __init__(self, index_path: str | Path, paths: dict, top_k: int = 4,
                 max_chars: int = 2000, curated_dir: str | Path | None = None):
        self.index_path = Path(index_path)
        self.paths = paths
        self.top_k = top_k
        self.max_chars = max_chars
        self.curated_dir = curated_dir

    def resolve(self, task: str, top_k: int | None = None) -> list[dict]:
        """Return excerpts of the best-matching skills for `task`."""
        if not self.index_path.exists():
            return []
        hits, _ = route(task, self.index_path, top_k=top_k or self.top_k)
        return load_excerpts(hits, self.paths, self.max_chars, self.curated_dir)

    def preview(self, task: str, top_k: int | None = None) -> list[dict]:
        """Ranked names + scores without loading bodies (fast preview)."""
        if not self.index_path.exists():
            return []
        hits, _ = route(task, self.index_path, top_k=top_k or self.top_k)
        return [{"name": h.get("name"), "source": h.get("source"),
                 "score": h.get("_score")} for h in hits]
