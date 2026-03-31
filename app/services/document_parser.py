"""Document parsing utilities for PDFs, text files, and CSVs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


class DocumentParsingError(RuntimeError):
    """Raised when a document cannot be parsed successfully."""


class UnsupportedFileTypeError(ValueError):
    """Raised when a file extension is not supported."""


@dataclass(slots=True)
class ParsedDocument:
    """Normalized result of parsing a document."""

    text: str
    file_type: str
    page_count: int | None
    metadata: dict[str, Any]


class DocumentParser:
    """Parse supported document types into normalized text."""

    SUPPORTED_TYPES = {".pdf", ".txt", ".csv"}

    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse the provided file into text plus lightweight metadata."""

        suffix = file_path.suffix.lower()
        if suffix not in self.SUPPORTED_TYPES:
            raise UnsupportedFileTypeError(f"Unsupported file type: {suffix}")

        if suffix == ".pdf":
            return self._parse_pdf(file_path)
        if suffix == ".txt":
            return self._parse_txt(file_path)
        return self._parse_csv(file_path)

    def _parse_pdf(self, file_path: Path) -> ParsedDocument:
        try:
            import fitz
        except ImportError as exc:
            raise DocumentParsingError("PyMuPDF is required to parse PDF files.") from exc

        try:
            document = fitz.open(file_path)
        except Exception as exc:
            raise DocumentParsingError(f"Unable to open PDF: {file_path.name}") from exc

        page_texts: list[str] = []
        try:
            for page_index, page in enumerate(document, start=1):
                page_text = page.get_text("text")
                page_texts.append(f"[Page {page_index}]\n{page_text}")
        except Exception as exc:
            raise DocumentParsingError(
                f"Failed while reading PDF content: {file_path.name}"
            ) from exc
        finally:
            document.close()

        combined_text = "\n\n".join(page_texts).strip()
        metadata: dict[str, Any] = {"page_count": len(page_texts)}
        return ParsedDocument(
            text=combined_text,
            file_type="pdf",
            page_count=len(page_texts),
            metadata=metadata,
        )

    def _parse_txt(self, file_path: Path) -> ParsedDocument:
        try:
            raw_text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            raw_text = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            raise DocumentParsingError(f"Unable to read text file: {file_path.name}") from exc

        return ParsedDocument(
            text=raw_text,
            file_type="txt",
            page_count=None,
            metadata={},
        )

    def _parse_csv(self, file_path: Path) -> ParsedDocument:
        try:
            dataframe = pd.read_csv(file_path)
        except Exception as exc:
            raise DocumentParsingError(f"Unable to read CSV file: {file_path.name}") from exc

        if dataframe.empty:
            text = "CSV document is empty."
        else:
            rows: list[str] = []
            filled = dataframe.fillna("")
            for row_index, row in filled.iterrows():
                rendered_row = " | ".join(f"{column}={row[column]}" for column in filled.columns)
                rows.append(f"Row {row_index + 1}: {rendered_row}")
            text = "\n".join(rows)

        metadata = {
            "row_count": int(dataframe.shape[0]),
            "column_count": int(dataframe.shape[1]),
            "columns": [str(column) for column in dataframe.columns.tolist()],
        }
        return ParsedDocument(
            text=text,
            file_type="csv",
            page_count=None,
            metadata=metadata,
        )
