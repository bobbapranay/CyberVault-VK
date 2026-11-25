# CyberVault RAG cybersecurity dataset

Downloaded on **2026-11-25**. The materials below are original publications or
source documents from their publishers; no PDF was synthesized or modified.
The source files remain unchanged. They were processed and indexed on
**2026-11-25** using CyberVault RAG's existing ingestion pipeline.

## NIST Cybersecurity Framework 2.0

| Field | Details |
|---|---|
| Title | *The NIST Cybersecurity Framework (CSF) 2.0* |
| Authors | Cherilyn Pascoe, Stephen Quinn, and Karen Scarfone |
| Publisher | National Institute of Standards and Technology (NIST), NIST CSWP 29 (2024) |
| Original publication page | <https://www.nist.gov/publications/nist-cybersecurity-framework-csf-20> |
| Original PDF | <https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=957258> |
| DOI | <https://doi.org/10.6028/NIST.CSWP.29> |
| Local file | `data/documents/NIST_CSWP_29_CSF_2.0.pdf` |
| Actual page count | 32 |
| License / reuse | See the NIST reuse note below. |
| Validation | PyPDF opened the PDF; all 32 pages yielded extractable text; 69,580 extracted characters; no empty pages; 1,518,858 bytes. |

NIST states that works created by NIST employees are generally not subject to
copyright protection in the United States under 17 U.S.C. § 105. Its
technical-publication terms grant royalty-free worldwide rights to reprint and
distribute, while reserving foreign rights; some NIST works may contain
third-party copyrighted material. Credit NIST and retain this source citation.
Review any separately credited third-party material before further
redistribution. See [NIST copyright and licensing terms](https://www.nist.gov/open/license).

## OWASP Top 10:2025

The following are separate, unmodified English Markdown source files from the
official OWASP Top 10 repository. Their original source URLs are listed per
file. They are Markdown documents and have **no fixed page count**; page counts
are therefore not applicable and are not estimated. The 32-page NIST PDF alone
exceeds the dataset's minimum page requirement.

| Local file (under `data/documents/owasp_top10_2025/`) | Title | Original source URL | Pages | Validation |
|---|---|---|---:|---|
| `0x00_2025-Introduction.md` | The Ten Most Critical Web Application Security Risks | <https://raw.githubusercontent.com/OWASP/Top10/master/2025/docs/en/0x00_2025-Introduction.md> | N/A (Markdown) | UTF-8 text, non-empty, headings present |
| `0x01_2025-About_OWASP.md` | About OWASP | <https://raw.githubusercontent.com/OWASP/Top10/master/2025/docs/en/0x01_2025-About_OWASP.md> | N/A (Markdown) | UTF-8 text, non-empty, headings present |
| `0x02_2025-What_are_Application_Security_Risks.md` | What are Application Security Risks? | <https://raw.githubusercontent.com/OWASP/Top10/master/2025/docs/en/0x02_2025-What_are_Application_Security_Risks.md> | N/A (Markdown) | UTF-8 text, non-empty, headings present |
| `0x03_2025-Establishing_a_Modern_Application_Security_Program.md` | Establishing a Modern Application Security Program | <https://raw.githubusercontent.com/OWASP/Top10/master/2025/docs/en/0x03_2025-Establishing_a_Modern_Application_Security_Program.md> | N/A (Markdown) | UTF-8 text, non-empty, headings present |
| `A01_2025-Broken_Access_Control.md` | A01:2025 Broken Access Control | <https://raw.githubusercontent.com/OWASP/Top10/master/2025/docs/en/A01_2025-Broken_Access_Control.md> | N/A (Markdown) | UTF-8 text, non-empty, headings present |
| `A02_2025-Security_Misconfiguration.md` | A02:2025 Security Misconfiguration | <https://raw.githubusercontent.com/OWASP/Top10/master/2025/docs/en/A02_2025-Security_Misconfiguration.md> | N/A (Markdown) | UTF-8 text, non-empty, headings present |
| `A03_2025-Software_Supply_Chain_Failures.md` | A03:2025 Software Supply Chain Failures | <https://raw.githubusercontent.com/OWASP/Top10/master/2025/docs/en/A03_2025-Software_Supply_Chain_Failures.md> | N/A (Markdown) | UTF-8 text, non-empty, headings present |
| `A04_2025-Cryptographic_Failures.md` | A04:2025 Cryptographic Failures | <https://raw.githubusercontent.com/OWASP/Top10/master/2025/docs/en/A04_2025-Cryptographic_Failures.md> | N/A (Markdown) | UTF-8 text, non-empty, headings present |
| `A05_2025-Injection.md` | A05:2025 Injection | <https://raw.githubusercontent.com/OWASP/Top10/master/2025/docs/en/A05_2025-Injection.md> | N/A (Markdown) | UTF-8 text, non-empty, headings present |
| `A06_2025-Insecure_Design.md` | A06:2025 Insecure Design | <https://raw.githubusercontent.com/OWASP/Top10/master/2025/docs/en/A06_2025-Insecure_Design.md> | N/A (Markdown) | UTF-8 text, non-empty, headings present |
| `A07_2025-Authentication_Failures.md` | A07:2025 Authentication Failures | <https://raw.githubusercontent.com/OWASP/Top10/master/2025/docs/en/A07_2025-Authentication_Failures.md> | N/A (Markdown) | UTF-8 text, non-empty, headings present |
| `A08_2025-Software_or_Data_Integrity_Failures.md` | A08:2025 Software or Data Integrity Failures | <https://raw.githubusercontent.com/OWASP/Top10/master/2025/docs/en/A08_2025-Software_or_Data_Integrity_Failures.md> | N/A (Markdown) | UTF-8 text, non-empty, headings present |
| `A09_2025-Security_Logging_and_Alerting_Failures.md` | A09:2025 Security Logging & Alerting Failures | <https://raw.githubusercontent.com/OWASP/Top10/master/2025/docs/en/A09_2025-Security_Logging_and_Alerting_Failures.md> | N/A (Markdown) | UTF-8 text, non-empty, headings present |
| `A10_2025-Mishandling_of_Exceptional_Conditions.md` | A10:2025 Mishandling of Exceptional Conditions | <https://raw.githubusercontent.com/OWASP/Top10/master/2025/docs/en/A10_2025-Mishandling_of_Exceptional_Conditions.md> | N/A (Markdown) | UTF-8 text, non-empty, headings present |
| `index.md` | OWASP Top 10:2025 | <https://raw.githubusercontent.com/OWASP/Top10/master/2025/docs/en/index.md> | N/A (Markdown) | UTF-8 text, non-empty, headings present |
| `X01_2025-Next_Steps.md` | Next Steps | <https://raw.githubusercontent.com/OWASP/Top10/master/2025/docs/en/X01_2025-Next_Steps.md> | N/A (Markdown) | UTF-8 text, non-empty, headings present |

**Publisher:** OWASP Foundation / OWASP Top 10 Project.

**License and attribution:** The OWASP Top 10 repository identifies its content
as [Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)](https://github.com/OWASP/Top10/blob/master/LICENSE). This permits redistribution
and adaptation subject to attribution, license-linking, and ShareAlike terms.
Attribute the OWASP Top 10 Project and link to the original source and license;
if adapting the material, identify changes and distribute adaptations under
CC BY-SA 4.0 or a compatible license. The downloaded files were not edited.
The [OWASP Top 10 2025 site](https://owasp.org/Top10/2025/) identifies 2025 as
the current released version.

**Validation:** All 16 files were downloaded from the listed official raw
repository URLs. Each is non-empty UTF-8 Markdown containing substantive text
and headings. No fixed page count applies to these source files.

## Dataset totals and handling

- **PDF pages:** 32 verified pages across 1 PDF; all pages have extractable text.
- **Additional source material:** 16 unpaginated OWASP Markdown files; each
  passed non-empty text and heading checks.
- **Overall:** 17 documents from two official publishers. The verified PDF
  content alone meets the 10–20-page minimum.
- **Processing:** All 17 files processed successfully; 32 PDF pages extracted;
  141 chunks generated with configured 500-token target and 100-token overlap.
- **Embeddings and indexing:** 141 real `gemini-embedding-001`
  `RETRIEVAL_DOCUMENT` embeddings were created at 3072 dimensions and stored
  persistently in the `cybervault_documents` ChromaDB collection under
  `data/chroma`. All 17 documents are complete; no duplicates were present
  before indexing.
- **Redistribution:** The OWASP material is redistributable under CC BY-SA 4.0
  with attribution and ShareAlike compliance. NIST's stated reuse terms are
  summarized above; check any third-party notices in the PDF before external
  redistribution.

## Repository publication handling

The local source corpus is intentionally excluded from Git by
`.gitignore` (`data/documents/`). OWASP Top 10 is published under CC BY-SA 4.0;
attribution and ShareAlike terms still apply to any redistribution. NIST's
general reuse terms do not resolve rights for every separately credited
third-party item. Review the PDF's notices before redistributing it. The
project documentation records the official URLs and filenames so users can
obtain the documents from their publishers. Local indexed counts in the
validation reports describe this working copy, not files included in a
published repository.
