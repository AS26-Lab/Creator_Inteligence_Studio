"""Dominio para componentes de embedding semantico local."""

from .model_sources import (
    SemanticEmbeddingArtifact,
    SemanticEmbeddingModelHealth,
    SemanticEmbeddingModelManifest,
    SEMANTIC_MODEL_CHUNKING_VERSION,
    SEMANTIC_MODEL_EMBEDDING_DIMENSION,
    SEMANTIC_MODEL_MAX_TOKENS,
    build_default_semantic_embedding_model_manifest,
    get_semantic_embedding_model_manifest,
)

__all__ = [
    "SemanticEmbeddingArtifact",
    "SemanticEmbeddingModelHealth",
    "SemanticEmbeddingModelManifest",
    "SEMANTIC_MODEL_CHUNKING_VERSION",
    "SEMANTIC_MODEL_EMBEDDING_DIMENSION",
    "SEMANTIC_MODEL_MAX_TOKENS",
    "build_default_semantic_embedding_model_manifest",
    "get_semantic_embedding_model_manifest",
]
