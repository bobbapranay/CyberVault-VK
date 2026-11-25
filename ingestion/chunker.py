"""Approximate-token chunking with paragraph and sentence boundary preference."""

from __future__ import annotations

import hashlib
import re
from typing import Iterable

from config import Settings, load_settings
from ingestion.models import ChunkingError, DocumentChunk, ExtractedDocument

_TOKEN_PATTERN = re.compile(r"\w+(?:['’]\w+)*(?:[.!?]+)?|[^\w\s]", re.UNICODE)
_PARAGRAPH_BREAK = re.compile(r"\r?\n[ \t]*\r?\n")
_SENTENCE_END = re.compile(r"[.!?][\"'”’)\]]*$")


def count_tokens(text: str) -> int:
    """Count approximate lexical tokens rather than characters.

    The lightweight tokenizer counts each Unicode word (including contractions)
    and standalone punctuation mark as one token. It is deterministic and
    dependency-free, but is an estimate rather than Gemini's tokenizer.
    """
    return sum(1 for _ in _TOKEN_PATTERN.finditer(text))


def validate_chunking_parameters(chunk_size: int, chunk_overlap: int) -> None:
    """Validate target size and overlap independently of application settings."""
    if (
        not isinstance(chunk_size, int)
        or isinstance(chunk_size, bool)
        or chunk_size <= 0
    ):
        raise ChunkingError("Chunk size must be a positive integer.")
    if (
        not isinstance(chunk_overlap, int)
        or isinstance(chunk_overlap, bool)
        or chunk_overlap < 0
    ):
        raise ChunkingError("Chunk overlap must be a non-negative integer.")
    if chunk_overlap >= chunk_size:
        raise ChunkingError("Chunk overlap must be smaller than chunk size.")


def _is_sentence_boundary(text: str, token_end: re.Match[str]) -> bool:
    context_start = max(0, token_end.start() - 8)
    return bool(_SENTENCE_END.search(text[context_start : token_end.end()]))


def _choose_preferred_end(
    text: str,
    tokens: list[re.Match[str]],
    start: int,
    end: int,
    chunk_size: int,
    chunk_overlap: int,
) -> int:
    """Prefer a nearby paragraph or sentence boundary without losing overlap."""
    lower_bound = max(
        start + chunk_overlap + 1,
        end - max(1, chunk_size // 5),
    )
    paragraph_ends: list[int] = []
    sentence_ends: list[int] = []
    for next_token in range(lower_bound, end + 1):
        if next_token >= len(tokens):
            continue
        previous = tokens[next_token - 1]
        following = tokens[next_token]
        gap = text[previous.end() : following.start()]
        if _PARAGRAPH_BREAK.search(gap):
            paragraph_ends.append(next_token)
        elif gap and gap.isspace() and _is_sentence_boundary(text, previous):
            sentence_ends.append(next_token)

    if paragraph_ends:
        return paragraph_ends[-1]
    if sentence_ends:
        return sentence_ends[-1]
    return end


def chunk_text(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
) -> list[str]:
    """Split text into bounded token windows with deterministic overlap."""
    validate_chunking_parameters(chunk_size, chunk_overlap)
    tokens = list(_TOKEN_PATTERN.finditer(text))
    if not tokens:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        if end < len(tokens):
            end = _choose_preferred_end(
                text,
                tokens,
                start,
                end,
                chunk_size,
                chunk_overlap,
            )

        chunk = text[tokens[start].start() : tokens[end - 1].end()].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(tokens):
            break
        next_start = max(start + 1, end - chunk_overlap)
        start = next_start
    return chunks


def _resolve_parameters(
    settings: Settings | None,
    chunk_size: int | None,
    chunk_overlap: int | None,
) -> tuple[int, int]:
    if chunk_size is not None and chunk_overlap is not None:
        resolved = (chunk_size, chunk_overlap)
    else:
        resolved_settings = settings or load_settings()
        resolved = (
            chunk_size if chunk_size is not None else resolved_settings.chunk_size,
            (
                chunk_overlap
                if chunk_overlap is not None
                else resolved_settings.chunk_overlap
            ),
        )
    validate_chunking_parameters(*resolved)
    return resolved


def _chunk_id(
    document_id: str,
    page_number: int | None,
    chunk_index: int,
    text: str,
) -> str:
    identity = f"{document_id}\0{page_number}\0{chunk_index}\0{text}".encode("utf-8")
    return f"chunk_{hashlib.sha256(identity).hexdigest()[:32]}"


def chunk_documents(
    documents: Iterable[ExtractedDocument],
    *,
    settings: Settings | None = None,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[DocumentChunk]:
    """Chunk extracted sections while preserving source and page metadata."""
    sections = list(documents)
    if not sections:
        return []
    resolved_size, resolved_overlap = _resolve_parameters(
        settings,
        chunk_size,
        chunk_overlap,
    )

    next_indices: dict[str, int] = {}
    chunks: list[DocumentChunk] = []
    for section in sections:
        text_chunks = chunk_text(section.text, resolved_size, resolved_overlap)
        chunk_index = next_indices.get(section.document_id, 0)
        for text in text_chunks:
            chunks.append(
                DocumentChunk(
                    chunk_id=_chunk_id(
                        section.document_id,
                        section.page_number,
                        chunk_index,
                        text,
                    ),
                    document_id=section.document_id,
                    filename=section.filename,
                    file_type=section.file_type,
                    source=section.source,
                    chunk_index=chunk_index,
                    page_number=section.page_number,
                    text=text,
                    token_count=count_tokens(text),
                )
            )
            chunk_index += 1
        next_indices[section.document_id] = chunk_index
    return chunks
