"""Document metadata and analysis routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_container
from app.core.container import ServiceContainer
from app.schemas.document import (
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentStatsResponse,
    KeywordResponse,
    SummaryResponse,
)
from app.services.document_service import DocumentNotFoundError

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=DocumentListResponse)
def list_documents(
    container: Annotated[ServiceContainer, Depends(get_container)],
) -> DocumentListResponse:
    """List all indexed documents."""

    return container.document_service.list_documents()


@router.get("/{document_id}", response_model=DocumentDetailResponse)
def get_document(
    document_id: str,
    container: Annotated[ServiceContainer, Depends(get_container)],
) -> DocumentDetailResponse:
    """Return metadata for a single document."""

    try:
        return container.document_service.get_document(document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found."
        ) from exc


@router.post("/{document_id}/summarize", response_model=SummaryResponse)
def summarize_document(
    document_id: str,
    container: Annotated[ServiceContainer, Depends(get_container)],
) -> SummaryResponse:
    """Generate or refresh a document summary."""

    try:
        return container.document_service.summarize_document(document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found."
        ) from exc


@router.get("/{document_id}/keywords", response_model=KeywordResponse)
def extract_keywords(
    document_id: str,
    container: Annotated[ServiceContainer, Depends(get_container)],
    top_n: int = Query(default=10, ge=3, le=25),
) -> KeywordResponse:
    """Return top keywords for a document."""

    try:
        return container.document_service.extract_keywords(document_id, top_n=top_n)
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found."
        ) from exc


@router.get("/{document_id}/stats", response_model=DocumentStatsResponse)
def get_document_stats(
    document_id: str,
    container: Annotated[ServiceContainer, Depends(get_container)],
) -> DocumentStatsResponse:
    """Return document statistics and computed keywords."""

    try:
        return container.document_service.document_stats(document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found."
        ) from exc
