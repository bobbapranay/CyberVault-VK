"""Per-document batch processing with isolated failures and deduplication."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Collection, Iterable

from config import load_settings
from ingestion.chunker import chunk_documents, validate_chunking_parameters
from ingestion.document_loader import (
    generate_document_id,
    load_document_bytes,
    validate_file_extension,
)
from ingestion.models import (
    ChunkingError,
    DocumentInput,
    DocumentLoadError,
    DocumentProcessingResult,
)

logger = logging.getLogger(__name__)
ProgressCallback = Callable[[int, int, str], None]


def ingest_documents(
    documents: Iterable[DocumentInput],
    *,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
    already_processed_ids: Collection[str] = (),
    progress_callback: ProgressCallback | None = None,
) -> list[DocumentProcessingResult]:
    """Load and chunk each input independently, preserving batch progress."""
    inputs = list(documents)
    if not inputs:
        return []

    if chunk_size is None or chunk_overlap is None:
        settings = load_settings()
        chunk_size = settings.chunk_size if chunk_size is None else chunk_size
        chunk_overlap = (
            settings.chunk_overlap if chunk_overlap is None else chunk_overlap
        )
    validate_chunking_parameters(chunk_size, chunk_overlap)

    seen_document_ids = set(already_processed_ids)
    results: list[DocumentProcessingResult] = []
    total = len(inputs)
    for index, document in enumerate(inputs):
        filename = "document"
        file_type = "unknown"
        document_id: str | None = None
        try:
            filename = Path(document.filename).name or "document"
            file_type = validate_file_extension(document.filename)
            document_id = generate_document_id(document.filename, document.content)
            if document_id in seen_document_ids:
                result = DocumentProcessingResult(
                    filename=filename,
                    file_type=file_type,
                    document_id=document_id,
                    pages_extracted=0,
                    chunks=(),
                    status="duplicate",
                )
            else:
                sections = load_document_bytes(
                    document.filename,
                    document.content,
                    source=document.source,
                )
                chunks = chunk_documents(
                    sections,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                )
                if not chunks:
                    raise ChunkingError(
                        "No text chunks were generated from this document."
                    )
                result = DocumentProcessingResult(
                        filename=filename,
                    file_type=file_type,
                    document_id=document_id,
                    pages_extracted=sum(
                        section.page_number is not None for section in sections
                    ),
                    chunks=tuple(chunks),
                    status="processed",
                )
                seen_document_ids.add(document_id)
        except (DocumentLoadError, ChunkingError) as exc:
            logger.warning("Ingestion failed for %s: %s", filename, exc)
            result = DocumentProcessingResult(
                filename=filename,
                file_type=file_type,
                document_id=document_id,
                pages_extracted=0,
                chunks=(),
                status="failed",
                error=str(exc),
            )
        except Exception:
            logger.exception("Unexpected ingestion error for %s", filename)
            result = DocumentProcessingResult(
                filename=filename,
                file_type=file_type,
                document_id=document_id,
                pages_extracted=0,
                chunks=(),
                status="failed",
                error="An unexpected error occurred while processing this file.",
            )

        results.append(result)
        if progress_callback is not None:
            progress_callback(index + 1, total, filename)
    return results
