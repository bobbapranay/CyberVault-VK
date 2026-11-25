# Evaluation report index

The earlier Phase 7 evaluation status is superseded by the completed live
Phase 8 validation. Its zero-vector and “live API not executed” statements no
longer describe the current project state.

- [Live retrieval evaluation](retrieval_evaluation.md) records eight real
  queries, exact relevant chunk IDs, top-five rankings, cosine distances, and
  measured metrics.
- [RAG versus Plain LLM](rag_vs_plain_llm.md) records three identical live
  questions, both model outputs, retrieved sources, and the comparison.
- [Phase 8 validation report](phase8_validation_report.md) summarizes dataset
  indexing, live RAG answers, citation checks, out-of-scope abstention, UI
  verification, regression checks, and limitations.
- [Phase 8 final report](phase8_final_report.md) records the final submission
  preparation, screenshots, security review, current persistence check, and
  final automated validation.

The local fixture queries in `evaluation/test_queries.py` remain test
fixtures; they are not the live-corpus evaluation described in these reports.
