"""Infraestructura para modelos personalizados por creador."""

from .artifact_store import (
    PersonalizationModelArtifact,
    PersonalizationModelManifest,
    PersonalizationModelManifestVersion,
    load_model_artifact,
    save_model_artifact,
    verify_model_artifact_path,
)
from .baseline_comparator import BaselineComparisonReport, build_reference_baselines
from .dataset_loader import PersonalizationTrainingDataset, load_training_dataset
from .evaluator import EvaluationResult, evaluate_predictions
from .explanation_builder import build_prediction_explanation, build_weight_explanations
from .feature_pipeline import (
    FEATURE_ALLOWLIST_VERSION,
    FEATURE_SCHEMA_COMPATIBLE_VERSIONS,
    FeaturePolicyEntry,
    FeaturePolicyReport,
    build_feature_policy,
    build_feature_policy_report,
    build_feature_matrix,
)
from .logistic_regression_trainer import TrainingOutcome, train_logistic_regression_baseline
from .model_loader import load_active_model_artifact

__all__ = [
    "BaselineComparisonReport",
    "EvaluationResult",
    "FEATURE_ALLOWLIST_VERSION",
    "FEATURE_SCHEMA_COMPATIBLE_VERSIONS",
    "FeaturePolicyEntry",
    "FeaturePolicyReport",
    "PersonalizationModelArtifact",
    "PersonalizationModelManifest",
    "PersonalizationModelManifestVersion",
    "PersonalizationTrainingDataset",
    "TrainingOutcome",
    "build_feature_matrix",
    "build_feature_policy",
    "build_feature_policy_report",
    "build_prediction_explanation",
    "build_reference_baselines",
    "build_weight_explanations",
    "evaluate_predictions",
    "load_active_model_artifact",
    "load_model_artifact",
    "load_training_dataset",
    "save_model_artifact",
    "train_logistic_regression_baseline",
    "verify_model_artifact_path",
]
