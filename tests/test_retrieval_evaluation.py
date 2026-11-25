"""Unit tests for source-based retrieval evaluation metrics."""

from core.retrieval_engine import RetrievedChunk
from evaluation.retrieval_evaluator import (
    RetrievalTestQuery,
    evaluate_retrieval,
    summarize_retrieval_evaluation,
)


def _chunk(
    filename: str,
    rank: int,
    *,
    document_id: str = "doc",
    distance: float = 0.1,
) -> RetrievedChunk:
    return RetrievedChunk(
        rank=rank,
        chunk_id=f"chunk-{rank}",
        document_id=document_id,
        filename=filename,
        file_type="txt",
        source=filename,
        chunk_index=rank - 1,
        page_number=None,
        token_count=10,
        cosine_distance=distance,
        text="fixture text",
    )


def test_hit_precision_recall_and_mrr() -> None:
    test_query = RetrievalTestQuery(
        query="What is password policy?",
        expected_filenames=("handbook.txt", "appendix.txt"),
    )
    retrieved = (
        _chunk("unrelated.txt", 1),
        _chunk("handbook.txt", 2),
        _chunk("appendix.txt", 3),
    )

    evaluation = evaluate_retrieval(test_query, retrieved, k=3)

    assert evaluation.hit is True
    assert evaluation.reciprocal_rank == 0.5
    assert evaluation.precision_at_k == 2.0 / 3.0
    assert evaluation.recall_at_k == 1.0


def test_missing_expected_source_reports_no_hit() -> None:
    test_query = RetrievalTestQuery(
        query="Unknown topic",
        expected_filenames=("missing.txt",),
    )
    evaluation = evaluate_retrieval(
        test_query,
        (_chunk("other.txt", 1),),
        k=1,
    )

    assert evaluation.hit is False
    assert evaluation.reciprocal_rank == 0.0
    assert evaluation.precision_at_k == 0.0
    assert evaluation.recall_at_k == 0.0


def test_expected_document_id_can_match() -> None:
    test_query = RetrievalTestQuery(
        query="Document ID lookup",
        expected_document_ids=("document-a",),
    )
    chunk = _chunk("handbook.txt", 1, document_id="document-a")

    evaluation = evaluate_retrieval(test_query, (chunk,), k=1)

    assert evaluation.hit is True
    assert evaluation.relevant_retrieved == ("document-a",)


def test_exact_chunk_labels_do_not_mark_other_chunks_from_same_document_relevant() -> None:
    test_query = RetrievalTestQuery(
        query="What is the exact policy?",
        expected_filenames=("handbook.txt",),
        expected_chunk_ids=("relevant-chunk",),
    )
    unrelated = RetrievedChunk(
        rank=1,
        chunk_id="unrelated-chunk",
        document_id="doc",
        filename="handbook.txt",
        file_type="txt",
        source="handbook.txt",
        chunk_index=0,
        page_number=None,
        token_count=10,
        cosine_distance=0.1,
        text="Related document, irrelevant section.",
    )
    relevant = RetrievedChunk(
        rank=2,
        chunk_id="relevant-chunk",
        document_id="doc",
        filename="handbook.txt",
        file_type="txt",
        source="handbook.txt",
        chunk_index=1,
        page_number=None,
        token_count=10,
        cosine_distance=0.2,
        text="The exact policy.",
    )

    evaluation = evaluate_retrieval(test_query, (unrelated, relevant), k=2)

    assert evaluation.hit is True
    assert evaluation.reciprocal_rank == 0.5
    assert evaluation.precision_at_k == 0.5
    assert evaluation.recall_at_k == 1.0
    assert evaluation.relevant_retrieved == ("relevant-chunk",)


def test_summary_calculates_mrr_and_average_metrics() -> None:
    first = evaluate_retrieval(
        RetrievalTestQuery("one", expected_filenames=("a.txt",)),
        (_chunk("a.txt", 1),),
        k=1,
    )
    second = evaluate_retrieval(
        RetrievalTestQuery("two", expected_filenames=("b.txt",)),
        (_chunk("other.txt", 1),),
        k=1,
    )

    summary = summarize_retrieval_evaluation((first, second))

    assert summary.hit_rate == 0.5
    assert summary.mean_precision_at_k == 0.5
    assert summary.mean_recall_at_k == 0.5
    assert summary.mean_reciprocal_rank == 0.5
