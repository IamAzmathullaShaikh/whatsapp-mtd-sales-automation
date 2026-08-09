"""Event bus + structured observability.

Every meaningful step emits a structured dict event. Handlers may subscribe
(logging, JSONL trace, metrics). Secrets are redacted before anything leaves
the process — tool args that look sensitive (tokens, keys, passwords, content
of writes) are never emitted in full.
"""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from pathlib import Path

logger = logging.getLogger("azmath")

_SECRET_KEYS = ("token", "key", "password", "secret", "auth", "credential", "content")
_SECRET_VALUE_RE = re.compile(
    r"(ghp_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{16,}|Bearer [A-Za-z0-9._-]{10,}|"
    r"AKIA[0-9A-Z]{16}|password[\"']?\s*[:=]\s*[\"'][^\"']+[\"'])",
    re.I)


def redact(text: str, limit: int = 2000) -> str:
    """Truncate + mask secret-shaped tokens. Never log secrets."""
    t = (text or "")[:limit]
    t = _SECRET_VALUE_RE.sub("***", t)
    return t


class EventBus:
    def __init__(self, events_file: str = "", session_id: str | None = None):
        self.session_id = session_id or uuid.uuid4().hex[:12]
        self._handlers = []
        self._jsonl = Path(events_file).expanduser() if events_file else None

    def subscribe(self, handler) -> None:
        self._handlers.append(handler)

    def emit(self, type_: str, **fields) -> dict:
        event = {
            "type": type_,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "session_id": self.session_id,
            "task_id": fields.pop("task_id", None),
        }
        for key, value in fields.items():
            if key in _SECRET_KEYS and isinstance(value, str):
                value = redact(value, 200)
            event[key] = value
        for handler in self._handlers:
            handler(event)
        if self._jsonl:
            self._jsonl.parent.mkdir(parents=True, exist_ok=True)
            with open(self._jsonl, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(event, default=str) + "\n")
        logger.debug("event %s %s", type_, json.dumps({k: v for k, v in event.items()
                                                      if k not in _SECRET_KEYS}, default=str))
        return event
