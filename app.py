"""Streamlit entry point for the CyberVault RAG application."""

from __future__ import annotations

import html
from typing import Any

from config import ConfigurationError, Settings, load_settings
from core.embedding_service import EmbeddingService
from core.generation_service import (
    GenerationError,
    GenerationService,
)
from core.retrieval_engine import RetrievalError, retrieve_documents
from core.rag_pipeline import (
    ComparisonResponse,
    RAGResponse,
    generate_comparison_response,
    generate_plain_llm_response,
    generate_rag_response,
)
from ingestion.document_loader import generate_document_id
from ingestion.inspection import inspect_chunks
from ingestion.indexing_pipeline import IndexingReport, index_processed_documents
from ingestion.models import DocumentInput, DocumentProcessingResult
from ingestion.processor import ingest_documents
from vectorstore.chroma_store import (
    ChromaStore,
    VectorStoreError,
    VectorStoreStatus,
)
from ui.components import (
    empty_state,
    metric_card,
    page_header,
    section_heading,
    status_card,
)


def _render_styles(st: Any) -> None:
    """Apply the unified CyberVault dark SaaS design system."""
    st.markdown(
        """
        <style>
        .stApp {
            background: radial-gradient(circle at 82% -12%, #18284d 0, #0b1220 44%, #080d19 100%);
            color: #e8edf8;
        }
        .block-container {
            max-width: 1180px;
            padding-top: 2.1rem;
            padding-bottom: 3rem;
        }
        [data-testid="stSidebar"] {
            background: #0a1020;
            border-right: 1px solid rgba(148, 163, 184, .14);
        }
        [data-testid="stSidebar"] * { color: #d7def0; }
        [data-testid="stSidebar"] [role="radiogroup"] label {
            border: 1px solid transparent;
            border-radius: 9px;
            padding: .58rem .7rem;
            margin: .12rem 0;
        }
        [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
            background: rgba(99, 102, 241, .16);
            border-color: rgba(129, 140, 248, .28);
        }
        .cv-brand { font-size: 1.12rem; font-weight: 780; letter-spacing: .01em; }
        .cv-tagline { color: #8997b4; font-size: .78rem; margin-top: .12rem; }
        .cv-eyebrow {
            color: #8b9bb9; font-size: .75rem; font-weight: 700;
            letter-spacing: .14em; text-transform: uppercase;
        }
        .cv-page-header { margin: 0 0 1.35rem; }
        .cv-page-header h1 {
            font-size: 2.15rem; letter-spacing: -.035em; margin: .28rem 0 .35rem;
        }
        .cv-page-header p { color: #aab6cd; max-width: 780px; margin: 0; }
        .cv-card {
            background: linear-gradient(145deg, rgba(22, 33, 57, .92), rgba(15, 23, 42, .94));
            border: 1px solid rgba(148, 163, 184, .16);
            border-radius: 14px; min-height: 118px; padding: 17px 18px;
            box-shadow: 0 10px 30px rgba(2, 6, 23, .10);
        }
        .cv-card-purple { border-top-color: rgba(167, 139, 250, .72); }
        .cv-card-blue { border-top-color: rgba(96, 165, 250, .72); }
        .cv-card-green { border-top-color: rgba(52, 211, 153, .72); }
        .cv-card-label { color: #aab6cd; font-size: .86rem; }
        .cv-card-value { color: #f3f6ff; font-size: 1.22rem; font-weight: 730; margin-top: 10px; }
        .cv-card-detail { color: #8492ad; font-size: .78rem; margin-top: 4px; }
        .cv-section {
            display: flex; align-items: baseline; gap: .7rem;
            font-size: 1.08rem; font-weight: 720; margin: 1.55rem 0 .75rem;
        }
        .cv-section small { color: #8492ad; font-size: .76rem; font-weight: 400; }
        .cv-status {
            background: rgba(15, 23, 42, .76); border: 1px solid rgba(148, 163, 184, .14);
            border-radius: 11px; padding: 14px 15px; min-height: 78px;
        }
        .cv-status-label { color: #aab6cd; font-size: .8rem; }
        .cv-status-value { color: #e8edf8; font-weight: 650; margin-top: 7px; }
        .cv-status-dot {
            display: inline-block; width: 7px; height: 7px; border-radius: 50%;
            background: #60a5fa; margin-right: 7px; vertical-align: 1px;
        }
        .cv-status-good .cv-status-dot { background: #34d399; }
        .cv-status-warning .cv-status-dot { background: #fbbf24; }
        .cv-status-error .cv-status-dot { background: #fb7185; }
        .cv-empty {
            background: linear-gradient(135deg, rgba(59, 130, 246, .10), rgba(124, 58, 237, .09));
            border: 1px solid rgba(129, 140, 248, .22); border-radius: 16px;
            padding: 24px; text-align: center; margin-top: 1rem;
        }
        .cv-empty h3 { margin: .35rem 0; }
        .cv-empty p { color: #aab6cd; margin: 0 auto; max-width: 620px; }
        div[data-testid="stRadio"] label { padding: .25rem 0; }
        [data-testid="stMetric"] {
            background: rgba(15, 23, 42, .68);
            border: 1px solid rgba(148, 163, 184, .12);
            border-radius: 12px;
            padding: 12px 14px;
        }
        [data-testid="stExpander"] {
            border: 1px solid rgba(148, 163, 184, .13);
            border-radius: 11px;
            background: rgba(15, 23, 42, .55);
        }
        div[data-testid="stTextInput"] input,
        div[data-testid="stTextArea"] textarea,
        div[data-testid="stNumberInput"] input {
            background: rgba(15, 23, 42, .72) !important;
            border-color: rgba(148, 163, 184, .22) !important;
        }
        .stButton > button {
            border-radius: 9px;
            border: 1px solid rgba(129, 140, 248, .24);
        }
        .cv-chat-user {
            margin-left: 12%; padding: 12px 14px; border-radius: 12px 12px 3px 12px;
            background: rgba(99, 102, 241, .16); border: 1px solid rgba(129, 140, 248, .22);
        }
        .cv-chat-assistant {
            margin-right: 12%; padding: 12px 14px; border-radius: 12px 12px 12px 3px;
            background: rgba(15, 23, 42, .72); border: 1px solid rgba(148, 163, 184, .14);
        }
        .cv-settings-value {
            color: #e8edf8; font-weight: 650; word-break: break-word;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _metric_card(st: Any, label: str, value: str, detail: str) -> None:
    """Render a dashboard metric without implying unimplemented functionality."""
    st.markdown(
        f"""
        <div class="cv-card">
            <div class="cv-card-label">{label}</div>
            <div class="cv-card-value">{value}</div>
            <div class="cv-card-detail">{detail}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _status_card(st: Any, label: str, value: str) -> None:
    """Render a concise system status card."""
    st.markdown(
        f"""
        <div class="cv-status">
            <div class="cv-status-label">{label}</div>
            <div class="cv-status-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _get_chroma_store(st: Any, settings: Settings) -> ChromaStore:
    """Reuse the session's persistent store client for the configured location."""
    cache_key = (
        str(settings.chroma_persist_directory),
        settings.chroma_collection_name,
    )
    if st.session_state.get("cv_chroma_store_key") != cache_key:
        store = ChromaStore(settings)
        st.session_state["cv_chroma_store"] = store
        st.session_state["cv_chroma_store_key"] = cache_key
    store = st.session_state.get("cv_chroma_store")
    if not isinstance(store, ChromaStore):
        raise VectorStoreError("Unable to initialize the ChromaDB collection.")
    return store


def _render_indexing_report(st: Any, report: IndexingReport) -> None:
    """Show actual per-run embedding and storage results."""
    columns = st.columns(5)
    columns[0].metric("Documents processed", report.documents_processed)
    columns[1].metric("Chunks generated", report.chunks_generated)
    columns[2].metric("Embeddings created", report.embeddings_created)
    columns[3].metric("Vectors stored", report.vectors_stored)
    columns[4].metric("Failures", report.failures)
    if report.failed_documents:
        st.warning(
            f"{report.failed_documents} document(s) failed or were only "
            "partially indexed. Successful batches were retained."
        )
    else:
        st.success(
            f"Indexing finished in {report.duration_seconds:.1f} seconds. "
            f"{report.duplicate_documents} already-indexed document(s) were skipped."
        )
    for result in report.document_results:
        label = f"{result.filename} · {result.status}"
        if result.error:
            st.warning(f"{label}: {result.error}")
        else:
            st.caption(
                f"{label} · {result.vectors_stored} vectors stored · "
                f"{result.embeddings_created} embeddings created"
            )


def _render_indexed_documents(st: Any, store: ChromaStore | None) -> None:
    """Render actual collection status and confirmed, document-scoped deletion."""
    st.subheader("Persistent vector database")
    if store is None:
        st.error("ChromaDB is unavailable. Check the configured storage path.")
        return

    try:
        status = store.get_status()
        documents = store.list_documents()
    except VectorStoreError as exc:
        st.error(f"Unable to read the ChromaDB collection: {exc}")
        return

    columns = st.columns(4)
    columns[0].metric("Connection", "Connected" if status.connected else "Offline")
    columns[1].metric("Collection", status.collection_name)
    columns[2].metric("Indexed documents", status.document_count)
    columns[3].metric("Stored vectors", status.vector_count)
    st.caption(f"Persistence directory: {status.persistence_directory}")

    st.subheader("Indexed documents")
    if not documents:
        st.info("No documents have been indexed in this ChromaDB collection.")
        return

    header = st.columns((3, 3, 1, 1, 1))
    for column, label in zip(
        header,
        ("Filename", "Document ID", "Type", "Chunks", "Status"),
    ):
        column.markdown(f"**{label}**")
    for document in documents:
        row = st.columns((3, 3, 1, 1, 1))
        row[0].write(document.filename)
        row[1].code(document.document_id)
        row[2].write(document.file_type.upper())
        row[3].write(
            f"{document.chunk_count}/{document.expected_chunk_count}"
        )
        row[4].write(document.status.capitalize())

    state = st.session_state
    selected = st.selectbox(
        "Select an indexed document to remove",
        documents,
        format_func=lambda item: f"{item.filename} · {item.document_id[:12]}",
        key="cv_delete_document_selection",
    )
    processed_documents = st.session_state.get("cv_processed_documents", {})
    processed = processed_documents.get(selected.document_id)
    with st.expander("Preview document metadata and processed chunks"):
        st.write(f"**Filename:** {selected.filename}")
        st.write(f"**Document ID:** `{selected.document_id}`")
        st.write(f"**File type:** {selected.file_type.upper()}")
        st.write(
            f"**Indexed chunks:** {selected.chunk_count} / "
            f"{selected.expected_chunk_count}"
        )
        if processed is None:
            st.caption(
                "The processed chunk set is not held in this session, "
                "but persisted vectors remain available."
            )
        else:
            for chunk in processed.chunks:
                page_label = (
                    f"Page {chunk.page_number}"
                    if chunk.page_number is not None
                    else "Document-level source"
                )
                st.markdown(
                    f"**Chunk {chunk.chunk_index + 1} · {page_label}**"
                )
                st.caption(
                    f"Chunk ID: {chunk.chunk_id} · "
                    f"Token count: {chunk.token_count}"
                )
                st.text(chunk.text)
    confirmation_id = state.get("cv_delete_confirmation")
    if confirmation_id != selected.document_id:
        if confirmation_id is not None:
            state.pop("cv_delete_confirmation", None)
        if st.button(
            "Delete selected document",
            key=f"cv_prepare_delete_{selected.document_id}",
        ):
            state["cv_delete_confirmation"] = selected.document_id
            st.rerun()
        return

    st.warning(
        f"Confirm permanent deletion of **{selected.filename}** and its "
        f"{selected.chunk_count} stored vector(s)."
    )
    confirm_column, cancel_column = st.columns(2)
    if confirm_column.button(
        "Confirm deletion",
        type="primary",
        key=f"cv_confirm_delete_{selected.document_id}",
    ):
        try:
            deleted_count = store.delete_document(selected.document_id)
        except VectorStoreError as exc:
            st.error(f"Document deletion failed: {exc}")
        else:
            state.pop("cv_delete_confirmation", None)
            st.success(f"Deleted {deleted_count} vector(s) for {selected.filename}.")
            st.rerun()
    if cancel_column.button(
        "Cancel",
        key=f"cv_cancel_delete_{selected.document_id}",
    ):
        state.pop("cv_delete_confirmation", None)
        st.rerun()


def _render_dashboard(
    st: Any, settings: Settings | None, config_error: str | None
) -> None:
    """Render the polished overview with only persisted and configured values."""
    store_status: VectorStoreStatus | None = None
    store_error: str | None = None
    if settings is not None:
        try:
            store_status = _get_chroma_store(st, settings).get_status()
        except VectorStoreError as exc:
            store_error = str(exc)

    page_header(
        st,
        eyebrow="SECURE KNOWLEDGE WORKSPACE",
        title="Welcome to CyberVault RAG",
        description=(
            "AI-powered document intelligence for grounded answers across "
            "your uploaded knowledge."
        ),
    )

    if config_error:
        st.error(f"Configuration issue: {config_error}")
    elif settings is not None and not settings.has_gemini_api_key:
        st.warning(
            "Gemini API key is not configured. Add GEMINI_API_KEY to your .env "
            "file to enable document indexing. The dashboard is available "
            "without it."
        )

    section_heading(st, "Workspace overview", "Live application state")
    columns = st.columns(5)
    if store_status is not None:
        indexed_documents = str(store_status.document_count)
        indexed_chunks = str(store_status.vector_count)
        database_value = "Connected"
        database_detail = store_status.collection_name
    else:
        indexed_documents = "Unavailable"
        indexed_chunks = "Unavailable"
        database_value = "Unavailable"
        database_detail = store_error or "Configuration is unavailable"
    metrics = (
        ("Indexed documents", indexed_documents, "Persistent collection", "green"),
        ("Indexed chunks", indexed_chunks, "Stored vectors", "blue"),
        ("Vector database", database_value, database_detail, "purple"),
        (
            "Embedding model",
            settings.embedding_model if settings is not None else "Unavailable",
            "Document and query vectors",
            "blue",
        ),
        (
            "Generation model",
            settings.generation_model if settings is not None else "Unavailable",
            "Configured for AI Chat",
            "purple",
        ),
    )
    for column, metric in zip(columns, metrics):
        with column:
            metric_card(
                st,
                label=metric[0],
                value=metric[1],
                detail=metric[2],
                tone=metric[3],
            )

    section_heading(st, "System status", "Configuration and connections")
    status_columns = st.columns(3)
    statuses = (
        (
            "Gemini API configuration",
            "Key configured · connectivity not tested"
            if settings is not None and settings.has_gemini_api_key
            else "Key missing",
        ),
        (
            "ChromaDB initialization",
            (
                f"Connected · {store_status.vector_count} vectors"
                if store_status is not None
                else f"Unavailable · {store_error or 'configuration unavailable'}"
            ),
        ),
        ("Application", "Running · ingestion, indexing, and retrieval enabled"),
    )
    for column, status in zip(status_columns, statuses):
        with column:
            tone = (
                "good"
                if status[0] == "Gemini API configuration"
                and "missing" not in status[1]
                else "good"
                if status[0] == "ChromaDB initialization"
                and "Connected" in status[1]
                else "warning"
            )
            status_card(st, label=status[0], value=status[1], tone=tone)

    section_heading(st, "Quick actions", "Continue your workflow")
    action_columns = st.columns(3)
    for column, (label, target) in zip(
        action_columns,
        (
            ("Upload documents", "Document Library"),
            ("Open retrieval", "Retrieval Playground"),
            ("Start AI Chat", "AI Chat"),
        ),
    ):
        with column:
            if st.button(label, use_container_width=True, key=f"cv_quick_{target}"):
                st.session_state["cv_navigation"] = target
                st.rerun()

    if store_status is not None and store_status.document_count == 0:
        empty_state(
            st,
            title="Your knowledge workspace is ready",
            description="Upload PDF, TXT, or Markdown documents, then index them to enable retrieval and RAG answers.",
        )


def _render_document_library(
    st: Any,
    settings: Settings | None,
    config_error: str | None,
) -> None:
    """Render uploads, chunk previews, indexing, and persistent management."""
    page_header(
        st,
        eyebrow="DOCUMENT WORKSPACE",
        title="Document Library",
        description=(
            "Upload, process, index, preview, and manage source documents "
            "with persistent vector storage."
        ),
    )

    if config_error or settings is None:
        st.error(config_error or "Application configuration is unavailable.")
        return

    state = st.session_state
    processed_documents = state.setdefault("cv_processed_documents", {})
    upload_results = state.setdefault("cv_upload_results", {})
    try:
        store = _get_chroma_store(st, settings)
        store_error = None
    except VectorStoreError as exc:
        store = None
        store_error = str(exc)
        st.warning(f"ChromaDB is unavailable: {store_error}")

    uploads = st.file_uploader(
        "Choose documents",
        type=["pdf", "txt", "md"],
        accept_multiple_files=True,
        help="PDF, UTF-8 text, and UTF-8 Markdown files are supported.",
        key="cv_document_uploads",
    )
    uploaded_payloads = (
        [(uploaded, uploaded.getvalue()) for uploaded in uploads] if uploads else []
    )
    upload_keys: list[str] = []
    duplicate_occurrences: dict[str, int] = {}
    for uploaded, content in uploaded_payloads:
        document_id = generate_document_id(uploaded.name, content)
        occurrence = duplicate_occurrences.get(document_id, 0)
        duplicate_occurrences[document_id] = occurrence + 1
        upload_keys.append(f"{document_id}:{occurrence}")

    if uploads and st.button("Process documents", type="primary"):
        inputs = [
            DocumentInput(filename=uploaded.name, content=content)
            for uploaded, content in uploaded_payloads
        ]
        progress = st.progress(0.0, text="Preparing documents...")

        def update_progress(completed: int, total: int, filename: str) -> None:
            progress.progress(
                completed / total,
                text=f"Processed {completed} of {total}: {filename}",
            )

        results = ingest_documents(
            inputs,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            already_processed_ids=processed_documents.keys(),
            progress_callback=update_progress,
        )
        for upload_key, result in zip(upload_keys, results):
            upload_results[upload_key] = result
            if result.status == "processed" and result.document_id is not None:
                processed_documents[result.document_id] = result
        progress.progress(1.0, text="Processing complete.")
        st.success(
            "Selected files processed. Chunks are ready in session memory; "
            "index them separately to persist vectors."
        )

    if uploads:
        st.subheader("Selected files")
        for (uploaded, _content), upload_key in zip(uploaded_payloads, upload_keys):
            result: DocumentProcessingResult | None = upload_results.get(upload_key)
            columns = st.columns((3, 1, 1, 1, 2))
            columns[0].markdown(f"**{uploaded.name}**")
            columns[1].write(uploaded.name.rsplit(".", 1)[-1].upper())
            if result is None:
                columns[2].write("—")
                columns[3].write("—")
                columns[4].write("Ready to process")
                continue

            existing = (
                processed_documents.get(result.document_id)
                if result.document_id is not None
                else None
            )
            summary = existing if result.status == "duplicate" and existing else result
            pages = (
                str(summary.pages_extracted)
                if summary.file_type == "pdf"
                else "N/A"
            )
            columns[2].write(pages)
            columns[3].write(str(len(summary.chunks)))
            columns[4].write(result.status.capitalize())
            if result.error:
                st.error(f"{uploaded.name}: {result.error}")
            elif result.status == "duplicate":
                st.info(
                    f"{uploaded.name} was already processed in this session; "
                    "the existing chunks were kept."
                )

    chunks = tuple(
        chunk
        for result in processed_documents.values()
        for chunk in result.chunks
    )
    total_pages = sum(
        result.pages_extracted for result in processed_documents.values()
    )
    inspection = inspect_chunks(
        chunks,
        total_documents_processed=len(processed_documents),
        total_pages_extracted=total_pages,
    )
    st.subheader("Session summary")
    summary_columns = st.columns(6)
    summary_columns[0].metric(
        "Documents processed", inspection.total_documents_processed
    )
    summary_columns[1].metric("Pages extracted", inspection.total_pages_extracted)
    summary_columns[2].metric("Chunks generated", inspection.total_chunks_generated)
    summary_columns[3].metric(
        "Average chunk length",
        f"{inspection.average_chunk_length:.1f} tokens",
    )
    summary_columns[4].metric(
        "Minimum chunk length",
        f"{inspection.minimum_chunk_length} tokens",
    )
    summary_columns[5].metric(
        "Maximum chunk length",
        f"{inspection.maximum_chunk_length} tokens",
    )
    st.caption(
        "Chunk lengths use the configured approximate tokenizer. Chunks stay "
        "in session memory until they are explicitly indexed."
    )

    successful_documents = tuple(
        result
        for result in processed_documents.values()
        if result.status == "processed"
    )
    if successful_documents:
        st.subheader("Index documents")
        if not settings.has_gemini_api_key:
            st.warning(
                "Add GEMINI_API_KEY to the project .env file before indexing. "
                "The key is never displayed in the interface."
            )
        if store_error:
            st.warning("Indexing is unavailable until ChromaDB is initialized.")
        if st.button(
            "Index processed documents",
            type="primary",
            disabled=not settings.has_gemini_api_key or store is None,
            key="cv_index_documents",
        ):
            index_progress = st.progress(0.0, text="Preparing embedding batches...")

            embedding_service = EmbeddingService(settings)

            def update_index_progress(completed: int, total: int) -> None:
                index_progress.progress(
                    completed / total,
                    text=f"Embedded batch {completed} of {total}",
                )

            try:
                report = index_processed_documents(
                    successful_documents,
                    embedding_service=embedding_service,
                    vector_store=store,
                    progress_callback=update_index_progress,
                )
            finally:
                embedding_service.close()
            index_progress.progress(1.0, text="Indexing attempt complete.")
            _render_indexing_report(st, report)
    elif not processed_documents:
        st.info("Process documents above to prepare chunks for indexing.")

    _render_indexed_documents(st, store)

    st.subheader("Generated chunk previews")
    for result in processed_documents.values():
        st.markdown(f"**{result.filename}** · {result.file_type.upper()}")
        for chunk in result.chunks:
            page_label = (
                f"Page {chunk.page_number}"
                if chunk.page_number is not None
                else "Document-level"
            )
            with st.expander(
                f"Chunk {chunk.chunk_index + 1} · {page_label} · "
                f"{chunk.token_count} tokens"
            ):
                st.caption(
                    f"Source: {chunk.filename} · {page_label} · "
                    f"Chunk index: {chunk.chunk_index} · "
                    f"Token count: {chunk.token_count}"
                )
                st.text(chunk.text)


def _render_retrieval_playground(
    st: Any,
    settings: Settings | None,
    config_error: str | None,
) -> None:
    """Render read-only semantic search over the persistent collection."""
    page_header(
        st,
        eyebrow="SEMANTIC SEARCH",
        title="Retrieval Playground",
        description=(
            "Find relevant source chunks with Gemini query embeddings. "
            "This view does not generate answers."
        ),
    )
    if config_error or settings is None:
        st.error(config_error or "Application configuration is unavailable.")
        return
    if not settings.has_gemini_api_key:
        st.warning(
            "GEMINI_API_KEY is not configured. Configure it before running "
            "semantic search."
        )

    try:
        store = _get_chroma_store(st, settings)
        status = store.get_status()
    except VectorStoreError as exc:
        st.error(f"Unable to initialize retrieval: {exc}")
        return

    if status.vector_count == 0:
        st.info(
            "No documents are indexed yet. Process and index documents in "
            "Document Library before searching."
        )
        return

    top_k = st.number_input(
        "Number of results",
        min_value=1,
        max_value=settings.retrieval_max_top_k,
        value=min(settings.retrieval_top_k, settings.retrieval_max_top_k),
        step=1,
        help="ChromaDB returns fewer results if the collection has fewer vectors.",
    )
    use_threshold = st.checkbox(
        "Apply maximum cosine distance",
        value=settings.retrieval_min_distance is not None,
        help=(
            "Lower cosine distance means a closer match. "
            "A threshold filters results with distance greater than the limit."
        ),
    )
    if use_threshold:
        threshold = st.number_input(
            "Maximum cosine distance",
            min_value=0.0,
            max_value=2.0,
            value=float(settings.retrieval_min_distance or 0.5),
            step=0.05,
            format="%.2f",
        )
    else:
        threshold = None

    query = st.text_area(
        "Natural-language question",
        placeholder="What does the document say about...",
    )
    if st.button(
        "Search",
        type="primary",
        disabled=not settings.has_gemini_api_key,
    ):
        if not query.strip():
            st.warning("Enter a non-empty natural-language question.")
            return
        embedding_service = EmbeddingService(settings)
        try:
            with st.spinner("Searching indexed documents..."):
                result = retrieve_documents(
                    query,
                    top_k=int(top_k),
                    maximum_top_k=settings.retrieval_max_top_k,
                    maximum_distance=threshold,
                    embedding_service=embedding_service,
                    vector_store=store,
                )
        except RetrievalError as exc:
            st.error(f"Retrieval failed: {exc}")
            return
        finally:
            embedding_service.close()

        st.subheader("Search results")
        result_columns = st.columns(3)
        result_columns[0].metric("Results returned", result.returned_count)
        result_columns[1].metric("Results requested", result.requested_top_k)
        result_columns[2].metric(
            "Execution time",
            f"{result.duration_seconds:.3f} s",
        )
        st.caption(f"Query: {result.query}")
        if threshold is not None:
            st.caption(
                "Cosine-distance threshold: "
                f"{threshold:.2f}; lower distances indicate closer matches."
            )
        if not result.chunks:
            st.info(
                "No matching chunks passed the configured distance limit "
                "or the collection contained no usable results."
            )
            return

        for chunk in result.chunks:
            page_label = (
                "Document-level source"
                if chunk.page_number is None
                or chunk.page_number == -1
                else f"Page {chunk.page_number}"
            )
            with st.expander(
                f"Rank {chunk.rank} · {chunk.filename} · "
                f"{page_label} · distance {chunk.cosine_distance:.6f}"
            ):
                st.write(f"**Source filename:** {chunk.filename}")
                st.write(f"**Page:** {page_label}")
                st.write(f"**Document ID:** `{chunk.document_id}`")
                st.write(f"**Chunk ID:** `{chunk.chunk_id}`")
                st.write(f"**Chunk index:** {chunk.chunk_index}")
                st.write(f"**Cosine distance:** {chunk.cosine_distance:.6f}")
                st.caption(
                    "Cosine distance is returned directly by ChromaDB. "
                    "Lower values indicate closer matches; this is not a "
                    "percentage or confidence score."
                )
                st.text(chunk.text)


def _render_source_list(st: Any, response: RAGResponse) -> None:
    """Display only source references validated from the generated answer."""
    if not response.source_references:
        st.caption("No verified citations were returned.")
        return
    with st.expander("Sources", expanded=True):
        for reference in response.source_references:
            page_label = (
                "Document-level source"
                if reference.page_number is None or reference.page_number == -1
                else f"Page {reference.page_number}"
            )
            st.markdown(
                f"[{reference.number}] **{reference.filename}** — {page_label}"
            )


def _render_retrieved_context(st: Any, response: RAGResponse) -> None:
    """Show the actual retrieved chunks used by the RAG answer."""
    if not response.retrieved_chunks:
        st.info("No retrieved chunks were available.")
        return
    with st.expander("Retrieved context", expanded=False):
        for chunk in response.retrieved_chunks:
            page_label = (
                "Document-level source"
                if chunk.page_number is None or chunk.page_number == -1
                else f"Page {chunk.page_number}"
            )
            st.markdown(
                f"**Rank {chunk.rank} · {chunk.filename} · {page_label}**"
            )
            st.caption(
                f"Chunk ID: {chunk.chunk_id} · "
                f"Cosine distance: {chunk.cosine_distance:.6f}"
            )
            st.text(chunk.text)


def _render_ai_chat(
    st: Any,
    settings: Settings | None,
    config_error: str | None,
) -> None:
    """Render chat history and Plain LLM/RAG/Compare generation modes."""
    page_header(
        st,
        eyebrow="GROUNDED CONVERSATION",
        title="AI Chat",
        description=(
            "Compare direct model responses with document-grounded RAG answers "
            "and inspect the supporting context."
        ),
    )
    if config_error or settings is None:
        st.error(config_error or "Application configuration is unavailable.")
        return
    if not settings.has_gemini_api_key:
        st.warning(
            "GEMINI_API_KEY is not configured. Configure it before generating "
            "answers."
        )

    try:
        store = _get_chroma_store(st, settings)
        status = store.get_status()
    except VectorStoreError as exc:
        st.error(f"Unable to initialize AI Chat: {exc}")
        return

    history = st.session_state.setdefault("cv_chat_history", [])
    if not history:
        empty_state(
            st,
            title="Start a grounded conversation",
            description=(
                "Choose RAG, Plain LLM, or Compare mode. RAG and Compare use "
                "the indexed document collection."
            ),
            label="AI CHAT",
        )
    mode = st.radio(
        "Response mode",
        ("RAG", "Plain LLM", "Compare"),
        horizontal=True,
    )
    top_k = st.number_input(
        "Retrieved chunks",
        min_value=1,
        max_value=settings.retrieval_max_top_k,
        value=min(settings.retrieval_top_k, settings.retrieval_max_top_k),
        step=1,
    )
    suggested = st.columns(3)
    for column, suggestion in zip(
        suggested,
        (
            "Summarize the main document topics.",
            "What risks or requirements are documented?",
            "What source supports this answer?",
        ),
    ):
        with column:
            if st.button(suggestion, use_container_width=True, key=f"cv_suggest_{suggestion[:8]}"):
                st.session_state["cv_chat_question"] = suggestion
    question_key = "cv_chat_question"
    question = st.text_area(
        "Question",
        placeholder="Ask a question about your uploaded documents...",
        key=question_key,
    )
    action_columns = st.columns((1, 3))
    submit = action_columns[0].button(
        "Send",
        type="primary",
        disabled=not settings.has_gemini_api_key,
    )
    clear = action_columns[1].button("Clear conversation")
    if clear:
        history.clear()
        st.rerun()

    if submit:
        if not question.strip():
            st.warning("Enter a non-empty question.")
            return
        if mode != "Plain LLM" and status.vector_count == 0:
            st.info(
                "No documents are indexed yet. Process and index documents "
                "in Document Library before using RAG or Compare mode."
            )
            return

        embedding_service = (
            EmbeddingService(settings)
            if mode != "Plain LLM"
            else None
        )
        generation_service = GenerationService(settings)
        try:
            if mode == "Plain LLM":
                with st.spinner("Generating Plain LLM response..."):
                    plain = generate_plain_llm_response(
                        question,
                        generation_service=generation_service,
                    )
                history.append(
                    {
                        "role": "assistant",
                        "mode": mode,
                        "question": question.strip(),
                        "plain_answer": plain.answer,
                        "model": plain.generation_model,
                    }
                )
                st.subheader("Plain LLM answer")
                st.write(plain.answer)
                st.caption(
                    f"Model: {plain.generation_model} · "
                    f"Generation time: "
                    f"{plain.generation_duration_seconds:.3f} s"
                )
            elif mode == "RAG":
                with st.spinner("Retrieving context and generating answer..."):
                    rag = generate_rag_response(
                        question,
                        top_k=int(top_k),
                        settings=settings,
                        embedding_service=embedding_service,
                        vector_store=store,
                        generation_service=generation_service,
                    )
                history.append(
                    {
                        "role": "assistant",
                        "mode": mode,
                        "question": question.strip(),
                        "rag_response": rag,
                    }
                )
                st.subheader("Grounded answer")
                if rag.missing_context:
                    st.info(rag.answer)
                else:
                    st.write(rag.answer)
                st.caption(
                    f"Model: {rag.generation_model} · "
                    f"Retrieved chunks: {len(rag.retrieved_chunks)} · "
                    f"Retrieval: {rag.retrieval_duration_seconds:.3f} s"
                )
                _render_source_list(st, rag)
                _render_retrieved_context(st, rag)
            else:
                with st.spinner("Running both response modes..."):
                    comparison = generate_comparison_response(
                        question,
                        top_k=int(top_k),
                        settings=settings,
                        embedding_service=embedding_service,
                        vector_store=store,
                        generation_service=generation_service,
                    )
                history.append(
                    {
                        "role": "assistant",
                        "mode": mode,
                        "question": question.strip(),
                        "comparison_response": comparison,
                    }
                )
                plain_column, rag_column = st.columns(2)
                with plain_column:
                    st.subheader("Plain LLM")
                    st.write(comparison.plain.answer)
                    st.caption(
                        f"Model: {comparison.plain.generation_model} · "
                        "No document retrieval"
                    )
                with rag_column:
                    st.subheader("RAG")
                    if comparison.rag.missing_context:
                        st.info(comparison.rag.answer)
                    else:
                        st.write(comparison.rag.answer)
                    st.caption(
                        f"Model: {comparison.rag.generation_model} · "
                        f"Retrieved chunks: "
                        f"{len(comparison.rag.retrieved_chunks)}"
                    )
                    _render_source_list(st, comparison.rag)
                    _render_retrieved_context(st, comparison.rag)
        except (RetrievalError, GenerationError) as exc:
            st.error(f"AI Chat failed: {exc}")
        finally:
            generation_service.close()
            if embedding_service is not None:
                embedding_service.close()

    if history:
        st.subheader("Conversation")
        for message in history:
            st.markdown(
                '<div class="cv-chat-user">'
                f"<strong>You</strong><br>{html.escape(message['question'])}"
                "</div>",
                unsafe_allow_html=True,
            )
            if message["mode"] == "Plain LLM":
                st.markdown(
                    '<div class="cv-chat-assistant">'
                    "<strong>Plain LLM</strong><br>"
                    f"{html.escape(message['plain_answer']).replace(chr(10), '<br>')}"
                    "</div>",
                    unsafe_allow_html=True,
                )
            elif message["mode"] == "RAG":
                rag = message["rag_response"]
                st.markdown(
                    '<div class="cv-chat-assistant">'
                    "<strong>RAG</strong><br>"
                    f"{html.escape(rag.answer).replace(chr(10), '<br>')}"
                    "</div>",
                    unsafe_allow_html=True,
                )
            else:
                comparison = message["comparison_response"]
                plain_column, rag_column = st.columns(2)
                with plain_column:
                    st.markdown("**Plain LLM:**")
                    st.write(comparison.plain.answer)
                with rag_column:
                    st.markdown("**RAG:**")
                    st.write(comparison.rag.answer)
            st.divider()


def _render_settings(
    st: Any,
    settings: Settings | None,
    config_error: str | None,
) -> None:
    """Render a polished read-only settings and configuration status page."""
    page_header(
        st,
        eyebrow="APPLICATION CONFIGURATION",
        title="Settings",
        description=(
            "Review active models, storage, chunking, retrieval, and generation "
            "configuration. API credentials are never displayed."
        ),
    )
    if config_error:
        st.error(f"Configuration issue: {config_error}")
        return
    if settings is None:
        st.error("Configuration is unavailable.")
        return

    section_heading(st, "Gemini configuration")
    gemini_label = "Connected key configured" if settings.has_gemini_api_key else "API key missing"
    gemini_tone = "good" if settings.has_gemini_api_key else "warning"
    status_columns = st.columns(3)
    status_card(
        status_columns[0],
        label="Gemini API",
        value=gemini_label,
        tone=gemini_tone,
    )
    status_card(
        status_columns[1],
        label="Embedding model",
        value=settings.embedding_model,
        tone="good",
    )
    status_card(
        status_columns[2],
        label="Generation model",
        value=settings.generation_model,
        tone="good",
    )

    section_heading(st, "Retrieval and storage")
    setting_rows = (
        ("Chunk size", str(settings.chunk_size), "Approximate tokens"),
        ("Chunk overlap", str(settings.chunk_overlap), "Approximate tokens"),
        ("Retrieval top-k", str(settings.retrieval_top_k), "Default result count"),
        ("Collection name", settings.chroma_collection_name, "ChromaDB collection"),
        (
            "Persistence directory",
            str(settings.chroma_persist_directory),
            "Local persistent storage",
        ),
        ("Generation temperature", str(settings.generation_temperature), "0.0–2.0"),
        (
            "Maximum output tokens",
            str(settings.generation_max_output_tokens),
            "Configured generation limit",
        ),
    )
    for start in range(0, len(setting_rows), 3):
        columns = st.columns(3)
        for column, (label, value, detail) in zip(
            columns,
            setting_rows[start : start + 3],
        ):
            metric_card(
                column,
                label=label,
                value=value,
                detail=detail,
                tone="blue",
            )

    if not settings.has_gemini_api_key:
        st.info(
            "Add GEMINI_API_KEY to the project .env file to enable indexing "
            "and generation. The value is not displayed."
        )
    st.caption(
        "Settings are loaded from environment variables and .env. "
        "Edit the configuration file outside the UI; credentials are not editable here."
    )


def main() -> None:
    """Run the Streamlit application."""
    try:
        import streamlit as st
    except ImportError as exc:
        raise RuntimeError(
            "Streamlit is not installed. Install the project dependencies "
            "with `pip install -r requirements.txt`."
        ) from exc

    st.set_page_config(
        page_title="CyberVault RAG",
        page_icon="🛡️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _render_styles(st)

    try:
        settings = load_settings()
        config_error = None
    except ConfigurationError as exc:
        settings = None
        config_error = str(exc)

    with st.sidebar:
        st.markdown('<div class="cv-brand">◈ CyberVault RAG</div>', unsafe_allow_html=True)
        st.markdown('<div class="cv-tagline">AI-Powered Document Intelligence</div>', unsafe_allow_html=True)
        st.markdown("---")
        page = st.radio(
            "Navigation",
            (
                "Dashboard",
                "Document Library",
                "Retrieval Playground",
                "AI Chat",
                "Settings",
            ),
            label_visibility="collapsed",
            key="cv_navigation",
        )
        st.markdown("---")
        st.caption("Phase 6 · Complete application")

    if page == "Dashboard":
        _render_dashboard(st, settings, config_error)
    elif page == "Document Library":
        _render_document_library(st, settings, config_error)
    elif page == "Retrieval Playground":
        _render_retrieval_playground(st, settings, config_error)
    elif page == "AI Chat":
        _render_ai_chat(st, settings, config_error)
    else:
        _render_settings(st, settings, config_error)


if __name__ == "__main__":
    main()
