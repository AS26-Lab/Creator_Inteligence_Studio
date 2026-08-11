"""Dominio del Creator Corpus."""

from .entities import (
    CorpusDocument,
    CorpusDocumentVersion,
    CorpusProvenanceEdge,
    CorpusSegment,
    CorpusSourceAsset,
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
    CorpusVersionSourceKind,
)

__all__ = [
    "CorpusDocument",
    "CorpusDocumentStatus",
    "CorpusDocumentType",
    "CorpusDocumentVersion",
    "CorpusProvenanceEdge",
    "CorpusProvenanceRelationType",
    "CorpusSegment",
    "CorpusSourceAsset",
    "CorpusSourceAssetStatus",
    "CorpusSourceType",
    "CorpusVersionSourceKind",
    "CreatorCorpusRepository",
    "build_corpus_identity_fingerprint",
    "build_corpus_provenance_fingerprint",
    "build_corpus_text_fingerprint",
]
