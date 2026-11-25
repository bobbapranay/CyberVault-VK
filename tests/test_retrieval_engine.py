"""Phase 4 retrieval tests with mocked Gemini queries and temporary ChromaDB."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from config import Settings
from core.embedding_service import EmbeddingService
from core.retrieval_engine import RetrievalError, retrieve_documents
from ingestion.models import DocumentChunk
from vectorstore.chroma_store import ChromaStore


def _settings(path: Path) -> Settings:
    return Settings(
        gemini_api_key="test-key",
        embedding_model="embedding-model",
        generation_model="generation-model",
        chroma_persist_directory=path,
        chroma_collection_name="cybervault_documents",
        chunk_size=500,
        chunk_overlap=100,
        retrieval_top_k=5,
        embedding_batch_size=32,
        embedding_dimension=2,
        retrieval_max_top_k=20,
    )


def _chunk(document_id: str, filename: str, index: int, page: int | None):
    return DocumentChunk(
        chunk_id=f"{document_id}-chunk-{index}",
        document_id=document_id,
        filename=filename,
        file_type=filename.rsplit(".", 1)[-1],
        source=filename,
        chunk_index=index,
        page_number=page,
        text=f"Source text for {filename} chunk {index}.",
        token_count=7,
    )


def test_retrieval_preserves_metadata_and_cosine_ranking(tmp_path: Path) -> None:
    store = ChromaStore(_settings(tmp_path / "vectors"))
    chunks = (
        _chunk("doc-a", "handbook.pdf", 0, 3),
        _chunk("doc-b", "policies.md", 1, None),
    )
    store.add_document(
        (chunks[0],),
        {chunks[0].chunk_id: (1.0, 0.0)},
    )
    store.add_document(
        (chunks[1],),
        {chunks[1].chunk_id: (0.8, 0.6)},
    )
    models = SimpleNamespace(
        embed_content=lambda **kwargs: SimpleNamespace(
            embeddings=[SimpleNamespace(values=[1.0, 0.0])]
        )
    )
    service = EmbeddingService(
        _settings(tmp_path / "vectors"),
        client=SimpleNamespace(models=models),
    )

    result = retrieve_documents(
        "How are passwords managed?",
        top_k=5,
        maximum_top_k=20,
        embedding_service=service,
        vector_store=store,
    )

    assert result.returned_count == 2
    assert result.requested_top_k == 5
    assert result.chunks[0].filename == "handbook.pdf"
    assert result.chunks[0].page_number == 3
    assert result.chunks[0].document_id == "doc-a"
    assert result.chunks[0].chunk_id == "doc-a-chunk-0"
    assert result.chunks[0].chunk_index == 0
    assert result.chunks[0].token_count == 7
    assert result.chunks[1].page_number is None
    assert result.chunks[0].cosine_distance <= result.chunks[1].cosine_distance


def test_empty_collection_returns_without_query_embedding(tmp_path: Path) -> None:
    store = ChromaStore(_settings(tmp_path / "vectors"))
    called = False

    class EmptyModels:
        def embed_content(self, **kwargs):
            nonlocal called
            called = True
            return None

    service = EmbeddingService(
        _settings(tmp_path / "vectors"),
        client=SimpleNamespace(models=EmptyModels()),
    )
    result = retrieve_documents(
        "A question",
        embedding_service=service,
        vector_store=store,
    )

    assert result.returned_count == 0
    assert result.chunks == ()
    assert called is False


@pytest.mark.parametrize("query", ["", " \n\t"])
def test_empty_query_is_rejected(tmp_path: Path, query: str) -> None:
    store = ChromaStore(_settings(tmp_path / "vectors"))
    service = EmbeddingService(
        _settings(tmp_path / "vectors"),
        client=SimpleNamespace(),
    )

    with pytest.raises(RetrievalError, match="must not be empty"):
        retrieve_documents(
            query,
            embedding_service=service,
            vector_store=store,
        )


@pytest.mark.parametrize("top_k", [0, -1, True, 2.5])
def test_invalid_top_k_is_rejected(tmp_path: Path, top_k) -> None:
    store = ChromaStore(_settings(tmp_path / "vectors"))
    service = EmbeddingService(
        _settings(tmp_path / "vectors"),
        client=SimpleNamespace(),
    )
    with pytest.raises(RetrievalError, match="top-k"):
        retrieve_documents(
            "A question",
            top_k=top_k,
            embedding_service=service,
            vector_store=store,
        )


def test_top_k_cannot_exceed_configured_maximum(tmp_path: Path) -> None:
    store = ChromaStore(_settings(tmp_path / "vectors"))
    service = EmbeddingService(
        _settings(tmp_path / "vectors"),
        client=SimpleNamespace(),
    )
    with pytest.raises(RetrievalError, match="configured maximum"):
        retrieve_documents(
            "A question",
            top_k=21,
            maximum_top_k=20,
            embedding_service=service,
            vector_store=store,
        )


def test_optional_distance_threshold_filters_results(tmp_path: Path) -> None:
    store = ChromaStore(_settings(tmp_path / "vectors"))
    chunks = (
        _chunk("doc-a", "a.txt", 0, None),
        _chunk("doc-b", "b.txt", 0, None),
    )
    store.add_document((chunks[0],), {chunks[0].chunk_id: (1.0, 0.0)})
    store.add_document((chunks[1],), {chunks[1].chunk_id: (0.0, 1.0)})
    models = SimpleNamespace(
        embed_content=lambda **kwargs: SimpleNamespace(
            embeddings=[SimpleNamespace(values=[1.0, 0.0])]
        )
    )
    service = EmbeddingService(
        _settings(tmp_path / "vectors"),
        client=SimpleNamespace(models=models),
    )

    strict = retrieve_documents(
        "A question",
        top_k=2,
        maximum_distance=0.01,
        embedding_service=service,
        vector_store=store,
    )
    disabled = retrieve_documents(
        "A question",
        top_k=2,
        maximum_distance=None,
        embedding_service=service,
        vector_store=store,
    )

    assert strict.returned_count == 1
    assert strict.chunks[0].filename == "a.txt"
    assert disabled.returned_count == 2
