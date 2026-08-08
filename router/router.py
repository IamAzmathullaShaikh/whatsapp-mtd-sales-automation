"""Router: load the library index and pick the best-matching skills."""

import json
from pathlib import Path

from .scoring import DEFAULT_WEIGHTS, rank, score_query


def load_index(path):
    """Load a JSON index produced by `scripts.indexer.build_index`."""
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def route(query, index_path, top_k=5, weights=None):
    """Return (hits, index) for a query. hits are index entries, best first."""
    index = load_index(index_path)
    docs = index.get("skills", [])
    return rank(query, docs, top_k=top_k, weights=weights or DEFAULT_WEIGHTS), index


def render_route(query, hits, top_k, template_text, weights=None):
    """Fill a route template ({{query}}, {{top_k}}, {{ranked}}) with hits."""
    weights = weights or DEFAULT_WEIGHTS
    ranked = "\n".join(
        f"- **{h.get('name')}** ({h.get('source')}) — score {score_query(query, h, weights)}\n"
        f"  {str(h.get('description', ''))[:160]}"
        for h in hits
    )
    return (
        template_text
        .replace("{{query}}", query)
        .replace("{{top_k}}", str(top_k))
        .replace("{{ranked}}", ranked)
    )
