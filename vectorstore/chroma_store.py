"""Persistent ChromaDB storage for Gemini-embedded document chunks."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from config import Settings, load_settings
from ingestion.models import DocumentChunk

logger = logging.getLogger(__name__)
COSINE_METADATA = {"hnsw:space": "cosine"}
UNPAGINATED_PAGE_NUMBER = -1


class VectorStoreError(RuntimeError):
    """Raised when the persistent vector store cannot be used safely."""


@dataclass(frozen=True)
class DocumentStoreResult:
    """Outcome of adding or completing one document in ChromaDB."""

    status: str
    stored_count: int
    duplicate_count: int
    failed_count: int
    error: str | None = None


@dataclass(frozen=True)
class IndexedDocument:
    """Summary of a document represented by stored chunk records."""

    document_id: str
    filename: str
    file_type: str
    chunk_count: int
    expected_chunk_count: int
    status: str


@dataclass(frozen=True)
class StoredVectorRecord:
    """A stored chunk record returned for inspection."""

    chunk_id: str
    text: str
    embedding: tuple[float, ...]
    metadata: dict[str, Any]


@dataclass(frozen=True)
class VectorStoreStatus:
    """Connection and actual persisted collection statistics."""

    connected: bool
    collection_name: str
    persistence_directory: Path
    vector_count: int
    document_count: int


class ChromaStore:
    """Manage a cosine-distance Chroma collection on persistent local storage."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        persist_directory: str | Path | None = None,
        collection_name: str | None = None,
        client: Any | None = None,
    ) -> None:
        resolved_settings = settings
        if resolved_settings is None and (
            persist_directory is None or collection_name is None
        ):
            resolved_settings = load_settings()

        configured_path = (
            persist_directory
            if persist_directory is not None
            else resolved_settings.chroma_persist_directory
        )
        configured_name = (
            collection_name
            if collection_name is not None
            else resolved_settings.chroma_collection_name
        )
        self.persist_directory = Path(configured_path).expanduser().resolve()
        self.collection_name = configured_name

        try:
            if self.persist_directory.exists() and not self.persist_directory.is_dir():
                raise VectorStoreError(
                    "The ChromaDB persistence path exists but is not a directory."
                )
            self.persist_directory.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            logger.warning(
                "Unable to prepare ChromaDB persistence directory (%s)",
                type(exc).__name__,
            )
            raise VectorStoreError(
                "Unable to create the ChromaDB persistence directory. "
                "Check the configured path and permissions."
            ) from exc

        try:
            if client is None:
                try:
                    import chromadb
                    from chromadb.config import Settings as ChromaSettings
                except ImportError as exc:
                    raise VectorStoreError(
                        "ChromaDB is not installed. Install project dependencies "
                        "with `pip install -r requirements.txt`."
                    ) from exc
                client = chromadb.PersistentClient(
                    path=str(self.persist_directory),
                    settings=ChromaSettings(anonymized_telemetry=False),
                )
            self.client = client
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata=COSINE_METADATA,
                embedding_function=None,
            )
            collection_metadata = self.collection.metadata or {}
            if collection_metadata.get("hnsw:space") != "cosine":
                raise VectorStoreError(
                    "The existing ChromaDB collection is not configured for cosine "
                    "distance. Choose a new collection name or migrate it explicitly."
                )
        except VectorStoreError:
            raise
        except Exception as exc:
            logger.warning(
                "Unable to initialize ChromaDB collection (%s)",
                type(exc).__name__,
            )
            raise VectorStoreError(
                "Unable to initialize the ChromaDB collection. Check the "
                "persistence directory and collection configuration."
            ) from exc

    @staticmethod
    def _chunk_metadata(
        chunk: DocumentChunk,
        expected_chunk_count: int,
    ) -> dict[str, str | int]:
        return {
            "chunk_id": chunk.chunk_id,
            "document_id": chunk.document_id,
            "filename": chunk.filename,
            "file_type": chunk.file_type,
            "chunk_index": chunk.chunk_index,
            "page_number": (
                chunk.page_number
                if chunk.page_number is not None
                else UNPAGINATED_PAGE_NUMBER
            ),
            "source": chunk.source,
            "token_count": chunk.token_count,
            "expected_chunk_count": expected_chunk_count,
        }

    @staticmethod
    def _validate_vectors(
        chunks: Sequence[DocumentChunk],
        embeddings: Mapping[str, Sequence[float]],
    ) -> None:
        chunk_ids = [chunk.chunk_id for chunk in chunks]
        if len(chunk_ids) != len(set(chunk_ids)):
            raise VectorStoreError("Chunk IDs must be unique within a document.")
        if set(embeddings) - set(chunk_ids):
            raise VectorStoreError(
                "Embedding results contain IDs that do not belong to this document."
            )

        dimensions: set[int] = set()
        for chunk_id, vector in embeddings.items():
            if not vector:
                raise VectorStoreError(f"Embedding for chunk {chunk_id} is empty.")
            if any(
                isinstance(value, bool) or not isinstance(value, (int, float))
                for value in vector
            ):
                raise VectorStoreError(
                    f"Embedding for chunk {chunk_id} contains non-numeric values."
                )
            if not all(math.isfinite(float(value)) for value in vector):
                raise VectorStoreError(
                    f"Embedding for chunk {chunk_id} contains non-finite values."
                )
            dimensions.add(len(vector))
        if len(dimensions) > 1:
            raise VectorStoreError(
                "Embedding vectors have inconsistent dimensions."
            )

    def _get_records_for_document(self, document_id: str) -> dict[str, Any]:
        try:
            return self.collection.get(
                where={"document_id": document_id},
                include=["metadatas"],
            )
        except Exception as exc:
            logger.warning(
                "Unable to inspect ChromaDB records (%s)",
                type(exc).__name__,
            )
            raise VectorStoreError(
                "Unable to inspect stored document vectors."
            ) from exc

    def get_document_chunk_ids(self, document_id: str) -> set[str]:
        """Return persisted chunk IDs belonging to one document."""
        records = self._get_records_for_document(document_id)
        return set(records.get("ids") or [])

    def document_exists(self, document_id: str) -> bool:
        """Return whether any vector for the document is present."""
        return bool(self.get_document_chunk_ids(document_id))

    def add_document(
        self,
        chunks: Sequence[DocumentChunk],
        embeddings: Mapping[str, Sequence[float]],
        *,
        reindex: bool = False,
        batch_size: int | None = None,
    ) -> DocumentStoreResult:
        """Store complete or partial chunk embeddings without overwriting IDs.

        If an earlier run stored only part of a document, a retry adds only its
        missing chunk IDs. A different chunk set for the same document ID is
        rejected unless the caller explicitly requests re-indexing.
        """
        if not chunks:
            raise VectorStoreError("No chunks were provided for storage.")
        document_ids = {chunk.document_id for chunk in chunks}
        if len(document_ids) != 1:
            raise VectorStoreError("A storage operation must contain one document.")
        self._validate_vectors(chunks, embeddings)

        document_id = chunks[0].document_id
        expected_ids = {chunk.chunk_id for chunk in chunks}
        existing_records = self._get_records_for_document(document_id)
        existing_ids = set(existing_records.get("ids") or [])

        if reindex and existing_ids and set(embeddings) != expected_ids:
            raise VectorStoreError(
                "Re-indexing requires embeddings for every chunk. Existing vectors "
                "were preserved; retry after all embeddings succeed."
            )
        if reindex and existing_ids:
            try:
                self.collection.delete(where={"document_id": document_id})
            except Exception as exc:
                logger.warning(
                    "Unable to remove existing document vectors for re-indexing (%s)",
                    type(exc).__name__,
                )
                raise VectorStoreError(
                    "Unable to remove existing vectors for this document."
                ) from exc
            existing_ids = set()
        elif existing_ids and not existing_ids.issubset(expected_ids):
            raise VectorStoreError(
                "This document ID already has a different chunk set. Use explicit "
                "re-indexing or delete the document before changing chunk settings."
            )

        if existing_ids == expected_ids and not reindex:
            return DocumentStoreResult(
                status="duplicate",
                stored_count=0,
                duplicate_count=len(existing_ids),
                failed_count=0,
            )

        chunks_by_id = {chunk.chunk_id: chunk for chunk in chunks}
        pending = [
            chunk
            for chunk in chunks
            if chunk.chunk_id not in existing_ids
            and chunk.chunk_id in embeddings
        ]
        effective_batch_size = 32 if batch_size is None else batch_size
        if effective_batch_size <= 0:
            raise VectorStoreError("ChromaDB batch size must be greater than zero.")

        failed_batch = False
        for start in range(0, len(pending), effective_batch_size):
            batch = pending[start : start + effective_batch_size]
            try:
                self.collection.add(
                    ids=[chunk.chunk_id for chunk in batch],
                    documents=[chunk.text for chunk in batch],
                    embeddings=[
                        [float(value) for value in embeddings[chunk.chunk_id]]
                        for chunk in batch
                    ],
                    metadatas=[
                        self._chunk_metadata(chunk, len(chunks))
                        for chunk in batch
                    ],
                )
            except Exception as exc:
                failed_batch = True
                logger.warning(
                    "Unable to store a ChromaDB batch (%s)",
                    type(exc).__name__,
                )

        persisted_ids = self.get_document_chunk_ids(document_id)
        new_count = len(persisted_ids - existing_ids)
        missing_count = len(expected_ids - persisted_ids)
        if missing_count:
            return DocumentStoreResult(
                status="partial" if persisted_ids else "failed",
                stored_count=new_count,
                duplicate_count=len(existing_ids),
                failed_count=missing_count,
                error=(
                    "Some vectors could not be stored. Retry indexing to complete "
                    "this document."
                ),
            )

        return DocumentStoreResult(
            status="reindexed" if reindex else "stored",
            stored_count=new_count,
            duplicate_count=len(existing_ids),
            failed_count=0,
            error=(
                "A ChromaDB batch reported an error, but all requested vectors "
                "were verified in storage."
                if failed_batch
                else None
            ),
        )

    def list_documents(self) -> list[IndexedDocument]:
        """List indexed document summaries grouped from persisted metadata."""
        try:
            records = self.collection.get(include=["metadatas"])
        except Exception as exc:
            logger.warning("Unable to list ChromaDB documents (%s)", type(exc).__name__)
            raise VectorStoreError("Unable to list indexed documents.") from exc

        grouped: dict[str, dict[str, Any]] = {}
        for metadata in records.get("metadatas") or []:
            if not isinstance(metadata, dict):
                continue
            document_id = metadata.get("document_id")
            if not isinstance(document_id, str):
                continue
            summary = grouped.setdefault(
                document_id,
                {
                    "filename": str(metadata.get("filename", "")),
                    "file_type": str(metadata.get("file_type", "")),
                    "chunk_count": 0,
                    "expected_chunk_count": 0,
                },
            )
            summary["chunk_count"] += 1
            summary["expected_chunk_count"] = max(
                summary["expected_chunk_count"],
                int(metadata.get("expected_chunk_count", 0)),
            )

        documents = [
            IndexedDocument(
                document_id=document_id,
                filename=summary["filename"],
                file_type=summary["file_type"],
                chunk_count=summary["chunk_count"],
                expected_chunk_count=summary["expected_chunk_count"],
                status=(
                    "indexed"
                    if summary["chunk_count"] >= summary["expected_chunk_count"]
                    else "partial"
                ),
            )
            for document_id, summary in grouped.items()
        ]
        return sorted(documents, key=lambda document: document.filename.casefold())

    def count_chunks_by_document(self, document_id: str) -> int:
        """Return actual persisted vector count for one document."""
        return len(self.get_document_chunk_ids(document_id))

    def get_vector_count(self) -> int:
        """Return the collection's persisted vector count."""
        try:
            return int(self.collection.count())
        except Exception as exc:
            logger.warning("Unable to count ChromaDB vectors (%s)", type(exc).__name__)
            raise VectorStoreError("Unable to count stored vectors.") from exc

    def search(
        self,
        query_embedding: Sequence[float],
        *,
        top_k: int,
    ) -> dict[str, list[Any]]:
        """Return raw cosine-nearest collection records for one query vector."""
        if top_k <= 0:
            raise VectorStoreError("Retrieval top-k must be greater than zero.")
        if not query_embedding:
            raise VectorStoreError("Query embedding must not be empty.")
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            for value in query_embedding
        ):
            raise VectorStoreError("Query embedding contains invalid values.")
        if self.get_vector_count() == 0:
            return {
                "ids": [[]],
                "documents": [[]],
                "metadatas": [[]],
                "distances": [[]],
            }
        try:
            return self.collection.query(
                query_embeddings=[
                    [float(value) for value in query_embedding]
                ],
                n_results=min(top_k, self.get_vector_count()),
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            logger.warning("ChromaDB retrieval failed (%s)", type(exc).__name__)
            raise VectorStoreError(
                "Unable to search the persistent vector collection."
            ) from exc

    def get_status(self) -> VectorStoreStatus:
        """Check the client heartbeat and return actual collection statistics."""
        try:
            self.client.heartbeat()
        except Exception as exc:
            logger.warning("ChromaDB heartbeat failed (%s)", type(exc).__name__)
            raise VectorStoreError("ChromaDB is not responding.") from exc
        return VectorStoreStatus(
            connected=True,
            collection_name=self.collection_name,
            persistence_directory=self.persist_directory,
            vector_count=self.get_vector_count(),
            document_count=len(self.list_documents()),
        )

    def get_sample_records(self, limit: int = 5) -> list[StoredVectorRecord]:
        """Return stored texts, metadata, and vectors for local verification."""
        if limit < 0:
            raise ValueError("Sample limit must be zero or greater.")
        if limit == 0:
            return []
        try:
            records = self.collection.get(
                limit=limit,
                include=["documents", "embeddings", "metadatas"],
            )
        except Exception as exc:
            logger.warning(
                "Unable to retrieve ChromaDB sample records (%s)",
                type(exc).__name__,
            )
            raise VectorStoreError("Unable to retrieve sample stored vectors.") from exc

        ids = records.get("ids") or []
        documents = records.get("documents") or []
        embeddings = records.get("embeddings")
        metadatas = records.get("metadatas") or []
        if embeddings is None:
            raise VectorStoreError("ChromaDB returned no stored embeddings.")
        samples: list[StoredVectorRecord] = []
        for index, chunk_id in enumerate(ids):
            vector = embeddings[index]
            if hasattr(vector, "tolist"):
                vector = vector.tolist()
            samples.append(
                StoredVectorRecord(
                    chunk_id=chunk_id,
                    text=documents[index] or "",
                    embedding=tuple(float(value) for value in vector),
                    metadata=metadatas[index] or {},
                )
            )
        return samples

    def delete_document(self, document_id: str) -> int:
        """Delete only the vectors whose metadata matches the document ID."""
        existing_ids = self.get_document_chunk_ids(document_id)
        if not existing_ids:
            return 0
        try:
            self.collection.delete(where={"document_id": document_id})
        except Exception as exc:
            logger.warning(
                "Unable to delete ChromaDB document vectors (%s)",
                type(exc).__name__,
            )
            raise VectorStoreError(
                "Unable to delete vectors for this document."
            ) from exc
        remaining_ids = self.get_document_chunk_ids(document_id)
        if remaining_ids:
            raise VectorStoreError(
                "Some vectors for this document remain after deletion."
            )
        return len(existing_ids)
