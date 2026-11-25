"""Tests for PDF, TXT, and Markdown loading and metadata."""

from io import BytesIO

import pytest
from pypdf import PdfReader, PdfWriter

from ingestion.document_loader import (
    generate_document_id,
    load_document,
    load_document_bytes,
    load_markdown_document,
    load_pdf_document,
    load_txt_document,
)
from ingestion.models import (
    DocumentLoadError,
    EmptyDocumentError,
    UnsupportedFileTypeError,
)
from tests.pdf_fixtures import build_pdf, write_pdf


def test_pdf_extracts_each_page_and_preserves_original_page_numbers(
    tmp_path,
) -> None:
    pdf_path = write_pdf(
        tmp_path / "report.pdf",
        ["First page has text", None, "Third page has text"],
    )

    sections = load_pdf_document(pdf_path)

    assert [section.page_number for section in sections] == [1, 3]
    assert "First page has text" in sections[0].text
    assert "Third page has text" in sections[1].text
    assert sections[0].document_id == sections[1].document_id
    assert sections[0].metadata["filename"] == "report.pdf"
    assert sections[0].metadata["file_type"] == "pdf"
    assert sections[0].metadata["source"] == str(pdf_path.resolve())


def test_load_document_dispatches_multi_page_pdf(tmp_path) -> None:
    pdf_path = write_pdf(tmp_path / "multi.pdf", ["Page one", "Page two"])

    sections = load_document(pdf_path)

    assert [section.page_number for section in sections] == [1, 2]


@pytest.mark.parametrize(
    ("filename", "loader"),
    [
        ("notes.txt", load_txt_document),
        ("notes.md", load_markdown_document),
    ],
)
def test_text_and_markdown_preserve_utf8_paragraphs_and_metadata(
    tmp_path, filename, loader
) -> None:
    expected = "Café notes.\n\nSecond paragraph."
    path = tmp_path / filename
    path.write_bytes(expected.encode("utf-8"))

    sections = loader(path)

    assert len(sections) == 1
    assert sections[0].text == expected
    assert sections[0].page_number is None
    assert sections[0].metadata["document_id"] == sections[0].document_id
    assert sections[0].metadata["source"] == str(path.resolve())


def test_uploaded_markdown_uses_filename_as_document_level_source() -> None:
    section = load_document_bytes("guide.MD", b"# Title\n\nBody.")[0]

    assert section.filename == "guide.MD"
    assert section.file_type == "md"
    assert section.page_number is None
    assert section.source == "guide.MD"


def test_empty_text_and_all_blank_pdf_are_rejected(tmp_path) -> None:
    text_path = tmp_path / "empty.txt"
    text_path.write_bytes(b" \r\n\t")
    pdf_path = write_pdf(tmp_path / "blank.pdf", [None, ""])

    with pytest.raises(EmptyDocumentError, match="contains no text"):
        load_txt_document(text_path)
    with pytest.raises(EmptyDocumentError, match="No extractable text"):
        load_pdf_document(pdf_path)


def test_unsupported_extension_and_invalid_pdf_are_reported(tmp_path) -> None:
    unsupported_path = tmp_path / "archive.doc"
    unsupported_path.write_bytes(b"content")
    invalid_pdf = tmp_path / "broken.pdf"
    invalid_pdf.write_bytes(b"not a PDF")

    with pytest.raises(UnsupportedFileTypeError, match="Supported formats"):
        load_document(unsupported_path)
    with pytest.raises(DocumentLoadError, match="corrupted or unreadable"):
        load_pdf_document(invalid_pdf)


def test_invalid_utf8_is_reported_without_lossy_decoding() -> None:
    with pytest.raises(DocumentLoadError, match="not valid UTF-8"):
        load_document_bytes("invalid.txt", b"\xff\xfe")


def test_encrypted_pdf_is_rejected_with_a_helpful_message() -> None:
    reader = PdfReader(BytesIO(build_pdf(["Secret text"])))
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    writer.encrypt("password")
    encrypted = BytesIO()
    writer.write(encrypted)

    with pytest.raises(DocumentLoadError, match="encrypted"):
        load_document_bytes("locked.pdf", encrypted.getvalue())


def test_document_ids_are_stable_and_content_sensitive() -> None:
    first = generate_document_id("report.txt", b"same content")

    assert generate_document_id("report.txt", b"same content") == first
    assert generate_document_id("report.txt", b"changed content") != first
    assert generate_document_id("renamed.txt", b"same content") != first
