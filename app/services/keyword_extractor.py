"""Simple frequency-based keyword extraction."""

from __future__ import annotations

import re
from collections import Counter


class KeywordExtractor:
    """Extract lightweight document keywords without external APIs."""

    _token_pattern = re.compile(r"[A-Za-z][A-Za-z0-9_-]{2,}")
    _stopwords = {
        "about",
        "after",
        "also",
        "been",
        "being",
        "between",
        "could",
        "document",
        "from",
        "have",
        "into",
        "more",
        "than",
        "that",
        "their",
        "there",
        "these",
        "they",
        "this",
        "using",
        "which",
        "with",
        "would",
        "your",
    }

    def extract(self, text: str, top_n: int = 10) -> list[str]:
        """Return the most frequent informative terms in the text."""

        tokens = [
            token.lower()
            for token in self._token_pattern.findall(text)
            if token.lower() not in self._stopwords
        ]
        counts = Counter(tokens)
        return [token for token, _ in counts.most_common(top_n)]
