"""Google GenAI document embedding with bounded retries and partial results."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import math
import time
from typing import Any, Callable, Sequence

from config import Settings, load_settings
from ingestion.models import DocumentChunk

logger = logging.getLogger(__name__)
RETRYABLE_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})
RETRYABLE_EXCEPTION_NAMES = frozenset(
    {
        "ConnectError",
        "ConnectTimeout",
        "ReadTimeout",
        "Timeout",
        "TimeoutError",
        "TimeoutException",
    }
)


class EmbeddingServiceError(RuntimeError):
    """Raised when an embedding request cannot be prepared or used."""


class MissingAPIKeyError(EmbeddingServiceError):
    """Raised when a live Gemini request is attempted without a key."""


class InvalidEmbeddingResponseError(EmbeddingServiceError):
    """Raised when the API response is incomplete or malformed."""


@dataclass(frozen=True)
class EmbeddedVector:
    """A chunk ID paired with its validated embedding vector."""

    chunk_id: str
    values: tuple[float, ...]


@dataclass(frozen=True)
class EmbeddingFailure:
    """A failed chunk embedding with a safe, user-facing reason."""

    chunk_id: str
    message: str


@dataclass(frozen=True)
class EmbeddingBatchResult:
    """Successful vectors and failures accumulated across request batches."""

    embeddings: tuple[EmbeddedVector, ...]
    failures: tuple[EmbeddingFailure, ...]
    batches_processed: int

    @property
    def successful_count(self) -> int:
        """Return the number of successfully embedded chunks."""
        return len(self.embeddings)

    @property
    def failed_count(self) -> int:
        """Return the number of chunks that could not be embedded."""
        return len(self.failures)


class EmbeddingService:
    """Create Gemini embeddings using the configured document task type.

    The Google GenAI SDK supports ``client.models.embed_content`` with a list
    of strings and ``EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")`` for
    ``gemini-embedding-001``. Requests are divided into bounded local batches.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        client: Any | None = None,
        max_retries: int = 3,
        base_delay_seconds: float = 0.5,
        max_delay_seconds: float = 4.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.settings = settings or load_settings()
        if max_retries < 0:
            raise ValueError("max_retries must be zero or greater.")
        if base_delay_seconds < 0 or max_delay_seconds < 0:
            raise ValueError("Retry delays must be zero or greater.")
        self._client = client
        self._owns_client = False
        self._max_retries = max_retries
        self._base_delay_seconds = base_delay_seconds
        self._max_delay_seconds = max_delay_seconds
        self._sleep = sleep
        self._embedding_dimension: int | None = None

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        if not self.settings.has_gemini_api_key:
            raise MissingAPIKeyError(
                "GEMINI_API_KEY is not configured. Add it to the project .env "
                "file before indexing documents."
            )
        try:
            from google import genai
        except ImportError as exc:
            raise EmbeddingServiceError(
                "Google GenAI SDK is not installed. Install project dependencies "
                "with `pip install -r requirements.txt`."
            ) from exc
        try:
            self._client = genai.Client(api_key=self.settings.gemini_api_key)
        except Exception as exc:
            logger.warning(
                "Unable to initialize the Gemini client (%s)",
                type(exc).__name__,
            )
            raise EmbeddingServiceError(
                "Unable to initialize the Gemini client. Check the environment "
                "and try again."
            ) from exc
        self._owns_client = True
        return self._client

    def get_client(self) -> Any:
        """Return the initialized SDK client for services sharing credentials."""
        return self._get_client()

    @staticmethod
    def _status_code(error: Exception) -> int | None:
        for attribute in ("code", "status_code", "status"):
            value = getattr(error, attribute, None)
            if isinstance(value, int):
                return value
        return None

    @classmethod
    def _is_retryable(cls, error: Exception) -> bool:
        if cls._status_code(error) in RETRYABLE_STATUS_CODES:
            return True
        if isinstance(error, (TimeoutError, ConnectionError)):
            return True
        return type(error).__name__ in RETRYABLE_EXCEPTION_NAMES

    def _validate_response(
        self,
        response: Any,
        expected_count: int,
    ) -> list[tuple[float, ...]]:
        response_embeddings = getattr(response, "embeddings", None)
        if not isinstance(response_embeddings, (list, tuple)):
            raise InvalidEmbeddingResponseError(
                "Gemini returned an invalid embedding response."
            )
        if len(response_embeddings) != expected_count:
            raise InvalidEmbeddingResponseError(
                "Gemini returned a different number of embeddings than requested."
            )

        vectors: list[tuple[float, ...]] = []
        for embedding in response_embeddings:
            raw_values = getattr(embedding, "values", None)
            if not isinstance(raw_values, (list, tuple)) or not raw_values:
                raise InvalidEmbeddingResponseError(
                    "Gemini returned an empty or malformed embedding vector."
                )
            if any(
                isinstance(value, bool) or not isinstance(value, (int, float))
                for value in raw_values
            ):
                raise InvalidEmbeddingResponseError(
                    "Gemini returned non-numeric embedding values."
                )
            values = tuple(float(value) for value in raw_values)
            if not all(math.isfinite(value) for value in values):
                raise InvalidEmbeddingResponseError(
                    "Gemini returned a non-finite embedding value."
                )
            vectors.append(values)

        dimensions = {len(vector) for vector in vectors}
        if len(dimensions) != 1:
            raise InvalidEmbeddingResponseError(
                "Gemini returned inconsistent embedding dimensions."
            )
        dimension = dimensions.pop()
        if dimension != self.settings.embedding_dimension:
            raise InvalidEmbeddingResponseError(
                "Gemini returned an unexpected embedding dimension."
            )
        if (
            self._embedding_dimension is not None
            and dimension != self._embedding_dimension
        ):
            raise InvalidEmbeddingResponseError(
                "Gemini returned an unexpected embedding dimension."
            )
        self._embedding_dimension = dimension
        return vectors

    def _embed_batch(
        self,
        texts: Sequence[str],
        *,
        task_type: str,
    ) -> list[tuple[float, ...]]:
        try:
            from google.genai import types
        except ImportError as exc:
            raise EmbeddingServiceError(
                "Google GenAI SDK is not installed. Install project dependencies "
                "with `pip install -r requirements.txt`."
            ) from exc

        client = self._get_client()
        for attempt in range(self._max_retries + 1):
            try:
                response = client.models.embed_content(
                    model=self.settings.embedding_model,
                    contents=list(texts),
                    config=types.EmbedContentConfig(
                        task_type=task_type,
                        output_dimensionality=self.settings.embedding_dimension,
                    ),
                )
                return self._validate_response(response, len(texts))
            except InvalidEmbeddingResponseError:
                raise
            except Exception as exc:
                status_code = self._status_code(exc)
                retryable = self._is_retryable(exc)
                if retryable and attempt < self._max_retries:
                    delay = min(
                        self._base_delay_seconds * (2**attempt),
                        self._max_delay_seconds,
                    )
                    logger.warning(
                        "Gemini embedding request failed with status %s; "
                        "retry %d of %d.",
                        status_code or type(exc).__name__,
                        attempt + 1,
                        self._max_retries,
                    )
                    self._sleep(delay)
                    continue
                if status_code == 429:
                    message = (
                        "Gemini rate limit reached after bounded retries. "
                        "Wait a short time and try again."
                    )
                else:
                    message = "Gemini embedding request failed."
                logger.warning(
                    "Gemini embedding batch failed with status %s (%s).",
                    status_code or "unknown",
                    type(exc).__name__,
                )
                raise EmbeddingServiceError(message) from exc

        raise EmbeddingServiceError("Gemini embedding request failed.")

    def embed_chunks(
        self,
        chunks: Sequence[DocumentChunk],
        *,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> EmbeddingBatchResult:
        """Embed chunks in configured batches and retain per-batch successes."""
        if not chunks:
            return EmbeddingBatchResult((), (), 0)

        chunk_ids = [chunk.chunk_id for chunk in chunks]
        if len(chunk_ids) != len(set(chunk_ids)):
            raise EmbeddingServiceError("Chunk IDs must be unique per request.")

        embeddings: list[EmbeddedVector] = []
        failures: list[EmbeddingFailure] = [
            EmbeddingFailure(chunk.chunk_id, "Chunk text is empty.")
            for chunk in chunks
            if not chunk.text.strip()
        ]
        valid_chunks = [chunk for chunk in chunks if chunk.text.strip()]
        if not valid_chunks:
            return EmbeddingBatchResult((), tuple(failures), 0)

        self._get_client()
        batch_size = self.settings.embedding_batch_size
        batches = [
            valid_chunks[start : start + batch_size]
            for start in range(0, len(valid_chunks), batch_size)
        ]
        for batch_index, batch in enumerate(batches, start=1):
            try:
                vectors = self._embed_batch(
                    [chunk.text for chunk in batch],
                    task_type="RETRIEVAL_DOCUMENT",
                )
                embeddings.extend(
                    EmbeddedVector(chunk.chunk_id, vector)
                    for chunk, vector in zip(batch, vectors)
                )
            except EmbeddingServiceError as exc:
                failures.extend(
                    EmbeddingFailure(chunk.chunk_id, str(exc)) for chunk in batch
                )
            if progress_callback is not None:
                progress_callback(batch_index, len(batches))

        return EmbeddingBatchResult(
            embeddings=tuple(embeddings),
            failures=tuple(failures),
            batches_processed=len(batches),
        )

    def embed_query(self, query: str) -> tuple[float, ...]:
        """Embed one natural-language query using Gemini RETRIEVAL_QUERY."""
        if not isinstance(query, str) or not query.strip():
            raise EmbeddingServiceError("Search query must not be empty.")
        vectors = self._embed_batch(
            [query.strip()],
            task_type="RETRIEVAL_QUERY",
        )
        if len(vectors) != 1:
            raise InvalidEmbeddingResponseError(
                "Gemini returned an invalid query embedding."
            )
        return vectors[0]

    def close(self) -> None:
        """Close a client created by this service; injected clients stay owned."""
        if self._owns_client and self._client is not None:
            self._client.close()
            self._client = None
            self._owns_client = False
