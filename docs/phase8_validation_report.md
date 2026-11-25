# Phase 8 — Step 5 validation report

## Result

Live RAG generation, Plain LLM comparison, retrieval evaluation, citation
checks, out-of-scope abstention, Streamlit AppTest, and regression checks were
completed against the existing CyberVault RAG dataset and persistent index.
The indexed source files and vectors were not modified by the evaluation or
test suite.

## Live configuration and dataset

- `GEMINI_API_KEY` was detected by the existing configuration loader. Its
  value was not printed, logged, or included in the reports.
- Embedding model: `gemini-embedding-001`; indexed document vectors are 3072
  dimensions. Live query embeddings used `RETRIEVAL_QUERY`.
- Generation model: `gemini-3.5-flash-lite`.
- Dataset: 17 original source files—one 32-page NIST CSF 2.0 PDF and 16 OWASP
  Top 10:2025 English Markdown documents. Dataset provenance and reuse terms
  are in [dataset_sources.md](dataset_sources.md).
- Persistent collection: `cybervault_documents`, containing 141 chunks and
  141 vectors. A post-test read confirmed all 17 source filenames and all 141
  vectors remained present.
- The live requests exercised six answerable RAG questions (the five below
  plus the OWASP incidence-rate comparison), three Plain LLM requests, three
  out-of-scope RAG requests, and eight retrieval-evaluation queries. A further
  live AI Chat Compare-mode AppTest was completed.

Some generation requests encountered transient HTTP 503 responses. The
service's bounded retries recovered, and all recorded live requests returned
responses. No credentials were exposed.

## End-to-end RAG answers and source verification

The following are actual Gemini responses, not mocked or reconstructed
answers. Citation numbers map to the numbered context sections supplied to
Gemini. Each listed chunk ID was found in the actual top-five retrieval for
that question, and its stored text was checked against the cited claims.
PDF page numbers are source page numbers; Markdown files are unpaginated.

### 1. NIST CSF 2.0 functions

**Question:** What are the six functions of NIST Cybersecurity Framework 2.0?

**Actual RAG answer:**

> The six functions of the NIST Cybersecurity Framework (CSF) 2.0 are:
>
> 1. **GOVERN (GV)** [3]
> 2. **IDENTIFY (ID)** [1], [3]
> 3. **PROTECT (PR)** [1]
> 4. **DETECT (DE)** [1]
> 5. **RESPOND (RS)** [1]
> 6. **RECOVER (RC)** [1]

| Citation | Retrieved source and chunk | Distance |
|---|---|---:|
| [1] | `NIST_CSWP_29_CSF_2.0.pdf`, p. 9 — `chunk_f57321f9dc7f5295105b0edcff455bf2` | 0.220108 |
| [3] | `NIST_CSWP_29_CSF_2.0.pdf`, p. 8 — `chunk_824f940ffca3bd8442ff578a8f9c4263` | 0.249287 |

Both cited NIST chunks contain the six function names.

### 2. OWASP Broken Access Control

**Question:** What is Broken Access Control according to OWASP Top 10:2025?

**Actual RAG answer:**

> According to the OWASP Top 10:2025, Broken Access Control is maintained at
> #1 as the most serious application security risk [4]. Access control
> enforces policy such that users cannot act outside of their intended
> permissions [1]. Failures typically lead to unauthorized information
> disclosure, modification or destruction of all data, or performing a
> business function outside the user's limits [1].
>
> Common access control vulnerabilities include:
> * Violation of the principle of least privilege (deny by default), where
>   access is available to anyone rather than being granted only for
>   particular capabilities, roles, or users [1].
> * Bypassing access control checks by modifying the URL (parameter tampering
>   or force browsing), internal application state, HTML page, or using an
>   attack tool that modifies API requests [1].
> * Permitting viewing or editing someone else's account by providing its
>   unique identifier (insecure direct object references) [2].
> * An accessible API with missing access controls for POST, PUT, and DELETE
>   [2].
> * Elevation of privilege, such as acting as a user without being logged in
>   or gaining privileges beyond those expected of the logged-in user (e.g.,
>   admin access) [2].
> * Metadata manipulation, such as replaying or tampering with a JSON Web
>   Token (JWT) access control token, a cookie, or a hidden field manipulated
>   to elevate privileges, or abusing JWT invalidation [2].
> * CORS misconfigurations allowing API access from unauthorized or untrusted
>   origins [2].
> * Force browsing (guessing URLs) to authenticated pages as an unauthenticated
>   user or to privileged pages as a standard user [2].

| Citation | Retrieved source and chunk | Distance |
|---|---|---:|
| [1] | `A01_2025-Broken_Access_Control.md` — `chunk_31ce54834c73ef29bed00955fe1f7ab7` | 0.217437 |
| [2] | `A01_2025-Broken_Access_Control.md` — `chunk_5a9ac4ab493996071a74b9c2a41acc1f` | 0.240691 |
| [4] | `0x00_2025-Introduction.md` — `chunk_b6fa11daf17823695925c162727061c8` | 0.271933 |

The cited A01 chunks contain the definition and listed access-control
vulnerabilities. The cited introduction places A01 first in its ordered
Top 10:2025 list. No Markdown page number was assigned.

### 3. OWASP Security Misconfiguration

**Question:** What are common Security Misconfiguration risks?

**Actual RAG answer:**

> Based on the provided documents, common security misconfiguration risks and
> vulnerabilities occur when:
>
> * Appropriate security hardening is missing across any part of the
>   application stack, or cloud service permissions are improperly configured
>   [1].
> * Unnecessary features (such as ports, services, pages, accounts, testing
>   frameworks, or privileges) are enabled or installed [1].
> * Default accounts and their passwords remain enabled and unchanged [1].
> * There is a lack of central configuration to intercept excessive error
>   messages, causing error handling to reveal stack traces or other overly
>   informative messages to users [1].
> * Latest security features on upgraded systems are disabled or configured
>   insecurely [1].
> * Insecure configurations result from an excessive prioritization of
>   backward compatibility [1].
> * Security settings in application servers, application frameworks
>   (e.g., Struts, Spring, ASP.NET), libraries, and databases are not set to
>   secure values [2].
> * Servers fail to send security headers or directives, or set them to
>   insecure values [2].

| Citation | Retrieved source and chunk | Distance |
|---|---|---:|
| [1] | `A02_2025-Security_Misconfiguration.md` — `chunk_7aa4742cf7391ff089050f2394c1f130` | 0.229718 |
| [2] | `A02_2025-Security_Misconfiguration.md` — `chunk_ea3c822bb64e69f61a0f5342f08b5b62` | 0.240499 |

Both cited chunks are from A02 and contain the configuration risks described.

### 4. OWASP Software Supply Chain Failures

**Question:** What does OWASP describe as Software Supply Chain Failures?

**Actual RAG answer:**

> OWASP describes Software Supply Chain Failures as breakdowns or other
> compromises in the process of building, distributing, or updating software,
> which are often caused by vulnerabilities or malicious changes in third-party
> code, tools, or other dependencies that the system relies on [1], [2].

| Citation | Retrieved source and chunk | Distance |
|---|---|---:|
| [1] | `A03_2025-Software_Supply_Chain_Failures.md` — `chunk_de3d3c23227ffe7adb257f3d29ae14ab` | 0.206260 |
| [2] | `A03_2025-Software_Supply_Chain_Failures.md` — `chunk_a4d256606fae99e5bc4ad570d0351fe7` | 0.220729 |

Both citations resolve to retrieved A03:2025 description/scenario chunks. The
answer's definition and dependency-related claims are present in those chunks.

### 5. NIST cybersecurity risk management

**Question:** How does the NIST framework approach cybersecurity risk
management?

**Actual RAG answer:**

> Based on the provided documents, the NIST Cybersecurity Framework (CSF) 2.0
> approaches cybersecurity risk management by providing guidance, a taxonomy
> of high-level outcomes, and a basis for communication across an organization
> (from executives to managers and practitioners) [1, 2].
>
> Key aspects of its approach include:
> * **Managing Risk Options:** Depending on potential impacts and likelihoods,
>   organizations can choose to handle risk by mitigating, transferring,
>   avoiding, or accepting negative risks, and realizing, sharing, enhancing,
>   or accepting positive risks [1].
> * **Core Functions:** The framework utilizes six related functions—GOVERN,
>   IDENTIFY, PROTECT, DETECT, RESPOND, and RECOVER—to inform strategic
>   decisions, secure assets, detect attacks, respond to incidents, and restore
>   operations [1, 4]. GOVERN sits at the center to inform how the other
>   functions are implemented [4].
> * **Non-Prescriptive Guidance:** The CSF does not prescribe how outcomes must
>   be achieved; instead, it provides links to online resources and guidance
>   on practices and controls [2].
> * **Integration with Enterprise Risk Management (ERM):** Organizations can
>   use an ERM approach alongside the CSF to balance risk considerations,
>   translate cybersecurity terminology into general risk management language
>   understood by executives, and integrate with other risk programs (such as
>   the NIST Risk Management Framework) [3].

| Citation | Retrieved source and chunk | Distance |
|---|---|---:|
| [1] | `NIST_CSWP_29_CSF_2.0.pdf`, p. 15 — `chunk_c4a1ce073a9b3bb42072e2b12b2c6398` | 0.273121 |
| [2] | `NIST_CSWP_29_CSF_2.0.pdf`, p. 2 — `chunk_5cdd6669ebd9c90c5a386c445ba1c30a` | 0.274180 |
| [3] | `NIST_CSWP_29_CSF_2.0.pdf`, p. 17 — `chunk_64b58345504e1968bc4a44e34ff7a9c9` | 0.274290 |
| [4] | `NIST_CSWP_29_CSF_2.0.pdf`, p. 9 — `chunk_f57321f9dc7f5295105b0edcff455bf2` | 0.274740 |

The cited pages were checked for their respective risk options, non-prescriptive
guidance, ERM integration, and Core functions.

## Citation verification

- Citation numbers in the five answers above map to the retrieved context
  sections by number and exact chunk ID; each referenced ID was present in that
  question's retrieval results.
- The cited chunk text was checked against the claims, and no source from an
  unrelated document was used for these answers.
- Citation validation removes numeric references that are not in the supplied
  context. The regression tests cover individual and grouped citation markers
  and invalid numbers.
- Markdown references are displayed as document-level sources without
  fabricated page numbers. PDF page values are the page metadata preserved by
  ingestion.
- A sixth answerable RAG request, on OWASP incidence rates, is documented in
  [the Plain LLM comparison](rag_vs_plain_llm.md). Its citation maps to the
  OWASP A01 score-table chunk containing the reported 20.15% maximum and 3.74%
  average values.

## Out-of-scope questions

Each question was sent through actual retrieval and Gemini generation. The
nearest-neighbor chunks below were not treated as evidence. In each case the
pipeline returned the safe insufficient-information response, set
`missing_context=True`, and returned no verified citation or source reference.

| Question | Closest retrieved chunk and distance | Actual final response |
|---|---|---|
| What is the current market price of CrowdStrike (CRWD) stock right now? | `NIST_CSWP_29_CSF_2.0.pdf`, p. 1, `chunk_72845ac13526ae2b2fac7894be1147b0`; 0.461850 | “The uploaded documents do not contain sufficient verified information to answer this question.” |
| What was Northwind Health's internal security incident yesterday? | `A10_2025-Mishandling_of_Exceptional_Conditions.md`, unpaginated, `chunk_30d2233163ccc262d38fc39c0f625098`; 0.368885 | “The uploaded documents do not contain sufficient verified information to answer this question.” |
| What is the exact minimum password length required by Acme Regional Bank? | `A07_2025-Authentication_Failures.md`, unpaginated, `chunk_e423c88f60a4d5ea47aa5d21311dfa1e`; 0.342750 | “The uploaded documents do not contain sufficient verified information to answer this question.” |

The nearest matches were unrelated to the requested current market quote,
private incident details, and organization-specific password policy. The
configured maximum-distance threshold is unset; retrieval still returns
nearest neighbors, while citation validation prevents uncited answers from
being presented as grounded.

## Plain LLM comparison

Three identical questions were run through Plain LLM and RAG with live
`gemini-3.5-flash-lite` requests. Plain LLM received no retrieved documents.
The observed differences:

- NIST functions: both modes listed the six functions correctly; RAG cited
  NIST pages 8–9.
- OWASP supply-chain definition: Plain LLM referred to older 2021 OWASP
  framing, while RAG returned the retrieved Top 10:2025 definition and
  citations.
- Broken Access Control rates: Plain LLM returned 94% and 3.81%, whereas the
  RAG answer cited the 2025 source's 20.15% maximum and 3.74% average.

The complete observed Plain and RAG responses, retrieved source IDs, distances,
and per-question assessment are in
[rag_vs_plain_llm.md](rag_vs_plain_llm.md). These examples do not show that RAG
is always better.

## Retrieval evaluation

Eight live semantic queries were evaluated at K=5 against manually annotated
exact relevant chunk IDs. All 14 unique gold IDs existed in the collection and
matched their expected source files.

| Metric | Result |
|---|---:|
| Hit Rate@5 | 1.000 |
| Mean Precision@5 | 0.350 |
| Mean Recall@5 | 1.000 |
| MRR | 0.938 (exact mean 0.9375) |

The question-level annotations, ranked top-five chunk IDs and distances, and
metric definitions are in [retrieval_evaluation.md](retrieval_evaluation.md).
These values apply only to the small, manually annotated sample.

## Streamlit AI Chat verification

- Streamlit AppTest completed **10 tests successfully**, covering page rendering,
  AI Chat mode selection, Settings secret non-display, conversation clearing,
  and source-reference formatting.
- A live AI Chat Compare-mode AppTest used the same NIST functions question in
  both paths. It completed with zero Streamlit exceptions, displayed the
  `Sources` and `Retrieved context` expanders, and rendered the cited NIST
  filenames and PDF page numbers.
- RAG, Plain LLM, and Compare service paths were exercised with live requests.
  The Plain path receives no retrieval context; Compare passes the same user
  question into both paths.
- App tests verify that the `Sources` expander maps citation numbers to source
  filenames and PDF page labels, and that the `Retrieved context` expander
  displays chunk ID, distance, source, and text.
- Out-of-scope responses display as an information/abstention message with no
  verified citations. App code does not render API credentials.
- The AppTest source-formatting check confirms Markdown sources use
  “Document-level source”, not an invented page number.

## Regression and persistence checks

- Full pytest suite: **102 passed**.
- Python compilation: `python -m compileall -q app.py config.py core ingestion vectorstore evaluation ui tests` — passed.
- Standalone Streamlit AppTest file: **10 passed**.
- Post-test persistence check: **17** source files, **17** indexed filenames,
  and **141** vectors remained present. The test suite did not overwrite the
  real collection.

One evidence-runner command returned a nonzero exit only after all live
responses and retrieval results had been recorded: its cleanup attempted
`ChromaStore.close()`, which is not an implemented method. This did not affect
the application, requests, or persistent collection; the independent
post-test check confirmed the collection remained intact.

## Limitations

- The retrieval evaluation has eight queries and manual chunk-level labels; it
  is too small to generalize to all cybersecurity questions.
- The optional cosine-distance threshold is unset. Nearest neighbors can be
  unrelated; the application does not claim that distance is a relevance
  probability.
- The current conservative abstention rule replaces any generated answer with
  no verified citation. This can reject an otherwise useful answer if the
  model fails to cite its supporting context.
- Citation validation verifies that citation numbers map to supplied chunks;
  it does not automatically prove entailment. The cited chunks in this report
  were manually checked.
- Chat history is session-local and is not stored in a persistent database.
- Gemini availability and quota can cause transient errors; bounded retries
  succeeded during this validation.

## Files changed for Step 5

- `app.py`
- `core/rag_pipeline.py`
- `evaluation/cybersecurity_queries.py`
- `evaluation/retrieval_evaluator.py`
- `tests/test_app.py`
- `tests/test_rag_pipeline.py`
- `tests/test_retrieval_evaluation.py`
- `README.md`
- `docs/evaluation_report.md`
- `docs/rag_vs_plain_llm.md`
- `docs/retrieval_evaluation.md`
- `docs/phase8_validation_report.md`

No source dataset files were edited. At the end of Step 5, no screenshots or
publication preparation had been performed; Step 6 capture and submission
status is recorded in [phase8_final_report.md](phase8_final_report.md) and
[final_submission_checklist.md](final_submission_checklist.md).
