# Final submission checklist

## Completed

- [x] **Screenshots:** Captured six genuine views from the running application
  in `docs/images/`, consistently sized at 970×673 and reviewed for visible
  credentials.
- [x] **README:** Updated with verified statistics, measured evaluation
  results, source and licensing guidance, six screenshot links, Windows setup,
  test distinctions, and requested repository metadata.
- [x] **Documentation:** Aligned the dataset, evaluation, comparison,
  validation, and repository submission records. Added
  [phase8_final_report.md](phase8_final_report.md).
- [x] **Security review:** `.env` remains ignored; `.env.example` is a
  placeholder. A non-environment text-file scan found no Google API key
  pattern or literal non-placeholder `GEMINI_API_KEY` assignment. The `.env`
  file was not read.
- [x] **Local data handling:** `.gitignore` excludes `data/chroma/` and
  `data/documents/`; the persistent database and original source documents
  were preserved.
- [x] **GitHub preparation:** Repository name, requested description/topics,
  and Windows commands are documented. Git is unavailable, so no repository
  was initialized and no commit or push occurred.
- [x] **Full tests:** `python -m pytest -q` — **102 passed**.
- [x] **Streamlit AppTest:** `python -m pytest -q tests/test_app.py` —
  **10 passed**.
- [x] **Compilation:** `python -m compileall -q app.py config.py core ingestion vectorstore evaluation ui tests` — passed.
- [x] **Application smoke test:** Running Streamlit application returned
  **HTTP 200**.
- [x] **Persistence:** Read-only check after tests confirmed **17 indexed
  filenames and 141 vectors** in `cybervault_documents`.
- [x] **Models:** `gemini-embedding-001` (3072 dimensions) and
  `gemini-3.5-flash-lite`; API key detection confirmed without exposing its
  value.

## Manual actions before publication

- [ ] Install Git and review `git status`, staged files, and
  `git diff --cached --stat`; Git ignore behavior and tracked files could not
  be verified in this environment.
- [ ] Confirm no `.env`, source corpus, ChromaDB data, or other local runtime
  data is staged.
- [ ] Review the NIST PDF's third-party notices before redistributing source
  material. Preserve OWASP attribution and CC BY-SA 4.0 terms for any
  redistribution.
- [ ] Create the GitHub repository and add its remote only after reviewing
  publication contents. Do not commit or push without explicit approval.

See [repository_submission.md](repository_submission.md) for the exact
publication commands and [phase8_final_report.md](phase8_final_report.md) for
the consolidated evidence and remaining limitations.
