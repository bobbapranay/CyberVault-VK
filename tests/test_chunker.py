"""Tests for approximate token counting and source-aware chunking."""

from dataclasses import FrozenInstanceError

import pytest

from ingestion.chunker import chunk_documents, chunk_text, count_tokens
from ingestion.models import ChunkingError, ExtractedDocument


def make_section(
    text: str,
    *,
    document_id: str = "doc_test",
    page_number: int | None = None,
) -> ExtractedDocument:
    return ExtractedDocument(
        document_id=document_id,
        filename="source.txt",
        file_type="txt",
        source="source.txt",
        text=text,
        page_number=page_number,
    )


def test_token_count_uses_lexical_tokens_not_character_count() -> None:
    assert count_tokens("alpha, beta!") == 3
    assert count_tokens("") == 0


def test_chunk_size_is_configurable_and_chunks_are_bounded() -> None:
    chunks = chunk_text(" ".join(f"word{index}" for index in range(19)), 6, 1)

    assert len(chunks) > 1
    assert all(count_tokens(chunk) <= 6 for chunk in chunks)


def test_consecutive_chunks_have_configured_token_overlap() -> None:
    chunks = chunk_text("a b c d e f g h i j", 4, 2)

    assert chunks == ["a b c d", "c d e f", "e f g h", "g h i j"]
    for previous, following in zip(chunks, chunks[1:]):
        assert previous.split()[-2:] == following.split()[:2]


def test_short_and_empty_documents_do_not_create_empty_chunks() -> None:
    assert chunk_text("A short document.", 20, 3) == ["A short document."]
    assert chunk_text(" \n\t ", 20, 3) == []


def test_paragraph_and_sentence_boundaries_are_preferred_when_near_target() -> None:
    paragraphs = "one two three four five six seven eight\n\nnine ten eleven twelve"
    paragraph_chunks = chunk_text(paragraphs, 10, 2)
    sentences = (
        "One two three four five. Six seven eight nine ten. "
        "Eleven twelve."
    )
    sentence_chunks = chunk_text(sentences, 10, 2)

    assert paragraph_chunks[0].endswith("eight")
    assert paragraph_chunks[1].startswith("seven eight")
    assert sentence_chunks[0].endswith("ten.")


def test_long_paragraph_is_split_without_splitting_words() -> None:
    words = [f"term{index}" for index in range(29)]

    chunks = chunk_text(" ".join(words), 7, 2)

    assert all(count_tokens(chunk) <= 7 for chunk in chunks)
    assert all(word in words for chunk in chunks for word in chunk.split())
    assert len(chunks) > 1


def test_chunking_rejects_overlap_equal_to_or_larger_than_size() -> None:
    with pytest.raises(ChunkingError, match="smaller than chunk size"):
        chunk_text("some words", 5, 5)
    with pytest.raises(ChunkingError, match="smaller than chunk size"):
        chunk_text("some words", 5, 6)


@pytest.mark.parametrize(
    ("chunk_size", "chunk_overlap", "message"),
    [
        (0, 0, "positive integer"),
        (-1, 0, "positive integer"),
        (5, -1, "non-negative integer"),
    ],
)
def test_chunking_rejects_invalid_size_and_negative_overlap(
    chunk_size: int,
    chunk_overlap: int,
    message: str,
) -> None:
    with pytest.raises(ChunkingError, match=message):
        chunk_text("some words", chunk_size, chunk_overlap)


def test_chunk_ids_are_stable_and_metadata_is_preserved() -> None:
    section = make_section("alpha beta gamma delta epsilon zeta")

    first = chunk_documents([section], chunk_size=3, chunk_overlap=1)
    second = chunk_documents([section], chunk_size=3, chunk_overlap=1)

    assert [chunk.chunk_id for chunk in first] == [
        chunk.chunk_id for chunk in second
    ]
    assert first[0].document_id == section.document_id
    assert first[0].filename == section.filename
    assert first[0].source == section.source
    assert first[0].metadata["chunk_index"] == 0
    with pytest.raises(FrozenInstanceError):
        first[0].text = "changed"


def test_pdf_sections_keep_page_numbers_and_document_chunk_indices() -> None:
    sections = [
        make_section("page one alpha beta", page_number=1),
        make_section("page two gamma delta", page_number=2),
    ]

    chunks = chunk_documents(sections, chunk_size=2, chunk_overlap=0)

    assert [chunk.page_number for chunk in chunks] == [1, 1, 2, 2]
    assert [chunk.chunk_index for chunk in chunks] == [0, 1, 2, 3]
    assert all(chunk.document_id == sections[0].document_id for chunk in chunks)
