"""Clearly labelled local retrieval test fixtures."""

from __future__ import annotations

from evaluation.retrieval_evaluator import RetrievalTestQuery


# These are local fixture expectations, not claims about real indexed documents.
LOCAL_RETRIEVAL_TEST_QUERIES = (
    RetrievalTestQuery(
        query="What is the purpose of the local security handbook?",
        expected_filenames=("security-handbook.txt",),
    ),
    RetrievalTestQuery(
        query="How should passwords be managed?",
        expected_filenames=("security-handbook.txt",),
    ),
)
