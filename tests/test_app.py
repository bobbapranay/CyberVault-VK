"""Import-level checks for the Streamlit entry point."""

import importlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock


def test_application_imports_without_running_streamlit() -> None:
    app = importlib.import_module("app")

    assert callable(app.main)


def test_document_library_page_renders_without_ingestion_errors() -> None:
    from streamlit.testing.v1 import AppTest

    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run(timeout=30)
    app.radio[0].set_value("Document Library").run(timeout=30)

    assert not app.exception
    assert any("Document Library" in item.value for item in app.markdown)
    assert app.file_uploader


def test_retrieval_playground_page_imports_and_renders() -> None:
    from streamlit.testing.v1 import AppTest

    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run(timeout=30)
    app.radio[0].set_value("Retrieval Playground").run(timeout=30)

    assert not app.exception
    assert any("Retrieval Playground" in item.value for item in app.markdown)


def test_ai_chat_page_imports_and_renders() -> None:
    from streamlit.testing.v1 import AppTest

    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run(timeout=30)
    app.radio[0].set_value("AI Chat").run(timeout=30)

    assert not app.exception
    assert any("AI Chat" in item.value for item in app.markdown)
    assert app.radio


def test_dashboard_page_renders_actual_status_components() -> None:
    from streamlit.testing.v1 import AppTest

    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run(timeout=30)

    assert not app.exception
    assert any(
        "Welcome to CyberVault RAG" in item.value
        for item in app.markdown
    )
    assert app.button


def test_settings_page_renders_without_api_key_exposure() -> None:
    from streamlit.testing.v1 import AppTest

    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run(timeout=30)
    app.radio[0].set_value("Settings").run(timeout=30)

    assert not app.exception
    assert any("Settings" in item.value for item in app.markdown)
    rendered_text = " ".join(item.value for item in app.markdown)
    assert "your_gemini_api_key_here" not in rendered_text


def test_ai_chat_clear_conversation_clears_session_history() -> None:
    from streamlit.testing.v1 import AppTest

    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run(timeout=30)
    app.radio[0].set_value("AI Chat").run(timeout=30)
    app.session_state["cv_chat_history"] = [
        {
            "role": "assistant",
            "mode": "Plain LLM",
            "question": "Old question",
            "plain_answer": "Old answer",
            "model": "test-model",
        }
    ]
    app.run(timeout=30)
    assert any("Old question" in item.value for item in app.markdown)

    clear_button = next(
        button for button in app.button if button.label == "Clear conversation"
    )
    clear_button.click().run(timeout=30)

    assert not app.exception
    assert app.session_state["cv_chat_history"] == []


def test_ai_chat_modes_render_without_submitting() -> None:
    from streamlit.testing.v1 import AppTest

    app_path = Path(__file__).resolve().parents[1] / "app.py"
    for mode in ("RAG", "Plain LLM", "Compare"):
        app = AppTest.from_file(str(app_path)).run(timeout=30)
        navigation = next(
            radio for radio in app.radio if radio.label == "Navigation"
        )
        navigation.set_value("AI Chat").run(timeout=30)
        response_mode = next(
            radio for radio in app.radio if radio.label == "Response mode"
        )
        response_mode.set_value(mode).run(timeout=30)

        assert not app.exception
        response_mode = next(
            radio for radio in app.radio if radio.label == "Response mode"
        )
        assert response_mode.value == mode


def test_verified_sources_render_in_an_expander_without_markdown_pages() -> None:
    from app import _render_source_list

    st = MagicMock()
    response = SimpleNamespace(
        source_references=(
            SimpleNamespace(
                number=1,
                filename="NIST_CSF.pdf",
                page_number=9,
            ),
            SimpleNamespace(
                number=2,
                filename="owasp.md",
                page_number=None,
            ),
        )
    )

    _render_source_list(st, response)

    st.expander.assert_called_once_with("Sources", expanded=True)
    assert [call.args[0] for call in st.markdown.call_args_list] == [
        "[1] **NIST_CSF.pdf** — Page 9",
        "[2] **owasp.md** — Document-level source",
    ]


def test_retrieved_context_expander_shows_chunk_source_and_text() -> None:
    from app import _render_retrieved_context

    st = MagicMock()
    response = SimpleNamespace(
        retrieved_chunks=(
            SimpleNamespace(
                rank=1,
                filename="owasp.md",
                page_number=None,
                chunk_id="chunk-example",
                cosine_distance=0.123456,
                text="Retrieved evidence.",
            ),
        )
    )

    _render_retrieved_context(st, response)

    st.expander.assert_called_once_with("Retrieved context", expanded=False)
    st.markdown.assert_called_once_with(
        "**Rank 1 · owasp.md · Document-level source**"
    )
    st.caption.assert_called_once_with(
        "Chunk ID: chunk-example · Cosine distance: 0.123456"
    )
    st.text.assert_called_once_with("Retrieved evidence.")
