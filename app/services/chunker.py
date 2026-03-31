"""Chunking logic for long-form document text."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TextChunk:
    """A chunk of document text with positional metadata."""

    chunk_index: int
    text: str
    start_word: int
    end_word: int
    word_count: int
    page_number: int | None = None


class TextChunker:
    """Split text into overlapping word windows."""

    def __init__(self, chunk_size_words: int, chunk_overlap_words: int) -> None:
        if chunk_overlap_words >= chunk_size_words:
            raise ValueError("chunk_overlap_words must be smaller than chunk_size_words")

        self.chunk_size_words = chunk_size_words
        self.chunk_overlap_words = chunk_overlap_words

    def chunk_text(self, text: str) -> list[TextChunk]:
        """Chunk text into overlapping word windows."""

        words = text.split()
        if not words:
            return []

        step = self.chunk_size_words - self.chunk_overlap_words
        chunks: list[TextChunk] = []

        for chunk_index, start in enumerate(range(0, len(words), step)):
            window = words[start : start + self.chunk_size_words]
            if not window:
                continue

            end = start + len(window)
            chunks.append(
                TextChunk(
                    chunk_index=chunk_index,
                    text=" ".join(window),
                    start_word=start,
                    end_word=end,
                    word_count=len(window),
                    page_number=self._guess_page_number(window),
                )
            )

            if end >= len(words):
                break

        return chunks

    @staticmethod
    def _guess_page_number(words: list[str]) -> int | None:
        """Infer a page marker if the parser included `[Page N]` tokens."""

        for index, token in enumerate(words):
            if token == "[Page" and index + 1 < len(words):
                candidate = words[index + 1].rstrip("]")
                if candidate.isdigit():
                    return int(candidate)
        return None
