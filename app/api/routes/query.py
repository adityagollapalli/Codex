"""Query routes for grounded question answering."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_container
from app.core.container import ServiceContainer
from app.schemas.query import QueryRequest, QueryResponse
from app.services.document_service import DocumentNotFoundError

router = APIRouter(tags=["query"])


@router.post("/query", response_model=QueryResponse)
def query_documents(
    payload: QueryRequest,
    container: Annotated[ServiceContainer, Depends(get_container)],
) -> QueryResponse:
    """Answer a question using retrieved document chunks as grounding context."""

    try:
        document_ids = (
            container.document_service.validate_document_ids(payload.document_ids)
            if payload.document_ids
            else None
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown document ID(s): {exc}",
        ) from exc

    return container.qa_engine.answer_question(
        question=payload.question,
        top_k=payload.top_k,
        document_ids=document_ids,
    )
