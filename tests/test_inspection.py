"""Tests for read-only chunk inspection statistics."""

import pytest

from ingestion.chunker import chunk_documents
from ingestion.inspection import get_chunk_by_id, inspect_chunks
from ingestion.models import ExtractedDocument


def test_inspection_reports_statistics_and_sample_previews() -> None:
    sections = [
        ExtractedDocument(
            document_id="doc-a",
            filename="a.txt",
            file_type="txt",
            source="a.txt",
            text="one two three four five",
        ),
        ExtractedDocument(
            document_id="doc-b",
            filename="b.pdf",
            file_type="pdf",
            source="b.pdf",
            page_number=2,
            text="six seven eight",
        ),
    ]
    chunks = chunk_documents(sections, chunk_size=3, chunk_overlap=1)

    report = inspect_chunks(chunks, sample_size=2)

    assert report.total_documents_processed == 2
    assert report.total_pages_extracted == 1
    assert report.total_chunks_generated == len(chunks)
    assert report.minimum_chunk_length >= 1
    assert report.maximum_chunk_length <= 3
    assert len(report.sample_chunks) == 2
    assert get_chunk_by_id(chunks, chunks[0].chunk_id) == chunks[0]
    with pytest.raises(KeyError):
        get_chunk_by_id(chunks, "missing")


def test_inspection_handles_no_chunks_and_rejects_negative_sample_size() -> None:
    report = inspect_chunks([])

    assert report.total_chunks_generated == 0
    assert report.average_chunk_length == 0
    assert report.minimum_chunk_length == 0
    assert report.maximum_chunk_length == 0
    with pytest.raises(ValueError, match="Sample size"):
        inspect_chunks([], sample_size=-1)
