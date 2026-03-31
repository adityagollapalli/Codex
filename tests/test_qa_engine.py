"""Tests for the grounded QA engine."""

from app.services.embedder import HashingEmbedder
from app.services.llm_provider import NullLLMProvider
from app.services.qa_engine import QAEngine
from app.services.vector_store import RetrievedChunk


class FakeVectorStore:
    """Simple stand-in for vector store queries."""

    def __init__(self, results: list[RetrievedChunk]) -> None:
        self.results = results

    def query(self, query_embedding, top_k, document_ids=None):  # type: ignore[no-untyped-def]
        return self.results[:top_k]


def test_qa_engine_returns_grounded_answer_with_citations() -> None:
    chunks = [
        RetrievedChunk(
            chunk_id="doc-1-chunk-0",
            document_id="doc-1",
            filename="report.txt",
            chunk_index=0,
            text="DocuMind supports PDF, TXT, and CSV uploads for downstream question answering.",
            score=0.84,
        ),
        RetrievedChunk(
            chunk_id="doc-1-chunk-1",
            document_id="doc-1",
            filename="report.txt",
            chunk_index=1,
            text="The system indexes overlapping chunks and returns cited snippets.",
            score=0.73,
        ),
    ]
    engine = QAEngine(
        embedder=HashingEmbedder(),
        vector_store=FakeVectorStore(chunks),  # type: ignore[arg-type]
        llm_provider=NullLLMProvider(),
    )

    response = engine.answer_question("What file types does DocuMind support?", top_k=2)

    assert "PDF" in response.answer
    assert len(response.citations) == 2
    assert response.citations[0].filename == "report.txt"
