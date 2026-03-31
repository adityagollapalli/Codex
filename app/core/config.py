"""Application settings for DocuMind."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Environment-driven runtime settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="DOCUMIND_",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "DocuMind API"
    app_version: str = "0.1.0"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    data_dir: Path = Field(default=Path("data"))
    upload_dir_name: str = "uploads"
    vector_store_dir_name: str = "chroma"
    database_filename: str = "documind.db"

    max_upload_size_mb: int = 25
    allowed_extensions: tuple[str, ...] = (".pdf", ".txt", ".csv")

    chunk_size_words: int = 180
    chunk_overlap_words: int = 40
    retrieval_top_k: int = 4
    max_summary_sentences: int = 4
    reading_speed_wpm: int = 220

    embedding_backend: str = "hash"
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimensions: int = 384
    vector_backend: str = "simple"
    vector_collection_name: str = "documind_chunks"
    simple_vector_store_filename: str = "vector_store.json"

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    @property
    def resolved_data_dir(self) -> Path:
        """Return the absolute data directory path."""

        return PROJECT_ROOT / self.data_dir

    @property
    def upload_dir(self) -> Path:
        """Directory used for persisted user uploads."""

        return self.resolved_data_dir / self.upload_dir_name

    @property
    def vector_store_dir(self) -> Path:
        """Directory used by the vector database."""

        return self.resolved_data_dir / self.vector_store_dir_name

    @property
    def simple_vector_store_path(self) -> Path:
        """File path used by the lightweight JSON vector store."""

        return self.resolved_data_dir / self.simple_vector_store_filename

    @property
    def database_path(self) -> Path:
        """Absolute path to the SQLite file."""

        return self.resolved_data_dir / self.database_filename

    @property
    def database_url(self) -> str:
        """SQLAlchemy SQLite connection string."""

        return f"sqlite:///{self.database_path.as_posix()}"

    def ensure_directories(self) -> None:
        """Create runtime directories if they do not already exist."""

        self.resolved_data_dir.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.vector_store_dir.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cache settings to avoid repeated environment parsing."""

    return Settings()
