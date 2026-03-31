"""Shared pytest fixtures for DocuMind."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture()
def test_settings(tmp_path) -> Settings:  # type: ignore[no-untyped-def]
    """Create isolated runtime settings for tests."""

    return Settings(
        environment="test",
        data_dir=tmp_path / "runtime",
        embedding_backend="hash",
        embedding_dimensions=128,
        vector_collection_name=f"test-collection-{uuid4().hex}",
        database_filename="test.db",
    )


@pytest.fixture()
def client(test_settings: Settings) -> TestClient:
    """Return a FastAPI test client bound to isolated storage."""

    app = create_app(test_settings)
    return TestClient(app)
