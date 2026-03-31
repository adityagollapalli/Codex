"""Question answering schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Request schema for retrieval-augmented Q&A."""

    question: str = Field(..., min_length=3, max_length=500)
    document_ids: list[str] | None = None
    top_k: int = Field(default=4, ge=1, le=10)


class Citation(BaseModel):
    """Grounding snippet returned alongside an answer."""

    document_id: str
    filename: str
    chunk_id: str
    chunk_index: int
    snippet: str
    score: float
    page_number: int | None = None


class QueryResponse(BaseModel):
    """Question-answering result with citations."""

    question: str
    answer: str
    citations: list[Citation]
    confidence_note: str
    retrieval_count: int
