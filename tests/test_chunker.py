"""Tests for text chunking behavior."""

from app.services.chunker import TextChunker


def test_chunker_creates_overlapping_windows() -> None:
    chunker = TextChunker(chunk_size_words=5, chunk_overlap_words=2)
    text = "one two three four five six seven eight nine ten"

    chunks = chunker.chunk_text(text)

    assert len(chunks) == 3
    assert chunks[0].text == "one two three four five"
    assert chunks[1].text == "four five six seven eight"
    assert chunks[2].text == "seven eight nine ten"
