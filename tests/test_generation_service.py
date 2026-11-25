"""Mocked Gemini generation service tests."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from config import Settings
from core.generation_service import (
    GenerationError,
    GenerationService,
    MissingGenerationAPIKeyError,
)


def _settings(path: Path, *, key: str | None = "test-key") -> Settings:
    return Settings(
        gemini_api_key=key,
        embedding_model="embedding-model",
        generation_model="gemini-test-model",
        chroma_persist_directory=path,
        chroma_collection_name="cybervault_documents",
        chunk_size=500,
        chunk_overlap=100,
        retrieval_top_k=5,
        embedding_dimension=2,
        generation_temperature=0.2,
        generation_max_output_tokens=512,
    )


class FakeModels:
    def __init__(self, outcomes):
        self.outcomes = iter(outcomes)
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        outcome = next(self.outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def test_successful_generation_uses_model_and_config(tmp_path: Path) -> None:
    models = FakeModels([SimpleNamespace(text="Grounded answer.")])
    service = GenerationService(
        _settings(tmp_path),
        client=SimpleNamespace(models=models),
    )

    result = service.generate(
        "What is the policy?",
        system_instruction="Use only the supplied context.",
    )

    assert result.text == "Grounded answer."
    assert result.model == "gemini-test-model"
    assert models.calls[0]["model"] == "gemini-test-model"
    assert models.calls[0]["config"].temperature == 0.2
    assert models.calls[0]["config"].max_output_tokens == 512
    assert models.calls[0]["config"].system_instruction == (
        "Use only the supplied context."
    )


def test_empty_response_is_rejected(tmp_path: Path) -> None:
    models = FakeModels([SimpleNamespace(text="  ")])
    service = GenerationService(
        _settings(tmp_path),
        client=SimpleNamespace(models=models),
    )

    with pytest.raises(GenerationError, match="empty response"):
        service.generate("Question")


def test_missing_api_key_is_rejected(tmp_path: Path) -> None:
    service = GenerationService(_settings(tmp_path, key=None), client=None)

    with pytest.raises(MissingGenerationAPIKeyError, match="GEMINI_API_KEY"):
        service.generate("Question")


def test_rate_limit_retries_are_bounded(tmp_path: Path) -> None:
    class APIError(Exception):
        code = 429

    delays = []
    models = FakeModels(
        [APIError("private"), APIError("private"), SimpleNamespace(text="Done")]
    )
    service = GenerationService(
        _settings(tmp_path),
        client=SimpleNamespace(models=models),
        max_retries=2,
        base_delay_seconds=0.25,
        max_delay_seconds=1.0,
        sleep=lambda delay: delays.append(delay),
    )

    result = service.generate("Question")

    assert result.text == "Done"
    assert len(models.calls) == 3
    assert delays == [0.25, 0.5]


def test_api_error_returns_safe_message(tmp_path: Path) -> None:
    class APIError(Exception):
        code = 503

    models = FakeModels([APIError("private technical detail")])
    service = GenerationService(
        _settings(tmp_path),
        client=SimpleNamespace(models=models),
        max_retries=0,
    )

    with pytest.raises(GenerationError, match="generation request failed"):
        service.generate("Question")
