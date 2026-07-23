"""Baselines de referencia para entrenamiento personalizado."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, precision_score, recall_score


@dataclass(frozen=True, slots=True)
class BaselineComparisonReport:
    name: str
    split_name: str
    metric_values: dict[str, float | None]
    threshold: float | None
    details_json: dict[str, Any]

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "split_name": self.split_name,
            "metric_values": dict(self.metric_values),
            "threshold": self.threshold,
            "details_json": dict(self.details_json),
        }


def _metric_bundle(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float | None]:
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)) if len(y_true) else None,
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)) if len(y_true) else None,
        "precision": float(precision_score(y_true, y_pred, zero_division=0)) if len(y_true) else None,
        "recall": float(recall_score(y_true, y_pred, zero_division=0)) if len(y_true) else None,
        "f1": float(f1_score(y_true, y_pred, zero_division=0)) if len(y_true) else None,
    }


def build_reference_baselines(
    *,
    y_train: np.ndarray,
    y_eval: np.ndarray,
    source_scores_train: np.ndarray,
    source_scores_eval: np.ndarray,
    threshold: float,
    random_seed: int,
    split_name: str,
) -> list[BaselineComparisonReport]:
    if y_train.size == 0 or y_eval.size == 0:
        return []
    majority_label = int(np.bincount(y_train.astype(int)).argmax())
    majority_predictions = np.full_like(y_eval, majority_label)
    majority_report = BaselineComparisonReport(
        name="majority_class_baseline",
        split_name=split_name,
        metric_values=_metric_bundle(y_eval, majority_predictions),
        threshold=float(majority_label),
        details_json={"majority_label": majority_label},
    )

    rng = np.random.RandomState(random_seed)
    positive_rate = float(np.mean(y_train == 1))
    random_predictions = rng.binomial(1, positive_rate, size=y_eval.shape[0]).astype(int)
    random_report = BaselineComparisonReport(
        name="stratified_random_baseline",
        split_name=split_name,
        metric_values=_metric_bundle(y_eval, random_predictions),
        threshold=positive_rate,
        details_json={"positive_rate": positive_rate, "seed": random_seed},
    )

    source_threshold = float(np.median(source_scores_train)) if source_scores_train.size else threshold
    source_predictions = (source_scores_eval >= source_threshold).astype(int)
    source_report = BaselineComparisonReport(
        name="source_rank_baseline",
        split_name=split_name,
        metric_values=_metric_bundle(y_eval, source_predictions),
        threshold=source_threshold,
        details_json={"source_threshold": source_threshold, "metric_source": "rank_score"},
    )
    return [majority_report, random_report, source_report]
