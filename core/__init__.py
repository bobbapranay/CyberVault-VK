"""Shared foundations for CyberVault RAG."""

from core.embedding_service import (
    EmbeddingBatchResult,
    EmbeddingFailure,
    EmbeddingService,
    EmbeddingServiceError,
    EmbeddedVector,
    MissingAPIKeyError,
)
from core.retrieval_engine import (
    RetrievedChunk,
    RetrievalError,
    RetrievalResult,
    inspect_retrieval,
    retrieve_documents,
)
from core.generation_service import (
    GenerationError,
    GenerationResult,
    GenerationService,
    MissingGenerationAPIKeyError,
)
from core.rag_pipeline import (
    ComparisonResponse,
    ContextBuildResult,
    PlainLLMResponse,
    RAGResponse,
    RAG_SYSTEM_PROMPT,
    SourceReference,
    build_document_context,
    generate_comparison_response,
    generate_plain_llm_response,
    generate_rag_response,
    validate_citations,
)

__all__ = [
    "EmbeddedVector",
    "EmbeddingBatchResult",
    "EmbeddingFailure",
    "EmbeddingService",
    "EmbeddingServiceError",
    "MissingAPIKeyError",
    "RetrievedChunk",
    "RetrievalError",
    "RetrievalResult",
    "inspect_retrieval",
    "retrieve_documents",
    "GenerationError",
    "GenerationResult",
    "GenerationService",
    "MissingGenerationAPIKeyError",
    "ComparisonResponse",
    "ContextBuildResult",
    "PlainLLMResponse",
    "RAGResponse",
    "RAG_SYSTEM_PROMPT",
    "SourceReference",
    "build_document_context",
    "generate_comparison_response",
    "generate_plain_llm_response",
    "generate_rag_response",
    "validate_citations",
]
