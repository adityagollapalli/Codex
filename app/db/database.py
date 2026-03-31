"""Database helpers for DocuMind."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.db.models import Base


class DatabaseManager:
    """Wrap SQLAlchemy engine and session factory creation."""

    def __init__(self, settings: Settings) -> None:
        if settings.database_url.startswith("sqlite"):
            connect_args = {"check_same_thread": False}
        else:
            connect_args = {}
        self.engine = create_engine(settings.database_url, connect_args=connect_args)
        self.session_factory = sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )

    def create_tables(self) -> None:
        """Create database tables if they do not exist."""

        Base.metadata.create_all(bind=self.engine)

    @contextmanager
    def session_scope(self) -> Iterator[Session]:
        """Yield a transactional session and handle commit/rollback."""

        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
