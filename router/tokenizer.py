"""Lightweight text tokenization for skill routing (stdlib only)."""

import re

STOPWORDS = frozenset({
    "a", "an", "the", "and", "or", "of", "to", "for", "in", "on", "at",
    "with", "how", "do", "does", "can", "i", "my", "me", "we", "our",
    "you", "your", "is", "are", "it", "its", "this", "that", "what",
    "which", "when", "where", "why", "from", "by", "as", "be", "been",
})

_WORD_RE = re.compile(r"[a-z0-9]+")


def tokenize(text):
    """Lowercase alphanumeric tokens; punctuation and case stripped."""
    return _WORD_RE.findall((text or "").lower())


def token_set(text):
    """Frozenset of tokens (used for overlap scoring)."""
    return frozenset(tokenize(text))


def significant_tokens(text):
    """Tokens minus stopwords and single characters — for keyword extraction."""
    return [t for t in tokenize(text) if t not in STOPWORDS and len(t) > 1]


def ngrams(tokens, n=2):
    """Set of n-word n-grams from a token list."""
    return {" ".join(tokens[i:i + n]) for i in range(max(0, len(tokens) - n + 1))}
