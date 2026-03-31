"""Common API schema definitions."""

from __future__ import annotations

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Response payload for service health checks."""

    status: str
    version: str


class MessageResponse(BaseModel):
    """Simple message payload for informational endpoints."""

    message: str
