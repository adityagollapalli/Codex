"""Grounded question-answering service."""

from __future__ import annotations

import re
from collections import Counter

from app.schemas.query import Citation, QueryResponse
from app.services.embedder import Embedder
from app.services.llm_provider import NullLLMProvider, OpenAIProvider
from app.services.vector_store import RetrievedChunk, VectorStore


class QAEngine:
    """Perform retrieval and synthesize grounded answers."""

    sentence_pattern = re.compile(r"(?<=[.!?])\s+")
    token_pattern = re.compile(r"[A-Za-z][A-Za-z0-9_-]+")

    def __init__(
        self,
        embedder: Embedder,
        vector_store: VectorStore,
        llm_provider: NullLLMProvider | OpenAIProvider,
    ) -> None:
        self.embedder = embedder
        self.vector_store = vector_store
        self.llm_provider = llm_provider

    def answer_question(
        self,
        question: str,
        top_k: int,
        document_ids: list[str] | None = None,
    ) -> QueryResponse:
        """Retrieve relevant chunks and produce a grounded answer."""

        query_embedding = self.embedder.embed_query(question)
        retrieved_chunks = self.vector_store.query(
            query_embedding=query_embedding,
            top_k=top_k,
            document_ids=document_ids,
        )

        if not retrieved_chunks:
            return QueryResponse(
                question=question,
                answer=(
                    "I could not find enough supporting context in the indexed "
                    "documents to answer that question."
                ),
                citations=[],
                confidence_note="No relevant chunks were retrieved.",
                retrieval_count=0,
            )

        answer = self._generate_answer(question=question, chunks=retrieved_chunks)
        citations = [
            Citation(
                document_id=chunk.document_id,
                filename=chunk.filename,
                chunk_id=chunk.chunk_id,
                chunk_index=chunk.chunk_index,
                snippet=self._truncate(chunk.text),
                score=chunk.score,
                page_number=chunk.page_number,
            )
            for chunk in retrieved_chunks
        ]
        confidence_note = self._confidence_note(retrieved_chunks)
        return QueryResponse(
            question=question,
            answer=answer,
            citations=citations,
            confidence_note=confidence_note,
            retrieval_count=len(retrieved_chunks),
        )

    def _generate_answer(self, question: str, chunks: list[RetrievedChunk]) -> str:
        context = "\n\n".join(
            f"[{chunk.filename}#chunk-{chunk.chunk_index}] {chunk.text}" for chunk in chunks
        )
        llm_result = (
            self.llm_provider.answer(question, context) if self.llm_provider.available else None
        )
        if llm_result and llm_result.content:
            return llm_result.content

        question_terms = {
            token.lower() for token in self.token_pattern.findall(question) if len(token) > 2
        }
        sentence_scores: list[tuple[float, str]] = []

        for chunk in chunks:
            for sentence in self.sentence_pattern.split(chunk.text):
                sentence = sentence.strip()
                if not sentence:
                    continue
                tokens = [token.lower() for token in self.token_pattern.findall(sentence)]
                overlap = len(question_terms.intersection(tokens))
                frequency_score = sum(Counter(tokens).values())
                sentence_scores.append(
                    (overlap * 10 + frequency_score * 0.05 + chunk.score, sentence)
                )

        best_sentences = [sentence for _, sentence in sorted(sentence_scores, reverse=True)[:3]]
        if not best_sentences:
            return (
                "I found related passages, but they did not contain enough clear "
                "evidence to form a grounded answer."
            )
        return " ".join(best_sentences)

    @staticmethod
    def _truncate(text: str, limit: int = 220) -> str:
        normalized = " ".join(text.split())
        if len(normalized) <= limit:
            return normalized
        return normalized[: limit - 3].rstrip() + "..."

    @staticmethod
    def _confidence_note(chunks: list[RetrievedChunk]) -> str:
        average_score = sum(chunk.score for chunk in chunks) / len(chunks)
        if average_score >= 0.65:
            return "High confidence: multiple closely matched chunks support this answer."
        if average_score >= 0.45:
            return (
                "Moderate confidence: the answer is grounded, but the supporting "
                "chunks are somewhat broad."
            )
        return "Low confidence: related chunks were found, but the match strength was weak."
