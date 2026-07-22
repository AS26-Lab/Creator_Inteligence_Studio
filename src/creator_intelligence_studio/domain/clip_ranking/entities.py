"""Entidades persistidas del ranking de clips."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from creator_intelligence_studio.shared.dates import to_iso_z

from .value_objects import ClipRankingReviewStatus, ClipRankingRunStatus


@dataclass(frozen=True, slots=True)
class ClipRankingRun:
    """Registro persistido de un ranking de clips."""

    id: str
    video_asset_id: str
    multimodal_analysis_id: str
    creator_id: str
    project_id: str
    status: ClipRankingRunStatus
    ranker_version: str
    configuration_fingerprint: str
    source_fingerprint: str
    candidate_count: int
    ranked_candidate_count: int
    selected_count: int
    rejected_count: int
    review_count: int
    started_at: datetime
    completed_at: datetime
    warning_code: str | None
    warning_message: str | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "video_asset_id": self.video_asset_id,
            "multimodal_analysis_id": self.multimodal_analysis_id,
            "creator_id": self.creator_id,
            "project_id": self.project_id,
            "status": self.status.value,
            "ranker_version": self.ranker_version,
            "configuration_fingerprint": self.configuration_fingerprint,
            "source_fingerprint": self.source_fingerprint,
            "candidate_count": self.candidate_count,
            "ranked_candidate_count": self.ranked_candidate_count,
            "selected_count": self.selected_count,
            "rejected_count": self.rejected_count,
            "review_count": self.review_count,
            "started_at": to_iso_z(self.started_at),
            "completed_at": to_iso_z(self.completed_at),
            "warning_code": self.warning_code,
            "warning_message": self.warning_message,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class RankedClipCandidate:
    """Candidato rankeado persistido."""

    id: str
    ranking_run_id: str
    multimodal_candidate_id: str
    rank_position: int
    original_start_seconds: float
    original_end_seconds: float
    adjusted_start_seconds: float
    adjusted_end_seconds: float
    duration_seconds: float
    candidate_type: str
    source_score: float
    source_confidence: float
    rank_score: float
    quality_score: float
    diversity_score: float
    overlap_penalty: float
    duration_score: float
    opening_score: float
    closing_score: float
    speech_score: float
    visual_score: float
    acoustic_score: float
    transition_score: float
    novelty_score: float
    evidence_strength_score: float
    review_status: ClipRankingReviewStatus
    user_rating: int | None
    user_note: str | None
    explanation: dict[str, Any] = field(default_factory=dict)
    tags: tuple[str, ...] = field(default_factory=tuple)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "ranking_run_id": self.ranking_run_id,
            "multimodal_candidate_id": self.multimodal_candidate_id,
            "rank_position": self.rank_position,
            "original_start_seconds": self.original_start_seconds,
            "original_end_seconds": self.original_end_seconds,
            "adjusted_start_seconds": self.adjusted_start_seconds,
            "adjusted_end_seconds": self.adjusted_end_seconds,
            "duration_seconds": self.duration_seconds,
            "candidate_type": self.candidate_type,
            "source_score": self.source_score,
            "source_confidence": self.source_confidence,
            "rank_score": self.rank_score,
            "quality_score": self.quality_score,
            "diversity_score": self.diversity_score,
            "overlap_penalty": self.overlap_penalty,
            "duration_score": self.duration_score,
            "opening_score": self.opening_score,
            "closing_score": self.closing_score,
            "speech_score": self.speech_score,
            "visual_score": self.visual_score,
            "acoustic_score": self.acoustic_score,
            "transition_score": self.transition_score,
            "novelty_score": self.novelty_score,
            "evidence_strength_score": self.evidence_strength_score,
            "review_status": self.review_status.value,
            "user_rating": self.user_rating,
            "user_note": self.user_note,
            "explanation": dict(self.explanation),
            "tags": list(self.tags),
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class ClipReviewEvent:
    """Evento historico de revision humana."""

    id: str
    ranked_clip_candidate_id: str
    event_index: int
    action: str
    previous_status: ClipRankingReviewStatus | None
    new_status: ClipRankingReviewStatus | None
    previous_start_seconds: float | None
    previous_end_seconds: float | None
    new_start_seconds: float | None
    new_end_seconds: float | None
    rating: int | None
    note: str | None
    tags: tuple[str, ...] = field(default_factory=tuple)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "ranked_clip_candidate_id": self.ranked_clip_candidate_id,
            "event_index": self.event_index,
            "action": self.action,
            "previous_status": self.previous_status.value if self.previous_status else None,
            "new_status": self.new_status.value if self.new_status else None,
            "previous_start_seconds": self.previous_start_seconds,
            "previous_end_seconds": self.previous_end_seconds,
            "new_start_seconds": self.new_start_seconds,
            "new_end_seconds": self.new_end_seconds,
            "rating": self.rating,
            "note": self.note,
            "tags": list(self.tags),
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class ClipCollection:
    """Coleccion de candidatos seleccionados."""

    id: str
    video_asset_id: str
    name: str
    description: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "video_asset_id": self.video_asset_id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class ClipCollectionItem:
    """Elemento dentro de una coleccion de clips."""

    id: str
    collection_id: str
    ranked_clip_candidate_id: str
    item_index: int
    custom_title: str | None
    custom_note: str | None
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "collection_id": self.collection_id,
            "ranked_clip_candidate_id": self.ranked_clip_candidate_id,
            "item_index": self.item_index,
            "custom_title": self.custom_title,
            "custom_note": self.custom_note,
            "created_at": to_iso_z(self.created_at),
        }
