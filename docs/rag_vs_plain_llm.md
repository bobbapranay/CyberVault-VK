# Live RAG versus Plain LLM comparison

## Method

All six answers below were generated in live requests to the configured
`gemini-3.5-flash-lite` model. For each comparison, the Plain LLM and RAG
requests used the identical question. Plain LLM received no indexed content
and no retrieval results; it was asked to answer directly and not claim that
uploaded documents had been consulted. RAG used a real `RETRIEVAL_QUERY`
embedding, the persistent ChromaDB collection, and the retrieved context
identified below. The results are observed outputs, not a claim that RAG is
always better.

Citation markers and their source references were checked against the actual
retrieved chunk IDs and the stored chunk text. OWASP Markdown sources are
unpaginated, so no page numbers are shown for them.

## Comparison 1 — NIST CSF 2.0 functions

**Question (both modes):** What are the six functions of NIST Cybersecurity
Framework 2.0?

### Plain LLM — actual response

> The six functions of the NIST Cybersecurity Framework (CSF) 2.0 are:
>
> 1. **Govern**
> 2. **Identify**
> 3. **Protect**
> 4. **Detect**
> 5. **Respond**
> 6. **Recover**

### RAG — actual response

> The six functions of the NIST Cybersecurity Framework (CSF) 2.0 are:
>
> 1. **GOVERN (GV)** [3]
> 2. **IDENTIFY (ID)** [1], [3]
> 3. **PROTECT (PR)** [1]
> 4. **DETECT (DE)** [1]
> 5. **RESPOND (RS)** [1]
> 6. **RECOVER (RC)** [1]

| Citation | Retrieved source | Chunk ID | Distance |
|---|---|---|---:|
| [1] | `NIST_CSWP_29_CSF_2.0.pdf`, p. 9 | `chunk_f57321f9dc7f5295105b0edcff455bf2` | 0.220108 |
| [3] | `NIST_CSWP_29_CSF_2.0.pdf`, p. 8 | `chunk_824f940ffca3bd8442ff578a8f9c4263` | 0.249287 |

Both modes answered correctly. The RAG citations point to retrieved NIST chunks
that list the six functions. The complete top-five ranking is in the
[retrieval evaluation](retrieval_evaluation.md).

## Comparison 2 — OWASP 2025 supply-chain definition

**Question (both modes):** What does OWASP describe as Software Supply Chain
Failures?

### Plain LLM — actual response

> The Open Worldwide Application Security Project (OWASP) includes **Software
> Supply Chain Failures** as part of its Top 10 Application Security Risks
> (specifically highlighted under risks such as *A06:2021 - Vulnerable and
> Outdated Components* or broader supply chain integrity discussions).
>
> OWASP describes Software Supply Chain Failures as vulnerabilities,
> compromises, or weaknesses that occur within the software development and
> deployment ecosystem. This supply chain encompasses everything and everyone
> involved in creating, building, and delivering software, including:
>
> * **Third-party code and libraries:** Using open-source or commercial
>   components, modules, and dependencies that contain known vulnerabilities
>   or malicious code.
> * **Build and deployment pipelines:** Compromises in the tools, continuous
>   integration/continuous deployment (CI/CD) servers, repositories, and
>   development environments used to compile and release the software.
> * **Vendor and supplier risks:** Security gaps introduced by third-party
>   vendors, managed service providers, or software development contractors
>   who have access to the codebase or infrastructure.
> * **Artifact tampering:** Unauthorized modifications to software updates,
>   packages, or container images after they have been built but before they
>   reach the end user.
>
> Ultimately, these failures happen when organizations lack visibility,
> inventory, or control over the external components and development
> processes that make up their final software products, leaving them exposed
> to third-party vulnerabilities and malicious injections.

### RAG — actual response

> OWASP describes Software Supply Chain Failures as breakdowns or other
> compromises in the process of building, distributing, or updating software,
> which are often caused by vulnerabilities or malicious changes in third-party
> code, tools, or other dependencies that the system relies on [1], [2].

| Citation | Retrieved source | Chunk ID | Distance |
|---|---|---|---:|
| [1] | `A03_2025-Software_Supply_Chain_Failures.md`, unpaginated | `chunk_de3d3c23227ffe7adb257f3d29ae14ab` | 0.206260 |
| [2] | `A03_2025-Software_Supply_Chain_Failures.md`, unpaginated | `chunk_a4d256606fae99e5bc4ad570d0351fe7` | 0.220729 |

The Plain answer included generally plausible supply-chain examples, but it
framed the answer around OWASP Top 10:2021 and A06:2021 rather than directly
answering the requested 2025 category. The RAG definition matches the
retrieved A03:2025 description. Its cited chunks contain the described
build/distribution/update breakdowns and third-party code/tool/dependency
risks.

## Comparison 3 — Broken Access Control incidence rates

**Question (both modes):** What maximum and average incidence rates does OWASP
report for Broken Access Control?

### Plain LLM — actual response

> According to the OWASP Top 10 (specifically the 2021 release), Broken Access
> Control was moved up to the #1 position. For this category:
>
> * **Maximum Incidence Rate:** 94%
> * **Average Incidence Rate:** 3.81%
>
> These figures represent the data collected across the contributed datasets
> for the OWASP Top 10 risk assessment, where Broken Access Control had the
> highest number of occurrences in applications tested.

### RAG — actual response

> OWASP reports a maximum incidence rate of 20.15% and an average incidence
> rate of 3.74% for Broken Access Control [1].

| Citation | Retrieved source | Chunk ID | Distance |
|---|---|---|---:|
| [1] | `A01_2025-Broken_Access_Control.md`, unpaginated | `chunk_31ce54834c73ef29bed00955fe1f7ab7` | 0.238647 |

The RAG answer matches the two values in the retrieved OWASP Top 10:2025 A01
score-table chunk. The Plain answer explicitly used the 2021 release and
returned values that do not match the requested OWASP Top 10:2025 source.

## Overall observations

- Both modes answered the NIST functions question correctly; the RAG answer
  also included source citations that map to retrieved NIST pages.
- The OWASP supply-chain comparison illustrates a version-specific difference:
  the Plain answer leaned on 2021 framing, while RAG used the indexed 2025
  definition.
- For the exact OWASP 2025 incidence-rate question, the Plain answer returned
  different values and the RAG answer matched the score-table chunk.
- Plain LLM responses have no document citations by design. Each displayed RAG
  citation above maps to a source actually included in the generation context.
- These three examples are a small sample. They do not establish that RAG is
  universally more accurate or useful.
