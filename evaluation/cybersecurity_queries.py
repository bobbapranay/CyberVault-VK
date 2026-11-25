"""Chunk-annotated retrieval evaluation set for the indexed cybersecurity corpus."""

from __future__ import annotations

from evaluation.retrieval_evaluator import RetrievalTestQuery


CYBERSECURITY_EVALUATION_QUERIES = (
    RetrievalTestQuery(
        query="What are the six functions of NIST Cybersecurity Framework 2.0?",
        expected_filenames=("NIST_CSWP_29_CSF_2.0.pdf",),
        expected_chunk_ids=(
            "chunk_f57321f9dc7f5295105b0edcff455bf2",
            "chunk_57e34efdead339306f219e4c4fdf3e4c",
            "chunk_824f940ffca3bd8442ff578a8f9c4263",
        ),
        expected_section="Introduction to the CSF Core; PDF pages 8-10.",
        expected_information=(
            "The Core lists GOVERN, IDENTIFY, PROTECT, DETECT, RESPOND, and RECOVER."
        ),
    ),
    RetrievalTestQuery(
        query="How does the NIST CSF 2.0 support cybersecurity risk management?",
        expected_filenames=("NIST_CSWP_29_CSF_2.0.pdf",),
        expected_chunk_ids=(
            "chunk_c4a1ce073a9b3bb42072e2b12b2c6398",
            "chunk_64b58345504e1968bc4a44e34ff7a9c9",
        ),
        expected_section=(
            "Improving Cybersecurity Risk Communication and Integration; "
            "PDF pages 15 and 17."
        ),
        expected_information=(
            "Risk handling options and integration with enterprise risk management."
        ),
    ),
    RetrievalTestQuery(
        query="How should organizations use CSF Implementation Tiers?",
        expected_filenames=("NIST_CSWP_29_CSF_2.0.pdf",),
        expected_chunk_ids=(
            "chunk_24ffce00e891abf56d499e89a297e2df",
            "chunk_9872a7f8e9be3f59863501bcfdd5e466",
        ),
        expected_section="CSF Tiers and Appendix B; PDF pages 13 and 29.",
        expected_information=(
            "Tiers characterize rigor of risk governance and management and "
            "complement, rather than replace, an organization's risk method."
        ),
    ),
    RetrievalTestQuery(
        query="What are the four categories within the NIST CSF GOVERN function?",
        expected_filenames=("NIST_CSWP_29_CSF_2.0.pdf",),
        expected_chunk_ids=(
            "chunk_2bc5b21ed9ad8bc2a8b004a8443869ce",
            "chunk_5675c54c03ed5cfe6b005f7b60bfd166",
        ),
        expected_section="GOVERN categories; PDF pages 21-22.",
        expected_information=(
            "The premise's count is incorrect: NIST lists six categories—"
            "Organizational Context, Risk Management Strategy, Roles, "
            "Responsibilities and Authorities, Policy, Oversight, and "
            "Cybersecurity Supply Chain Risk Management."
        ),
    ),
    RetrievalTestQuery(
        query="What is Broken Access Control and what common failures does OWASP identify?",
        expected_filenames=("A01_2025-Broken_Access_Control.md",),
        expected_chunk_ids=(
            "chunk_5a9ac4ab493996071a74b9c2a41acc1f",
        ),
        expected_section="OWASP Top 10:2025 A01 Description.",
        expected_information=(
            "Failure to enforce intended permissions, including least-privilege "
            "violations and access-control bypasses."
        ),
    ),
    RetrievalTestQuery(
        query="What maximum and average incidence rates does OWASP report for Broken Access Control?",
        expected_filenames=("A01_2025-Broken_Access_Control.md",),
        expected_chunk_ids=(
            "chunk_31ce54834c73ef29bed00955fe1f7ab7",
        ),
        expected_section="OWASP Top 10:2025 A01 Score Table.",
        expected_information=(
            "Maximum incidence rate 20.15%; average incidence rate 3.74%."
        ),
    ),
    RetrievalTestQuery(
        query="What configuration problems are common in OWASP Security Misconfiguration?",
        expected_filenames=("A02_2025-Security_Misconfiguration.md",),
        expected_chunk_ids=(
            "chunk_ea3c822bb64e69f61a0f5342f08b5b62",
        ),
        expected_section="OWASP Top 10:2025 A02 Description.",
        expected_information=(
            "Insecure defaults, unnecessary features, unchanged default accounts, "
            "excessive error detail, and insecure platform settings."
        ),
    ),
    RetrievalTestQuery(
        query="What are Software Supply Chain Failures and how do they occur?",
        expected_filenames=("A03_2025-Software_Supply_Chain_Failures.md",),
        expected_chunk_ids=(
            "chunk_de3d3c23227ffe7adb257f3d29ae14ab",
            "chunk_4f9de3eb7457f555becadd331ac189de",
        ),
        expected_section="OWASP Top 10:2025 A03 Description and scenarios.",
        expected_information=(
            "Breakdowns or compromises in building, distributing, or updating "
            "software, often due to vulnerabilities or malicious changes in "
            "third-party code, tools, or dependencies."
        ),
    ),
)
