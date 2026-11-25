# Live retrieval evaluation

## Scope and method

This evaluation ran eight live `RETRIEVAL_QUERY` embedding requests against the
persistent `cybervault_documents` ChromaDB collection using
`gemini-embedding-001`. It used the real indexed NIST CSF 2.0 PDF and OWASP
Top 10:2025 Markdown files, with `K=5`. ChromaDB's cosine distances are
reported as returned; lower values indicate closer matches and are not
percentages or confidence scores.

Each query has manually annotated, exact relevant chunk IDs, expected source
filename(s), section, and answer information. Only the exact IDs count as
relevant for the metrics. A different chunk from an expected document does
not count automatically. The source filename is also recorded to distinguish
document-level relevance from the chunk-level relevance used in scoring.

For each query:

- **Hit@5** is 1 if at least one annotated chunk is in the top five.
- **Precision@5** is the number of annotated chunks retrieved in the top five,
  divided by five.
- **Recall@5** is the number of annotated chunks retrieved in the top five,
  divided by the number of annotated chunks for that query.
- **Reciprocal rank** is `1 / rank` of the first annotated chunk, or zero if
  none is found. MRR is the mean across queries.

The fourth question contains an intentionally incorrect premise: NIST CSF 2.0
has six GOVERN categories, not four. The relevant annotation records the
source's actual information.

## Queries and annotations

| # | Question | Expected source | Expected section and relevant information | Annotated chunk IDs |
|---:|---|---|---|---|
| 1 | What are the six functions of NIST Cybersecurity Framework 2.0? | `NIST_CSWP_29_CSF_2.0.pdf` | CSF Core introduction, PDF pp. 8–10; GOVERN, IDENTIFY, PROTECT, DETECT, RESPOND, RECOVER. | `chunk_f57321f9dc7f5295105b0edcff455bf2`, `chunk_57e34efdead339306f219e4c4fdf3e4c`, `chunk_824f940ffca3bd8442ff578a8f9c4263` |
| 2 | How does the NIST CSF 2.0 support cybersecurity risk management? | `NIST_CSWP_29_CSF_2.0.pdf` | Risk communication and integration, pp. 15 and 17; risk handling options and ERM integration. | `chunk_c4a1ce073a9b3bb42072e2b12b2c6398`, `chunk_64b58345504e1968bc4a44e34ff7a9c9` |
| 3 | How should organizations use CSF Implementation Tiers? | `NIST_CSWP_29_CSF_2.0.pdf` | CSF Tiers and Appendix B, pp. 13 and 29; characterize rigor of risk governance and management and complement, rather than replace, an organization's risk method. | `chunk_24ffce00e891abf56d499e89a297e2df`, `chunk_9872a7f8e9be3f59863501bcfdd5e466` |
| 4 | What are the four categories within the NIST CSF GOVERN function? | `NIST_CSWP_29_CSF_2.0.pdf` | GOVERN categories, pp. 21–22; premise is incorrect—NIST lists six: Organizational Context, Risk Management Strategy, Roles, Responsibilities and Authorities, Policy, Oversight, and Cybersecurity Supply Chain Risk Management. | `chunk_2bc5b21ed9ad8bc2a8b004a8443869ce`, `chunk_5675c54c03ed5cfe6b005f7b60bfd166` |
| 5 | What is Broken Access Control and what common failures does OWASP identify? | `A01_2025-Broken_Access_Control.md` | OWASP Top 10:2025 A01 Description; failure to enforce intended permissions, including least-privilege violations and access-control bypasses. | `chunk_5a9ac4ab493996071a74b9c2a41acc1f` |
| 6 | What maximum and average incidence rates does OWASP report for Broken Access Control? | `A01_2025-Broken_Access_Control.md` | A01 score table; maximum incidence 20.15%, average incidence 3.74%. | `chunk_31ce54834c73ef29bed00955fe1f7ab7` |
| 7 | What configuration problems are common in OWASP Security Misconfiguration? | `A02_2025-Security_Misconfiguration.md` | A02 Description; insecure defaults, unnecessary features, unchanged default accounts, excessive error detail, and insecure platform settings. | `chunk_ea3c822bb64e69f61a0f5342f08b5b62` |
| 8 | What are Software Supply Chain Failures and how do they occur? | `A03_2025-Software_Supply_Chain_Failures.md` | A03 Description and scenarios; breakdowns or compromises when building, distributing, or updating software, including vulnerable or malicious third-party code, tools, or dependencies. | `chunk_de3d3c23227ffe7adb257f3d29ae14ab`, `chunk_4f9de3eb7457f555becadd331ac189de` |

All 14 unique annotated IDs were checked against the live collection before
scoring: each existed and its stored filename matched the expected source.

## Per-query metrics

| # | Hit@5 | Precision@5 | Recall@5 | Reciprocal rank |
|---:|---:|---:|---:|---:|
| 1 | 1 | 0.600 | 1.000 | 1.000 |
| 2 | 1 | 0.400 | 1.000 | 1.000 |
| 3 | 1 | 0.400 | 1.000 | 1.000 |
| 4 | 1 | 0.400 | 1.000 | 1.000 |
| 5 | 1 | 0.200 | 1.000 | 1.000 |
| 6 | 1 | 0.200 | 1.000 | 1.000 |
| 7 | 1 | 0.200 | 1.000 | 1.000 |
| 8 | 1 | 0.400 | 1.000 | 0.500 |

## Actual top-five results

`Relevant` marks only an exact annotated chunk ID. PDF page numbers are
1-based source pages. Markdown files have no page number.

| Query | Rank | Retrieved source | Chunk ID | Cosine distance | Relevant |
|---:|---:|---|---|---:|:---:|
| 1 | 1 | `NIST_CSWP_29_CSF_2.0.pdf`, p. 9 | `chunk_f57321f9dc7f5295105b0edcff455bf2` | 0.220108 | Yes |
| 1 | 2 | `NIST_CSWP_29_CSF_2.0.pdf`, p. 10 | `chunk_57e34efdead339306f219e4c4fdf3e4c` | 0.246628 | Yes |
| 1 | 3 | `NIST_CSWP_29_CSF_2.0.pdf`, p. 8 | `chunk_824f940ffca3bd8442ff578a8f9c4263` | 0.249287 | Yes |
| 1 | 4 | `NIST_CSWP_29_CSF_2.0.pdf`, p. 26 | `chunk_93b29d217ecf29d156e33924d01a009f` | 0.254832 | No |
| 1 | 5 | `NIST_CSWP_29_CSF_2.0.pdf`, p. 20 | `chunk_baa2e6b7c14156ac4314a937f16decac` | 0.262681 | No |
| 2 | 1 | `NIST_CSWP_29_CSF_2.0.pdf`, p. 15 | `chunk_c4a1ce073a9b3bb42072e2b12b2c6398` | 0.233563 | Yes |
| 2 | 2 | `NIST_CSWP_29_CSF_2.0.pdf`, p. 17 | `chunk_64b58345504e1968bc4a44e34ff7a9c9` | 0.238157 | Yes |
| 2 | 3 | `NIST_CSWP_29_CSF_2.0.pdf`, p. 19 | `chunk_c7b038409881ef6cdb78c96fde396660` | 0.246815 | No |
| 2 | 4 | `NIST_CSWP_29_CSF_2.0.pdf`, p. 5 | `chunk_84759461d2dab894e293e49034255236` | 0.247244 | No |
| 2 | 5 | `NIST_CSWP_29_CSF_2.0.pdf`, p. 5 | `chunk_c3e62b6283896e9d7a2d9a5801421bcd` | 0.248909 | No |
| 3 | 1 | `NIST_CSWP_29_CSF_2.0.pdf`, p. 13 | `chunk_24ffce00e891abf56d499e89a297e2df` | 0.218197 | Yes |
| 3 | 2 | `NIST_CSWP_29_CSF_2.0.pdf`, p. 29 | `chunk_9872a7f8e9be3f59863501bcfdd5e466` | 0.236083 | Yes |
| 3 | 3 | `NIST_CSWP_29_CSF_2.0.pdf`, p. 12 | `chunk_8e76f27ef73c70603ea3171964a22919` | 0.237144 | No |
| 3 | 4 | `NIST_CSWP_29_CSF_2.0.pdf`, p. 4 | `chunk_55f3681e6bd144088be291a8781fe480` | 0.242271 | No |
| 3 | 5 | `NIST_CSWP_29_CSF_2.0.pdf`, p. 5 | `chunk_84759461d2dab894e293e49034255236` | 0.244254 | No |
| 4 | 1 | `NIST_CSWP_29_CSF_2.0.pdf`, p. 21 | `chunk_2bc5b21ed9ad8bc2a8b004a8443869ce` | 0.235688 | Yes |
| 4 | 2 | `NIST_CSWP_29_CSF_2.0.pdf`, p. 22 | `chunk_5675c54c03ed5cfe6b005f7b60bfd166` | 0.245031 | Yes |
| 4 | 3 | `NIST_CSWP_29_CSF_2.0.pdf`, p. 8 | `chunk_824f940ffca3bd8442ff578a8f9c4263` | 0.246697 | No |
| 4 | 4 | `NIST_CSWP_29_CSF_2.0.pdf`, p. 20 | `chunk_baa2e6b7c14156ac4314a937f16decac` | 0.248400 | No |
| 4 | 5 | `NIST_CSWP_29_CSF_2.0.pdf`, p. 10 | `chunk_57e34efdead339306f219e4c4fdf3e4c` | 0.261612 | No |
| 5 | 1 | `A01_2025-Broken_Access_Control.md`, unpaginated | `chunk_5a9ac4ab493996071a74b9c2a41acc1f` | 0.233876 | Yes |
| 5 | 2 | `A01_2025-Broken_Access_Control.md`, unpaginated | `chunk_39c5ad391a168eee4ffea089c75bc5f5` | 0.258065 | No |
| 5 | 3 | `A01_2025-Broken_Access_Control.md`, unpaginated | `chunk_31ce54834c73ef29bed00955fe1f7ab7` | 0.271806 | No |
| 5 | 4 | `A01_2025-Broken_Access_Control.md`, unpaginated | `chunk_914d1cb99c22ace2b5fcb4f54d76cf6d` | 0.279072 | No |
| 5 | 5 | `A01_2025-Broken_Access_Control.md`, unpaginated | `chunk_e3513c9bd1df809e371cbc49d5cd38cb` | 0.282727 | No |
| 6 | 1 | `A01_2025-Broken_Access_Control.md`, unpaginated | `chunk_31ce54834c73ef29bed00955fe1f7ab7` | 0.238647 | Yes |
| 6 | 2 | `0x02_2025-What_are_Application_Security_Risks.md`, unpaginated | `chunk_e195331c0eb44e46d9c67e8ae10dff13` | 0.288118 | No |
| 6 | 3 | `A01_2025-Broken_Access_Control.md`, unpaginated | `chunk_5a9ac4ab493996071a74b9c2a41acc1f` | 0.288134 | No |
| 6 | 4 | `0x00_2025-Introduction.md`, unpaginated | `chunk_b6fa11daf17823695925c162727061c8` | 0.293095 | No |
| 6 | 5 | `A06_2025-Insecure_Design.md`, unpaginated | `chunk_4784b017a438a4410d949f83c59f376d` | 0.293952 | No |
| 7 | 1 | `A02_2025-Security_Misconfiguration.md`, unpaginated | `chunk_ea3c822bb64e69f61a0f5342f08b5b62` | 0.224191 | Yes |
| 7 | 2 | `A02_2025-Security_Misconfiguration.md`, unpaginated | `chunk_c2edd60fea3dd8d071bc3d73460bf707` | 0.228261 | No |
| 7 | 3 | `A02_2025-Security_Misconfiguration.md`, unpaginated | `chunk_7aa4742cf7391ff089050f2394c1f130` | 0.232498 | No |
| 7 | 4 | `A02_2025-Security_Misconfiguration.md`, unpaginated | `chunk_2f105aa5fa1c7ca91198f8ab82b8c280` | 0.240156 | No |
| 7 | 5 | `A02_2025-Security_Misconfiguration.md`, unpaginated | `chunk_dbf9bda069c719249ca296af25a1dfae` | 0.274683 | No |
| 8 | 1 | `A08_2025-Software_or_Data_Integrity_Failures.md`, unpaginated | `chunk_c9c87909b09703324479e49ab4121d0f` | 0.213264 | No |
| 8 | 2 | `A03_2025-Software_Supply_Chain_Failures.md`, unpaginated | `chunk_4f9de3eb7457f555becadd331ac189de` | 0.218341 | Yes |
| 8 | 3 | `A03_2025-Software_Supply_Chain_Failures.md`, unpaginated | `chunk_de3d3c23227ffe7adb257f3d29ae14ab` | 0.232480 | Yes |
| 8 | 4 | `A03_2025-Software_Supply_Chain_Failures.md`, unpaginated | `chunk_a4d256606fae99e5bc4ad570d0351fe7` | 0.236817 | No |
| 8 | 5 | `A08_2025-Software_or_Data_Integrity_Failures.md`, unpaginated | `chunk_7b57d642bd5734d20b3cba27e15d7559` | 0.243738 | No |

## Aggregate results

| Metric | Measured result |
|---|---:|
| Hit Rate@5 | 1.000 |
| Mean Precision@5 | 0.350 |
| Mean Recall@5 | 1.000 |
| Mean Reciprocal Rank | 0.938 (exact mean: 0.9375) |

These are results for this small, manually annotated eight-query sample, not a
general estimate of retrieval quality. The sample is chunk-level and does not
evaluate generation quality.
