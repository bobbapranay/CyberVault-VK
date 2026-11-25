"""Application configuration and validation."""

from __future__ import annotations

import os
import re
import math
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent


class ConfigurationError(ValueError):
    """Raised when an application setting has an invalid value."""


@dataclass(frozen=True)
class Settings:
    """Validated application settings.

    The Gemini API key is optional so the dashboard can start before a user
    configures their credentials.
    """

    gemini_api_key: str | None
    embedding_model: str
    generation_model: str
    chroma_persist_directory: Path
    chroma_collection_name: str
    chunk_size: int
    chunk_overlap: int
    retrieval_top_k: int
    embedding_batch_size: int = 32
    embedding_dimension: int = 3072
    retrieval_max_top_k: int = 20
    retrieval_min_distance: float | None = None
    generation_temperature: float = 0.2
    generation_max_output_tokens: int = 1024
    rag_context_limit: int = 12000

    @property
    def has_gemini_api_key(self) -> bool:
        """Return whether a non-empty Gemini API key is configured."""
        return bool(self.gemini_api_key)


def _read_integer(name: str, default: int) -> int:
    """Read an integer environment variable or raise a safe error."""
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer.") from exc


def _read_optional_float(name: str, default: float | None) -> float | None:
    """Read an optional finite float setting; blank or 'off' disables it."""
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip()
    if not value or value.casefold() in {"off", "none", "disabled"}:
        return None
    try:
        return float(value)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be a number or disabled.") from exc


def _read_float(name: str, default: float) -> float:
    """Read a float environment variable or raise a safe error."""
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be a number.") from exc


def validate_config(settings: Settings) -> None:
    """Validate model, storage, and retrieval settings."""
    if not settings.embedding_model.strip():
        raise ConfigurationError("GEMINI_EMBEDDING_MODEL must not be empty.")
    if not settings.generation_model.strip():
        raise ConfigurationError("GEMINI_GENERATION_MODEL must not be empty.")
    if not str(settings.chroma_persist_directory).strip():
        raise ConfigurationError("CHROMA_PERSIST_DIRECTORY must not be empty.")

    collection_name = settings.chroma_collection_name
    if (
        not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{1,61}[A-Za-z0-9]", collection_name)
        or ".." in collection_name
    ):
        raise ConfigurationError(
            "CHROMA_COLLECTION_NAME must be 3–63 characters, start and end "
            "with a letter or number, and contain only letters, numbers, "
            "dots, underscores, or hyphens."
        )
    if settings.chunk_size <= 0:
        raise ConfigurationError("CHUNK_SIZE must be greater than zero.")
    if settings.chunk_overlap < 0 or settings.chunk_overlap >= settings.chunk_size:
        raise ConfigurationError(
            "CHUNK_OVERLAP must be zero or greater and smaller than CHUNK_SIZE."
        )
    if settings.retrieval_top_k <= 0:
        raise ConfigurationError("RETRIEVAL_TOP_K must be greater than zero.")
    if not 1 <= settings.embedding_batch_size <= 100:
        raise ConfigurationError(
            "EMBEDDING_BATCH_SIZE must be between 1 and 100."
        )
    if settings.embedding_dimension <= 0:
        raise ConfigurationError("EMBEDDING_DIMENSION must be greater than zero.")
    if settings.retrieval_max_top_k <= 0:
        raise ConfigurationError("RETRIEVAL_MAX_TOP_K must be greater than zero.")
    if settings.retrieval_top_k > settings.retrieval_max_top_k:
        raise ConfigurationError(
            "RETRIEVAL_TOP_K must not exceed RETRIEVAL_MAX_TOP_K."
        )
    if settings.retrieval_min_distance is not None:
        if not math.isfinite(settings.retrieval_min_distance):
            raise ConfigurationError(
                "RETRIEVAL_MIN_DISTANCE must be a finite number or disabled."
            )
        if not 0.0 <= settings.retrieval_min_distance <= 2.0:
            raise ConfigurationError(
                "RETRIEVAL_MIN_DISTANCE must be between 0.0 and 2.0."
            )
    if not 0.0 <= settings.generation_temperature <= 2.0:
        raise ConfigurationError(
            "GENERATION_TEMPERATURE must be between 0.0 and 2.0."
        )
    if settings.generation_max_output_tokens <= 0:
        raise ConfigurationError(
            "GENERATION_MAX_OUTPUT_TOKENS must be greater than zero."
        )
    if settings.rag_context_limit <= 0:
        raise ConfigurationError("RAG_CONTEXT_LIMIT must be greater than zero.")


def load_settings() -> Settings:
    """Load settings from the project's .env file and process environment."""
    try:
        from dotenv import load_dotenv
    except ImportError as exc:
        raise ConfigurationError(
            "python-dotenv is not installed. Install project dependencies "
            "with `pip install -r requirements.txt`."
        ) from exc

    load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=False)

    persist_directory = os.getenv(
        "CHROMA_PERSIST_DIRECTORY",
        str(PROJECT_ROOT / "data" / "chroma"),
    ).strip()
    if not persist_directory:
        raise ConfigurationError("CHROMA_PERSIST_DIRECTORY must not be empty.")
    api_key = os.getenv("GEMINI_API_KEY", "").strip() or None

    settings = Settings(
        gemini_api_key=api_key,
        embedding_model=os.getenv(
            "GEMINI_EMBEDDING_MODEL", "gemini-embedding-001"
        ).strip(),
        generation_model=os.getenv(
            "GEMINI_GENERATION_MODEL", "gemini-3.5-flash-lite"
        ).strip(),
        chroma_persist_directory=Path(persist_directory).expanduser(),
        chroma_collection_name=os.getenv(
            "CHROMA_COLLECTION_NAME", "cybervault_documents"
        ).strip(),
        chunk_size=_read_integer("CHUNK_SIZE", 500),
        chunk_overlap=_read_integer("CHUNK_OVERLAP", 100),
        retrieval_top_k=_read_integer("RETRIEVAL_TOP_K", 5),
        embedding_batch_size=_read_integer("EMBEDDING_BATCH_SIZE", 32),
        embedding_dimension=_read_integer("EMBEDDING_DIMENSION", 3072),
        retrieval_max_top_k=_read_integer("RETRIEVAL_MAX_TOP_K", 20),
        retrieval_min_distance=_read_optional_float(
            "RETRIEVAL_MIN_DISTANCE",
            None,
        ),
        generation_temperature=_read_float("GENERATION_TEMPERATURE", 0.2),
        generation_max_output_tokens=_read_integer(
            "GENERATION_MAX_OUTPUT_TOKENS",
            1024,
        ),
        rag_context_limit=_read_integer("RAG_CONTEXT_LIMIT", 12000),
    )
    validate_config(settings)
    return settings
