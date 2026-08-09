"""Web tools — behind a small provider abstraction so a different search/
fetch backend (e.g. Serper, a headless browser) can be dropped in later.

The default provider is stdlib-only: urllib fetch + a DuckDuckGo HTML search.
When the network is unreachable the tools return a clear "capability
unavailable" failure — they never fake a result.
"""

from __future__ import annotations

import html
import re
import urllib.parse
import urllib.request
from typing import Protocol

from .base import Permission, Tool, ToolResult, require

_TIMEOUT = 15.0


class WebProvider(Protocol):
    def search(self, query: str, max_results: int) -> list[dict]: ...

    def fetch(self, url: str, max_chars: int) -> str: ...


class StdlibWebProvider:
    """urllib-based provider: DuckDuckGo HTML search + generic page fetch."""

    name = "stdlib"

    def search(self, query: str, max_results: int) -> list[dict]:
        q = urllib.parse.quote(query)
        req = urllib.request.Request(
            f"https://html.duckduckgo.com/html/?q={q}",
            headers={"User-Agent": "Mozilla/5.0 azmath-agent"})
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            page = resp.read().decode("utf-8", errors="replace")
        results = []
        # DuckDuckGo HTML results: <a class="result__a" href="...">title</a>
        for m in re.finditer(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
                             page, re.S):
            url, title = html.unescape(m.group(1)), re.sub(r"<[^>]+>", "", m.group(2))
            url = re.sub(r"^//", "https://", url)
            results.append({"title": html.unescape(title).strip(), "url": url})
            if len(results) >= max_results:
                break
        return results

    def fetch(self, url: str, max_chars: int) -> str:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 azmath-agent"})
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            raw = resp.read(max_chars * 4)
        text = raw.decode("utf-8", errors="replace")
        text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text, flags=re.S | re.I)
        text = re.sub(r"<[^>]+>", " ", text)
        text = html.unescape(re.sub(r"\s+", " ", text)).strip()
        return text[:max_chars]


class Search(Tool):
    name = "web.search"
    description = "Search the web for a query; returns titles and URLs."
    parameters = {
        "query": {"type": "string", "description": "search query", "required": True},
        "max_results": {"type": "integer", "description": "default 5", "required": False},
    }
    permission = Permission.SAFE

    def __init__(self, provider: WebProvider):
        self.provider = provider

    def run(self, args):
        def fn(a):
            missing = require(a, "query")
            if missing:
                return ToolResult(tool=self.name, ok=False, error=f"missing args: {missing}")
            try:
                results = self.provider.search(a["query"], int(a.get("max_results") or 5))
            except Exception as exc:
                return ToolResult(
                    tool=self.name, ok=False,
                    error=f"capability unavailable: web search provider failed ({exc})")
            if not results:
                return ToolResult(tool=self.name, ok=False, error="no results returned")
            return "\n".join(f"- {r['title']}\n  {r['url']}" for r in results)
        return self._execute(fn, args)


class Fetch(Tool):
    name = "web.fetch"
    description = "Fetch a URL and extract readable text (title + body)."
    parameters = {
        "url": {"type": "string", "description": "http(s) URL", "required": True},
        "max_chars": {"type": "integer", "description": "default 20000", "required": False},
    }
    permission = Permission.SAFE

    def __init__(self, provider: WebProvider):
        self.provider = provider

    def run(self, args):
        def fn(a):
            missing = require(a, "url")
            if missing:
                return ToolResult(tool=self.name, ok=False, error=f"missing args: {missing}")
            url = a["url"]
            if not url.startswith(("http://", "https://")):
                return ToolResult(tool=self.name, ok=False,
                                  error=f"unsupported URL scheme: {url[:40]}")
            try:
                text = self.provider.fetch(url, int(a.get("max_chars") or 20000))
            except Exception as exc:
                return ToolResult(
                    tool=self.name, ok=False,
                    error=f"capability unavailable: could not fetch {url} ({exc})")
            if not text.strip():
                return ToolResult(tool=self.name, ok=False,
                                  error=f"fetched {url} but extracted no readable text")
            return text
        return self._execute(fn, args)


def register_web(registry, provider: WebProvider | None = None) -> None:
    registry.register(Search(provider or StdlibWebProvider()))
    registry.register(Fetch(provider or StdlibWebProvider()))
