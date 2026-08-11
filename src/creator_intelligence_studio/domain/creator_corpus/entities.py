"""Entidades persistidas del Creator Corpus."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from creator_intelligence_studio.shared.dates import to_iso_z

from .value_objects import (
    CorpusAuthorshipClass,
    CorpusDocumentStatus,
    CorpusDocumentType,
    CorpusProvenanceRelationType,
    CorpusSourceAssetStatus,
    CorpusSourceType,
    CorpusVersionSourceKind,
)


@dataclass(frozen=True, slots=True)
class CorpusSourceAsset:
    id: str
    creator_id: str
    project_id: str | None
    source_type: CorpusSourceType
    original_name: str
    local_path: str | None
    content_hash: str
    size_bytes: int
    mime_type: str | None
    status: CorpusSourceAssetStatus
    source_metadata_json: str
    created_at: datetime
    imported_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "project_id": self.project_id,
            "source_type": self.source_type.value,
            "original_name": self.original_name,
            "local_path": self.local_path,
            "content_hash": self.content_hash,
            "size_bytes": self.size_bytes,
            "mime_type": self.mime_type,
            "status": self.status.value,
            "source_metadata_json": self.source_metadata_json,
            "created_at": to_iso_z(self.created_at),
            "imported_at": to_iso_z(self.imported_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class CorpusDocument:
    id: str
    creator_id: str
    source_asset_id: str | None
    project_id: str | None
    document_type: CorpusDocumentType
    title: str
    language: str | None
    current_version_id: str | None
    status: CorpusDocumentStatus
    document_identity_hash: str
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "source_asset_id": self.source_asset_id,
            "project_id": self.project_id,
            "document_type": self.document_type.value,
            "title": self.title,
            "language": self.language,
            "current_version_id": self.current_version_id,
            "status": self.status.value,
            "document_identity_hash": self.document_identity_hash,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class CorpusDocumentVersion:
    id: str
    document_id: str
    creator_id: str
    version_number: int
    content: str
    content_hash: str
    raw_content: str
    normalized_content: str
    raw_content_hash: str
    normalization_version: str
    authorship_class: CorpusAuthorshipClass
    retrieval_eligible: bool
    voice_learning_eligible: bool
    quality_flags: tuple[str, ...]
    source_kind: CorpusVersionSourceKind
    source_asset_id: str | None
    parent_version_id: str | None
    language: str | None
    created_by: str | None
    metadata_json: str
    created_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "document_id": self.document_id,
            "creator_id": self.creator_id,
            "version_number": self.version_number,
            "content": self.content,
            "content_hash": self.content_hash,
            "raw_content": self.raw_content,
            "normalized_content": self.normalized_content,
            "raw_content_hash": self.raw_content_hash,
            "normalization_version": self.normalization_version,
            "authorship_class": self.authorship_class.value,
            "retrieval_eligible": self.retrieval_eligible,
            "voice_learning_eligible": self.voice_learning_eligible,
            "quality_flags": list(self.quality_flags),
            "source_kind": self.source_kind.value,
            "source_asset_id": self.source_asset_id,
            "parent_version_id": self.parent_version_id,
            "language": self.language,
            "created_by": self.created_by,
            "metadata_json": self.metadata_json,
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class CorpusSegment:
    id: str
    document_version_id: str
    creator_id: str
    sequence: int
    start_seconds: float | None
    end_seconds: float | None
    text: str
    raw_text: str
    confidence: float | None
    review_state: str | None
    normalization_version: str
    retrieval_eligible: bool
    voice_learning_eligible: bool
    quality_flags: tuple[str, ...]
    source_reference_type: str | None
    source_reference_id: str | None
    metadata_json: str
    created_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "document_version_id": self.document_version_id,
            "creator_id": self.creator_id,
            "sequence": self.sequence,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "text": self.text,
            "raw_text": self.raw_text,
            "confidence": self.confidence,
            "review_state": self.review_state,
            "normalization_version": self.normalization_version,
            "retrieval_eligible": self.retrieval_eligible,
            "voice_learning_eligible": self.voice_learning_eligible,
            "quality_flags": list(self.quality_flags),
            "source_reference_type": self.source_reference_type,
            "source_reference_id": self.source_reference_id,
            "metadata_json": self.metadata_json,
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class CorpusProvenanceEdge:
    id: str
    creator_id: str
    parent_type: str
    parent_id: str
    child_version_id: str
    relation_type: CorpusProvenanceRelationType
    metadata_json: str
    created_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "parent_type": self.parent_type,
            "parent_id": self.parent_id,
            "child_version_id": self.child_version_id,
            "relation_type": self.relation_type.value,
            "metadata_json": self.metadata_json,
            "created_at": to_iso_z(self.created_at),
        }
