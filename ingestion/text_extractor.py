"""Text extraction helpers for supported document formats."""

from __future__ import annotations

from io import BytesIO
import logging

from ingestion.models import DocumentLoadError

logger = logging.getLogger(__name__)


def decode_utf8(data: bytes, filename: str) -> str:
    """Decode UTF-8 text, including an optional BOM, without lossy fallback."""
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise DocumentLoadError(
            f"{filename} is not valid UTF-8. Re-save it with UTF-8 encoding."
        ) from exc


def extract_pdf_pages(data: bytes) -> list[tuple[int, str]]:
    """Extract non-empty text page by page, retaining original page numbers."""
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise DocumentLoadError(
            "PDF support is unavailable. Install the project dependencies "
            "with `pip install -r requirements.txt`."
        ) from exc

    try:
        reader = PdfReader(BytesIO(data), strict=False)
        if reader.is_encrypted:
            raise DocumentLoadError(
                "This PDF is encrypted. Remove its password before uploading."
            )

        pages: list[tuple[int, str]] = []
        for page_number, page in enumerate(reader.pages, start=1):
            try:
                page_text = page.extract_text() or ""
            except Exception as exc:
                logger.warning("Unable to extract text from PDF page %d", page_number)
                raise DocumentLoadError(
                    f"Text could not be extracted from PDF page {page_number}."
                ) from exc
            if page_text.strip():
                pages.append((page_number, page_text))
        return pages
    except DocumentLoadError:
        raise
    except Exception as exc:
        raise DocumentLoadError(
            "This PDF is corrupted or unreadable. Check the file and try again."
        ) from exc
