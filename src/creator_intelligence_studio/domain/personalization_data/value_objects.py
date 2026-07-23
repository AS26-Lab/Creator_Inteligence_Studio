"""Objetos de valor para la preparacion de datos de personalizacion."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .errors import PersonalizationDataValidationError


class PersonalizationDatasetStatus(str, Enum):
    BUILDING = "building"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"
    STALE = "stale"
    ARCHIVED = "archived"


class PersonalizationSplitName(str, Enum):
    TRAIN = "train"
    VALIDATION = "validation"
    TEST = "test"
    EXCLUDED = "excluded"


class PersonalizationReadinessStatus(str, Enum):
    NOT_READY = "not_ready"
    COLLECTING_FEEDBACK = "collecting_feedback"
    LIMITED = "limited"
    READY_FOR_BASELINE = "ready_for_baseline"
    READY_FOR_EVALUATION = "ready_for_evaluation"
    READY_FOR_PERSONALIZED_TRAINING = "ready_for_personalized_training"
    BLOCKED_BY_QUALITY = "blocked_by_quality"
    BLOCKED_BY_CONFLICTS = "blocked_by_conflicts"


class PersonalizationLabel(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL_OR_UNCERTAIN = "neutral_or_uncertain"
    EXCLUDED = "excluded"


@dataclass(frozen=True, slots=True)
class PersonalizationDatasetOptions:
    """Configuracion reproducible para datasets de personalizacion."""

    dataset_version_prefix: str = "v1"
    feature_schema_version: str = "1"
    label_schema_version: str = "1"
    train_ratio: float = 0.7
    validation_ratio: float = 0.15
    test_ratio: float = 0.15
    minimum_examples_for_baseline: int = 10
    minimum_reviewed_examples_for_baseline: int = 8
    minimum_positive_examples: int = 2
    minimum_negative_examples: int = 2
    minimum_examples_for_evaluation: int = 20
    minimum_videos_for_evaluation: int = 3
    minimum_examples_for_personalized_training: int = 50
    max_duplicate_ratio: float = 0.20
    max_overlap_ratio: float = 0.25
    max_missing_feature_ratio: float = 0.20
    max_conflict_ratio: float = 0.15
    max_leakage_risk: float = 0.25
    max_excluded_ratio: float = 0.40
    split_seed: int = 17
    transcript_excerpt_limit: int = 240
    allow_sensitive_excerpt: bool = False
    conflict_policy: str = "excluded"

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_version_prefix": self.dataset_version_prefix,
            "feature_schema_version": self.feature_schema_version,
            "label_schema_version": self.label_schema_version,
            "train_ratio": self.train_ratio,
            "validation_ratio": self.validation_ratio,
            "test_ratio": self.test_ratio,
            "minimum_examples_for_baseline": self.minimum_examples_for_baseline,
            "minimum_reviewed_examples_for_baseline": self.minimum_reviewed_examples_for_baseline,
            "minimum_positive_examples": self.minimum_positive_examples,
            "minimum_negative_examples": self.minimum_negative_examples,
            "minimum_examples_for_evaluation": self.minimum_examples_for_evaluation,
            "minimum_videos_for_evaluation": self.minimum_videos_for_evaluation,
            "minimum_examples_for_personalized_training": self.minimum_examples_for_personalized_training,
            "max_duplicate_ratio": self.max_duplicate_ratio,
            "max_overlap_ratio": self.max_overlap_ratio,
            "max_missing_feature_ratio": self.max_missing_feature_ratio,
            "max_conflict_ratio": self.max_conflict_ratio,
            "max_leakage_risk": self.max_leakage_risk,
            "max_excluded_ratio": self.max_excluded_ratio,
            "split_seed": self.split_seed,
            "transcript_excerpt_limit": self.transcript_excerpt_limit,
            "allow_sensitive_excerpt": self.allow_sensitive_excerpt,
            "conflict_policy": self.conflict_policy,
        }


def normalize_personalization_dataset_options(options: PersonalizationDatasetOptions) -> PersonalizationDatasetOptions:
    if not options.dataset_version_prefix.strip():
        raise PersonalizationDataValidationError("dataset_version_prefix no puede estar vacio.")
    if not options.feature_schema_version.strip():
        raise PersonalizationDataValidationError("feature_schema_version no puede estar vacio.")
    if not options.label_schema_version.strip():
        raise PersonalizationDataValidationError("label_schema_version no puede estar vacio.")
    if options.train_ratio < 0 or options.validation_ratio < 0 or options.test_ratio < 0:
        raise PersonalizationDataValidationError("Los splits no pueden ser negativos.")
    split_total = options.train_ratio + options.validation_ratio + options.test_ratio
    if split_total <= 0:
        raise PersonalizationDataValidationError("La suma de los splits debe ser mayor que cero.")
    if options.minimum_examples_for_baseline < 0:
        raise PersonalizationDataValidationError("minimum_examples_for_baseline no puede ser negativo.")
    if options.minimum_reviewed_examples_for_baseline < 0:
        raise PersonalizationDataValidationError("minimum_reviewed_examples_for_baseline no puede ser negativo.")
    if options.minimum_positive_examples < 0 or options.minimum_negative_examples < 0:
        raise PersonalizationDataValidationError("Los minimos de positivos y negativos no pueden ser negativos.")
    if options.minimum_examples_for_evaluation < 0 or options.minimum_videos_for_evaluation < 0:
        raise PersonalizationDataValidationError("Los minimos de evaluacion no pueden ser negativos.")
    if options.minimum_examples_for_personalized_training < 0:
        raise PersonalizationDataValidationError("minimum_examples_for_personalized_training no puede ser negativo.")
    for value in (
        options.max_duplicate_ratio,
        options.max_overlap_ratio,
        options.max_missing_feature_ratio,
        options.max_conflict_ratio,
        options.max_leakage_risk,
        options.max_excluded_ratio,
    ):
        if not 0.0 <= value <= 1.0:
            raise PersonalizationDataValidationError("Los umbrales porcentuales deben estar entre 0 y 1.")
    if options.split_seed < 0:
        raise PersonalizationDataValidationError("split_seed no puede ser negativo.")
    if options.transcript_excerpt_limit < 0:
        raise PersonalizationDataValidationError("transcript_excerpt_limit no puede ser negativo.")
    if options.conflict_policy not in {"excluded", "neutral_or_uncertain"}:
        raise PersonalizationDataValidationError("conflict_policy no es valido.")
    return options
