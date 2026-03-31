"""FastAPI entrypoint for DocuMind."""

from __future__ import annotations

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.container import ServiceContainer
from app.core.logging_config import configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""

    active_settings = settings or get_settings()
    active_settings.ensure_directories()
    configure_logging(active_settings.log_level)

    app = FastAPI(
        title=active_settings.app_name,
        version=active_settings.app_version,
        description="Intelligent document analysis and grounded question-answering API.",
    )
    app.state.settings = active_settings
    app.state.container = ServiceContainer(active_settings)
    app.include_router(api_router, prefix=active_settings.api_v1_prefix)

    @app.get("/", tags=["health"])
    def root() -> dict[str, str]:
        return {
            "name": active_settings.app_name,
            "docs": "/docs",
            "health": f"{active_settings.api_v1_prefix}/health",
        }

    return app


app = create_app()
