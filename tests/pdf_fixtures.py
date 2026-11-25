"""Small generated PDF fixtures for document loader tests."""

from __future__ import annotations

from pathlib import Path


def build_pdf(page_texts: list[str | None]) -> bytes:
    """Build a minimal PDF with selectable Helvetica text on requested pages."""
    page_count = len(page_texts)
    font_object = 3 + 2 * page_count
    kids = " ".join(
        f"{3 + 2 * index} 0 R" for index in range(page_count)
    )
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{kids}] /Count {page_count} >>".encode("ascii"),
    ]

    for index, page_text in enumerate(page_texts):
        page_object = 3 + 2 * index
        content_object = page_object + 1
        objects.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                f"/Resources << /Font << /F1 {font_object} 0 R >> >> "
                f"/Contents {content_object} 0 R >>"
            ).encode("ascii")
        )
        escaped_text = (page_text or "").replace("\\", "\\\\")
        escaped_text = escaped_text.replace("(", "\\(").replace(")", "\\)")
        stream = (
            f"BT /F1 12 Tf 72 720 Td ({escaped_text}) Tj ET"
            if page_text
            else ""
        ).encode("ascii")
        objects.append(
            f"<< /Length {len(stream)} >>\nstream\n".encode("ascii")
            + stream
            + b"\nendstream"
        )

    objects.append(
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    )
    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for object_number, value in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{object_number} 0 obj\n".encode("ascii"))
        output.extend(value)
        output.extend(b"\nendobj\n")

    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(output)


def write_pdf(path: Path, page_texts: list[str | None]) -> Path:
    """Write a generated PDF fixture to a temporary path."""
    path.write_bytes(build_pdf(page_texts))
    return path
