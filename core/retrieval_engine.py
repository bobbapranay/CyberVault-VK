"""Semantic retrieval using Gemini query embeddings and ChromaDB."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import time
from typing import Any, Mapping, Sequence

from core.embedding_service import (
    EmbeddingService,
    EmbeddingServiceError,
)
from vectorstore.chroma_store import ChromaStore, VectorStoreError

logger = logging.getLogger(__name__)
UNPAGINATED_PAGE_NUMBER = -1


class RetrievalError(RuntimeError):
    """Raised when a retrieval request cannot be completed."""


@dataclass(frozen=True)
class RetrievedChunk:
    """One ranked source chunk and its original cosine distance."""

    rank: int
    chunk_id: str
    document_id: str
    filename: str
    file_type: str
    source: str
    chunk_index: int
    page_number: int | None
    token_count: int
    cosine_distance: float
    text: str


@dataclass(frozen=True)
class RetrievalResult:
    """Read-only retrieval response and execution statistics."""

    query: str
    requested_top_k: int
    maximum_distance: float | None
    returned_count: int
    duration_seconds: float
    chunks: tuple[RetrievedChunk, ...]


def _nested_first(result: Mapping[str, Any], key: str) -> list[Any]:
    value = result.get(key)
    if not isinstance(value, (list, tuple)) or not value:
        return []
    first = value[0]
    return list(first) if isinstance(first, (list, tuple)) else []


def _safe_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


def _safe_float(value: Any) -> float:
    if isinstance(value, bool):
        raise RetrievalError("ChromaDB returned a malformed cosine distance.")
    if not isinstance(value, (int, float)):
        raise RetrievalError("ChromaDB returned a malformed cosine distance.")
    distance = float(value)
    if not (-2.0 <= distance <= 2.0):
        raise RetrievalError("ChromaDB returned an invalid cosine distance.")
    import math

    if not math.isfinite(distance):
        raise RetrievalError("ChromaDB returned a non-finite cosine distance.")
    return distance


def inspect_retrieval(result: RetrievalResult) -> dict[str, Any]:
    """Return a read-only, serializable inspection view of a retrieval result."""
    return {
        "query": result.query,
        "requested_top_k": result.requested_top_k,
        "maximum_distance": result.maximum_distance,
        "returned_count": result.returned_count,
        "duration_seconds": result.duration_seconds,
        "results": [
            {
                "rank": chunk.rank,
                "filename": chunk.filename,
                "page_number": (
                    "Document-level source"
                    if chunk.page_number is None
                    or chunk.page_number == UNPAGINATED_PAGE_NUMBER
                    else chunk.page_number
                ),
                "document_id": chunk.document_id,
                "chunk_id": chunk.chunk_id,
                "chunk_index": chunk.chunk_index,
                "cosine_distance": chunk.cosine_distance,
                "text": chunk.text,
            }
            for chunk in result.chunks
        ],
    }


def retrieve_documents(
    query: str,
    *,
    top_k: int = 5,
    maximum_top_k: int = 20,
    maximum_distance: float | None = None,
    embedding_service: EmbeddingService,
    vector_store: ChromaStore,
) -> RetrievalResult:
    """Embed a query and rank source chunks by ChromaDB cosine distance.

    ChromaDB cosine distance is lower for closer matches. The optional threshold
    retains only chunks with ``cosine_distance <= maximum_distance``; no
    similarity percentage or confidence score is fabricated.
    """
    if not isinstance(query, str) or not query.strip():
        raise RetrievalError("Search query must not be empty.")
    if isinstance(top_k, bool) or not isinstance(top_k, int):
        raise RetrievalError("Retrieval top-k must be a positive integer.")
    if top_k <= 0:
        raise RetrievalError("Retrieval top-k must be greater than zero.")
    if top_k > maximum_top_k:
        raise RetrievalError(
            f"Retrieval top-k cannot exceed the configured maximum of "
            f"{maximum_top_k}."
        )
    if maximum_distance is not None:
        if isinstance(maximum_distance, bool):
            raise RetrievalError("The retrieval distance threshold is invalid.")
        if not isinstance(maximum_distance, (int, float)):
            raise RetrievalError("The retrieval distance threshold is invalid.")
        if not 0.0 <= float(maximum_distance) <= 2.0:
            raise RetrievalError(
                "The retrieval distance threshold must be between 0.0 and 2.0."
            )

    started_at = time.monotonic()
    try:
        vector_count = vector_store.get_vector_count()
    except VectorStoreError as exc:
        raise RetrievalError(
            "Unable to verify the persistent vector collection."
        ) from exc
    if vector_count == 0:
        return RetrievalResult(
            query=query.strip(),
            requested_top_k=top_k,
            maximum_distance=maximum_distance,
            returned_count=0,
            duration_seconds=time.monotonic() - started_at,
            chunks=(),
        )

    try:
        query_embedding = embedding_service.embed_query(query)
    except EmbeddingServiceError as exc:
        logger.warning("Query embedding failed (%s)", type(exc).__name__)
        raise RetrievalError(str(exc)) from exc

    if len(query_embedding) != embedding_service.settings.embedding_dimension:
        raise RetrievalError(
            "The query embedding dimension does not match document embeddings."
        )

    try:
        raw = vector_store.search(query_embedding, top_k=top_k)
    except VectorStoreError as exc:
        raise RetrievalError(str(exc)) from exc

    ids = _nested_first(raw, "ids")
    documents = _nested_first(raw, "documents")
    metadatas = _nested_first(raw, "metadatas")
    distances = _nested_first(raw, "distances")
    result_count = min(
        len(ids),
        len(documents),
        len(metadatas),
        len(distances),
    )

    chunks: list[RetrievedChunk] = []
    for index in range(result_count):
        metadata = metadatas[index]
        if not isinstance(metadata, Mapping):
            logger.warning("Skipping retrieval result with malformed metadata.")
            continue
        distance = _safe_float(distances[index])
        if (
            maximum_distance is not None
            and distance > float(maximum_distance)
        ):
            continue
        page_number = _safe_int(metadata.get("page_number"), -1)
        normalized_page = (
            None
            if page_number == UNPAGINATED_PAGE_NUMBER
            else page_number
        )
        chunk_id = str(metadata.get("chunk_id") or ids[index])
        document_id = str(metadata.get("document_id") or "")
        filename = str(metadata.get("filename") or metadata.get("source") or "")
        chunks.append(
            RetrievedChunk(
                rank=len(chunks) + 1,
                chunk_id=chunk_id,
                document_id=document_id,
                filename=filename,
                file_type=str(metadata.get("file_type") or ""),
                source=str(metadata.get("source") or filename),
                chunk_index=_safe_int(metadata.get("chunk_index")),
                page_number=normalized_page,
                token_count=_safe_int(metadata.get("token_count")),
                cosine_distance=distance,
                text=str(documents[index] or ""),
            )
        )

    return RetrievalResult(
        query=query.strip(),
        requested_top_k=top_k,
        maximum_distance=maximum_distance,
        returned_count=len(chunks),
        duration_seconds=time.monotonic() - started_at,
        chunks=tuple(chunks),
    )
