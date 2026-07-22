"""Objetos de valor para ranking de clips."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .errors import ClipRankingValidationError


class ClipRankingRunStatus(str, Enum):
    """Estados persistidos de un ranking de clips."""

    NOT_RANKED = "not_ranked"
    QUEUED = "queued"
    SCORING = "scoring"
    ADJUSTING_BORDERS = "adjusting_borders"
    RESOLVING_OVERLAPS = "resolving_overlaps"
    APPLYING_DIVERSITY = "applying_diversity"
    MIGRATING_FEEDBACK = "migrating_feedback"
    SAVING_RESULTS = "saving_results"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    STALE = "stale"


class ClipRankingReviewStatus(str, Enum):
    """Estados humanos de revision."""

    UNREVIEWED = "unreviewed"
    SHORTLISTED = "shortlisted"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"
    DUPLICATE = "duplicate"
    INVALID = "invalid"
    EXPORTED = "exported"


class ClipRankingProfile(str, Enum):
    """Perfiles iniciales de ranking."""

    BALANCED = "balanced"
    SPEECH_FOCUSED = "speech_focused"
    VISUAL_FOCUSED = "visual_focused"
    HIGH_ENERGY = "high_energy"
    STORY_BEATS = "story_beats"


@dataclass(frozen=True, slots=True)
class ClipRankingOptions:
    """Configuracion reproducible del ranking de clips."""

    profile: ClipRankingProfile = ClipRankingProfile.BALANCED
    minimum_duration_seconds: float = 3.0
    recommended_duration_seconds: float = 8.0
    target_short_duration_seconds: float = 15.0
    target_medium_duration_seconds: float = 30.0
    maximum_duration_seconds: float = 90.0
    iou_duplicate_threshold: float = 0.80
    iou_overlap_threshold: float = 0.35
    diversity_min_gap_seconds: float = 8.0
    diversity_window_seconds: float = 30.0
    ranker_version: str = "v1"
    source_fingerprint_version: str = "v1"
    base_score_weight: float = 0.22
    confidence_weight: float = 0.12
    activity_weight: float = 0.12
    novelty_weight: float = 0.10
    transition_weight: float = 0.10
    evidence_weight: float = 0.10
    speech_weight: float = 0.08
    visual_weight: float = 0.08
    acoustic_weight: float = 0.08
    duration_weight: float = 0.04
    overlap_penalty_weight: float = 0.08
    silence_penalty_weight: float = 0.05
    low_activity_penalty_weight: float = 0.05
    missing_source_penalty_weight: float = 0.05
    duplicate_penalty_weight: float = 0.08
    diversity_weight: float = 0.10

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile": self.profile.value,
            "minimum_duration_seconds": self.minimum_duration_seconds,
            "recommended_duration_seconds": self.recommended_duration_seconds,
            "target_short_duration_seconds": self.target_short_duration_seconds,
            "target_medium_duration_seconds": self.target_medium_duration_seconds,
            "maximum_duration_seconds": self.maximum_duration_seconds,
            "iou_duplicate_threshold": self.iou_duplicate_threshold,
            "iou_overlap_threshold": self.iou_overlap_threshold,
            "diversity_min_gap_seconds": self.diversity_min_gap_seconds,
            "diversity_window_seconds": self.diversity_window_seconds,
            "ranker_version": self.ranker_version,
            "source_fingerprint_version": self.source_fingerprint_version,
            "base_score_weight": self.base_score_weight,
            "confidence_weight": self.confidence_weight,
            "activity_weight": self.activity_weight,
            "novelty_weight": self.novelty_weight,
            "transition_weight": self.transition_weight,
            "evidence_weight": self.evidence_weight,
            "speech_weight": self.speech_weight,
            "visual_weight": self.visual_weight,
            "acoustic_weight": self.acoustic_weight,
            "duration_weight": self.duration_weight,
            "overlap_penalty_weight": self.overlap_penalty_weight,
            "silence_penalty_weight": self.silence_penalty_weight,
            "low_activity_penalty_weight": self.low_activity_penalty_weight,
            "missing_source_penalty_weight": self.missing_source_penalty_weight,
            "duplicate_penalty_weight": self.duplicate_penalty_weight,
            "diversity_weight": self.diversity_weight,
        }


def normalize_clip_ranking_config(options: ClipRankingOptions) -> ClipRankingOptions:
    """Valida y normaliza la configuracion de ranking."""

    if options.minimum_duration_seconds <= 0:
        raise ClipRankingValidationError("minimum_duration_seconds debe ser mayor que cero.")
    if options.recommended_duration_seconds < options.minimum_duration_seconds:
        raise ClipRankingValidationError("recommended_duration_seconds debe ser mayor o igual que minimum_duration_seconds.")
    if options.target_short_duration_seconds < options.minimum_duration_seconds:
        raise ClipRankingValidationError("target_short_duration_seconds debe ser mayor o igual que minimum_duration_seconds.")
    if options.target_medium_duration_seconds < options.target_short_duration_seconds:
        raise ClipRankingValidationError("target_medium_duration_seconds debe ser mayor o igual que target_short_duration_seconds.")
    if options.maximum_duration_seconds < options.minimum_duration_seconds:
        raise ClipRankingValidationError("maximum_duration_seconds debe ser mayor o igual que minimum_duration_seconds.")
    if not 0.0 <= options.iou_duplicate_threshold <= 1.0:
        raise ClipRankingValidationError("iou_duplicate_threshold debe estar entre 0 y 1.")
    if not 0.0 <= options.iou_overlap_threshold <= 1.0:
        raise ClipRankingValidationError("iou_overlap_threshold debe estar entre 0 y 1.")
    if options.diversity_min_gap_seconds < 0:
        raise ClipRankingValidationError("diversity_min_gap_seconds no puede ser negativo.")
    if options.diversity_window_seconds <= 0:
        raise ClipRankingValidationError("diversity_window_seconds debe ser mayor que cero.")
    if not options.ranker_version.strip():
        raise ClipRankingValidationError("ranker_version no puede estar vacio.")
    if not options.source_fingerprint_version.strip():
        raise ClipRankingValidationError("source_fingerprint_version no puede estar vacio.")
    weights = (
        options.base_score_weight,
        options.confidence_weight,
        options.activity_weight,
        options.novelty_weight,
        options.transition_weight,
        options.evidence_weight,
        options.speech_weight,
        options.visual_weight,
        options.acoustic_weight,
        options.duration_weight,
        options.overlap_penalty_weight,
        options.silence_penalty_weight,
        options.low_activity_penalty_weight,
        options.missing_source_penalty_weight,
        options.duplicate_penalty_weight,
        options.diversity_weight,
    )
    if any(weight < 0 for weight in weights):
        raise ClipRankingValidationError("Los pesos del ranking no pueden ser negativos.")
    return options
