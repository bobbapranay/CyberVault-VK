"""Integration tests for batch processing, isolation, and deduplication."""

from ingestion.models import DocumentInput
from ingestion.processor import ingest_documents


def test_multiple_documents_process_with_partial_failure_and_progress() -> None:
    inputs = [
        DocumentInput("first.txt", b"first document with enough text"),
        DocumentInput("broken.pdf", b"not a PDF"),
        DocumentInput("third.md", b"# Third\n\nAnother valid document"),
    ]
    progress: list[tuple[int, int, str]] = []

    results = ingest_documents(
        inputs,
        chunk_size=5,
        chunk_overlap=1,
        progress_callback=lambda done, total, name: progress.append(
            (done, total, name)
        ),
    )

    assert [result.status for result in results] == [
        "processed",
        "failed",
        "processed",
    ]
    assert results[0].chunks
    assert results[1].error and "corrupted or unreadable" in results[1].error
    assert results[2].chunks[0].source == "third.md"
    assert progress == [
        (1, 3, "first.txt"),
        (2, 3, "broken.pdf"),
        (3, 3, "third.md"),
    ]


def test_duplicate_upload_is_not_reprocessed() -> None:
    document = DocumentInput("same.txt", b"some reusable content")
    first_result = ingest_documents(
        [document],
        chunk_size=4,
        chunk_overlap=1,
    )[0]
    duplicate_result = ingest_documents(
        [document],
        chunk_size=4,
        chunk_overlap=1,
        already_processed_ids={first_result.document_id},
    )[0]

    assert first_result.status == "processed"
    assert duplicate_result.status == "duplicate"
    assert duplicate_result.document_id == first_result.document_id
    assert duplicate_result.chunks == ()


def test_duplicates_within_a_batch_only_add_chunks_once() -> None:
    document = DocumentInput("same.txt", b"same batch duplicate text")

    results = ingest_documents(
        [document, document],
        chunk_size=4,
        chunk_overlap=1,
    )

    assert [result.status for result in results] == ["processed", "duplicate"]


def test_empty_batch_returns_without_loading_configuration() -> None:
    assert ingest_documents([]) == []
