"""Vector storage and retrieval backends."""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from app.core.config import Settings


@dataclass(slots=True)
class VectorChunk:
    """Chunk payload stored in the vector database."""

    id: str
    document_id: str
    filename: str
    chunk_index: int
    text: str
    embedding: list[float]
    page_number: int | None = None


@dataclass(slots=True)
class RetrievedChunk:
    """Result returned from vector retrieval."""

    chunk_id: str
    document_id: str
    filename: str
    chunk_index: int
    text: str
    score: float
    page_number: int | None = None


class VectorStore(Protocol):
    """Protocol implemented by vector store backends."""

    def upsert_chunks(self, chunks: list[VectorChunk]) -> None:
        """Insert or update vectors."""

    def query(
        self,
        query_embedding: list[float],
        top_k: int,
        document_ids: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        """Retrieve the most relevant chunks."""

    def delete_document(self, document_id: str) -> None:
        """Delete all vectors for a document."""


class ChromaVectorStore:
    """Thin wrapper around a persistent Chroma collection."""

    def __init__(self, persist_directory: str, collection_name: str) -> None:
        try:
            import chromadb
        except ImportError as exc:
            raise RuntimeError("chromadb must be installed to use the vector store.") from exc

        self._client = chromadb.PersistentClient(path=persist_directory)
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert_chunks(self, chunks: list[VectorChunk]) -> None:
        """Insert or update chunk vectors and their metadata."""

        if not chunks:
            return

        self._collection.upsert(
            ids=[chunk.id for chunk in chunks],
            documents=[chunk.text for chunk in chunks],
            embeddings=[chunk.embedding for chunk in chunks],
            metadatas=[self._metadata_for_chunk(chunk) for chunk in chunks],
        )

    def query(
        self,
        query_embedding: list[float],
        top_k: int,
        document_ids: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        """Return top matching chunks for the provided embedding."""

        if document_ids:
            results: list[RetrievedChunk] = []
            for document_id in document_ids:
                results.extend(
                    self._query_once(
                        query_embedding, top_k=top_k, where={"document_id": document_id}
                    )
                )
            return sorted(results, key=lambda item: item.score, reverse=True)[:top_k]

        return self._query_once(query_embedding, top_k=top_k, where=None)

    def delete_document(self, document_id: str) -> None:
        """Remove all vectors for a document."""

        self._collection.delete(where={"document_id": document_id})

    def _query_once(
        self,
        query_embedding: list[float],
        top_k: int,
        where: dict[str, Any] | None,
    ) -> list[RetrievedChunk]:
        raw = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
        )
        ids = raw.get("ids", [[]])[0]
        documents = raw.get("documents", [[]])[0]
        metadatas = raw.get("metadatas", [[]])[0]
        distances = raw.get("distances", [[]])[0]

        results: list[RetrievedChunk] = []
        for chunk_id, text, metadata, distance in zip(
            ids, documents, metadatas, distances, strict=True
        ):
            score = 1.0 / (1.0 + float(distance))
            results.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    document_id=str(metadata["document_id"]),
                    filename=str(metadata["filename"]),
                    chunk_index=int(metadata["chunk_index"]),
                    text=str(text),
                    score=round(score, 4),
                    page_number=int(metadata["page_number"])
                    if metadata.get("page_number")
                    else None,
                )
            )
        return results

    @staticmethod
    def _metadata_for_chunk(chunk: VectorChunk) -> dict[str, Any]:
        metadata: dict[str, Any] = {
            "document_id": chunk.document_id,
            "filename": chunk.filename,
            "chunk_index": chunk.chunk_index,
        }
        if chunk.page_number is not None:
            metadata["page_number"] = chunk.page_number
        return metadata


class SimpleVectorStore:
    """JSON-backed vector store for lightweight local development and tests."""

    def __init__(self, persist_path: Path) -> None:
        self.persist_path = persist_path
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        self._records: dict[str, dict[str, Any]] = {}
        self._load()

    def upsert_chunks(self, chunks: list[VectorChunk]) -> None:
        if not chunks:
            return

        for chunk in chunks:
            self._records[chunk.id] = {
                "id": chunk.id,
                "document_id": chunk.document_id,
                "filename": chunk.filename,
                "chunk_index": chunk.chunk_index,
                "text": chunk.text,
                "embedding": chunk.embedding,
                "page_number": chunk.page_number,
            }
        self._save()

    def query(
        self,
        query_embedding: list[float],
        top_k: int,
        document_ids: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        candidates = list(self._records.values())
        if document_ids:
            allowed = set(document_ids)
            candidates = [record for record in candidates if record["document_id"] in allowed]

        scored: list[RetrievedChunk] = []
        for record in candidates:
            score = self._cosine_similarity(query_embedding, record["embedding"])
            scored.append(
                RetrievedChunk(
                    chunk_id=str(record["id"]),
                    document_id=str(record["document_id"]),
                    filename=str(record["filename"]),
                    chunk_index=int(record["chunk_index"]),
                    text=str(record["text"]),
                    score=round(score, 4),
                    page_number=(int(record["page_number"]) if record.get("page_number") else None),
                )
            )
        return sorted(scored, key=lambda item: item.score, reverse=True)[:top_k]

    def delete_document(self, document_id: str) -> None:
        self._records = {
            chunk_id: record
            for chunk_id, record in self._records.items()
            if record["document_id"] != document_id
        }
        self._save()

    def _load(self) -> None:
        if not self.persist_path.exists():
            self._records = {}
            return

        raw = json.loads(self.persist_path.read_text(encoding="utf-8"))
        self._records = {entry["id"]: entry for entry in raw}

    def _save(self) -> None:
        payload = list(self._records.values())
        self.persist_path.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")

    @staticmethod
    def _cosine_similarity(left: list[float], right: list[float]) -> float:
        if not left or not right or len(left) != len(right):
            return 0.0

        dot = sum(a * b for a, b in zip(left, right, strict=True))
        left_norm = math.sqrt(sum(a * a for a in left))
        right_norm = math.sqrt(sum(b * b for b in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return max(0.0, dot / (left_norm * right_norm))


def build_vector_store(settings: Settings, logger: logging.Logger) -> VectorStore:
    """Create the configured vector store with a safe fallback path."""

    backend = settings.vector_backend.lower()
    if backend == "simple":
        logger.info("Using simple JSON vector store backend.")
        return SimpleVectorStore(settings.simple_vector_store_path)

    try:
        logger.info("Using ChromaDB vector store backend.")
        return ChromaVectorStore(
            persist_directory=str(settings.vector_store_dir),
            collection_name=settings.vector_collection_name,
        )
    except Exception as exc:
        logger.warning("Falling back to simple vector store: %s", exc)
        return SimpleVectorStore(settings.simple_vector_store_path)
