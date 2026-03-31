"""FastAPI dependency helpers."""

from __future__ import annotations

from fastapi import Request

from app.core.container import ServiceContainer


def get_container(request: Request) -> ServiceContainer:
    """Return the shared service container attached to the app."""

    return request.app.state.container
