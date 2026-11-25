"""Orchestrate Phase 2 chunks through Gemini and persistent ChromaDB."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import time
from typing import Callable, Collection, Iterable

from core.embedding_service import (
    EmbeddingService,
    EmbeddingServiceError,
)
from ingestion.models import DocumentChunk, DocumentProcessingResult
from vectorstore.chroma_store import ChromaStore, VectorStoreError

logger = logging.getLogger(__name__)
IndexProgressCallback = Callable[[int, int], None]


@dataclass(frozen=True)
class DocumentIndexResult:
    """Indexing result and counts for one previously processed document."""

    document_id: str
    filename: str
    status: str
    chunk_count: int
    embeddings_created: int
    vectors_stored: int
    failures: int
    error: str | None = None


@dataclass(frozen=True)
class IndexingReport:
    """Batch-level indexing counts, outcomes, and elapsed time."""

    documents_processed: int
    pages_extracted: int
    chunks_generated: int
    embeddings_created: int
    vectors_stored: int
    failures: int
    failed_documents: int
    duplicate_documents: int
    duration_seconds: float
    document_results: tuple[DocumentIndexResult, ...]


def index_processed_documents(
    documents: Iterable[DocumentProcessingResult],
    *,
    embedding_service: EmbeddingService,
    vector_store: ChromaStore,
    reindex_document_ids: Collection[str] = (),
    progress_callback: IndexProgressCallback | None = None,
) -> IndexingReport:
    """Embed and store successful Phase 2 results without reloading files.

    Existing chunk IDs are skipped. A partial prior run is resumed by embedding
    only its missing chunks. Re-indexing is explicit and scoped to the provided
    document IDs.
    """
    started_at = time.monotonic()
    processed = [
        document
        for document in documents
        if document.status == "processed" and document.document_id
    ]
    document_results: dict[int, DocumentIndexResult] = {}
    pending_by_document: dict[
        str, tuple[int, DocumentProcessingResult, list[DocumentChunk]]
    ] = {}
    seen_document_ids: set[str] = set()

    for result_index, document in enumerate(processed):
        document_id = document.document_id
        if document_id in seen_document_ids:
            document_results[result_index] = DocumentIndexResult(
                document_id=document_id,
                filename=document.filename,
                status="duplicate",
                chunk_count=len(document.chunks),
                embeddings_created=0,
                vectors_stored=0,
                failures=0,
            )
            continue
        seen_document_ids.add(document_id)
        if not document.chunks:
            document_results[result_index] = DocumentIndexResult(
                document_id=document_id,
                filename=document.filename,
                status="failed",
                chunk_count=0,
                embeddings_created=0,
                vectors_stored=0,
                failures=1,
                error="No chunks were available for indexing.",
            )
            continue

        expected_ids = {chunk.chunk_id for chunk in document.chunks}
        try:
            existing_ids = (
                set()
                if document_id in reindex_document_ids
                else vector_store.get_document_chunk_ids(document_id)
            )
        except VectorStoreError as exc:
            document_results[result_index] = DocumentIndexResult(
                document_id=document_id,
                filename=document.filename,
                status="failed",
                chunk_count=len(document.chunks),
                embeddings_created=0,
                vectors_stored=0,
                failures=len(document.chunks),
                error=str(exc),
            )
            continue

        if existing_ids and not existing_ids.issubset(expected_ids):
            document_results[result_index] = DocumentIndexResult(
                document_id=document_id,
                filename=document.filename,
                status="failed",
                chunk_count=len(document.chunks),
                embeddings_created=0,
                vectors_stored=0,
                failures=len(document.chunks),
                error=(
                    "This document has a different indexed chunk set. Delete it "
                    "or explicitly re-index it before continuing."
                ),
            )
            continue
        if existing_ids == expected_ids and document_id not in reindex_document_ids:
            document_results[result_index] = DocumentIndexResult(
                document_id=document_id,
                filename=document.filename,
                status="duplicate",
                chunk_count=len(document.chunks),
                embeddings_created=0,
                vectors_stored=0,
                failures=0,
            )
            continue

        pending_by_document[document_id] = (
            result_index,
            document,
            [chunk for chunk in document.chunks if chunk.chunk_id not in existing_ids],
        )

    pending_chunks = [
        chunk
        for _result_index, _document, chunks in pending_by_document.values()
        for chunk in chunks
    ]
    embedding_results = None
    if pending_chunks:
        try:
            embedding_results = embedding_service.embed_chunks(
                pending_chunks,
                progress_callback=progress_callback,
            )
        except EmbeddingServiceError as exc:
            logger.warning(
                "Gemini embedding pipeline stopped (%s)",
                type(exc).__name__,
            )
            for document_id, (result_index, document, chunks) in (
                pending_by_document.items()
            ):
                document_results[result_index] = DocumentIndexResult(
                    document_id=document_id,
                    filename=document.filename,
                    status="failed",
                    chunk_count=len(document.chunks),
                    embeddings_created=0,
                    vectors_stored=0,
                    failures=len(chunks),
                    error=str(exc),
                )

    if embedding_results is not None:
        vector_by_id = {
            embedding.chunk_id: embedding.values
            for embedding in embedding_results.embeddings
        }
        failure_by_id = {
            failure.chunk_id: failure.message
            for failure in embedding_results.failures
        }
        for document_id, (result_index, document, chunks) in (
            pending_by_document.items()
        ):
            document_failures = [
                failure_by_id[chunk.chunk_id]
                for chunk in chunks
                if chunk.chunk_id in failure_by_id
            ]
            if document_id in reindex_document_ids and document_failures:
                document_results[result_index] = DocumentIndexResult(
                    document_id=document_id,
                    filename=document.filename,
                    status="failed",
                    chunk_count=len(document.chunks),
                    embeddings_created=sum(
                        chunk.chunk_id in vector_by_id for chunk in chunks
                    ),
                    vectors_stored=0,
                    failures=len(document_failures),
                    error=" ".join(dict.fromkeys(document_failures)),
                )
                continue
            try:
                document_vectors = {
                    chunk.chunk_id: vector_by_id[chunk.chunk_id]
                    for chunk in chunks
                    if chunk.chunk_id in vector_by_id
                }
                store_result = vector_store.add_document(
                    document.chunks,
                    document_vectors,
                    reindex=document_id in reindex_document_ids,
                    batch_size=embedding_service.settings.embedding_batch_size,
                )
                errors = document_failures.copy()
                if store_result.error:
                    errors.append(store_result.error)
                document_results[result_index] = DocumentIndexResult(
                    document_id=document_id,
                    filename=document.filename,
                    status=store_result.status,
                    chunk_count=len(document.chunks),
                    embeddings_created=sum(
                        chunk.chunk_id in vector_by_id for chunk in chunks
                    ),
                    vectors_stored=store_result.stored_count,
                    failures=store_result.failed_count,
                    error=" ".join(dict.fromkeys(errors)) or None,
                )
            except VectorStoreError as exc:
                logger.warning(
                    "ChromaDB document storage failed (%s)",
                    type(exc).__name__,
                )
                document_results[result_index] = DocumentIndexResult(
                    document_id=document_id,
                    filename=document.filename,
                    status="failed",
                    chunk_count=len(document.chunks),
                    embeddings_created=sum(
                        chunk.chunk_id in vector_by_id for chunk in chunks
                    ),
                    vectors_stored=0,
                    failures=len(chunks),
                    error=str(exc),
                )

    ordered_results = tuple(
        document_results[index]
        for index in range(len(processed))
        if index in document_results
    )
    return IndexingReport(
        documents_processed=len(processed),
        pages_extracted=sum(document.pages_extracted for document in processed),
        chunks_generated=sum(len(document.chunks) for document in processed),
        embeddings_created=sum(
            result.embeddings_created for result in ordered_results
        ),
        vectors_stored=sum(result.vectors_stored for result in ordered_results),
        failures=sum(result.failures for result in ordered_results),
        failed_documents=sum(
            result.status in {"failed", "partial"} for result in ordered_results
        ),
        duplicate_documents=sum(
            result.status == "duplicate" for result in ordered_results
        ),
        duration_seconds=time.monotonic() - started_at,
        document_results=ordered_results,
    )
