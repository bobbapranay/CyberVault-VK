"""Presentation-only Streamlit components."""

from typing import Any


def page_header(
    st: Any,
    *,
    eyebrow: str,
    title: str,
    description: str,
) -> None:
    """Render a consistent compact page heading."""
    st.markdown(
        f"""
        <div class="cv-page-header">
            <div class="cv-eyebrow">{eyebrow}</div>
            <h1>{title}</h1>
            <p>{description}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_heading(st: Any, title: str, caption: str | None = None) -> None:
    """Render a section heading with an optional caption."""
    st.markdown(
        f"""
        <div class="cv-section">
            <span>{title}</span>
            {f'<small>{caption}</small>' if caption else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_card(
    st: Any,
    *,
    label: str,
    value: str,
    detail: str,
    tone: str = "blue",
) -> None:
    """Render an actual-status metric card."""
    st.markdown(
        f"""
        <div class="cv-card cv-card-{tone}">
            <div class="cv-card-label">{label}</div>
            <div class="cv-card-value">{value}</div>
            <div class="cv-card-detail">{detail}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_card(
    st: Any,
    *,
    label: str,
    value: str,
    tone: str = "neutral",
) -> None:
    """Render a status card with an accessible textual tone."""
    st.markdown(
        f"""
        <div class="cv-status cv-status-{tone}">
            <div class="cv-status-label">{label}</div>
            <div class="cv-status-value"><span class="cv-status-dot"></span>{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def empty_state(
    st: Any,
    *,
    title: str,
    description: str,
    label: str = "CYBERVAULT WORKSPACE",
) -> None:
    """Render a calm, informative empty state."""
    st.markdown(
        f"""
        <div class="cv-empty">
            <div class="cv-eyebrow">{label}</div>
            <h3>{title}</h3>
            <p>{description}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
