"""Persistent ChromaDB storage tests using temporary local directories."""

from pathlib import Path

import pytest

from config import Settings
from ingestion.models import DocumentChunk
from vectorstore.chroma_store import (
    ChromaStore,
    UNPAGINATED_PAGE_NUMBER,
    VectorStoreError,
)


def _settings(path: Path) -> Settings:
    return Settings(
        gemini_api_key=None,
        embedding_model="embedding-model",
        generation_model="generation-model",
        chroma_persist_directory=path,
        chroma_collection_name="cybervault_documents",
        chunk_size=500,
        chunk_overlap=100,
        retrieval_top_k=5,
    )


def _chunks(
    document_id: str,
    filename: str,
    *,
    pages: tuple[int | None, ...] = (None, None),
) -> tuple[DocumentChunk, ...]:
    return tuple(
        DocumentChunk(
            chunk_id=f"{document_id}-chunk-{index}",
            document_id=document_id,
            filename=filename,
            file_type=filename.rsplit(".", 1)[-1],
            source=filename,
            chunk_index=index,
            page_number=page,
            text=f"Content for {filename}, chunk {index}.",
            token_count=5,
        )
        for index, page in enumerate(pages)
    )


def _vectors(chunks: tuple[DocumentChunk, ...]):
    return {
        chunk.chunk_id: (float(index + 1), float(index + 2))
        for index, chunk in enumerate(chunks)
    }


def test_add_stores_cosine_collection_and_source_metadata(tmp_path: Path) -> None:
    store = ChromaStore(_settings(tmp_path / "vectors"))
    chunks = _chunks("document-a", "a.pdf", pages=(2, 4))

    result = store.add_document(chunks, _vectors(chunks))
    records = store.get_sample_records(limit=5)

    assert result.status == "stored"
    assert result.stored_count == 2
    assert store.collection.metadata["hnsw:space"] == "cosine"
    assert records[0].metadata["document_id"] == "document-a"
    assert records[0].metadata["filename"] == "a.pdf"
    assert records[0].metadata["page_number"] in (2, 4)
    assert records[0].metadata["source"] == "a.pdf"
    assert records[0].metadata["token_count"] == 5
    assert len(records[0].embedding) == 2


def test_missing_page_number_uses_chroma_supported_sentinel(tmp_path: Path) -> None:
    store = ChromaStore(_settings(tmp_path / "vectors"))
    chunks = _chunks("document-a", "a.txt")

    store.add_document(chunks, _vectors(chunks))

    assert all(
        record.metadata["page_number"] == UNPAGINATED_PAGE_NUMBER
        for record in store.get_sample_records()
    )


def test_duplicate_insertion_does_not_add_vectors_twice(tmp_path: Path) -> None:
    store = ChromaStore(_settings(tmp_path / "vectors"))
    chunks = _chunks("document-a", "a.txt")
    vectors = _vectors(chunks)

    first = store.add_document(chunks, vectors)
    second = store.add_document(chunks, vectors)

    assert first.status == "stored"
    assert second.status == "duplicate"
    assert store.get_vector_count() == len(chunks)


def test_partial_document_can_resume_without_replacing_existing_vectors(
    tmp_path: Path,
) -> None:
    store = ChromaStore(_settings(tmp_path / "vectors"))
    chunks = _chunks("document-a", "a.txt", pages=(None, None, None))
    vectors = _vectors(chunks)

    initial = store.add_document(chunks, {chunks[0].chunk_id: vectors[chunks[0].chunk_id]})
    resumed = store.add_document(chunks, vectors)

    assert initial.status == "partial"
    assert initial.failed_count == 2
    assert resumed.status == "stored"
    assert resumed.stored_count == 2
    assert store.get_vector_count() == 3


def test_document_listing_status_and_scoped_deletion(tmp_path: Path) -> None:
    store = ChromaStore(_settings(tmp_path / "vectors"))
    first = _chunks("document-a", "a.txt")
    second = _chunks("document-b", "b.md")
    store.add_document(first, _vectors(first))
    store.add_document(second, _vectors(second))

    documents = store.list_documents()
    deleted = store.delete_document("document-a")

    assert {document.document_id for document in documents} == {
        "document-a",
        "document-b",
    }
    assert all(document.status == "indexed" for document in documents)
    assert deleted == len(first)
    assert store.get_document_chunk_ids("document-a") == set()
    assert store.get_document_chunk_ids("document-b") == {
        chunk.chunk_id for chunk in second
    }
    assert store.get_status().vector_count == len(second)


def test_data_persists_when_a_new_client_opens_the_same_directory(
    tmp_path: Path,
) -> None:
    path = tmp_path / "persistent"
    first_store = ChromaStore(_settings(path))
    chunks = _chunks("document-a", "a.txt")
    first_store.add_document(chunks, _vectors(chunks))

    second_store = ChromaStore(_settings(path))

    assert second_store.get_document_chunk_ids("document-a") == {
        chunk.chunk_id for chunk in chunks
    }


def test_storage_rejects_vectors_from_another_document(tmp_path: Path) -> None:
    store = ChromaStore(_settings(tmp_path / "vectors"))
    chunks = _chunks("document-a", "a.txt")

    with pytest.raises(VectorStoreError, match="do not belong"):
        store.add_document(chunks, {"unrelated": (1.0, 2.0)})


def test_incomplete_reindex_preserves_existing_vectors(tmp_path: Path) -> None:
    store = ChromaStore(_settings(tmp_path / "vectors"))
    chunks = _chunks("document-a", "a.txt")
    vectors = _vectors(chunks)
    store.add_document(chunks, vectors)

    with pytest.raises(VectorStoreError, match="Existing vectors were preserved"):
        store.add_document(
            chunks,
            {chunks[0].chunk_id: (8.0, 9.0)},
            reindex=True,
        )

    records = store.get_sample_records()
    assert store.get_vector_count() == len(chunks)
    assert {record.chunk_id: record.embedding for record in records} == vectors
