"""Long-term memory: an intentionally stored, inspectable JSON store.

The backend is replaceable (the facade only needs get/save/search/delete).
Nothing is written without an explicit persistence decision — the caller gates
it behind settings.memory.persist_without_approval or an approval prompt.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

_WORD_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return set(_WORD_RE.findall((text or "").lower()))


class JsonMemory:
    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser()
        self._data: dict = self._load()

    def _load(self) -> dict:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return {}
        return {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._data, indent=2, ensure_ascii=False),
                       encoding="utf-8")
        tmp.replace(self.path)

    # -- API -----------------------------------------------------------------
    def save(self, key: str, value: str, metadata: dict | None = None) -> None:
        entry = {
            "key": key,
            "value": value,
            "metadata": metadata or {},
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        self._data[key] = entry
        self._save()

    def get(self, key: str) -> dict | None:
        return self._data.get(key)

    def delete(self, key: str) -> bool:
        existed = key in self._data
        self._data.pop(key, None)
        if existed:
            self._save()
        return existed

    def list_keys(self) -> list[str]:
        return list(self._data)

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """Keyword-overlap relevance over values + metadata. Cheap, CPU-first."""
        q = _tokens(query)
        if not q:
            return []
        scored = []
        for key, entry in self._data.items():
            hay = f"{key} {entry.get('value', '')} {entry.get('metadata', {})}"
            hay_tokens = _tokens(hay)
            score = len(q & hay_tokens) / len(q)
            if score > 0:
                scored.append((score, key, entry))
        scored.sort(key=lambda t: -t[0])
        return [e for _, _, e in scored[:top_k]]

    def inspect(self) -> list[dict]:
        """All entries without values (for the CLI memory list)."""
        return [{"key": k, "ts": v.get("ts"), "metadata": v.get("metadata", {})}
                for k, v in self._data.items()]
