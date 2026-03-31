"""Document-related request and response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DocumentSummaryItem(BaseModel):
    """Compact document metadata used in list views."""

    id: str
    filename: str
    file_type: str
    upload_timestamp: datetime
    chunk_count: int
    word_count: int
    page_count: int | None = None
    estimated_reading_minutes: int
    summary_status: str


class DocumentUploadResponse(BaseModel):
    """Response returned after a successful upload and ingestion."""

    document: DocumentSummaryItem
    metadata: dict[str, Any]


class DocumentDetailResponse(BaseModel):
    """Detailed document metadata and analysis state."""

    id: str
    filename: str
    stored_filename: str
    file_type: str
    file_size_bytes: int
    upload_timestamp: datetime
    page_count: int | None = None
    chunk_count: int
    word_count: int
    estimated_reading_minutes: int
    summary_status: str
    summary_text: str | None = None
    source_metadata: dict[str, Any]


class DocumentListResponse(BaseModel):
    """List response for document catalog endpoints."""

    items: list[DocumentSummaryItem]
    total: int


class DocumentStatsResponse(BaseModel):
    """Computed statistics for a single document."""

    document_id: str
    filename: str
    file_type: str
    word_count: int
    chunk_count: int
    page_count: int | None = None
    estimated_reading_minutes: int
    top_keywords: list[str] = Field(default_factory=list)


class KeywordResponse(BaseModel):
    """Keywords extracted from a document."""

    document_id: str
    keywords: list[str]


class SummaryResponse(BaseModel):
    """Summary payload for a document."""

    document_id: str
    summary: str
    summary_status: str
