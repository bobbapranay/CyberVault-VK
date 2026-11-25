"""Tests for application configuration loading and validation."""

from pathlib import Path

import pytest

from config import ConfigurationError, Settings, load_settings, validate_config


def _clear_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "GEMINI_API_KEY",
        "GEMINI_EMBEDDING_MODEL",
        "GEMINI_GENERATION_MODEL",
        "CHROMA_PERSIST_DIRECTORY",
        "CHROMA_COLLECTION_NAME",
        "CHUNK_SIZE",
        "CHUNK_OVERLAP",
        "RETRIEVAL_TOP_K",
        "EMBEDDING_BATCH_SIZE",
        "EMBEDDING_DIMENSION",
        "RETRIEVAL_MAX_TOP_K",
        "RETRIEVAL_MIN_DISTANCE",
        "GENERATION_TEMPERATURE",
        "GENERATION_MAX_OUTPUT_TOKENS",
        "RAG_CONTEXT_LIMIT",
    ):
        monkeypatch.delenv(name, raising=False)


def test_configuration_defaults(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    _clear_settings(monkeypatch)
    monkeypatch.setattr("config.PROJECT_ROOT", tmp_path)
    monkeypatch.chdir(tmp_path)

    settings = load_settings()

    assert settings.embedding_model == "gemini-embedding-001"
    assert settings.generation_model == "gemini-3.5-flash-lite"
    assert settings.chroma_persist_directory.name == "chroma"
    assert settings.chroma_collection_name == "cybervault_documents"
    assert (settings.chunk_size, settings.chunk_overlap, settings.retrieval_top_k) == (
        500,
        100,
        5,
    )
    assert settings.embedding_batch_size == 32
    assert settings.embedding_dimension == 3072
    assert settings.retrieval_max_top_k == 20
    assert settings.retrieval_min_distance is None
    assert settings.generation_temperature == 0.2
    assert settings.generation_max_output_tokens == 1024
    assert settings.rag_context_limit == 12000


def test_environment_variables_are_loaded_from_dotenv(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    _clear_settings(monkeypatch)
    monkeypatch.setattr("config.PROJECT_ROOT", tmp_path)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "GEMINI_API_KEY=dotenv-test-key\n"
        "GEMINI_GENERATION_MODEL=custom-model\n"
        "EMBEDDING_BATCH_SIZE=7\n"
        "EMBEDDING_DIMENSION=1536\n",
        encoding="utf-8",
    )

    settings = load_settings()

    assert settings.gemini_api_key == "dotenv-test-key"
    assert settings.generation_model == "custom-model"
    assert settings.embedding_batch_size == 7
    assert settings.embedding_dimension == 1536


def test_environment_values_override_dotenv(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    _clear_settings(monkeypatch)
    monkeypatch.setattr("config.PROJECT_ROOT", tmp_path)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("GEMINI_API_KEY=dotenv-key\n", encoding="utf-8")
    monkeypatch.setenv("GEMINI_API_KEY", "environment-key")

    settings = load_settings()

    assert settings.gemini_api_key == "environment-key"


def test_missing_api_key_is_supported(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    _clear_settings(monkeypatch)
    monkeypatch.setattr("config.PROJECT_ROOT", tmp_path)
    monkeypatch.chdir(tmp_path)

    settings = load_settings()

    assert settings.gemini_api_key is None
    assert not settings.has_gemini_api_key


def test_configuration_validation_rejects_invalid_chunk_overlap() -> None:
    settings = Settings(
        gemini_api_key=None,
        embedding_model="embedding-model",
        generation_model="generation-model",
        chroma_persist_directory=Path("data/chroma"),
        chroma_collection_name="cybervault_documents",
        chunk_size=100,
        chunk_overlap=100,
        retrieval_top_k=5,
    )

    with pytest.raises(ConfigurationError, match="CHUNK_OVERLAP"):
        validate_config(settings)


def test_configuration_validation_rejects_non_integer_environment_value(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    _clear_settings(monkeypatch)
    monkeypatch.setattr("config.PROJECT_ROOT", tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RETRIEVAL_TOP_K", "many")

    with pytest.raises(ConfigurationError, match="RETRIEVAL_TOP_K must be an integer"):
        load_settings()


def test_configuration_validation_rejects_invalid_collection_name() -> None:
    settings = Settings(
        gemini_api_key=None,
        embedding_model="embedding-model",
        generation_model="generation-model",
        chroma_persist_directory=Path("data/chroma"),
        chroma_collection_name="bad collection",
        chunk_size=500,
        chunk_overlap=100,
        retrieval_top_k=5,
    )

    with pytest.raises(ConfigurationError, match="CHROMA_COLLECTION_NAME"):
        validate_config(settings)


def test_configuration_validation_rejects_oversized_embedding_batch() -> None:
    settings = Settings(
        gemini_api_key=None,
        embedding_model="embedding-model",
        generation_model="generation-model",
        chroma_persist_directory=Path("data/chroma"),
        chroma_collection_name="cybervault_documents",
        chunk_size=500,
        chunk_overlap=100,
        retrieval_top_k=5,
        embedding_batch_size=101,
    )

    with pytest.raises(ConfigurationError, match="EMBEDDING_BATCH_SIZE"):
        validate_config(settings)


def test_configuration_validation_rejects_nonpositive_embedding_dimension() -> None:
    settings = Settings(
        gemini_api_key=None,
        embedding_model="embedding-model",
        generation_model="generation-model",
        chroma_persist_directory=Path("data/chroma"),
        chroma_collection_name="cybervault_documents",
        chunk_size=500,
        chunk_overlap=100,
        retrieval_top_k=5,
        embedding_dimension=0,
    )

    with pytest.raises(ConfigurationError, match="EMBEDDING_DIMENSION"):
        validate_config(settings)


def test_retrieval_threshold_can_be_disabled(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    _clear_settings(monkeypatch)
    monkeypatch.setattr("config.PROJECT_ROOT", tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RETRIEVAL_MIN_DISTANCE", "off")

    settings = load_settings()

    assert settings.retrieval_min_distance is None


def test_retrieval_top_k_cannot_exceed_configured_maximum() -> None:
    settings = Settings(
        gemini_api_key=None,
        embedding_model="embedding-model",
        generation_model="generation-model",
        chroma_persist_directory=Path("data/chroma"),
        chroma_collection_name="cybervault_documents",
        chunk_size=500,
        chunk_overlap=100,
        retrieval_top_k=21,
        retrieval_max_top_k=20,
    )

    with pytest.raises(ConfigurationError, match="RETRIEVAL_MAX_TOP_K"):
        validate_config(settings)
