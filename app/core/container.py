"""Application service container."""

from __future__ import annotations

import logging

from app.core.config import Settings
from app.db.database import DatabaseManager
from app.services.chunker import TextChunker
from app.services.document_parser import DocumentParser
from app.services.document_service import DocumentService
from app.services.embedder import build_embedder
from app.services.keyword_extractor import KeywordExtractor
from app.services.llm_provider import build_llm_provider
from app.services.qa_engine import QAEngine
from app.services.summarizer import SummarizerService
from app.services.text_cleaner import TextCleaner
from app.services.vector_store import build_vector_store


class ServiceContainer:
    """Instantiate and expose shared services for the API."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.logger = logging.getLogger("documind")
        self.settings.ensure_directories()

        self.database = DatabaseManager(settings)
        self.database.create_tables()

        self.parser = DocumentParser()
        self.cleaner = TextCleaner()
        self.chunker = TextChunker(
            chunk_size_words=settings.chunk_size_words,
            chunk_overlap_words=settings.chunk_overlap_words,
        )
        self.embedder = build_embedder(settings=settings, logger=self.logger)
        self.vector_store = build_vector_store(settings=settings, logger=self.logger)
        self.llm_provider = build_llm_provider(settings)
        self.keyword_extractor = KeywordExtractor()
        self.summarizer = SummarizerService(
            llm_provider=self.llm_provider,
            max_sentences=settings.max_summary_sentences,
        )
        self.document_service = DocumentService(
            settings=settings,
            database=self.database,
            parser=self.parser,
            cleaner=self.cleaner,
            chunker=self.chunker,
            embedder=self.embedder,
            vector_store=self.vector_store,
            summarizer=self.summarizer,
            keyword_extractor=self.keyword_extractor,
            logger=self.logger,
        )
        self.qa_engine = QAEngine(
            embedder=self.embedder,
            vector_store=self.vector_store,
            llm_provider=self.llm_provider,
        )
