"""Text normalization helpers."""

from __future__ import annotations

import re


class TextCleaner:
    """Normalize extracted text before chunking."""

    _whitespace_pattern = re.compile(r"[ \t]+")
    _blank_line_pattern = re.compile(r"\n{3,}")
    _null_pattern = re.compile(r"[\x00-\x08\x0B-\x1F\x7F]")

    def clean(self, text: str) -> str:
        """Normalize whitespace and strip obvious control-character noise."""

        text = self._null_pattern.sub(" ", text)
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = self._whitespace_pattern.sub(" ", text)
        text = re.sub(r" ?\n ?", "\n", text)
        text = self._blank_line_pattern.sub("\n\n", text)
        return text.strip()
