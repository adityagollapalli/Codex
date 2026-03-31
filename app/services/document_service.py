"""High-level document ingestion and metadata services."""

from __future__ import annotations

import logging
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy import desc, select

from app.core.config import Settings
from app.db.database import DatabaseManager
from app.db.models import ChunkRecord, DocumentRecord
from app.schemas.document import (
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentStatsResponse,
    DocumentSummaryItem,
    DocumentUploadResponse,
    KeywordResponse,
    SummaryResponse,
)
from app.services.chunker import TextChunker
from app.services.document_parser import (
    DocumentParser,
    DocumentParsingError,
    UnsupportedFileTypeError,
)
from app.services.embedder import Embedder
from app.services.keyword_extractor import KeywordExtractor
from app.services.summarizer import SummarizerService
from app.services.text_cleaner import TextCleaner
from app.services.vector_store import VectorChunk, VectorStore


class DocumentNotFoundError(LookupError):
    """Raised when a document ID does not exist."""


class DocumentService:
    """Coordinate persistence, parsing, chunking, and metadata reporting."""

    filename_pattern = re.compile(r"[^A-Za-z0-9._-]+")

    def __init__(
        self,
        settings: Settings,
        database: DatabaseManager,
        parser: DocumentParser,
        cleaner: TextCleaner,
        chunker: TextChunker,
        embedder: Embedder,
        vector_store: VectorStore,
        summarizer: SummarizerService,
        keyword_extractor: KeywordExtractor,
        logger: logging.Logger,
    ) -> None:
        self.settings = settings
        self.database = database
        self.parser = parser
        self.cleaner = cleaner
        self.chunker = chunker
        self.embedder = embedder
        self.vector_store = vector_store
        self.summarizer = summarizer
        self.keyword_extractor = keyword_extractor
        self.logger = logger

    def ingest_file(self, filename: str, content: bytes) -> DocumentUploadResponse:
        """Persist and process an uploaded file."""

        suffix = Path(filename).suffix.lower()
        if suffix not in self.settings.allowed_extensions:
            raise UnsupportedFileTypeError(f"Unsupported file type: {suffix}")

        max_bytes = self.settings.max_upload_size_mb * 1024 * 1024
        if len(content) > max_bytes:
            raise ValueError(
                f"Uploaded file exceeds the {self.settings.max_upload_size_mb} MB limit."
            )

        document_id = str(uuid4())
        safe_name = self._sanitize_filename(filename)
        stored_filename = f"{document_id}{suffix}"
        file_path = self.settings.upload_dir / stored_filename

        try:
            file_path.write_bytes(content)
            parsed = self.parser.parse(file_path)
            cleaned_text = self.cleaner.clean(parsed.text)
            if not cleaned_text:
                raise DocumentParsingError("Document did not contain any readable text.")

            chunks = self.chunker.chunk_text(cleaned_text)
            if not chunks:
                raise DocumentParsingError("Document text could not be chunked.")

            embeddings = self.embedder.embed_texts([chunk.text for chunk in chunks])
            word_count = len(cleaned_text.split())
            reading_minutes = max(1, math.ceil(word_count / self.settings.reading_speed_wpm))

            document = DocumentRecord(
                id=document_id,
                filename=safe_name,
                stored_filename=stored_filename,
                file_path=str(file_path),
                file_type=parsed.file_type,
                file_size_bytes=len(content),
                upload_timestamp=datetime.now(timezone.utc),
                page_count=parsed.page_count,
                chunk_count=len(chunks),
                word_count=word_count,
                estimated_reading_minutes=reading_minutes,
                summary_status="pending",
                source_metadata=parsed.metadata,
            )
            chunk_rows = [
                ChunkRecord(
                    id=self._chunk_id(document_id, chunk.chunk_index),
                    document_id=document_id,
                    chunk_index=chunk.chunk_index,
                    text=chunk.text,
                    word_count=chunk.word_count,
                    start_word=chunk.start_word,
                    end_word=chunk.end_word,
                    page_number=chunk.page_number,
                    chunk_metadata={},
                )
                for chunk in chunks
            ]
            vector_chunks = [
                VectorChunk(
                    id=self._chunk_id(document_id, chunk.chunk_index),
                    document_id=document_id,
                    filename=safe_name,
                    chunk_index=chunk.chunk_index,
                    text=chunk.text,
                    embedding=embedding,
                    page_number=chunk.page_number,
                )
                for chunk, embedding in zip(chunks, embeddings, strict=True)
            ]

            with self.database.session_scope() as session:
                session.add(document)
                session.add_all(chunk_rows)

            self.vector_store.upsert_chunks(vector_chunks)
            self.logger.info("Ingested document %s with %s chunks.", document_id, len(chunks))
            return DocumentUploadResponse(
                document=self._to_summary_item(document),
                metadata=parsed.metadata,
            )
        except Exception:
            self._cleanup_failed_ingestion(document_id=document_id, file_path=file_path)
            raise

    def list_documents(self) -> DocumentListResponse:
        """Return all documents ordered by most recent upload."""

        with self.database.session_scope() as session:
            statement = select(DocumentRecord).order_by(desc(DocumentRecord.upload_timestamp))
            records = session.scalars(statement).all()
            items = [self._to_summary_item(record) for record in records]
            return DocumentListResponse(items=items, total=len(items))

    def get_document(self, document_id: str) -> DocumentDetailResponse:
        """Fetch a single document's persisted metadata."""

        with self.database.session_scope() as session:
            record = session.get(DocumentRecord, document_id)
            if record is None:
                raise DocumentNotFoundError(document_id)

            return DocumentDetailResponse(
                id=record.id,
                filename=record.filename,
                stored_filename=record.stored_filename,
                file_type=record.file_type,
                file_size_bytes=record.file_size_bytes,
                upload_timestamp=record.upload_timestamp,
                page_count=record.page_count,
                chunk_count=record.chunk_count,
                word_count=record.word_count,
                estimated_reading_minutes=record.estimated_reading_minutes,
                summary_status=record.summary_status,
                summary_text=record.summary_text,
                source_metadata=record.source_metadata,
            )

    def summarize_document(self, document_id: str) -> SummaryResponse:
        """Generate or refresh a summary for a document."""

        with self.database.session_scope() as session:
            record = session.get(DocumentRecord, document_id)
            if record is None:
                raise DocumentNotFoundError(document_id)

            text = self._document_text(session=session, document_id=document_id)
            summary = self.summarizer.summarize(text)
            record.summary_text = summary
            record.summary_status = "completed"
            record.summary_generated_at = datetime.now(timezone.utc)
            session.add(record)

            return SummaryResponse(
                document_id=record.id,
                summary=summary,
                summary_status=record.summary_status,
            )

    def extract_keywords(self, document_id: str, top_n: int = 10) -> KeywordResponse:
        """Return keywords for the selected document."""

        with self.database.session_scope() as session:
            record = session.get(DocumentRecord, document_id)
            if record is None:
                raise DocumentNotFoundError(document_id)

            text = self._document_text(session=session, document_id=document_id)
            keywords = self.keyword_extractor.extract(text, top_n=top_n)
            return KeywordResponse(document_id=document_id, keywords=keywords)

    def document_stats(self, document_id: str) -> DocumentStatsResponse:
        """Return document statistics and top keywords."""

        with self.database.session_scope() as session:
            record = session.get(DocumentRecord, document_id)
            if record is None:
                raise DocumentNotFoundError(document_id)

            text = self._document_text(session=session, document_id=document_id)
            return DocumentStatsResponse(
                document_id=record.id,
                filename=record.filename,
                file_type=record.file_type,
                word_count=record.word_count,
                chunk_count=record.chunk_count,
                page_count=record.page_count,
                estimated_reading_minutes=record.estimated_reading_minutes,
                top_keywords=self.keyword_extractor.extract(text, top_n=8),
            )

    def validate_document_ids(self, document_ids: list[str]) -> list[str]:
        """Ensure all requested document IDs exist before retrieval."""

        with self.database.session_scope() as session:
            existing_ids = {
                row[0]
                for row in session.execute(
                    select(DocumentRecord.id).where(DocumentRecord.id.in_(document_ids))
                ).all()
            }
        missing = sorted(set(document_ids) - existing_ids)
        if missing:
            raise DocumentNotFoundError(", ".join(missing))
        return document_ids

    def _document_text(self, session, document_id: str) -> str:  # type: ignore[no-untyped-def]
        statement = (
            select(ChunkRecord)
            .where(ChunkRecord.document_id == document_id)
            .order_by(ChunkRecord.chunk_index)
        )
        chunks = session.scalars(statement).all()
        return " ".join(chunk.text for chunk in chunks)

    def _cleanup_failed_ingestion(self, document_id: str, file_path: Path) -> None:
        """Best-effort cleanup after a failed ingestion attempt."""

        try:
            self.vector_store.delete_document(document_id)
        except Exception:
            pass

        try:
            with self.database.session_scope() as session:
                record = session.get(DocumentRecord, document_id)
                if record is not None:
                    session.delete(record)
        except Exception:
            pass

        if file_path.exists():
            file_path.unlink(missing_ok=True)

    def _sanitize_filename(self, filename: str) -> str:
        sanitized = self.filename_pattern.sub("_", Path(filename).name).strip("._")
        return sanitized or "document"

    @staticmethod
    def _chunk_id(document_id: str, chunk_index: int) -> str:
        return f"{document_id}-chunk-{chunk_index}"

    @staticmethod
    def _to_summary_item(record: DocumentRecord) -> DocumentSummaryItem:
        return DocumentSummaryItem(
            id=record.id,
            filename=record.filename,
            file_type=record.file_type,
            upload_timestamp=record.upload_timestamp,
            chunk_count=record.chunk_count,
            word_count=record.word_count,
            page_count=record.page_count,
            estimated_reading_minutes=record.estimated_reading_minutes,
            summary_status=record.summary_status,
        )
