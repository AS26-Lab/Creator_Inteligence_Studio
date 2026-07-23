"""Servicio de entrenamiento y scoring personalizado por creador."""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

import numpy as np

from creator_intelligence_studio.application.services.catalog_service import CatalogService
from creator_intelligence_studio.application.services.clip_ranking_service import ClipRankingService
from creator_intelligence_studio.application.services.personalization_dataset_service import PersonalizationDatasetReport, PersonalizationDatasetService
from creator_intelligence_studio.domain.errors import NotFoundError
from creator_intelligence_studio.domain.personalization_data.entities import CreatorDatasetExample, CreatorDatasetSnapshot, CreatorFeatureSchema
from creator_intelligence_studio.domain.personalization_data.errors import PersonalizationDataStateError
from creator_intelligence_studio.domain.personalization_data.value_objects import PersonalizationDatasetStatus, PersonalizationReadinessStatus
from creator_intelligence_studio.domain.personalization_models.entities import (
    PersonalizationModelComparison,
    PersonalizationModelMetric,
    PersonalizationModelPrediction,
    PersonalizationModelRegistryEntry,
    PersonalizationTrainingRun,
)
from creator_intelligence_studio.domain.personalization_models.errors import PersonalizationModelArtifactError, PersonalizationModelStateError, PersonalizationModelValidationError
from creator_intelligence_studio.domain.personalization_models.repositories import PersonalizationModelRepository
from creator_intelligence_studio.domain.personalization_models.services import (
    build_personalization_model_configuration_fingerprint,
    build_personalization_model_source_fingerprint,
    is_personalization_model_stale,
)
from creator_intelligence_studio.domain.personalization_models.value_objects import (
    PersonalizationModelFamily,
    PersonalizationModelOptions,
    PersonalizationModelRegistryStatus,
    PersonalizationModelTrainingStatus,
)
from creator_intelligence_studio.domain.personalization_data.services import build_personalization_configuration_fingerprint, build_personalization_source_fingerprint
from creator_intelligence_studio.infrastructure.personalization_data.feature_extractor import extract_dataset_features
from creator_intelligence_studio.infrastructure.personalization_models.artifact_store import (
    PersonalizationModelArtifact,
    PersonalizationModelManifest,
    build_default_dependencies,
    load_model_artifact,
    save_model_artifact,
    verify_model_artifact_path,
)
from creator_intelligence_studio.infrastructure.personalization_models.baseline_comparator import BaselineComparisonReport, build_reference_baselines
from creator_intelligence_studio.infrastructure.personalization_models.dataset_loader import PersonalizationTrainingDataset, load_training_dataset
from creator_intelligence_studio.infrastructure.personalization_models.evaluator import EvaluationResult, evaluate_predictions
from creator_intelligence_studio.infrastructure.personalization_models.explanation_builder import PersonalizationPredictionExplanation, build_prediction_explanation, build_weight_explanations
from creator_intelligence_studio.infrastructure.personalization_models.feature_pipeline import build_feature_policy
from creator_intelligence_studio.infrastructure.personalization_models.logistic_regression_trainer import TrainingOutcome, train_logistic_regression_baseline
from creator_intelligence_studio.infrastructure.personalization_models.model_loader import load_active_model_artifact
from creator_intelligence_studio.infrastructure.persistence.sqlite_personalization_model_repository import SQLitePersonalizationModelRepository
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.shared.dates import to_iso_z, utc_now
from creator_intelligence_studio.shared.paths import ProjectPaths


@dataclass(frozen=True, slots=True)
class TrainingValidationReport:
    snapshot: CreatorDatasetSnapshot
    feature_schema: CreatorFeatureSchema
    status: str
    eligible: bool
    warnings: tuple[str, ...]
    errors: tuple[str, ...]
    reasons: tuple[str, ...]
    source_fingerprint: str
    configuration_fingerprint: str
    readiness_status: PersonalizationReadinessStatus
    readiness_score: float
    label_counts: dict[str, int]
    split_counts: dict[str, int]
    conflict_count: int
    is_stale: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "snapshot": self.snapshot.to_dict(),
            "feature_schema": self.feature_schema.to_dict(),
            "status": self.status,
            "eligible": self.eligible,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "reasons": list(self.reasons),
            "source_fingerprint": self.source_fingerprint,
            "configuration_fingerprint": self.configuration_fingerprint,
            "readiness_status": self.readiness_status.value,
            "readiness_score": self.readiness_score,
            "label_counts": dict(self.label_counts),
            "split_counts": dict(self.split_counts),
            "conflict_count": self.conflict_count,
            "is_stale": self.is_stale,
        }


@dataclass(frozen=True, slots=True)
class TrainingSplitReport:
    split_name: str
    evaluation: EvaluationResult | None
    baselines: tuple[BaselineComparisonReport, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "split_name": self.split_name,
            "evaluation": self.evaluation.to_dict() if self.evaluation else None,
            "baselines": [baseline.to_dict() for baseline in self.baselines],
        }


@dataclass(frozen=True, slots=True)
class PersonalizationTrainingReport:
    validation: TrainingValidationReport
    training_run: PersonalizationTrainingRun | None
    feature_policy: dict[str, object]
    metrics: tuple[PersonalizationModelMetric, ...]
    predictions: tuple[PersonalizationModelPrediction, ...]
    splits: tuple[TrainingSplitReport, ...]
    artifact: PersonalizationModelArtifact | None
    outcome_status: str
    warnings: tuple[str, ...]
    errors: tuple[str, ...]
    baseline_summary: tuple[dict[str, object], ...]
    model_active: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "validation": self.validation.to_dict(),
            "training_run": self.training_run.to_dict() if self.training_run else None,
            "feature_policy": dict(self.feature_policy),
            "metrics": [metric.to_dict() for metric in self.metrics],
            "predictions": [prediction.to_dict() for prediction in self.predictions],
            "splits": [split.to_dict() for split in self.splits],
            "artifact": {
                "manifest": self.artifact.manifest.to_dict(),
                "manifest_path": str(self.artifact.manifest_path),
                "model_path": str(self.artifact.model_path),
                "metrics_path": str(self.artifact.metrics_path),
                "feature_schema_path": str(self.artifact.feature_schema_path),
            }
            if self.artifact
            else None,
            "outcome_status": self.outcome_status,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "baseline_summary": [dict(item) for item in self.baseline_summary],
            "model_active": self.model_active,
        }


@dataclass(frozen=True, slots=True)
class PersonalizationActiveModelReport:
    registry_entry: PersonalizationModelRegistryEntry
    artifact_verified: bool
    manifest: dict[str, object] | None
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "registry_entry": self.registry_entry.to_dict(),
            "artifact_verified": self.artifact_verified,
            "manifest": dict(self.manifest) if self.manifest else None,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True, slots=True)
class PersonalizedScoreReport:
    creator_id: str
    project_id: str | None
    training_run_id: str
    candidate_id: str
    positive_score: float
    predicted_label: str
    threshold: float
    explanation: PersonalizationPredictionExplanation
    feature_policy: dict[str, object]
    warnings: tuple[str, ...]
    errors: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "creator_id": self.creator_id,
            "project_id": self.project_id,
            "training_run_id": self.training_run_id,
            "candidate_id": self.candidate_id,
            "positive_score": self.positive_score,
            "predicted_label": self.predicted_label,
            "threshold": self.threshold,
            "explanation": self.explanation.to_dict(),
            "feature_policy": dict(self.feature_policy),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }


def _metric_summary(metrics: tuple[PersonalizationModelMetric, ...]) -> dict[str, float | None]:
    summary: dict[str, float | None] = {}
    for metric in metrics:
        key = f"{metric.split_name}.{metric.metric_name}"
        summary[key] = metric.metric_value
    return summary


def _artifact_root(paths: ProjectPaths, creator_id: str, training_run_id: str) -> Path:
    return paths.models_directory / "personalization" / creator_id / training_run_id


def _default_model_name() -> str:
    return "personalization_logistic_regression"


def _build_feature_policy_payload(report: TrainingValidationReport) -> dict[str, object]:
    return {
        "schema_version": report.feature_schema.schema_version,
        "allowlist_version": "1",
        "entries": [
            {
                "name": entry.name,
                "included": entry.included,
                "reason": entry.reason,
                "origin": entry.origin,
                "transformation": entry.transformation,
                "missing_policy": entry.missing_policy,
                "expected_range": list(entry.expected_range) if entry.expected_range is not None else None,
            }
            for entry in build_feature_policy(report.feature_schema).entries
        ],
    }


class PersonalizationTrainingService:
    def __init__(
        self,
        *,
        settings: AppSettings,
        paths: ProjectPaths,
        catalog_service: CatalogService,
        clip_service: ClipRankingService,
        dataset_service: PersonalizationDatasetService,
        model_repository: PersonalizationModelRepository,
        logger: logging.Logger | None = None,
        options: PersonalizationModelOptions | None = None,
    ) -> None:
        self.settings = settings
        self.paths = paths
        self.catalog_service = catalog_service
        self.clip_service = clip_service
        self.dataset_service = dataset_service
        self.model_repository = model_repository
        self.logger = logger or logging.getLogger("creator_intelligence_studio.personalization_models")
        self.options = options or PersonalizationModelOptions()

    def _require_creator(self, creator_id: str):
        creator = self.catalog_service.get_creator(creator_id)
        if creator is None:
            raise NotFoundError("El creador solicitado no existe.")
        return creator

    def _require_snapshot_report(self, snapshot_id: str) -> PersonalizationDatasetReport:
        snapshot_report = self.dataset_service.get_dataset_snapshot(snapshot_id)
        if snapshot_report.snapshot is None:
            raise NotFoundError("El snapshot solicitado no existe.")
        return snapshot_report

    def _progress(self, progress_callback: Callable[[str, float], None] | None, phase: str, ratio: float) -> None:
        if progress_callback is not None:
            progress_callback(phase, ratio)
        self.logger.info("Personalization models progress: %s %.2f", phase, ratio)

    def _assess_snapshot(self, snapshot_report: PersonalizationDatasetReport) -> TrainingValidationReport:
        snapshot = snapshot_report.snapshot
        feature_schema = snapshot_report.feature_schema
        reasons: list[str] = []
        warnings: list[str] = list(snapshot_report.warnings)
        errors: list[str] = list(snapshot_report.errors)
        eligible = True
        status = "ready"
        if snapshot.status not in {PersonalizationDatasetStatus.COMPLETED, PersonalizationDatasetStatus.COMPLETED_WITH_WARNINGS}:
            eligible = False
            status = "blocked"
            reasons.append(f"Snapshot en estado {snapshot.status.value}.")
        if snapshot.readiness_status not in {
            PersonalizationReadinessStatus.READY_FOR_BASELINE,
            PersonalizationReadinessStatus.READY_FOR_EVALUATION,
            PersonalizationReadinessStatus.READY_FOR_PERSONALIZED_TRAINING,
        }:
            eligible = False
            status = "blocked_by_quality"
            reasons.append(f"Readiness insuficiente: {snapshot.readiness_status.value}.")
        if snapshot_report.is_stale:
            eligible = False
            status = "blocked_by_quality"
            reasons.append("El snapshot esta stale.")
        if snapshot.conflict_count > 0:
            warnings.append("El snapshot contiene conflictos registrados.")
        if snapshot.example_count < self.options.minimum_examples_for_baseline:
            eligible = False
            status = "insufficient_data"
            reasons.append("No hay suficientes ejemplos para el baseline.")
        if snapshot.positive_count < 1 or snapshot.negative_count < 1:
            eligible = False
            status = "insufficient_data"
            reasons.append("Se requieren al menos una clase positiva y una negativa.")
        if snapshot.train_count <= 0:
            eligible = False
            status = "insufficient_data"
            reasons.append("El split train esta vacio.")
        if snapshot.feature_schema_version != self.options.feature_schema_version:
            eligible = False
            status = "incompatible_schema"
            reasons.append("El esquema de features es incompatible.")
        if snapshot.label_schema_version != self.options.label_schema_version:
            eligible = False
            status = "incompatible_schema"
            reasons.append("El esquema de labels es incompatible.")
        if snapshot.positive_count + snapshot.negative_count == 0:
            eligible = False
            status = "insufficient_data"
            reasons.append("No hay labels positivas ni negativas.")
        if snapshot.readiness_status == PersonalizationReadinessStatus.BLOCKED_BY_CONFLICTS:
            eligible = False
            status = "blocked_by_conflicts"
            reasons.append("El snapshot esta bloqueado por conflictos.")
        if snapshot.readiness_status == PersonalizationReadinessStatus.BLOCKED_BY_QUALITY:
            eligible = False
            status = "blocked_by_quality"
            reasons.append("La calidad del snapshot esta bloqueada.")
        if snapshot_report.quality_report and snapshot_report.quality_report.leakage_risk_score > self.options.max_leakage_risk:
            eligible = False
            status = "blocked_by_leakage"
            reasons.append("Riesgo de leakage demasiado alto.")
        label_counts = {
            "positive": snapshot.positive_count,
            "negative": snapshot.negative_count,
            "neutral_or_uncertain": snapshot.neutral_count,
            "excluded": snapshot.excluded_count,
        }
        return TrainingValidationReport(
            snapshot=snapshot,
            feature_schema=feature_schema,
            status=status if not eligible else "ready",
            eligible=eligible,
            warnings=tuple(warnings),
            errors=tuple(errors),
            reasons=tuple(reasons),
            source_fingerprint=snapshot.source_fingerprint,
            configuration_fingerprint=build_personalization_model_configuration_fingerprint(self.options),
            readiness_status=snapshot.readiness_status,
            readiness_score=snapshot.readiness_score,
            label_counts=label_counts,
            split_counts={
                "train": snapshot.train_count,
                "validation": snapshot.validation_count,
                "test": snapshot.test_count,
                "excluded": snapshot.excluded_count,
            },
            conflict_count=snapshot.conflict_count,
            is_stale=snapshot_report.is_stale,
        )

    def validate_training_snapshot(self, snapshot_id: str) -> TrainingValidationReport:
        return self._assess_snapshot(self._require_snapshot_report(snapshot_id))

    def _build_validation_report(self, snapshot_report: PersonalizationDatasetReport) -> TrainingValidationReport:
        snapshot = snapshot_report.snapshot
        feature_schema = snapshot_report.feature_schema
        label_counts = {
            "positive": snapshot.positive_count,
            "negative": snapshot.negative_count,
            "neutral_or_uncertain": snapshot.neutral_count,
            "excluded": snapshot.excluded_count,
        }
        report = self._assess_snapshot(snapshot_report)
        return report

    def _latest_completed_run_for_snapshot(self, snapshot_id: str) -> PersonalizationTrainingRun | None:
        runs = self.model_repository.list_training_runs_by_creator_id(self.dataset_service.get_dataset_snapshot(snapshot_id).snapshot.creator_id)
        for run in runs:
            if run.snapshot_id == snapshot_id and run.status in {
                PersonalizationModelTrainingStatus.COMPLETED,
                PersonalizationModelTrainingStatus.COMPLETED_WITH_WARNINGS,
            }:
                return run
        return None

    def _example_id_sort_key(self, example: CreatorDatasetExample) -> tuple[str, float, str]:
        return (example.video_asset_id, example.start_seconds, example.id)

    def _build_metrics_rows(
        self,
        *,
        run_id: str,
        split_name: str,
        evaluation: EvaluationResult | None,
        baseline_metrics: list[BaselineComparisonReport],
    ) -> list[PersonalizationModelMetric]:
        rows: list[PersonalizationModelMetric] = []
        if evaluation is not None:
            for metric_name, metric_value in evaluation.metric_values.items():
                rows.append(
                    PersonalizationModelMetric(
                        id=str(uuid4()),
                        training_run_id=run_id,
                        split_name=split_name,
                        metric_name=metric_name,
                        metric_value=metric_value,
                        support=evaluation.support,
                        details_json={"kind": "model"},
                        created_at=utc_now(),
                    )
                )
        for baseline in baseline_metrics:
            for metric_name, metric_value in baseline.metric_values.items():
                rows.append(
                    PersonalizationModelMetric(
                        id=str(uuid4()),
                        training_run_id=run_id,
                        split_name=f"{split_name}:{baseline.name}",
                        metric_name=metric_name,
                        metric_value=metric_value,
                        support=evaluation.support if evaluation else None,
                        details_json=baseline.details_json | {"kind": "baseline", "baseline_name": baseline.name},
                        created_at=utc_now(),
                    )
                )
        return rows

    def _extract_source_scores(self, dataset: PersonalizationTrainingDataset, matrix: np.ndarray) -> np.ndarray:
        if "rank_score" in dataset.feature_names:
            index = dataset.feature_names.index("rank_score")
        elif "source_score" in dataset.feature_names:
            index = dataset.feature_names.index("source_score")
        else:
            return np.zeros(matrix.shape[0], dtype=float)
        return matrix[:, index].astype(float) if matrix.size else np.zeros(matrix.shape[0], dtype=float)

    def _build_evaluation(
        self,
        *,
        split_name: str,
        dataset: PersonalizationTrainingDataset,
        model,
        threshold: float,
        X: np.ndarray,
        y: np.ndarray,
        examples: tuple[CreatorDatasetExample, ...],
        source_scores_train: np.ndarray,
        source_scores_eval: np.ndarray,
        random_seed: int,
    ) -> tuple[EvaluationResult | None, list[BaselineComparisonReport], list[PersonalizationModelPrediction]]:
        if X.size == 0 or y.size == 0:
            return None, [], []
        y_score = model.predict_proba(X)[:, 1]
        y_pred = (y_score >= threshold).astype(int)
        transformed = model[:-1].transform(X) if hasattr(model, "__getitem__") else model.named_steps["scaler"].transform(model.named_steps["imputer"].transform(X))
        coefficients = model.named_steps["model"].coef_[0]
        intercept = float(model.named_steps["model"].intercept_[0])
        evaluations: list[dict[str, Any]] = []
        predictions_payload: list[dict[str, Any]] = []
        prediction_rows: list[PersonalizationModelPrediction] = []
        for index, example in enumerate(examples):
            explanation = build_prediction_explanation(
                feature_names=dataset.feature_names,
                raw_feature_values=np.asarray(X[index], dtype=float),
                transformed_values=np.asarray(transformed[index], dtype=float),
                coefficients=np.asarray(coefficients, dtype=float),
                intercept=intercept,
                threshold=threshold,
            )
            predictions_payload.append(explanation.to_dict())
            prediction_rows.append(
                PersonalizationModelPrediction(
                    id=str(uuid4()),
                    training_run_id="",
                    dataset_example_id=example.id,
                    split_name=split_name,
                    true_label="positive" if int(y[index]) == 1 else "negative",
                    predicted_label="positive" if int(y_pred[index]) == 1 else "negative",
                    positive_score=float(y_score[index]),
                    decision_threshold=threshold,
                    is_correct=int(y[index]) == int(y_pred[index]),
                    explanation_json=explanation.to_dict(),
                    created_at=utc_now(),
                )
            )
        evaluation = evaluate_predictions(
            split_name=split_name,
            y_true=y,
            y_pred=y_pred,
            y_score=y_score,
            threshold=threshold,
            support_ids=[example.id for example in examples],
            explanations=predictions_payload,
        )
        baselines = build_reference_baselines(
            y_train=dataset.y_train,
            y_eval=y,
            source_scores_train=source_scores_train,
            source_scores_eval=source_scores_eval,
            threshold=threshold,
            random_seed=random_seed,
            split_name=split_name,
        )
        return evaluation, baselines, prediction_rows

    def _choose_threshold(self, y_true: np.ndarray, scores: np.ndarray, primary_metric: str) -> float:
        if y_true.size == 0 or len(set(y_true.tolist())) < 2:
            return self.options.decision_threshold
        candidate_thresholds = sorted(set(float(value) for value in scores.tolist() + [0.5]))
        best_threshold = self.options.decision_threshold
        best_score = -1.0
        for threshold in candidate_thresholds:
            predictions = (scores >= threshold).astype(int)
            if primary_metric == "f1":
                from sklearn.metrics import f1_score

                score = float(f1_score(y_true, predictions, zero_division=0))
            elif primary_metric == "precision":
                from sklearn.metrics import precision_score

                score = float(precision_score(y_true, predictions, zero_division=0))
            elif primary_metric == "recall":
                from sklearn.metrics import recall_score

                score = float(recall_score(y_true, predictions, zero_division=0))
            else:
                from sklearn.metrics import balanced_accuracy_score

                score = float(balanced_accuracy_score(y_true, predictions))
            if score > best_score:
                best_score = score
                best_threshold = threshold
        return best_threshold

    def train_personalization_baseline(
        self,
        snapshot_id: str,
        force: bool = False,
        progress_callback: Callable[[str, float], None] | None = None,
    ) -> PersonalizationTrainingReport:
        snapshot_report = self.dataset_service.get_dataset_snapshot(snapshot_id)
        if snapshot_report.snapshot is None:
            raise NotFoundError("El snapshot solicitado no existe.")
        validation_report = self._build_validation_report(snapshot_report)
        if not validation_report.eligible:
            raise PersonalizationModelStateError("; ".join(validation_report.reasons))
        if not force:
            existing = self._latest_completed_run_for_snapshot(snapshot_id)
            if existing is not None and existing.artifact_path:
                artifact = load_model_artifact(self.paths.project_root / existing.artifact_path)
                metrics = tuple(self.model_repository.list_metrics_by_run_id(existing.id))
                predictions = tuple(self.model_repository.list_predictions_by_run_id(existing.id))
                return PersonalizationTrainingReport(
                    validation=validation_report,
                    training_run=existing,
                    feature_policy=build_feature_policy(validation_report.feature_schema).to_dict(),
                    metrics=metrics,
                    predictions=predictions,
                    splits=(),
                    artifact=artifact,
                    outcome_status="baseline_only",
                    warnings=validation_report.warnings,
                    errors=validation_report.errors,
                    baseline_summary=(),
                    model_active=False,
                )
        self._progress(progress_callback, "Validando dataset", 0.05)
        dataset = load_training_dataset(
            snapshot=validation_report.snapshot,
            examples=list(snapshot_report.examples),
            feature_schema=validation_report.feature_schema,
            strict_feature_policy=self.options.strict_feature_policy,
        )
        if dataset.X_train.size == 0 or dataset.y_train.size == 0:
            raise PersonalizationModelStateError("El conjunto train esta vacio.")
        if len(set(dataset.y_train.tolist())) < 2:
            raise PersonalizationModelStateError("El baseline requiere dos clases entrenables.")
        self._progress(progress_callback, "Preparando pipeline", 0.2)
        training_run = PersonalizationTrainingRun(
            id=str(uuid4()),
            creator_id=validation_report.snapshot.creator_id,
            project_id=validation_report.snapshot.project_id,
            snapshot_id=snapshot_id,
            status=PersonalizationModelTrainingStatus.QUEUED,
            model_family=PersonalizationModelFamily.LOGISTIC_REGRESSION,
            model_version=self.options.model_version,
            trainer_version=self.options.trainer_version,
            feature_schema_version=self.options.feature_schema_version,
            label_schema_version=self.options.label_schema_version,
            configuration_fingerprint=build_personalization_model_configuration_fingerprint(self.options),
            source_fingerprint=build_personalization_model_source_fingerprint({"snapshot": validation_report.snapshot.to_dict(), "examples": len(snapshot_report.examples)}),
            train_count=dataset.split_counts["train"],
            validation_count=dataset.split_counts["validation"],
            test_count=dataset.split_counts["test"],
            positive_count=validation_report.snapshot.positive_count,
            negative_count=validation_report.snapshot.negative_count,
            excluded_count=dataset.excluded_count,
            random_seed=self.options.random_seed,
            decision_threshold=self.options.decision_threshold,
            artifact_path=None,
            artifact_fingerprint=None,
            started_at=utc_now(),
            completed_at=None,
            warning_code=None,
            warning_message=None,
            error_code=None,
            error_message=None,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        training_run = self.model_repository.upsert_training_run(training_run)
        self._progress(progress_callback, "Entrenando baseline", 0.4)
        training_outcome: TrainingOutcome = train_logistic_regression_baseline(
            dataset.X_train,
            dataset.y_train,
            regularization_c=self.options.regularization_c,
            max_iter=self.options.max_iter,
            random_seed=self.options.random_seed,
            feature_names=dataset.feature_names,
            class_weight_mode=self.options.class_weight_mode,
        )
        model = training_outcome.pipeline
        train_scores = model.predict_proba(dataset.X_train)[:, 1]
        threshold = self.options.decision_threshold
        if dataset.has_validation:
            threshold = self._choose_threshold(dataset.y_validation, model.predict_proba(dataset.X_validation)[:, 1], self.options.metric_primary)
        self._progress(progress_callback, "Evaluando validation", 0.6)
        source_scores_train = self._extract_source_scores(dataset, dataset.X_train)
        source_scores_validation = self._extract_source_scores(dataset, dataset.X_validation)
        source_scores_test = self._extract_source_scores(dataset, dataset.X_test)
        validation_eval, validation_baselines, validation_predictions = self._build_evaluation(
            split_name="validation",
            dataset=dataset,
            model=model,
            threshold=threshold,
            X=dataset.X_validation,
            y=dataset.y_validation,
            examples=dataset.validation_examples,
            source_scores_train=source_scores_train,
            source_scores_eval=source_scores_validation,
            random_seed=self.options.random_seed,
        )
        self._progress(progress_callback, "Evaluando test", 0.75)
        test_eval, test_baselines, test_predictions = self._build_evaluation(
            split_name="test",
            dataset=dataset,
            model=model,
            threshold=threshold,
            X=dataset.X_test,
            y=dataset.y_test,
            examples=dataset.test_examples,
            source_scores_train=source_scores_train,
            source_scores_eval=source_scores_test,
            random_seed=self.options.random_seed + 1,
        )
        train_eval, train_baselines, train_predictions = self._build_evaluation(
            split_name="train",
            dataset=dataset,
            model=model,
            threshold=threshold,
            X=dataset.X_train if self.options.allow_train_diagnostics else np.empty((0, len(dataset.feature_names))),
            y=dataset.y_train if self.options.allow_train_diagnostics else np.empty((0,), dtype=int),
            examples=dataset.train_examples if self.options.allow_train_diagnostics else tuple(),
            source_scores_train=source_scores_train,
            source_scores_eval=source_scores_train,
            random_seed=self.options.random_seed + 2,
        )
        self._progress(progress_callback, "Guardando artefacto", 0.85)
        metrics: list[PersonalizationModelMetric] = []
        predictions: list[PersonalizationModelPrediction] = []
        splits: list[TrainingSplitReport] = []
        baseline_summary: list[dict[str, object]] = []
        for split_name, evaluation, baselines, rows in (
            ("train", train_eval, train_baselines, train_predictions),
            ("validation", validation_eval, validation_baselines, validation_predictions),
            ("test", test_eval, test_baselines, test_predictions),
        ):
            if evaluation is None:
                continue
            metrics.extend(self._build_metrics_rows(run_id=training_run.id, split_name=split_name, evaluation=evaluation, baseline_metrics=baselines))
            predictions.extend(
                [
                    replace(
                        prediction,
                        training_run_id=training_run.id,
                        id=str(uuid4()),
                        created_at=utc_now(),
                    )
                    for prediction in rows
                ]
            )
            splits.append(TrainingSplitReport(split_name=split_name, evaluation=evaluation, baselines=tuple(baselines)))
            baseline_summary.extend([baseline.to_dict() for baseline in baselines])
        artifact_root = _artifact_root(self.paths, validation_report.snapshot.creator_id, training_run.id)
        manifest = PersonalizationModelManifest(
            manifest_version="1",
            creator_id=validation_report.snapshot.creator_id,
            project_id=validation_report.snapshot.project_id,
            snapshot_id=validation_report.snapshot.id,
            training_run_id=training_run.id,
            model_name=_default_model_name(),
            model_family=PersonalizationModelFamily.LOGISTIC_REGRESSION.value,
            model_version=self.options.model_version,
            trainer_version=self.options.trainer_version,
            feature_schema_version=self.options.feature_schema_version,
            label_schema_version=self.options.label_schema_version,
            configuration_fingerprint=training_run.configuration_fingerprint,
            source_fingerprint=training_run.source_fingerprint,
            artifact_fingerprint="",
            threshold=threshold,
            python_version=__import__("platform").python_version(),
            platform=__import__("platform").platform(),
            dependencies=build_default_dependencies(),
            metrics_summary=_metric_summary(tuple(metrics)),
            created_at=to_iso_z(utc_now()),
        )
        artifact = save_model_artifact(
            artifact_root=artifact_root,
            model=model,
            manifest=manifest,
            metrics_payload={
                "validation": validation_eval.to_dict() if validation_eval else None,
                "test": test_eval.to_dict() if test_eval else None,
                "train": train_eval.to_dict() if train_eval and self.options.allow_train_diagnostics else None,
                "baselines": baseline_summary,
                "threshold": threshold,
                "feature_policy": build_feature_policy(validation_report.feature_schema).to_dict(),
            },
            feature_schema_payload=validation_report.feature_schema.to_dict(),
        )
        self._progress(progress_callback, "Registrando modelo", 0.95)
        final_status = PersonalizationModelTrainingStatus.COMPLETED_WITH_WARNINGS if (not dataset.has_validation or not dataset.has_test) else PersonalizationModelTrainingStatus.COMPLETED
        model_status = "promising_baseline"
        if validation_eval and validation_eval.metric_values.get(self.options.metric_primary) is not None:
            primary_value = validation_eval.metric_values[self.options.metric_primary] or 0.0
            best_baseline = max((baseline.metric_values.get(self.options.metric_primary) or 0.0 for baseline in validation_baselines), default=0.0)
            if primary_value > best_baseline + 0.01:
                model_status = "candidate_for_activation"
            elif primary_value > best_baseline:
                model_status = "promising_baseline"
            else:
                model_status = "no_improvement"
        if not dataset.has_validation or not dataset.has_test:
            model_status = "evaluation_not_ready"
        if validation_report.readiness_status == PersonalizationReadinessStatus.BLOCKED_BY_CONFLICTS:
            model_status = "blocked_by_quality"
        training_run = self.model_repository.upsert_training_run(
            replace(
                training_run,
                status=final_status,
                artifact_path=str(artifact_root.relative_to(self.paths.project_root)),
                artifact_fingerprint=artifact.manifest.artifact_fingerprint,
                completed_at=utc_now(),
                warning_code=None if not dataset.has_validation else ("warnings" if dataset.excluded_count else None),
                warning_message="; ".join(validation_report.warnings) if validation_report.warnings else None,
                error_code=None,
                error_message=None,
                updated_at=utc_now(),
            )
        )
        metrics = tuple(self.model_repository.upsert_metrics(training_run.id, metrics))
        predictions = tuple(self.model_repository.upsert_predictions(training_run.id, predictions))
        registry_entry = self.model_repository.upsert_registry_entry(
            PersonalizationModelRegistryEntry(
                id=str(uuid4()),
                creator_id=training_run.creator_id,
                project_id=training_run.project_id,
                training_run_id=training_run.id,
                model_name=_default_model_name(),
                status=PersonalizationModelRegistryStatus.CANDIDATE,
                is_active=False,
                activated_at=None,
                retired_at=None,
                created_at=utc_now(),
                updated_at=utc_now(),
            )
        )
        _ = registry_entry
        self._progress(progress_callback, "Completado", 1.0)
        return PersonalizationTrainingReport(
            validation=validation_report,
            training_run=training_run,
                    feature_policy=build_feature_policy(validation_report.feature_schema).to_dict(),
            metrics=metrics,
            predictions=predictions,
            splits=tuple(splits),
            artifact=artifact,
            outcome_status=model_status,
            warnings=validation_report.warnings + (("No hay validation suficiente" if not dataset.has_validation else ""), ("No hay test suficiente" if not dataset.has_test else "")),
            errors=validation_report.errors,
            baseline_summary=tuple(baseline_summary),
            model_active=False,
        )

    def get_training_run(self, training_run_id: str) -> PersonalizationTrainingRun | None:
        return self.model_repository.get_training_run_by_id(training_run_id)

    def list_creator_training_runs(self, creator_id: str) -> list[PersonalizationTrainingRun]:
        return self.model_repository.list_training_runs_by_creator_id(creator_id)

    def get_training_metrics(self, training_run_id: str) -> list[PersonalizationModelMetric]:
        return self.model_repository.list_metrics_by_run_id(training_run_id)

    def list_training_predictions(self, training_run_id: str, split: str | None = None) -> list[PersonalizationModelPrediction]:
        predictions = self.model_repository.list_predictions_by_run_id(training_run_id)
        if split is None:
            return predictions
        return [prediction for prediction in predictions if prediction.split_name == split]

    def compare_training_runs(self, baseline_run_id: str, candidate_run_id: str) -> PersonalizationModelComparison:
        baseline = self.model_repository.get_training_run_by_id(baseline_run_id)
        candidate = self.model_repository.get_training_run_by_id(candidate_run_id)
        if baseline is None or candidate is None:
            raise NotFoundError("Uno de los training runs no existe.")
        baseline_metrics = {metric.metric_name: metric.metric_value for metric in self.model_repository.list_metrics_by_run_id(baseline_run_id) if metric.split_name == "validation"}
        candidate_metrics = {metric.metric_name: metric.metric_value for metric in self.model_repository.list_metrics_by_run_id(candidate_run_id) if metric.split_name == "validation"}
        primary_metric = self.options.metric_primary
        baseline_value = baseline_metrics.get(primary_metric)
        candidate_value = candidate_metrics.get(primary_metric)
        comparison = PersonalizationModelComparison(
            id=str(uuid4()),
            creator_id=candidate.creator_id,
            baseline_run_id=baseline_run_id,
            candidate_run_id=candidate_run_id,
            comparison_status="completed",
            primary_metric=primary_metric,
            baseline_value=baseline_value,
            candidate_value=candidate_value,
            difference=(candidate_value - baseline_value) if baseline_value is not None and candidate_value is not None else None,
            warnings_json={},
            created_at=utc_now(),
        )
        return self.model_repository.upsert_comparison(comparison)

    def activate_model(self, training_run_id: str) -> PersonalizationActiveModelReport:
        run = self.model_repository.get_training_run_by_id(training_run_id)
        if run is None:
            raise NotFoundError("El training run solicitado no existe.")
        if not run.artifact_path:
            raise PersonalizationModelArtifactError("El training run no tiene artefacto.")
        artifact = self.verify_model_artifact(training_run_id)
        if not artifact.artifact_verified:
            raise PersonalizationModelArtifactError("El artefacto no pudo verificarse.")
        current_entries = self.model_repository.list_registry_entries_by_creator_id(run.creator_id)
        for entry in current_entries:
            if entry.is_active:
                self.model_repository.upsert_registry_entry(
                    replace(entry, status=PersonalizationModelRegistryStatus.INACTIVE, is_active=False, updated_at=utc_now())
                )
        entry = self.model_repository.get_registry_entry_by_training_run_id(training_run_id)
        if entry is None:
            entry = PersonalizationModelRegistryEntry(
                id=str(uuid4()),
                creator_id=run.creator_id,
                project_id=run.project_id,
                training_run_id=training_run_id,
                model_name=_default_model_name(),
                status=PersonalizationModelRegistryStatus.CANDIDATE,
                is_active=False,
                activated_at=None,
                retired_at=None,
                created_at=utc_now(),
                updated_at=utc_now(),
            )
        entry = self.model_repository.upsert_registry_entry(
            replace(
                entry,
                status=PersonalizationModelRegistryStatus.ACTIVE,
                is_active=True,
                activated_at=utc_now(),
                retired_at=None,
                updated_at=utc_now(),
            )
        )
        return PersonalizationActiveModelReport(
            registry_entry=entry,
            artifact_verified=True,
            manifest=dict(artifact.manifest) if artifact.manifest is not None else None,
            warnings=(),
        )

    def deactivate_model(self, training_run_id: str) -> PersonalizationModelRegistryEntry | None:
        entry = self.model_repository.get_registry_entry_by_training_run_id(training_run_id)
        if entry is None:
            return None
        updated = self.model_repository.upsert_registry_entry(
            replace(entry, status=PersonalizationModelRegistryStatus.INACTIVE, is_active=False, updated_at=utc_now())
        )
        return updated

    def retire_model(self, training_run_id: str) -> PersonalizationModelRegistryEntry | None:
        entry = self.model_repository.get_registry_entry_by_training_run_id(training_run_id)
        if entry is None:
            return None
        updated = self.model_repository.upsert_registry_entry(
            replace(
                entry,
                status=PersonalizationModelRegistryStatus.RETIRED,
                is_active=False,
                retired_at=utc_now(),
                updated_at=utc_now(),
            )
        )
        return updated

    def get_active_creator_model(self, creator_id: str, project_id: str | None = None) -> PersonalizationActiveModelReport | None:
        entry = self.model_repository.get_active_registry_entry(creator_id, project_id)
        if entry is None:
            return None
        verified = False
        manifest_payload = None
        try:
            verified = self.verify_model_artifact(entry.training_run_id).artifact_verified
            if verified:
                run = self.model_repository.get_training_run_by_id(entry.training_run_id)
                if run and run.artifact_path:
                    artifact = load_model_artifact(self.paths.project_root / run.artifact_path)
                    manifest_payload = artifact.manifest.to_dict()
        except Exception as exc:  # pragma: no cover - defensive
            return PersonalizationActiveModelReport(registry_entry=entry, artifact_verified=False, manifest=None, warnings=(str(exc),))
        return PersonalizationActiveModelReport(registry_entry=entry, artifact_verified=verified, manifest=manifest_payload)

    def verify_model_artifact(self, training_run_id: str) -> PersonalizationActiveModelReport:
        run = self.model_repository.get_training_run_by_id(training_run_id)
        if run is None:
            raise NotFoundError("El training run solicitado no existe.")
        if not run.artifact_path:
            return PersonalizationActiveModelReport(
                registry_entry=self.model_repository.get_registry_entry_by_training_run_id(training_run_id) or PersonalizationModelRegistryEntry(
                    id=str(uuid4()),
                    creator_id=run.creator_id,
                    project_id=run.project_id,
                    training_run_id=training_run_id,
                    model_name=_default_model_name(),
                    status=PersonalizationModelRegistryStatus.ARTIFACT_MISSING,
                    is_active=False,
                    activated_at=None,
                    retired_at=None,
                    created_at=utc_now(),
                    updated_at=utc_now(),
                ),
                artifact_verified=False,
                manifest=None,
                warnings=("No existe ruta de artefacto.",),
            )
        artifact_root = self.paths.project_root / run.artifact_path
        if not verify_model_artifact_path(artifact_root):
            entry = self.model_repository.get_registry_entry_by_training_run_id(training_run_id)
            if entry is None:
                entry = self.model_repository.upsert_registry_entry(
                    PersonalizationModelRegistryEntry(
                        id=str(uuid4()),
                        creator_id=run.creator_id,
                        project_id=run.project_id,
                        training_run_id=training_run_id,
                        model_name=_default_model_name(),
                        status=PersonalizationModelRegistryStatus.ARTIFACT_MISSING,
                        is_active=False,
                        activated_at=None,
                        retired_at=None,
                        created_at=utc_now(),
                        updated_at=utc_now(),
                    )
                )
            return PersonalizationActiveModelReport(registry_entry=entry, artifact_verified=False, manifest=None, warnings=("El artefacto no esta completo.",))
        artifact = load_model_artifact(artifact_root)
        return PersonalizationActiveModelReport(
            registry_entry=self.model_repository.get_registry_entry_by_training_run_id(training_run_id)
            or self.model_repository.upsert_registry_entry(
                PersonalizationModelRegistryEntry(
                    id=str(uuid4()),
                    creator_id=run.creator_id,
                    project_id=run.project_id,
                    training_run_id=training_run_id,
                    model_name=_default_model_name(),
                    status=PersonalizationModelRegistryStatus.CANDIDATE,
                    is_active=False,
                    activated_at=None,
                    retired_at=None,
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
            ),
            artifact_verified=True,
            manifest=artifact.manifest.to_dict(),
            warnings=(),
        )

    def delete_model_artifact(self, training_run_id: str) -> bool:
        run = self.model_repository.get_training_run_by_id(training_run_id)
        if run is None or not run.artifact_path:
            return False
        artifact_root = self.paths.project_root / run.artifact_path
        if artifact_root.exists() and self.paths.models_directory in artifact_root.parents:
            shutil.rmtree(artifact_root)
            return True
        return False

    def _score_candidate_internal(self, creator_id: str, candidate_id: str) -> PersonalizedScoreReport:
        active = self.get_active_creator_model(creator_id)
        if active is None:
            raise PersonalizationModelStateError("No existe un modelo activo para este creador.")
        if not active.artifact_verified or not active.manifest:
            raise PersonalizationModelArtifactError("El artefacto activo no pudo verificarse.")
        run = self.model_repository.get_training_run_by_id(active.registry_entry.training_run_id)
        if run is None:
            raise NotFoundError("El training run del modelo activo no existe.")
        model_artifact = load_model_artifact(self.paths.project_root / run.artifact_path)
        if model_artifact.manifest.feature_schema_version != self.options.feature_schema_version:
            raise PersonalizationModelStateError("El esquema de features del modelo es incompatible.")
        candidate_report = self.clip_service.get_ranked_candidate(candidate_id)
        ranking_run = self.clip_service.clip_repository.get_by_id(candidate_report.ranking_run_id)
        if ranking_run is None:
            raise NotFoundError("El ranking del candidato solicitado no existe.")
        ranking_report = self.clip_service.get_ranking_run(ranking_run.video_asset_id)
        if ranking_report.run is None or ranking_report.multimodal_report is None or ranking_report.multimodal_report.analysis is None:
            raise PersonalizationModelStateError("El candidato no tiene fuentes suficientes para puntuar.")
        multimodal_report = ranking_report.multimodal_report
        transcription = multimodal_report.transcription
        if transcription is not None:
            transcription = self.clip_service.transcription_repository.get_by_id(transcription.id) or transcription
            transcription_segments = self.clip_service.transcription_repository.list_segments(transcription.id)
        else:
            transcription_segments = []
        candidate_map = {candidate.id: candidate for candidate in multimodal_report.candidates}
        multimodal_candidate = candidate_map.get(candidate_report.multimodal_candidate_id)
        extracted = extract_dataset_features(
            video_duration_seconds=float(multimodal_report.analysis.duration_seconds or 0.0),
            profile=ranking_report.run.profile if hasattr(ranking_report.run, "profile") else "balanced",
            multimodal_analysis=multimodal_report.analysis,
            multimodal_windows=list(multimodal_report.windows),
            multimodal_candidate=multimodal_candidate,
            ranking_run=ranking_report.run,
            ranked_candidate=candidate_report,
            transcription=transcription,
            transcription_segments=list(transcription_segments),
            acoustic_analysis=multimodal_report.acoustic_analysis,
            visual_analysis=multimodal_report.visual_analysis,
            nearby_candidate_count=sum(
                1
                for other in ranking_report.candidates
                if other.id != candidate_report.id
                and abs(other.adjusted_start_seconds - candidate_report.adjusted_start_seconds) < 30.0
            ),
            collections_count=len(self.clip_service.clip_repository.list_collections(ranking_report.run.video_asset_id)),
            review_event_count=len(self.clip_service.clip_repository.list_review_events(candidate_report.id)),
            conflict_count=0,
        )
        feature_schema = self.dataset_service.personalization_repository.get_feature_schema(self.options.feature_schema_version)
        if feature_schema is None:
            raise PersonalizationModelStateError("No existe un esquema de features compatible para el modelo.")
        feature_policy = build_feature_policy(feature_schema)
        included_features = [entry.name for entry in feature_policy.entries if entry.included]
        raw_vector = np.array([[extracted.feature_vector.get(name) for name in included_features]], dtype=float)
        if np.isinf(raw_vector).any():
            raise PersonalizationModelValidationError("Se detectaron infinitos en el candidato.")
        model = model_artifact.model
        score = float(model.predict_proba(raw_vector)[0, 1])
        threshold = float(model_artifact.manifest.threshold)
        transformed = model[:-1].transform(raw_vector)
        explanation = build_prediction_explanation(
            feature_names=tuple(included_features),
            raw_feature_values=raw_vector[0],
            transformed_values=transformed[0],
            coefficients=model.named_steps["model"].coef_[0],
            intercept=float(model.named_steps["model"].intercept_[0]),
            threshold=threshold,
        )
        return PersonalizedScoreReport(
            creator_id=creator_id,
            project_id=run.project_id,
            training_run_id=run.id,
            candidate_id=candidate_id,
            positive_score=score,
            predicted_label="positive" if score >= threshold else "negative",
            threshold=threshold,
            explanation=explanation,
            feature_policy=feature_policy.to_dict(),
            warnings=(),
            errors=(),
        )

    def score_candidate_for_creator(self, creator_id: str, candidate_id: str) -> PersonalizedScoreReport:
        self._require_creator(creator_id)
        return self._score_candidate_internal(creator_id, candidate_id)

    def score_candidates_for_video(self, creator_id: str, video_id: str) -> list[PersonalizedScoreReport]:
        self._require_creator(creator_id)
        ranking_report = self.clip_service.get_ranking_run(video_id)
        if ranking_report.run is None:
            raise NotFoundError("No existe ranking de clips para el video solicitado.")
        return [self._score_candidate_internal(creator_id, candidate.id) for candidate in ranking_report.candidates]

    def explain_personalized_score(self, creator_id: str, candidate_id: str) -> dict[str, object]:
        return self.score_candidate_for_creator(creator_id, candidate_id).explanation.to_dict()


def build_personalization_training_service(
    *,
    settings: AppSettings,
    paths: ProjectPaths,
    catalog_service: CatalogService,
    clip_service: ClipRankingService,
    dataset_service: PersonalizationDatasetService,
    model_repository: PersonalizationModelRepository,
    logger: logging.Logger | None = None,
    options: PersonalizationModelOptions | None = None,
) -> PersonalizationTrainingService:
    return PersonalizationTrainingService(
        settings=settings,
        paths=paths,
        catalog_service=catalog_service,
        clip_service=clip_service,
        dataset_service=dataset_service,
        model_repository=model_repository,
        logger=logger,
        options=options,
    )
