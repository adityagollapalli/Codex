"""Document summarization service."""

from __future__ import annotations

import re
from collections import Counter

from app.services.llm_provider import NullLLMProvider, OpenAIProvider


class SummarizerService:
    """Summarize text using an optional LLM or an extractive fallback."""

    sentence_pattern = re.compile(r"(?<=[.!?])\s+")
    token_pattern = re.compile(r"[A-Za-z][A-Za-z0-9_-]{2,}")

    def __init__(
        self,
        llm_provider: NullLLMProvider | OpenAIProvider,
        max_sentences: int = 4,
    ) -> None:
        self.llm_provider = llm_provider
        self.max_sentences = max_sentences

    def summarize(self, text: str) -> str:
        """Summarize input text with graceful fallback behavior."""

        llm_result = self.llm_provider.summarize(text) if self.llm_provider.available else None
        if llm_result and llm_result.content:
            return llm_result.content
        return self._extractive_summary(text)

    def _extractive_summary(self, text: str) -> str:
        sentences = [
            sentence.strip() for sentence in self.sentence_pattern.split(text) if sentence.strip()
        ]
        if not sentences:
            return "No text was available to summarize."
        if len(sentences) <= self.max_sentences:
            return " ".join(sentences)

        token_counts = Counter(
            token.lower() for token in self.token_pattern.findall(text) if len(token) > 3
        )
        scored = []
        for sentence in sentences:
            score = sum(
                token_counts[token.lower()] for token in self.token_pattern.findall(sentence)
            )
            scored.append((score, sentence))

        top_sentences = [
            sentence for _, sentence in sorted(scored, reverse=True)[: self.max_sentences]
        ]
        ordered = [sentence for sentence in sentences if sentence in top_sentences]
        return " ".join(ordered[: self.max_sentences])
