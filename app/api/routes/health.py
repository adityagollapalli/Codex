"""Health and service info endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.schemas.common import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def healthcheck(request: Request) -> HealthResponse:
    """Return a lightweight service health payload."""

    settings = request.app.state.settings
    return HealthResponse(status="ok", version=settings.app_version)
