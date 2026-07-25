"""Entidades persistidas de Creator Language Analysis."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from creator_intelligence_studio.shared.dates import to_iso_z

from .narrative_types import NarrativeProfileSummary
from .value_objects import (
    CreatorLanguageAnalysisRunStatus,
    CreatorLanguageCandidateStatus,
    CreatorLanguageConfidenceLevel,
    CreatorLanguageCorpusSourceIncludeStatus,
    CreatorLanguageCorpusStatus,
    CreatorLanguagePatternStatus,
    CreatorLanguagePatternType,
    CreatorLanguageScope,
    CreatorLanguageSourceType,
    CreatorLanguageTargetMemoryType,
)


@dataclass(frozen=True, slots=True)
class CreatorLanguageCorpus:
    id: str
    creator_id: str
    name: str
    description: str | None
    language: str
    platform: str | None
    content_type: str | None
    topic: str | None
    status: CreatorLanguageCorpusStatus
    source_count: int
    token_count: int
    duration_seconds: float | None
    source_fingerprint: str
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "name": self.name,
            "description": self.description,
            "language": self.language,
            "platform": self.platform,
            "content_type": self.content_type,
            "topic": self.topic,
            "status": self.status.value,
            "source_count": self.source_count,
            "token_count": self.token_count,
            "duration_seconds": self.duration_seconds,
            "source_fingerprint": self.source_fingerprint,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class CreatorLanguageCorpusSource:
    id: str
    corpus_id: str
    source_type: CreatorLanguageSourceType
    source_id: str
    video_asset_id: str | None
    publication_id: str | None
    transcription_id: str | None
    segment_id: str | None
    start_seconds: float | None
    end_seconds: float | None
    text_snapshot: str
    language: str
    platform: str | None
    content_type: str | None
    topic: str | None
    include_status: CreatorLanguageCorpusSourceIncludeStatus
    exclusion_reason: str | None
    created_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "corpus_id": self.corpus_id,
            "source_type": self.source_type.value,
            "source_id": self.source_id,
            "video_asset_id": self.video_asset_id,
            "publication_id": self.publication_id,
            "transcription_id": self.transcription_id,
            "segment_id": self.segment_id,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "text_snapshot": self.text_snapshot,
            "language": self.language,
            "platform": self.platform,
            "content_type": self.content_type,
            "topic": self.topic,
            "include_status": self.include_status.value,
            "exclusion_reason": self.exclusion_reason,
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class CreatorLanguageAnalysisRun:
    id: str
    creator_id: str
    corpus_id: str
    analysis_version: str
    status: CreatorLanguageAnalysisRunStatus
    configuration_json: str
    source_fingerprint: str
    source_count: int
    token_count: int
    sentence_count: int
    warning_count: int
    started_at: datetime | None
    completed_at: datetime | None
    error_code: str | None
    error_message: str | None
    created_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "corpus_id": self.corpus_id,
            "analysis_version": self.analysis_version,
            "status": self.status.value,
            "configuration_json": self.configuration_json,
            "source_fingerprint": self.source_fingerprint,
            "source_count": self.source_count,
            "token_count": self.token_count,
            "sentence_count": self.sentence_count,
            "warning_count": self.warning_count,
            "started_at": to_iso_z(self.started_at),
            "completed_at": to_iso_z(self.completed_at),
            "error_code": self.error_code,
            "error_message": self.error_message,
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class CreatorLanguageMetric:
    id: str
    analysis_run_id: str
    metric_key: str
    metric_group: str
    numeric_value: float | None
    text_value: str | None
    unit: str
    scope: CreatorLanguageScope
    platform: str | None
    content_type: str | None
    topic: str | None
    sample_size: int
    confidence_level: CreatorLanguageConfidenceLevel
    warning_codes_json: str
    created_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "analysis_run_id": self.analysis_run_id,
            "metric_key": self.metric_key,
            "metric_group": self.metric_group,
            "numeric_value": self.numeric_value,
            "text_value": self.text_value,
            "unit": self.unit,
            "scope": self.scope.value,
            "platform": self.platform,
            "content_type": self.content_type,
            "topic": self.topic,
            "sample_size": self.sample_size,
            "confidence_level": self.confidence_level.value,
            "warning_codes_json": self.warning_codes_json,
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class CreatorLanguagePattern:
    id: str
    analysis_run_id: str
    creator_id: str
    pattern_type: CreatorLanguagePatternType
    pattern_key: str
    title: str
    description: str
    scope: CreatorLanguageScope
    platform: str | None
    content_type: str | None
    topic: str | None
    frequency_count: int
    supporting_example_count: int
    contradicting_example_count: int
    confidence_level: CreatorLanguageConfidenceLevel
    confidence_score: float | None
    status: CreatorLanguagePatternStatus
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "analysis_run_id": self.analysis_run_id,
            "creator_id": self.creator_id,
            "pattern_type": self.pattern_type.value,
            "pattern_key": self.pattern_key,
            "title": self.title,
            "description": self.description,
            "scope": self.scope.value,
            "platform": self.platform,
            "content_type": self.content_type,
            "topic": self.topic,
            "frequency_count": self.frequency_count,
            "supporting_example_count": self.supporting_example_count,
            "contradicting_example_count": self.contradicting_example_count,
            "confidence_level": self.confidence_level.value,
            "confidence_score": self.confidence_score,
            "status": self.status.value,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class CreatorLanguagePatternEvidence:
    id: str
    pattern_id: str
    corpus_source_id: str
    start_seconds: float | None
    end_seconds: float | None
    quoted_text: str
    normalized_text: str
    supports_pattern: bool
    weight: float
    notes: str | None
    created_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "pattern_id": self.pattern_id,
            "corpus_source_id": self.corpus_source_id,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "quoted_text": self.quoted_text,
            "normalized_text": self.normalized_text,
            "supports_pattern": self.supports_pattern,
            "weight": self.weight,
            "notes": self.notes,
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class CreatorNarrativeProfile:
    id: str
    creator_id: str
    analysis_run_id: str
    profile_version: int
    status: str
    summary: str
    opening_profile_json: str
    development_profile_json: str
    explanation_profile_json: str
    humor_profile_json: str
    pacing_profile_json: str
    closing_profile_json: str
    platform_differences_json: str
    content_type_differences_json: str
    limitations_json: str
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "analysis_run_id": self.analysis_run_id,
            "profile_version": self.profile_version,
            "status": self.status,
            "summary": self.summary,
            "opening_profile_json": self.opening_profile_json,
            "development_profile_json": self.development_profile_json,
            "explanation_profile_json": self.explanation_profile_json,
            "humor_profile_json": self.humor_profile_json,
            "pacing_profile_json": self.pacing_profile_json,
            "closing_profile_json": self.closing_profile_json,
            "platform_differences_json": self.platform_differences_json,
            "content_type_differences_json": self.content_type_differences_json,
            "limitations_json": self.limitations_json,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class CreatorLanguageCandidate:
    id: str
    creator_id: str
    analysis_run_id: str
    candidate_type: str
    target_memory_type: CreatorLanguageTargetMemoryType
    proposed_key: str
    proposed_value_json: str
    scope: CreatorLanguageScope
    platform: str | None
    content_type: str | None
    topic: str | None
    evidence_json: str
    confidence_level: CreatorLanguageConfidenceLevel
    status: CreatorLanguageCandidateStatus
    review_reason: str | None
    created_at: datetime
    reviewed_at: datetime | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "analysis_run_id": self.analysis_run_id,
            "candidate_type": self.candidate_type,
            "target_memory_type": self.target_memory_type.value,
            "proposed_key": self.proposed_key,
            "proposed_value_json": self.proposed_value_json,
            "scope": self.scope.value,
            "platform": self.platform,
            "content_type": self.content_type,
            "topic": self.topic,
            "evidence_json": self.evidence_json,
            "confidence_level": self.confidence_level.value,
            "status": self.status.value,
            "review_reason": self.review_reason,
            "created_at": to_iso_z(self.created_at),
            "reviewed_at": to_iso_z(self.reviewed_at),
        }


@dataclass(frozen=True, slots=True)
class CreatorLanguageProfileSnapshot:
    id: str
    creator_id: str
    profile_version: int
    snapshot_json: str
    source_fingerprint: str
    status: str
    created_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "profile_version": self.profile_version,
            "snapshot_json": self.snapshot_json,
            "source_fingerprint": self.source_fingerprint,
            "status": self.status,
            "created_at": to_iso_z(self.created_at),
        }

