"""Immutable document and ingestion data models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


class DocumentLoadError(ValueError):
    """Raised when a document cannot be read or extracted."""


class UnsupportedFileTypeError(DocumentLoadError):
    """Raised when a document has an unsupported extension."""


class EmptyDocumentError(DocumentLoadError):
    """Raised when a document contains no extractable text."""


class ChunkingError(ValueError):
    """Raised when text cannot be divided using the requested settings."""


@dataclass(frozen=True)
class ExtractedDocument:
    """A text section with the metadata needed to trace it to its source."""

    document_id: str
    filename: str
    file_type: str
    source: str
    text: str
    page_number: int | None = None

    @property
    def metadata(self) -> dict[str, str | int | None]:
        """Return source metadata; non-paginated files use ``None`` for page."""
        return {
            "document_id": self.document_id,
            "filename": self.filename,
            "file_type": self.file_type,
            "page_number": self.page_number,
            "source": self.source,
        }


@dataclass(frozen=True)
class DocumentChunk:
    """A stable, token-counted section of an extracted document."""

    chunk_id: str
    document_id: str
    filename: str
    file_type: str
    source: str
    chunk_index: int
    page_number: int | None
    text: str
    token_count: int

    @property
    def metadata(self) -> dict[str, str | int | None]:
        """Return chunk and source metadata, excluding the chunk text."""
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "filename": self.filename,
            "file_type": self.file_type,
            "source": self.source,
            "chunk_index": self.chunk_index,
            "page_number": self.page_number,
            "token_count": self.token_count,
        }


@dataclass(frozen=True)
class DocumentInput:
    """An uploaded document's filename, bytes, and optional source label."""

    filename: str
    content: bytes
    source: str | None = None


DocumentStatus = Literal["processed", "duplicate", "failed"]


@dataclass(frozen=True)
class DocumentProcessingResult:
    """Outcome for a single document in a batch."""

    filename: str
    file_type: str
    document_id: str | None
    pages_extracted: int
    chunks: tuple[DocumentChunk, ...]
    status: DocumentStatus
    error: str | None = None
