"""Unit tests for Gemini document embedding without live API requests."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from config import Settings
from core.embedding_service import (
    EmbeddingService,
    EmbeddingServiceError,
    MissingAPIKeyError,
)
from ingestion.models import DocumentChunk


class FakeModels:
    def __init__(self, outcomes):
        self.outcomes = iter(outcomes)
        self.calls = []

    def embed_content(self, **kwargs):
        self.calls.append(kwargs)
        outcome = next(self.outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class FakeAPIError(Exception):
    def __init__(self, code: int):
        super().__init__("private diagnostic")
        self.code = code


def _settings(
    *,
    api_key: str | None = "test-key",
    batch_size: int = 2,
    dimension: int = 2,
) -> Settings:
    return Settings(
        gemini_api_key=api_key,
        embedding_model="configured-embedding-model",
        generation_model="configured-generation-model",
        chroma_persist_directory=Path("data/chroma"),
        chroma_collection_name="cybervault_documents",
        chunk_size=500,
        chunk_overlap=100,
        retrieval_top_k=5,
        embedding_batch_size=batch_size,
        embedding_dimension=dimension,
    )


def _chunk(chunk_id: str, text: str = "sample document text") -> DocumentChunk:
    return DocumentChunk(
        chunk_id=chunk_id,
        document_id="document-1",
        filename="sample.txt",
        file_type="txt",
        source="sample.txt",
        chunk_index=int(chunk_id.rsplit("-", 1)[-1]),
        page_number=None,
        text=text,
        token_count=3,
    )


def _response(count: int, dimension: int = 2):
    return SimpleNamespace(
        embeddings=[
            SimpleNamespace(values=[float(index + 1)] * dimension)
            for index in range(count)
        ]
    )


def _service(outcomes, *, batch_size: int = 2, dimension: int = 2, **kwargs):
    models = FakeModels(outcomes)
    client = SimpleNamespace(models=models)
    return EmbeddingService(
        _settings(batch_size=batch_size, dimension=dimension),
        client=client,
        **kwargs,
    ), models


def test_embed_uses_configured_model_and_document_task_type() -> None:
    service, models = _service([_response(1)])

    result = service.embed_chunks([_chunk("chunk-0")])

    assert result.successful_count == 1
    assert models.calls[0]["model"] == "configured-embedding-model"
    assert models.calls[0]["config"].task_type == "RETRIEVAL_DOCUMENT"
    assert models.calls[0]["config"].output_dimensionality == 2
    assert result.embeddings[0].chunk_id == "chunk-0"


def test_empty_input_does_not_initialize_gemini_client() -> None:
    service = EmbeddingService(_settings(api_key=None), client=None)

    assert service.embed_chunks([]).batches_processed == 0
    assert service.embed_chunks([_chunk("chunk-0", " \n")]).failed_count == 1


def test_embedding_batches_are_bounded_and_keep_chunk_relationships() -> None:
    service, models = _service(
        [_response(2), _response(2), _response(1)],
        batch_size=2,
    )
    chunks = [_chunk(f"chunk-{index}") for index in range(5)]
    progress = []

    result = service.embed_chunks(
        chunks,
        progress_callback=lambda done, total: progress.append((done, total)),
    )

    assert [len(call["contents"]) for call in models.calls] == [2, 2, 1]
    assert [embedding.chunk_id for embedding in result.embeddings] == [
        chunk.chunk_id for chunk in chunks
    ]
    assert progress == [(1, 3), (2, 3), (3, 3)]


def test_failed_batch_does_not_discard_successful_batches() -> None:
    service, _models = _service(
        [FakeAPIError(503), _response(2)],
        batch_size=2,
        max_retries=0,
    )

    result = service.embed_chunks(
        [_chunk(f"chunk-{index}") for index in range(4)]
    )

    assert result.successful_count == 2
    assert result.failed_count == 2
    assert {item.chunk_id for item in result.failures} == {"chunk-0", "chunk-1"}
    assert {item.chunk_id for item in result.embeddings} == {"chunk-2", "chunk-3"}
    assert "private diagnostic" not in result.failures[0].message


def test_rate_limit_uses_bounded_exponential_retry() -> None:
    service, models = _service(
        [FakeAPIError(429), FakeAPIError(429), _response(1)],
        batch_size=1,
        max_retries=2,
        base_delay_seconds=0.25,
        max_delay_seconds=1,
        sleep=lambda delay: delays.append(delay),
    )
    delays = []

    result = service.embed_chunks([_chunk("chunk-0")])

    assert result.successful_count == 1
    assert len(models.calls) == 3
    assert delays == [0.25, 0.5]


def test_unexpected_embedding_dimension_is_reported_as_chunk_failure() -> None:
    service, _models = _service([_response(1, dimension=3)])

    result = service.embed_chunks([_chunk("chunk-0")])

    assert result.successful_count == 0
    assert result.failed_count == 1
    assert "unexpected embedding dimension" in result.failures[0].message


def test_missing_api_key_is_reported_without_creating_a_client() -> None:
    service = EmbeddingService(_settings(api_key=None), client=None)

    with pytest.raises(MissingAPIKeyError, match="GEMINI_API_KEY"):
        service.embed_chunks([_chunk("chunk-0")])


def test_embed_query_uses_retrieval_query_task_type() -> None:
    service, models = _service([_response(1, dimension=2)])

    vector = service.embed_query("What is password rotation?")

    assert vector == (1.0, 1.0)
    assert models.calls[0]["config"].task_type == "RETRIEVAL_QUERY"
    assert models.calls[0]["config"].output_dimensionality == 2


def test_empty_query_is_rejected_without_client_call() -> None:
    service, models = _service([_response(1)])

    with pytest.raises(EmbeddingServiceError, match="must not be empty"):
        service.embed_query("  ")
    assert models.calls == []
