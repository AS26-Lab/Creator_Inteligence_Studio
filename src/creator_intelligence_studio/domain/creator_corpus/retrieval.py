"""Contratos de recuperacion local del Creator Corpus."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from creator_intelligence_studio.shared.dates import to_iso_z

from .value_objects import CorpusAuthorshipClass, CorpusDocumentStatus, CorpusDocumentType


class CorpusRetrievalSort(str, Enum):
    RELEVANCE = "relevance"
    UPDATED_DESC = "updated_desc"
    CREATED_DESC = "created_desc"
    TITLE = "title"


@dataclass(frozen=True, slots=True)
class CorpusRetrievalQuery:
    creator_id: str
    query_text: str | None = None
    project_id: str | None = None
    document_types: tuple[CorpusDocumentType | str, ...] = ()
    authorship_classes: tuple[CorpusAuthorshipClass | str, ...] = ()
    languages: tuple[str, ...] = ()
    statuses: tuple[CorpusDocumentStatus | str, ...] = ()
    retrieval_eligible_only: bool = True
    current_versions_only: bool = True
    date_from: datetime | None = None
    date_to: datetime | None = None
    source_asset_id: str | None = None
    document_id: str | None = None
    segment_id: str | None = None
    limit: int = 20
    offset: int = 0
    sort: CorpusRetrievalSort = CorpusRetrievalSort.RELEVANCE

    def to_dict(self) -> dict[str, Any]:
        return {
            "creator_id": self.creator_id,
            "query_text": self.query_text,
            "project_id": self.project_id,
            "document_types": [item.value if hasattr(item, "value") else str(item) for item in self.document_types],
            "authorship_classes": [item.value if hasattr(item, "value") else str(item) for item in self.authorship_classes],
            "languages": list(self.languages),
            "statuses": [item.value if hasattr(item, "value") else str(item) for item in self.statuses],
            "retrieval_eligible_only": self.retrieval_eligible_only,
            "current_versions_only": self.current_versions_only,
            "date_from": to_iso_z(self.date_from),
            "date_to": to_iso_z(self.date_to),
            "source_asset_id": self.source_asset_id,
            "document_id": self.document_id,
            "segment_id": self.segment_id,
            "limit": self.limit,
            "offset": self.offset,
            "sort": self.sort.value,
        }


@dataclass(frozen=True, slots=True)
class CorpusRetrievalResultItem:
    creator_id: str
    project_id: str | None
    document_id: str
    version_id: str
    segment_id: str | None
    row_kind: str
    document_type: CorpusDocumentType
    title: str
    language: str | None
    authorship_class: CorpusAuthorshipClass
    source_kind: str
    source_asset_id: str | None
    status: CorpusDocumentStatus
    text: str
    snippet: str
    provenance_summary: str
    retrieval_eligible: bool
    voice_learning_eligible: bool
    is_current_version: bool
    version_number: int
    segment_start_seconds: float | None
    segment_end_seconds: float | None
    segment_confidence: float | None
    segment_review_state: str | None
    quality_flags: tuple[str, ...]
    relevance_score: float
    relevance_reason: str
    match_reasons: tuple[str, ...]
    created_at: datetime
    updated_at: datetime
    version_created_at: datetime
    source_segment_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "creator_id": self.creator_id,
            "project_id": self.project_id,
            "document_id": self.document_id,
            "version_id": self.version_id,
            "segment_id": self.segment_id,
            "source_segment_ids": list(self.source_segment_ids),
            "row_kind": self.row_kind,
            "document_type": self.document_type.value,
            "title": self.title,
            "language": self.language,
            "authorship_class": self.authorship_class.value,
            "source_kind": self.source_kind,
            "source_asset_id": self.source_asset_id,
            "status": self.status.value,
            "text": self.text,
            "snippet": self.snippet,
            "provenance_summary": self.provenance_summary,
            "retrieval_eligible": self.retrieval_eligible,
            "voice_learning_eligible": self.voice_learning_eligible,
            "is_current_version": self.is_current_version,
            "version_number": self.version_number,
            "segment_start_seconds": self.segment_start_seconds,
            "segment_end_seconds": self.segment_end_seconds,
            "segment_confidence": self.segment_confidence,
            "segment_review_state": self.segment_review_state,
            "quality_flags": list(self.quality_flags),
            "relevance_score": self.relevance_score,
            "relevance_reason": self.relevance_reason,
            "match_reasons": list(self.match_reasons),
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
            "version_created_at": to_iso_z(self.version_created_at),
        }


@dataclass(frozen=True, slots=True)
class CorpusRetrievalIndexHealth:
    creator_id: str | None
    supports_fts5: bool
    document_count: int
    version_count: int
    segment_count: int
    indexed_row_count: int
    indexed_document_row_count: int
    indexed_segment_row_count: int
    expected_row_count: int
    missing_row_count: int
    stale_row_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "creator_id": self.creator_id,
            "supports_fts5": self.supports_fts5,
            "document_count": self.document_count,
            "version_count": self.version_count,
            "segment_count": self.segment_count,
            "indexed_row_count": self.indexed_row_count,
            "indexed_document_row_count": self.indexed_document_row_count,
            "indexed_segment_row_count": self.indexed_segment_row_count,
            "expected_row_count": self.expected_row_count,
            "missing_row_count": self.missing_row_count,
            "stale_row_count": self.stale_row_count,
        }


@dataclass(frozen=True, slots=True)
class CorpusRetrievalResult:
    query: CorpusRetrievalQuery
    total_count: int
    returned_count: int
    results: tuple[CorpusRetrievalResultItem, ...]
    index_health: CorpusRetrievalIndexHealth | None
    retrieval_mode_used: str = "lexical"

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query.to_dict(),
            "total_count": self.total_count,
            "returned_count": self.returned_count,
            "results": [item.to_dict() for item in self.results],
            "index_health": self.index_health.to_dict() if self.index_health else None,
            "retrieval_mode_used": self.retrieval_mode_used,
        }
