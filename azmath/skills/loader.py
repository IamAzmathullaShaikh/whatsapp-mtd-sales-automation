"""Skill loader: read skill bodies for prompt injection.

Reuses the library's normalized tree (skills/normalized/<source__>/<name>/
body.md) and curated project skills (.agents/skills/<name>/SKILL.md) — the
same layout the skilllib pipeline produces.
"""

from __future__ import annotations

from pathlib import Path

from scripts.common import CURATED_DIR


def load_excerpts(hits: list[dict], paths: dict, max_chars: int = 2000,
                  curated_dir: Path | None = None) -> list[dict]:
    """Excerpt each routed hit's body (first max_chars)."""
    curated_dir = Path(curated_dir) if curated_dir else CURATED_DIR
    excerpts = []
    for h in hits:
        if h.get("source") == "curated/local":
            body_path = curated_dir / h.get("name", "") / "SKILL.md"
        else:
            source_dir = str(h.get("source", "")).replace("/", "__")
            body_path = Path(paths["normalized"]) / source_dir / h.get("name", "") / "body.md"
        if not body_path.exists():
            continue
        body = body_path.read_text(encoding="utf-8", errors="replace")
        excerpts.append({
            "name": h.get("name", ""),
            "source": h.get("source", ""),
            "description": str(h.get("description", ""))[:400],
            "body_excerpt": body[:max_chars],
        })
    return excerpts
