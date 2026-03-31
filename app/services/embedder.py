"""Embedding providers for semantic retrieval."""

from __future__ import annotations

import hashlib
import logging
import math
import re
from collections.abc import Sequence
from typing import Protocol

import numpy as np

from app.core.config import Settings


class Embedder(Protocol):
    """Protocol implemented by embedding backends."""

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed a list of texts."""

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query string."""


class SentenceTransformerEmbedder:
    """Sentence-transformers wrapper with lazy model loading."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._model = None

    @property
    def model(self):  # type: ignore[no-untyped-def]
        """Load the embedding model lazily."""

        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        embeddings = self.model.encode(list(texts), normalize_embeddings=True)
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]


class HashingEmbedder:
    """Deterministic fallback embedder for tests and offline environments."""

    token_pattern = re.compile(r"[A-Za-z0-9_]+")

    def __init__(self, dimensions: int = 384) -> None:
        self.dimensions = dimensions

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed_single(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed_single(text)

    def _embed_single(self, text: str) -> list[float]:
        vector = np.zeros(self.dimensions, dtype=float)
        tokens = self.token_pattern.findall(text.lower())
        if not tokens:
            return vector.tolist()

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], byteorder="big") % self.dimensions
            sign = -1.0 if digest[4] % 2 else 1.0
            weight = 1.0 + (digest[5] / 255.0)
            vector[index] += sign * weight

        norm = math.sqrt(float(np.dot(vector, vector)))
        if norm > 0:
            vector /= norm
        return vector.tolist()


def build_embedder(settings: Settings, logger: logging.Logger) -> Embedder:
    """Build the configured embedder with a resilient fallback."""

    backend = settings.embedding_backend.lower()
    if backend == "hash":
        logger.info("Using hashing embedder backend.")
        return HashingEmbedder(dimensions=settings.embedding_dimensions)

    try:
        from sentence_transformers import SentenceTransformer  # noqa: F401

        logger.info("Using sentence-transformer embedder backend.")
        return SentenceTransformerEmbedder(model_name=settings.embedding_model_name)
    except Exception as exc:
        logger.warning("Falling back to hashing embedder: %s", exc)
        return HashingEmbedder(dimensions=settings.embedding_dimensions)
