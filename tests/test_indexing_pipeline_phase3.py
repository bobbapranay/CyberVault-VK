"""Phase 2 to Phase 3 orchestration tests with mocked Gemini responses."""

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

from config import Settings
from core.embedding_service import EmbeddingService
from ingestion.indexing_pipeline import index_processed_documents
from ingestion.models import DocumentChunk, DocumentProcessingResult
from vectorstore.chroma_store import ChromaStore


class FakeModels:
    def __init__(self, outcomes=None):
        self.calls = []
        self.outcomes = iter(outcomes or [])

    def embed_content(self, **kwargs):
        self.calls.append(kwargs)
        outcome = next(self.outcomes, None)
        if isinstance(outcome, Exception):
            raise outcome
        if outcome is not None:
            return outcome
        return SimpleNamespace(
            embeddings=[
                SimpleNamespace(values=[float(index + 1), float(index + 2)])
                for index, _ in enumerate(kwargs["contents"])
            ]
        )


def _settings(path: Path, *, key: str = "test-key") -> Settings:
    return Settings(
        gemini_api_key=key,
        embedding_model="configured-embedding-model",
        generation_model="configured-generation-model",
        chroma_persist_directory=path,
        chroma_collection_name="cybervault_documents",
        chunk_size=500,
        chunk_overlap=100,
        retrieval_top_k=5,
        embedding_batch_size=2,
        embedding_dimension=2,
    )


def _document(
    document_id: str,
    filename: str,
    *,
    page: int | None = None,
    chunk_count: int = 1,
):
    chunks = tuple(
        DocumentChunk(
            chunk_id=f"{document_id}-chunk-{index}",
            document_id=document_id,
            filename=filename,
            file_type=filename.rsplit(".", 1)[-1],
            source=filename,
            chunk_index=index,
            page_number=page,
            text=f"Text for {filename}, chunk {index}.",
            token_count=4,
        )
        for index in range(chunk_count)
    )
    return DocumentProcessingResult(
        filename=filename,
        file_type=chunks[0].file_type,
        document_id=document_id,
        pages_extracted=chunk_count if page is not None else 0,
        chunks=chunks,
        status="processed",
    )


def test_pipeline_embeds_and_stores_each_document_with_its_own_vectors(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path / "vectors")
    models = FakeModels()
    service = EmbeddingService(
        settings,
        client=SimpleNamespace(models=models),
    )
    store = ChromaStore(settings)
    documents = [
        _document("document-a", "a.pdf", page=3),
        _document("document-b", "b.txt"),
    ]

    report = index_processed_documents(
        documents,
        embedding_service=service,
        vector_store=store,
    )

    assert report.documents_processed == 2
    assert report.pages_extracted == 1
    assert report.chunks_generated == 2
    assert report.embeddings_created == 2
    assert report.vectors_stored == 2
    assert report.failures == 0
    assert {item.status for item in report.document_results} == {"stored"}
    assert store.get_vector_count() == 2
    assert [len(call["contents"]) for call in models.calls] == [2]


def test_pipeline_skips_documents_that_are_already_indexed(tmp_path: Path) -> None:
    settings = _settings(tmp_path / "vectors")
    models = FakeModels()
    service = EmbeddingService(
        settings,
        client=SimpleNamespace(models=models),
    )
    store = ChromaStore(settings)
    document = _document("document-a", "a.txt")

    first = index_processed_documents(
        [document],
        embedding_service=service,
        vector_store=store,
    )
    second = index_processed_documents(
        [document],
        embedding_service=service,
        vector_store=store,
    )

    assert first.vectors_stored == 1
    assert second.duplicate_documents == 1
    assert second.embeddings_created == 0
    assert len(models.calls) == 1


def test_pipeline_resumes_after_partial_embedding_failure(tmp_path: Path) -> None:
    settings = replace(
        _settings(tmp_path / "vectors"),
        embedding_batch_size=1,
    )
    store = ChromaStore(settings)
    document = _document("document-a", "a.txt", chunk_count=2)
    first_models = FakeModels(
        [
            SimpleNamespace(embeddings=[SimpleNamespace(values=[1.0, 2.0])]),
            RuntimeError("private API diagnostic"),
        ]
    )
    first_service = EmbeddingService(
        settings,
        client=SimpleNamespace(models=first_models),
        max_retries=0,
    )

    first_report = index_processed_documents(
        [document],
        embedding_service=first_service,
        vector_store=store,
    )

    second_models = FakeModels(
        [SimpleNamespace(embeddings=[SimpleNamespace(values=[3.0, 4.0])])]
    )
    second_service = EmbeddingService(
        settings,
        client=SimpleNamespace(models=second_models),
    )
    second_report = index_processed_documents(
        [document],
        embedding_service=second_service,
        vector_store=store,
    )

    assert first_report.document_results[0].status == "partial"
    assert first_report.vectors_stored == 1
    assert second_report.document_results[0].status == "stored"
    assert second_report.embeddings_created == 1
    assert second_report.vectors_stored == 1
    assert len(second_models.calls[0]["contents"]) == 1
    assert store.get_vector_count() == 2


def test_pipeline_reports_duplicate_document_ids_without_overwriting_results(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path / "vectors")
    models = FakeModels()
    service = EmbeddingService(
        settings,
        client=SimpleNamespace(models=models),
    )
    store = ChromaStore(settings)
    document = _document("document-a", "a.txt")

    report = index_processed_documents(
        [document, document],
        embedding_service=service,
        vector_store=store,
    )

    assert [result.status for result in report.document_results] == [
        "stored",
        "duplicate",
    ]
    assert report.duplicate_documents == 1
    assert store.get_vector_count() == 1


def test_failed_reindex_keeps_the_previous_complete_document(tmp_path: Path) -> None:
    settings = replace(
        _settings(tmp_path / "vectors"),
        embedding_batch_size=1,
    )
    old_vectors = {
        "document-a-chunk-0": (1.0, 2.0),
        "document-a-chunk-1": (3.0, 4.0),
    }
    store = ChromaStore(settings)
    document = _document("document-a", "a.txt", chunk_count=2)
    store.add_document(document.chunks, old_vectors)
    models = FakeModels(
        [
            SimpleNamespace(embeddings=[SimpleNamespace(values=[8.0, 9.0])]),
            RuntimeError("private API diagnostic"),
        ]
    )
    service = EmbeddingService(
        settings,
        client=SimpleNamespace(models=models),
        max_retries=0,
    )

    report = index_processed_documents(
        [document],
        embedding_service=service,
        vector_store=store,
        reindex_document_ids={"document-a"},
    )

    records = store.get_sample_records()
    assert report.document_results[0].status == "failed"
    assert {record.chunk_id: record.embedding for record in records} == old_vectors
