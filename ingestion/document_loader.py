"""File validation, stable IDs, and document-level text loading."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from ingestion.models import (
    DocumentLoadError,
    EmptyDocumentError,
    ExtractedDocument,
    UnsupportedFileTypeError,
)
from ingestion.text_extractor import decode_utf8, extract_pdf_pages

logger = logging.getLogger(__name__)
SUPPORTED_FILE_TYPES = frozenset({"pdf", "txt", "md"})


def validate_file_extension(filename: str) -> str:
    """Return a normalized supported extension or raise a clear error."""
    file_type = Path(filename).suffix.lower().lstrip(".")
    if file_type not in SUPPORTED_FILE_TYPES:
        supported = ", ".join(
            f".{extension}" for extension in sorted(SUPPORTED_FILE_TYPES)
        )
        raise UnsupportedFileTypeError(
            f"Unsupported file type for {Path(filename).name or 'document'}. "
            f"Supported formats: {supported}."
        )
    return file_type


def generate_document_id(filename: str, content: bytes) -> str:
    """Generate a stable ID from a normalized filename and the file bytes."""
    normalized_name = Path(filename).name.casefold().encode("utf-8", errors="replace")
    digest = hashlib.sha256(normalized_name + b"\0" + content).hexdigest()
    return f"doc_{digest[:32]}"


def _read_path(path: str | Path, expected_type: str) -> list[ExtractedDocument]:
    file_path = Path(path)
    actual_type = validate_file_extension(file_path.name)
    if actual_type != expected_type:
        raise UnsupportedFileTypeError(
            f"Expected a .{expected_type} document, received .{actual_type}."
        )
    try:
        content = file_path.read_bytes()
    except OSError as exc:
        logger.warning("Unable to read document %s", file_path.name)
        raise DocumentLoadError(
            f"Unable to read {file_path.name}. Check that it exists and is readable."
        ) from exc
    return load_document_bytes(
        file_path.name,
        content,
        source=str(file_path.resolve()),
    )


def load_pdf_document(path: str | Path) -> list[ExtractedDocument]:
    """Load a PDF file as one extracted section per non-empty page."""
    return _read_path(path, "pdf")


def load_txt_document(path: str | Path) -> list[ExtractedDocument]:
    """Load a UTF-8 plain-text document as one document-level section."""
    return _read_path(path, "txt")


def load_markdown_document(path: str | Path) -> list[ExtractedDocument]:
    """Load a UTF-8 Markdown document as one document-level section."""
    return _read_path(path, "md")


def load_document(path: str | Path) -> list[ExtractedDocument]:
    """Load a supported file path and preserve its source path in metadata."""
    file_type = validate_file_extension(Path(path).name)
    loaders = {
        "pdf": load_pdf_document,
        "txt": load_txt_document,
        "md": load_markdown_document,
    }
    return loaders[file_type](path)


def load_document_bytes(
    filename: str,
    content: bytes,
    source: str | None = None,
) -> list[ExtractedDocument]:
    """Load an uploaded file from bytes without writing it to disk."""
    file_type = validate_file_extension(filename)
    safe_filename = Path(filename).name or "document"
    source_label = source or safe_filename
    document_id = generate_document_id(safe_filename, content)

    if file_type == "pdf":
        sections = [
            ExtractedDocument(
                document_id=document_id,
                filename=safe_filename,
                file_type=file_type,
                source=source_label,
                page_number=page_number,
                text=text,
            )
            for page_number, text in extract_pdf_pages(content)
        ]
        if not sections:
            raise EmptyDocumentError(
                "No extractable text was found in this PDF. It may be empty or "
                "contain scanned images; OCR is not available in this phase."
            )
        return sections

    text = decode_utf8(content, safe_filename)
    if not text.strip():
        raise EmptyDocumentError(f"{safe_filename} contains no text.")

    return [
        ExtractedDocument(
            document_id=document_id,
            filename=safe_filename,
            file_type=file_type,
            source=source_label,
            page_number=None,
            text=text,
        )
    ]
