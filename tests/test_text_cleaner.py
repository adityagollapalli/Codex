"""Tests for the text normalization service."""

from app.services.text_cleaner import TextCleaner


def test_cleaner_normalizes_whitespace_and_control_characters() -> None:
    cleaner = TextCleaner()

    cleaned = cleaner.clean("Hello\x00   world\r\n\r\n\r\nThis\t\tis   text.")

    assert cleaned == "Hello world\n\nThis is text."
