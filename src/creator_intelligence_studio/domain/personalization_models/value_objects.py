"""Objetos de valor para modelos personalizados por creador."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .errors import PersonalizationModelValidationError


class PersonalizationModelTrainingStatus(str, Enum):
    QUEUED = "queued"
    VALIDATING_DATASET = "validating_dataset"
    PREPARING_FEATURES = "preparing_features"
    TRAINING = "training"
    EVALUATING = "evaluating"
    SAVING_ARTIFACT = "saving_artifact"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


class PersonalizationModelRegistryStatus(str, Enum):
    CANDIDATE = "candidate"
    ACTIVE = "active"
    INACTIVE = "inactive"
    RETIRED = "retired"
    INVALID = "invalid"
    ARTIFACT_MISSING = "artifact_missing"
    INCOMPATIBLE = "incompatible"


class PersonalizationModelFamily(str, Enum):
    LOGISTIC_REGRESSION = "logistic_regression"


@dataclass(frozen=True, slots=True)
class PersonalizationModelOptions:
    """Configuracion reproducible del baseline personalizado."""

    model_family: PersonalizationModelFamily = PersonalizationModelFamily.LOGISTIC_REGRESSION
    model_version: str = "v1"
    trainer_version: str = "1"
    feature_schema_version: str = "1"
    label_schema_version: str = "1"
    regularization_c: float = 1.0
    max_iter: int = 1000
    random_seed: int = 17
    decision_threshold: float = 0.5
    minimum_examples_for_baseline: int = 2
    max_leakage_risk: float = 0.95
    class_weight_mode: str = "balanced"
    metric_primary: str = "balanced_accuracy"
    strict_feature_policy: bool = True
    allow_train_diagnostics: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_family": self.model_family.value,
            "model_version": self.model_version,
            "trainer_version": self.trainer_version,
            "feature_schema_version": self.feature_schema_version,
            "label_schema_version": self.label_schema_version,
            "regularization_c": self.regularization_c,
            "max_iter": self.max_iter,
            "random_seed": self.random_seed,
            "decision_threshold": self.decision_threshold,
            "minimum_examples_for_baseline": self.minimum_examples_for_baseline,
            "max_leakage_risk": self.max_leakage_risk,
            "class_weight_mode": self.class_weight_mode,
            "metric_primary": self.metric_primary,
            "strict_feature_policy": self.strict_feature_policy,
            "allow_train_diagnostics": self.allow_train_diagnostics,
        }


def normalize_personalization_model_options(options: PersonalizationModelOptions) -> PersonalizationModelOptions:
    if options.regularization_c <= 0:
        raise PersonalizationModelValidationError("regularization_c debe ser mayor que cero.")
    if options.max_iter <= 0:
        raise PersonalizationModelValidationError("max_iter debe ser mayor que cero.")
    if not 0.0 <= options.decision_threshold <= 1.0:
        raise PersonalizationModelValidationError("decision_threshold debe estar entre 0 y 1.")
    if options.minimum_examples_for_baseline <= 0:
        raise PersonalizationModelValidationError("minimum_examples_for_baseline debe ser mayor que cero.")
    if not 0.0 <= options.max_leakage_risk <= 1.0:
        raise PersonalizationModelValidationError("max_leakage_risk debe estar entre 0 y 1.")
    if options.random_seed < 0:
        raise PersonalizationModelValidationError("random_seed no puede ser negativo.")
    if options.metric_primary not in {"balanced_accuracy", "f1", "precision", "recall"}:
        raise PersonalizationModelValidationError("metric_primary no es valido.")
    if options.class_weight_mode not in {"balanced", "none"}:
        raise PersonalizationModelValidationError("class_weight_mode no es valido.")
    return options
