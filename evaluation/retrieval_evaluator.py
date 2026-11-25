"""Retrieval evaluation metrics and predefined local test cases."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Sequence

from core.retrieval_engine import RetrievedChunk, RetrievalResult


@dataclass(frozen=True)
class RetrievalTestQuery:
    """A retrieval check with exact relevant chunks or legacy source labels."""

    query: str
    expected_filenames: tuple[str, ...] = ()
    expected_document_ids: tuple[str, ...] = ()
    expected_chunk_ids: tuple[str, ...] = ()
    expected_section: str = ""
    expected_information: str = ""


@dataclass(frozen=True)
class RetrievalEvaluation:
    """Metric values for one test query."""

    query: str
    hit: bool
    reciprocal_rank: float
    precision_at_k: float
    recall_at_k: float
    relevant_retrieved: tuple[str, ...]


@dataclass(frozen=True)
class RetrievalEvaluationSummary:
    """Aggregate metrics for a group of retrieval test queries."""

    hit_rate: float
    mean_precision_at_k: float
    mean_recall_at_k: float
    mean_reciprocal_rank: float
    evaluations: tuple[RetrievalEvaluation, ...]


def evaluate_retrieval(
    test_query: RetrievalTestQuery,
    retrieved: RetrievedChunk | Sequence[RetrievedChunk] | RetrievalResult,
    *,
    k: int,
) -> RetrievalEvaluation:
    """Compare results to annotated chunks, falling back to source identities.

    When exact relevant chunk IDs are supplied, they take precedence over
    filename/document labels so unrelated chunks from the same document are
    not automatically counted as relevant.
    """
    if k <= 0:
        raise ValueError("Evaluation k must be greater than zero.")
    if isinstance(retrieved, RetrievedChunk):
        chunks = (retrieved,)
    elif isinstance(retrieved, RetrievalResult):
        chunks = retrieved.chunks
    else:
        chunks = tuple(retrieved)
    top_chunks = chunks[:k]

    expected_filenames = {
        filename.casefold() for filename in test_query.expected_filenames
    }
    expected_document_ids = set(test_query.expected_document_ids)
    expected_chunk_ids = set(test_query.expected_chunk_ids)
    relevant_labels: set[str] = set()
    for chunk in top_chunks:
        if expected_chunk_ids:
            if chunk.chunk_id in expected_chunk_ids:
                relevant_labels.add(chunk.chunk_id)
        elif chunk.filename.casefold() in expected_filenames:
            relevant_labels.add(chunk.filename.casefold())
        elif chunk.document_id in expected_document_ids:
            relevant_labels.add(chunk.document_id)

    all_expected = (
        expected_chunk_ids
        if expected_chunk_ids
        else {*expected_filenames, *expected_document_ids}
    )
    retrieved_relevant = tuple(sorted(relevant_labels))
    reciprocal_rank = 0.0
    for rank, chunk in enumerate(top_chunks, start=1):
        is_relevant = (
            chunk.chunk_id in expected_chunk_ids
            if expected_chunk_ids
            else (
                chunk.filename.casefold() in expected_filenames
                or chunk.document_id in expected_document_ids
            )
        )
        if is_relevant:
            reciprocal_rank = 1.0 / rank
            break
    hit = bool(reciprocal_rank)
    precision = (
        len(relevant_labels) / k
        if all_expected
        else 0.0
    )
    recall = (
        len(relevant_labels) / len(all_expected)
        if all_expected
        else 0.0
    )
    return RetrievalEvaluation(
        query=test_query.query,
        hit=hit,
        reciprocal_rank=reciprocal_rank,
        precision_at_k=min(1.0, precision),
        recall_at_k=min(1.0, recall),
        relevant_retrieved=retrieved_relevant,
    )


def summarize_retrieval_evaluation(
    evaluations: Iterable[RetrievalEvaluation],
) -> RetrievalEvaluationSummary:
    """Calculate hit rate, mean precision, mean recall, and MRR."""
    items = tuple(evaluations)
    if not items:
        return RetrievalEvaluationSummary(0.0, 0.0, 0.0, 0.0, ())
    count = len(items)
    return RetrievalEvaluationSummary(
        hit_rate=sum(item.hit for item in items) / count,
        mean_precision_at_k=(
            sum(item.precision_at_k for item in items) / count
        ),
        mean_recall_at_k=sum(item.recall_at_k for item in items) / count,
        mean_reciprocal_rank=(
            sum(item.reciprocal_rank for item in items) / count
        ),
        evaluations=items,
    )


def evaluate_test_queries(
    test_queries: Iterable[RetrievalTestQuery],
    retrieve: Callable[[str, int], RetrievalResult],
    *,
    k: int,
) -> RetrievalEvaluationSummary:
    """Execute predefined test questions against a real retrieval callable."""
    evaluations = [
        evaluate_retrieval(
            test_query,
            retrieve(test_query.query, k),
            k=k,
        )
        for test_query in test_queries
    ]
    return summarize_retrieval_evaluation(evaluations)
