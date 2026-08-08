"""Pure scoring functions for skill routing (stdlib only, fully testable).

A skill document looks like an index entry:

    {
        "id": "anthropics/skills/xlsx",
        "name": "xlsx",
        "source": "anthropics/skills",
        "description": "Use this skill any time a spreadsheet file is ...",
        "keywords": ["xlsx", "spreadsheet", "excel", ...],
    }

Scoring is overlap-coefficient per field (name weighted highest, then
keywords, then description) plus a bigram bonus for multi-word skill names
(e.g. "excel-schema-and-mapping" matches "excel schema").
"""

from .tokenizer import ngrams, token_set, tokenize

DEFAULT_WEIGHTS = {"name": 3.0, "description": 1.0, "keywords": 2.0, "bigrams": 1.0}


def overlap(a, b):
    """Overlap coefficient |a∩b|/|a|; 0.0 when the query set is empty."""
    if not a:
        return 0.0
    return len(a & b) / len(a)


def score_query(query, doc, weights=None):
    """Score one skill document against a query string. 0.0 = no match."""
    weights = weights or DEFAULT_WEIGHTS
    q = token_set(query)
    if not q:
        return 0.0
    s = (
        weights["name"] * overlap(q, token_set(doc.get("name", "")))
        + weights["description"] * overlap(q, token_set(doc.get("description", "")))
        + weights["keywords"] * overlap(q, frozenset(doc.get("keywords") or []))
    )
    q_bi = ngrams(tokenize(query), 2)
    n_bi = ngrams(tokenize(doc.get("name", "")), 2)
    s += weights["bigrams"] * overlap(q_bi, n_bi)
    return round(s, 4)


def rank(query, docs, top_k=5, weights=None):
    """Return the top_k documents with a positive score, best first.

    Ties break alphabetically by name for deterministic output.
    """
    scored = []
    for d in docs:
        s = score_query(query, d, weights)
        if s > 0:
            scored.append((s, d.get("name", ""), d))
    scored.sort(key=lambda t: (-t[0], t[1]))
    return [t[2] for t in scored[:top_k]]
