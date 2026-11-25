"""RAG context, citations, missing-context, Plain LLM, and compare tests."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from config import Settings
from core.generation_service import (
    GenerationError,
    GenerationResult,
    GenerationService,
)
from core.rag_pipeline import (
    build_document_context,
    generate_comparison_response,
    generate_plain_llm_response,
    generate_rag_response,
    validate_citations,
)
from core.retrieval_engine import (
    RetrievedChunk,
    RetrievalResult,
)


def _settings(path: Path) -> Settings:
    return Settings(
        gemini_api_key="test-key",
        embedding_model="embedding-model",
        generation_model="gemini-test-model",
        chroma_persist_directory=path,
        chroma_collection_name="cybervault_documents",
        chunk_size=500,
        chunk_overlap=100,
        retrieval_top_k=5,
        embedding_dimension=2,
        rag_context_limit=500,
        generation_temperature=0.2,
        generation_max_output_tokens=512,
    )


def _chunk(
    chunk_id: str,
    filename: str,
    text: str,
    *,
    rank: int = 1,
    page: int | None = None,
) -> RetrievedChunk:
    return RetrievedChunk(
        rank=rank,
        chunk_id=chunk_id,
        document_id=f"doc-{filename}",
        filename=filename,
        file_type=filename.rsplit(".", 1)[-1],
        source=filename,
        chunk_index=rank - 1,
        page_number=page,
        token_count=10,
        cosine_distance=0.12,
        text=text,
    )


class FakeGenerationService:
    def __init__(self, text: str = "Supported answer [1]."):
        self.text = text
        self.calls = []

    def generate(self, prompt, *, system_instruction=None):
        self.calls.append((prompt, system_instruction))
        return GenerationResult(
            text=self.text,
            model="gemini-test-model",
            duration_seconds=0.01,
        )


def test_context_preserves_metadata_and_rejects_duplicate_context() -> None:
    chunk = _chunk("chunk-1", "guide.pdf", "Three-layer architecture.", page=12)
    result = build_document_context((chunk, chunk), context_limit=1000)

    assert "[1]" in result.text
    assert "guide.pdf" in result.text
    assert "Page 12" in result.text
    assert "Chunk ID: chunk-1" in result.text
    assert result.included_chunk_ids == ("chunk-1",)
    assert result.truncated is False


def test_context_marks_document_level_source() -> None:
    chunk = _chunk("chunk-1", "notes.txt", "Passwords rotate monthly.")
    result = build_document_context((chunk,))

    assert "Document-level source" in result.text


def test_context_limit_does_not_include_partial_chunk(tmp_path: Path) -> None:
    chunk = _chunk("chunk-1", "guide.txt", "A" * 1000)
    result = build_document_context((chunk,), context_limit=100)

    assert result.text == ""
    assert result.truncated is True


def test_citation_validation_removes_unretrieved_reference() -> None:
    chunk = _chunk("chunk-1", "guide.txt", "A supported fact.")
    context = build_document_context((chunk,))

    answer, references = validate_citations(
        "Supported [1]. Unsupported [99].",
        context.source_references,
    )

    assert "[99]" not in answer
    assert "[1]" in answer
    assert len(references) == 1
    assert references[0].filename == "guide.txt"


def test_citation_number_maps_to_the_correct_chunk_and_page() -> None:
    first = _chunk("chunk-1", "first.pdf", "First source.", page=2)
    second = _chunk("chunk-2", "second.pdf", "Second source.", rank=2, page=8)
    context = build_document_context((first, second))

    answer, references = validate_citations(
        "Supported by the second source [2]. Invented [3].",
        context.source_references,
    )

    assert "[3]" not in answer
    assert "[2]" in answer
    assert references == (context.source_references[1],)
    assert references[0].chunk_id == "chunk-2"
    assert references[0].filename == "second.pdf"
    assert references[0].page_number == 8


def test_grouped_citations_keep_valid_sources_and_remove_invalid_numbers() -> None:
    first = _chunk("chunk-1", "first.pdf", "First source.", page=2)
    second = _chunk("chunk-2", "second.pdf", "Second source.", rank=2, page=8)
    context = build_document_context((first, second))

    answer, references = validate_citations(
        "Supported by both [1, 2]. Mixed [2, 99]. Invalid [99].",
        context.source_references,
    )

    assert "[1, 2]" in answer
    assert "Mixed [2]." in answer
    assert "Invalid [99]" not in answer
    assert tuple(reference.number for reference in references) == (1, 2)


def test_rag_pipeline_retrieves_and_injects_context(monkeypatch, tmp_path: Path) -> None:
    from core import rag_pipeline

    chunk = _chunk("chunk-1", "guide.txt", "The vault uses three layers.")
    retrieval = RetrievalResult(
        query="architecture",
        requested_top_k=5,
        maximum_distance=None,
        returned_count=1,
        duration_seconds=0.02,
        chunks=(chunk,),
    )
    generator = FakeGenerationService(
        "The vault uses three layers [1]."
    )
    monkeypatch.setattr(
        rag_pipeline,
        "retrieve_documents",
        lambda *args, **kwargs: retrieval,
    )
    embedding = SimpleNamespace(settings=_settings(tmp_path))
    store = SimpleNamespace()

    response = generate_rag_response(
        "What architecture does the vault use?",
        settings=_settings(tmp_path),
        embedding_service=embedding,
        vector_store=store,
        generation_service=generator,
    )

    assert "three layers" in response.answer
    assert response.retrieved_chunks == (chunk,)
    assert response.source_references[0].filename == "guide.txt"
    prompt = generator.calls[0][0]
    assert "DOCUMENT CONTEXT" in prompt
    assert "three layers" in prompt


def test_rag_without_a_valid_citation_returns_insufficient_context(
    monkeypatch,
    tmp_path: Path,
) -> None:
    from core import rag_pipeline

    chunk = _chunk("chunk-1", "guide.txt", "A related but insufficient fact.")
    retrieval = RetrievalResult(
        query="unanswerable",
        requested_top_k=5,
        maximum_distance=None,
        returned_count=1,
        duration_seconds=0.01,
        chunks=(chunk,),
    )
    monkeypatch.setattr(
        rag_pipeline,
        "retrieve_documents",
        lambda *args, **kwargs: retrieval,
    )
    generator = FakeGenerationService("An unsupported claim [99].")

    response = generate_rag_response(
        "Question not answered by the context",
        settings=_settings(tmp_path),
        embedding_service=SimpleNamespace(settings=_settings(tmp_path)),
        vector_store=SimpleNamespace(),
        generation_service=generator,
    )

    assert response.missing_context is True
    assert response.source_references == ()
    assert "do not contain sufficient verified information" in response.answer
    assert "unsupported claim" not in response.answer


def test_missing_context_skips_generation(monkeypatch, tmp_path: Path) -> None:
    from core import rag_pipeline

    retrieval = RetrievalResult(
        query="unknown",
        requested_top_k=5,
        maximum_distance=None,
        returned_count=0,
        duration_seconds=0.01,
        chunks=(),
    )
    monkeypatch.setattr(
        rag_pipeline,
        "retrieve_documents",
        lambda *args, **kwargs: retrieval,
    )
    generator = FakeGenerationService()

    response = generate_rag_response(
        "What is outside the uploaded documents?",
        settings=_settings(tmp_path),
        embedding_service=SimpleNamespace(settings=_settings(tmp_path)),
        vector_store=SimpleNamespace(),
        generation_service=generator,
    )

    assert response.missing_context is True
    assert "do not contain" in response.answer
    assert generator.calls == []


def test_plain_llm_does_not_receive_document_context() -> None:
    generator = FakeGenerationService("General answer.")

    response = generate_plain_llm_response(
        "Explain cybersecurity",
        generation_service=generator,
    )

    prompt = generator.calls[0][0]
    assert "DOCUMENT CONTEXT" not in prompt
    assert "Do not claim" in generator.calls[0][1]
    assert response.answer == "General answer."


def test_compare_runs_plain_and_rag_independently(monkeypatch, tmp_path: Path) -> None:
    from core import rag_pipeline

    chunk = _chunk("chunk-1", "guide.txt", "Document-specific fact.")
    retrieval = RetrievalResult(
        query="specific fact",
        requested_top_k=5,
        maximum_distance=None,
        returned_count=1,
        duration_seconds=0.01,
        chunks=(chunk,),
    )
    monkeypatch.setattr(
        rag_pipeline,
        "retrieve_documents",
        lambda *args, **kwargs: retrieval,
    )
    generator = FakeGenerationService("Document-specific fact [1].")

    result = generate_comparison_response(
        "What is the specific fact?",
        settings=_settings(tmp_path),
        embedding_service=SimpleNamespace(settings=_settings(tmp_path)),
        vector_store=SimpleNamespace(),
        generation_service=generator,
    )

    assert result.question == "What is the specific fact?"
    assert len(generator.calls) == 2
    assert "DOCUMENT CONTEXT" not in generator.calls[0][0]
    assert "DOCUMENT CONTEXT" in generator.calls[1][0]
