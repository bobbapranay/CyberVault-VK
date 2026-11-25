"""Gemini text generation for Plain LLM and grounded RAG responses."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import time
from typing import Any, Callable

from config import Settings, load_settings

logger = logging.getLogger(__name__)
RETRYABLE_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})


class GenerationError(RuntimeError):
    """Raised when Gemini text generation cannot be completed."""


class MissingGenerationAPIKeyError(GenerationError):
    """Raised when generation is attempted without a configured API key."""


@dataclass(frozen=True)
class GenerationResult:
    """A validated generated text response."""

    text: str
    model: str
    duration_seconds: float


class GenerationService:
    """Generate text through the configured Gemini model."""

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
        self._client = client
        self._owns_client = False
        self._max_retries = max_retries
        self._base_delay_seconds = base_delay_seconds
        self._max_delay_seconds = max_delay_seconds
        self._sleep = sleep

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        if not self.settings.has_gemini_api_key:
            raise MissingGenerationAPIKeyError(
                "GEMINI_API_KEY is not configured. Add it before generating."
            )
        try:
            from google import genai
        except ImportError as exc:
            raise GenerationError(
                "Google GenAI SDK is not installed. Install project dependencies."
            ) from exc
        try:
            self._client = genai.Client(api_key=self.settings.gemini_api_key)
        except Exception as exc:
            logger.warning(
                "Unable to initialize Gemini generation client (%s)",
                type(exc).__name__,
            )
            raise GenerationError(
                "Unable to initialize the Gemini generation client."
            ) from exc
        self._owns_client = True
        return self._client

    @staticmethod
    def _status_code(error: Exception) -> int | None:
        for attribute in ("code", "status_code", "status"):
            value = getattr(error, attribute, None)
            if isinstance(value, int):
                return value
        return None

    def generate(
        self,
        prompt: str,
        *,
        system_instruction: str | None = None,
    ) -> GenerationResult:
        """Generate text with configured model, temperature, and token limit."""
        if not isinstance(prompt, str) or not prompt.strip():
            raise GenerationError("Generation prompt must not be empty.")
        try:
            from google.genai import types
        except ImportError as exc:
            raise GenerationError(
                "Google GenAI SDK is not installed. Install project dependencies."
            ) from exc

        client = self._get_client()
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=self.settings.generation_temperature,
            max_output_tokens=self.settings.generation_max_output_tokens,
        )
        started_at = time.monotonic()
        for attempt in range(self._max_retries + 1):
            try:
                response = client.models.generate_content(
                    model=self.settings.generation_model,
                    contents=prompt,
                    config=config,
                )
                text = getattr(response, "text", None)
                if not isinstance(text, str) or not text.strip():
                    raise GenerationError("Gemini returned an empty response.")
                return GenerationResult(
                    text=text.strip(),
                    model=self.settings.generation_model,
                    duration_seconds=time.monotonic() - started_at,
                )
            except GenerationError:
                raise
            except Exception as exc:
                status_code = self._status_code(exc)
                retryable = status_code in RETRYABLE_STATUS_CODES
                retryable = retryable or isinstance(
                    exc,
                    (TimeoutError, ConnectionError),
                )
                if retryable and attempt < self._max_retries:
                    delay = min(
                        self._base_delay_seconds * (2**attempt),
                        self._max_delay_seconds,
                    )
                    logger.warning(
                        "Gemini generation failed with status %s; retry %d of %d.",
                        status_code or type(exc).__name__,
                        attempt + 1,
                        self._max_retries,
                    )
                    self._sleep(delay)
                    continue
                if status_code == 429:
                    message = (
                        "Gemini rate limit reached after bounded retries. "
                        "Wait and try again."
                    )
                else:
                    message = "Gemini generation request failed."
                logger.warning(
                    "Gemini generation failed with status %s (%s).",
                    status_code or "unknown",
                    type(exc).__name__,
                )
                raise GenerationError(message) from exc

        raise GenerationError("Gemini generation request failed.")

    def close(self) -> None:
        """Close only a client created by this service."""
        if self._owns_client and self._client is not None:
            self._client.close()
            self._client = None
            self._owns_client = False
