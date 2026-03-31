"""Tests for document parsing helpers."""

from pathlib import Path

import pytest

from app.services.document_parser import DocumentParser, UnsupportedFileTypeError


def test_parse_txt_document(tmp_path: Path) -> None:
    parser = DocumentParser()
    path = tmp_path / "notes.txt"
    path.write_text("Alpha\nBeta", encoding="utf-8")

    parsed = parser.parse(path)

    assert parsed.file_type == "txt"
    assert parsed.text == "Alpha\nBeta"


def test_parse_csv_document(tmp_path: Path) -> None:
    parser = DocumentParser()
    path = tmp_path / "table.csv"
    path.write_text("name,score\nAda,95\nGrace,98\n", encoding="utf-8")

    parsed = parser.parse(path)

    assert parsed.file_type == "csv"
    assert "Row 1: name=Ada | score=95" in parsed.text
    assert parsed.metadata["row_count"] == 2


def test_parse_unsupported_document_type(tmp_path: Path) -> None:
    parser = DocumentParser()
    path = tmp_path / "archive.docx"
    path.write_text("content", encoding="utf-8")

    with pytest.raises(UnsupportedFileTypeError):
        parser.parse(path)
