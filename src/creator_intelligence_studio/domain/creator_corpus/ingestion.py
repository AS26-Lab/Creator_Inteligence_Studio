"""Contratos de ingesta del Creator Corpus."""

from __future__ import annotations

from dataclasses import dataclass

from .value_objects import (
    CorpusAuthorshipClass,
    CorpusIngestionPolicy,
)


@dataclass(frozen=True, slots=True)
class CorpusTextNormalizationResult:
    raw_content: str
    normalized_content: str
    normalization_version: str
    raw_content_hash: str
    normalized_content_hash: str
    quality_flags: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "raw_content": self.raw_content,
            "normalized_content": self.normalized_content,
            "normalization_version": self.normalization_version,
            "raw_content_hash": self.raw_content_hash,
            "normalized_content_hash": self.normalized_content_hash,
            "quality_flags": list(self.quality_flags),
        }


@dataclass(frozen=True, slots=True)
class CorpusEligibility:
    retrieval_eligible: bool
    voice_learning_eligible: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "retrieval_eligible": self.retrieval_eligible,
            "voice_learning_eligible": self.voice_learning_eligible,
        }


@dataclass(frozen=True, slots=True)
class CorpusIngestionRequest:
    creator_id: str
    source_type: str
    source_reference: str | None
    document_type: str
    title: str
    language: str | None
    content: str
    segments: tuple[dict[str, object], ...] = ()
    source_kind: str = "import"
    project_id: str | None = None
    metadata: dict[str, object] | None = None
    ingestion_policy: CorpusIngestionPolicy = CorpusIngestionPolicy.SKIP_IF_DUPLICATE
    source_asset_id: str | None = None
    created_by: str | None = "system"
    authorship_class: CorpusAuthorshipClass | None = None
    promote_current: bool | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "creator_id": self.creator_id,
            "source_type": self.source_type,
            "source_reference": self.source_reference,
            "document_type": self.document_type,
            "title": self.title,
            "language": self.language,
            "content": self.content,
            "segments": [dict(segment) for segment in self.segments],
            "source_kind": self.source_kind,
            "project_id": self.project_id,
            "metadata": self.metadata or {},
            "ingestion_policy": self.ingestion_policy.value,
            "source_asset_id": self.source_asset_id,
            "created_by": self.created_by,
            "authorship_class": self.authorship_class.value if self.authorship_class else None,
            "promote_current": self.promote_current,
        }


@dataclass(frozen=True, slots=True)
class CorpusIngestionResult:
    creator_id: str
    document_id: str
    version_id: str
    source_asset_id: str | None
    created_new_document: bool
    created_new_version: bool
    deduplicated: bool
    normalization: CorpusTextNormalizationResult
    eligibility: CorpusEligibility
    quality_flags: tuple[str, ...]
    title: str
    document_type: str
    source_kind: str
    source_reference: str | None
    project_id: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "creator_id": self.creator_id,
            "document_id": self.document_id,
            "version_id": self.version_id,
            "source_asset_id": self.source_asset_id,
            "created_new_document": self.created_new_document,
            "created_new_version": self.created_new_version,
            "deduplicated": self.deduplicated,
            "normalization": self.normalization.to_dict(),
            "eligibility": self.eligibility.to_dict(),
            "quality_flags": list(self.quality_flags),
            "title": self.title,
            "document_type": self.document_type,
            "source_kind": self.source_kind,
            "source_reference": self.source_reference,
            "project_id": self.project_id,
        }
