# Phase 8 final submission report

## Status

Submission preparation is complete for local review. No repository was
initialized, committed, or pushed. Git is not installed in the current
environment, so staged-file and repository-status checks remain manual.

## Screenshots and application

Six genuine screenshots were captured from the running Streamlit application
and saved under `docs/images/`. They share 970×673 dimensions:

- `dashboard.png` — actual 17-document, 141-chunk dashboard status.
- `document-library.png` — indexed source library.
- `retrieval-playground.png` — live NIST semantic retrieval results.
- `ai-chat-rag.png` — live grounded answer with source citations.
- `ai-chat-compare.png` — Plain LLM and RAG responses to the same question.
- `retrieved-context.png` — expanded retrieved context and source metadata.

The images were reviewed for visible credentials. The final local application
smoke test returned HTTP 200.

## Dataset and persistent index

The unchanged local corpus contains one 32-page NIST CSF 2.0 PDF and 16 OWASP
Top 10:2025 Markdown files. The collection has 17 indexed filenames and 141
persisted vectors; a read-only check after the final tests confirmed both
counts. The 141 document embeddings are 3072-dimensional and use
`gemini-embedding-001`. Generation uses `gemini-3.5-flash-lite`.

The vector database and source corpus are excluded from Git. The source
provenance and reuse guidance are in [dataset_sources.md](dataset_sources.md).
Review the NIST PDF's third-party notices before redistributing any of its
contents; follow OWASP CC BY-SA 4.0 terms if redistributing OWASP content.

## Live evaluation evidence

The detailed [Phase 8 validation report](phase8_validation_report.md) records
the actual Gemini requests and their sources. It includes five grounded
answers with citation-to-chunk checks, three out-of-scope questions that
received the insufficient-information response without citations, and a
three-question live Plain LLM versus RAG comparison. The observations include
cases where both modes answered correctly and cases where retrieved,
version-specific evidence changed the answer.

The separate [retrieval evaluation](retrieval_evaluation.md) records eight
live queries at K=5, exact relevant chunk IDs, and measured results:

| Metric | Result |
|---|---:|
| Hit Rate@5 | 1.000 |
| Mean Precision@5 | 0.350 |
| Mean Recall@5 | 1.000 |
| Mean Reciprocal Rank | 0.938 (exact mean 0.9375) |

These are results from a small manually annotated sample, not a general
quality guarantee. The full observed model outputs are in
[rag_vs_plain_llm.md](rag_vs_plain_llm.md).

## Final validation

- `python -m pytest -q`: **102 passed**.
- `python -m pytest -q tests/test_app.py`: **10 passed**.
- Python compilation with `python -m compileall -q app.py config.py core ingestion vectorstore evaluation ui tests`: passed.
- Running Streamlit app smoke test: **HTTP 200**.
- Post-test read-only ChromaDB check: **17 filenames, 141 vectors**.
- Configuration check: API key detected without displaying its value;
  configured embedding and generation models match the reported models.
- Text-file secret scan: **no Google API key pattern or literal non-placeholder
  `GEMINI_API_KEY` assignment found**. `.env` was not read.

Automated tests mock Gemini calls. The live API and RAG evidence above is
separately recorded and was not substituted with mocked output.

## Security and publication readiness

`.env.example` contains a placeholder only. `.gitignore` excludes `.env`,
related local environment files, private key material, Streamlit secrets,
`data/chroma/`, and `data/documents/`. Git being unavailable prevented a
tracked-file audit and `git check-ignore`; these must be verified after Git is
installed. No commit, remote, repository creation, or push was performed.

Recommended repository metadata and the exact Windows publication commands
are in [repository_submission.md](repository_submission.md). Review `git
status` and `git diff --cached --stat` after staging, confirm that no local
database, corpus file, or credential is staged, and obtain explicit approval
before committing or pushing.

## Remaining limitations

- The eight-query retrieval evaluation is small and manually annotated.
- The optional retrieval distance threshold is unset; nearest neighbors are
  not a semantic relevance guarantee.
- Citation validation checks mapping to retrieved context; it does not
  automatically prove entailment.
- The corpus is local-only until source licensing and publisher notices have
  been reviewed for publication.
- Git installation and repository staging/publication review remain manual.
