"""API router aggregation."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import documents, health, query, upload

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(upload.router)
api_router.include_router(documents.router)
api_router.include_router(query.router)
