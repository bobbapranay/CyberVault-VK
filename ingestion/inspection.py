"""Read-only statistics and lookup helpers for generated chunks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ingestion.models import DocumentChunk


@dataclass(frozen=True)
class ChunkInspection:
    """Aggregate statistics and immutable chunk previews."""

    total_documents_processed: int
    total_pages_extracted: int
    total_chunks_generated: int
    average_chunk_length: float
    minimum_chunk_length: int
    maximum_chunk_length: int
    sample_chunks: tuple[DocumentChunk, ...]


def inspect_chunks(
    chunks: Iterable[DocumentChunk],
    *,
    total_documents_processed: int | None = None,
    total_pages_extracted: int | None = None,
    sample_size: int = 5,
) -> ChunkInspection:
    """Calculate token-length statistics without mutating supplied chunks."""
    if sample_size < 0:
        raise ValueError("Sample size must be zero or greater.")

    chunk_list = tuple(chunks)
    lengths = [chunk.token_count for chunk in chunk_list]
    document_count = (
        total_documents_processed
        if total_documents_processed is not None
        else len({chunk.document_id for chunk in chunk_list})
    )
    page_count = (
        total_pages_extracted
        if total_pages_extracted is not None
        else len(
            {
                (chunk.document_id, chunk.page_number)
                for chunk in chunk_list
                if chunk.page_number is not None
            }
        )
    )
    return ChunkInspection(
        total_documents_processed=document_count,
        total_pages_extracted=page_count,
        total_chunks_generated=len(chunk_list),
        average_chunk_length=sum(lengths) / len(lengths) if lengths else 0.0,
        minimum_chunk_length=min(lengths, default=0),
        maximum_chunk_length=max(lengths, default=0),
        sample_chunks=chunk_list[:sample_size],
    )


def get_chunk_by_id(
    chunks: Iterable[DocumentChunk],
    chunk_id: str,
) -> DocumentChunk:
    """Return a matching immutable chunk without changing its collection."""
    for chunk in chunks:
        if chunk.chunk_id == chunk_id:
            return chunk
    raise KeyError(f"No chunk found with ID {chunk_id!r}.")
