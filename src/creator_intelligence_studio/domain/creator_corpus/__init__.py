"""Dominio del Creator Corpus."""

from .entities import (
    CorpusDocument,
    CorpusDocumentVersion,
    CorpusProvenanceEdge,
    CorpusSegment,
    CorpusSourceAsset,
)
from .ingestion import (
    CorpusEligibility,
    CorpusIngestionRequest,
    CorpusIngestionResult,
    CorpusTextNormalizationResult,
)
from .repositories import CreatorCorpusRepository
from .services import (
    build_corpus_identity_fingerprint,
    build_corpus_provenance_fingerprint,
    build_corpus_text_fingerprint,
)
from .value_objects import (
    CorpusDocumentStatus,
    CorpusDocumentType,
    CorpusProvenanceRelationType,
    CorpusSourceAssetStatus,
    CorpusSourceType,
    CorpusAuthorshipClass,
    CorpusIngestionPolicy,
    CorpusVersionSourceKind,
    TEXT_NORMALIZATION_VERSION,
)

__all__ = [
    "CorpusDocument",
    "CorpusDocumentStatus",
    "CorpusDocumentType",
    "CorpusDocumentVersion",
    "CorpusEligibility",
    "CorpusProvenanceEdge",
    "CorpusProvenanceRelationType",
    "CorpusIngestionPolicy",
    "CorpusIngestionRequest",
    "CorpusIngestionResult",
    "CorpusSegment",
    "CorpusSourceAsset",
    "CorpusSourceAssetStatus",
    "CorpusSourceType",
    "CorpusAuthorshipClass",
    "CorpusVersionSourceKind",
    "CreatorCorpusRepository",
    "build_corpus_identity_fingerprint",
    "build_corpus_provenance_fingerprint",
    "build_corpus_text_fingerprint",
    "CorpusTextNormalizationResult",
    "TEXT_NORMALIZATION_VERSION",
]
