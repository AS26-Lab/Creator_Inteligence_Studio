"""Allowlist y conversion de features para entrenamiento personalizado."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from creator_intelligence_studio.domain.personalization_data.entities import CreatorFeatureSchema, CreatorDatasetExample
from creator_intelligence_studio.domain.personalization_models.errors import PersonalizationModelValidationError


FEATURE_ALLOWLIST_VERSION = "1"
FEATURE_SCHEMA_COMPATIBLE_VERSIONS = {"1"}

_INCLUDED_FEATURES = {
    "source_score",
    "source_confidence",
    "combined_activity_score",
    "transition_score",
    "novelty_score",
    "candidate_duration_seconds",
    "candidate_duration_ratio",
    "relative_start_seconds",
    "relative_end_seconds",
    "distance_to_start_seconds",
    "distance_to_end_seconds",
    "word_count",
    "word_density",
    "has_transcription",
    "transcription_segment_count",
    "nearby_candidate_count",
    "source_available_transcription",
    "source_available_acoustic",
    "source_available_visual",
    "multimodal_window_count",
    "multimodal_window_speech_ratio",
    "multimodal_window_silence_ratio",
    "multimodal_window_speech_rate",
    "multimodal_window_acoustic_energy",
    "multimodal_window_acoustic_change",
    "multimodal_window_visual_motion",
    "multimodal_window_visual_change",
    "multimodal_window_brightness",
    "multimodal_window_cut_count",
    "multimodal_window_acoustic_event_count",
    "multimodal_window_visual_event_count",
    "rank_score",
    "quality_score",
    "diversity_score",
    "overlap_penalty",
    "duration_score",
    "opening_score",
    "closing_score",
    "speech_score",
    "visual_score",
    "acoustic_score",
    "evidence_strength_score",
    "acoustic_average_energy",
    "acoustic_peak_energy",
    "acoustic_dynamic_range",
    "acoustic_pause_count",
    "acoustic_longest_pause_seconds",
    "acoustic_words_per_minute",
    "visual_average_brightness",
    "visual_average_contrast",
    "visual_average_motion",
    "visual_peak_motion",
    "visual_detected_cut_count",
    "visual_detected_scene_count",
    "collections_count",
    "review_event_count",
    "manual_bounds_changed",
    "candidate_conflict_count",
}

_EXCLUDED_FEATURES = {
    "candidate_type",
    "profile",
    "current_review_status",
    "current_rating",
}

_FEATURE_REASONS = {
    "candidate_type": "categorical feature not used in baseline v1",
    "profile": "leaks ranker configuration and is not a source signal",
    "current_review_status": "human decision metadata excluded to avoid leakage",
    "current_rating": "human decision metadata excluded to avoid leakage",
}


@dataclass(frozen=True, slots=True)
class FeaturePolicyEntry:
    name: str
    included: bool
    origin: str
    reason: str
    transformation: str
    missing_policy: str
    expected_range: tuple[float | int | None, float | int | None] | None

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "included": self.included,
            "origin": self.origin,
            "reason": self.reason,
            "transformation": self.transformation,
            "missing_policy": self.missing_policy,
            "expected_range": list(self.expected_range) if self.expected_range is not None else None,
        }


@dataclass(frozen=True, slots=True)
class FeaturePolicyReport:
    schema_version: str
    allowlist_version: str
    entries: tuple[FeaturePolicyEntry, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "allowlist_version": self.allowlist_version,
            "entries": [entry.to_dict() for entry in self.entries],
        }


@dataclass(frozen=True, slots=True)
class PersonalizationTrainingDataset:
    feature_names: tuple[str, ...]
    feature_policy: FeaturePolicyReport
    train_examples: tuple[CreatorDatasetExample, ...]
    validation_examples: tuple[CreatorDatasetExample, ...]
    test_examples: tuple[CreatorDatasetExample, ...]
    excluded_examples: tuple[CreatorDatasetExample, ...]
    X_train: np.ndarray
    y_train: np.ndarray
    sample_weight_train: np.ndarray
    X_validation: np.ndarray
    y_validation: np.ndarray
    sample_weight_validation: np.ndarray
    X_test: np.ndarray
    y_test: np.ndarray
    sample_weight_test: np.ndarray
    excluded_count: int
    label_counts: dict[str, int]
    split_counts: dict[str, int]
    missing_feature_count: int
    unexpected_feature_names: tuple[str, ...]

    @property
    def has_validation(self) -> bool:
        return self.X_validation.size > 0 and self.y_validation.size > 0

    @property
    def has_test(self) -> bool:
        return self.X_test.size > 0 and self.y_test.size > 0


def build_feature_policy(feature_schema: CreatorFeatureSchema) -> FeaturePolicyReport:
    if feature_schema.schema_version not in FEATURE_SCHEMA_COMPATIBLE_VERSIONS:
        raise PersonalizationModelValidationError(
            f"Esquema de features incompatible: {feature_schema.schema_version}"
        )
    entries: list[FeaturePolicyEntry] = []
    for name in feature_schema.feature_names:
        definition = feature_schema.feature_definitions.get(name, {})
        included = name in _INCLUDED_FEATURES
        reason = "included in baseline v1" if included else _FEATURE_REASONS.get(name, "excluded in baseline v1")
        entries.append(
            FeaturePolicyEntry(
                name=name,
                included=included,
                origin=str(definition.get("origin") or "unknown"),
                reason=reason,
                transformation="numeric_identity" if included else "excluded",
                missing_policy="impute_median" if included else "preserve_null",
                expected_range=tuple(definition.get("range")) if definition.get("range") else None,
            )
        )
    unexpected = sorted(set(feature_schema.feature_names) - set(entry.name for entry in entries))
    if unexpected:
        raise PersonalizationModelValidationError(f"Features inesperadas: {unexpected}")
    return FeaturePolicyReport(
        schema_version=feature_schema.schema_version,
        allowlist_version=FEATURE_ALLOWLIST_VERSION,
        entries=tuple(entries),
    )


def build_feature_policy_report(feature_schema: CreatorFeatureSchema) -> FeaturePolicyReport:
    return build_feature_policy(feature_schema)


def _coerce_numeric(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        if np.isnan(value) or np.isinf(value):
            return None
        return float(value)
    try:
        coerced = float(value)
    except (TypeError, ValueError):
        return None
    if np.isnan(coerced) or np.isinf(coerced):
        return None
    return coerced


def build_feature_matrix(
    examples: tuple[CreatorDatasetExample, ...],
    feature_policy: FeaturePolicyReport,
    *,
    strict: bool = True,
) -> tuple[np.ndarray, tuple[str, ...], int, tuple[str, ...]]:
    included_entries = [entry for entry in feature_policy.entries if entry.included]
    feature_names = tuple(entry.name for entry in included_entries)
    unexpected_feature_names: set[str] = set()
    rows: list[list[float | None]] = []
    missing_feature_count = 0
    known_features = {entry.name for entry in feature_policy.entries}
    for example in examples:
        if strict:
            unexpected = set(example.feature_vector) - known_features
            if unexpected:
                unexpected_feature_names.update(unexpected)
        row: list[float | None] = []
        for entry in included_entries:
            value = _coerce_numeric(example.feature_vector.get(entry.name))
            if value is None:
                missing_feature_count += 1
            row.append(value)
        rows.append(row)
    if strict and unexpected_feature_names:
        raise PersonalizationModelValidationError(
            f"Features inesperadas en el dataset: {sorted(unexpected_feature_names)}"
        )
    if not rows:
        matrix = np.empty((0, len(feature_names)), dtype=float)
    else:
        matrix = np.array([[np.nan if value is None else float(value) for value in row] for row in rows], dtype=float)
    if matrix.size and not np.isfinite(matrix[np.isfinite(matrix)]).all():
        # allow NaN for imputer, but reject infinities
        if np.isinf(matrix).any():
            raise PersonalizationModelValidationError("Se detectaron infinitos en las features.")
    return matrix, feature_names, missing_feature_count, tuple(sorted(unexpected_feature_names))
