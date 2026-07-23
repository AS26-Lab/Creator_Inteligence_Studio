"""Evaluacion de modelos personalizados."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    split_name: str
    metric_values: dict[str, float | None]
    support: int
    predictions: list[dict[str, Any]]

    def to_dict(self) -> dict[str, object]:
        return {
            "split_name": self.split_name,
            "metric_values": dict(self.metric_values),
            "support": self.support,
            "predictions": [dict(prediction) for prediction in self.predictions],
        }


def _specificity_from_confusion_matrix(matrix: np.ndarray) -> float | None:
    if matrix.size != 4:
        return None
    tn, fp, fn, tp = matrix.ravel()
    denominator = tn + fp
    if denominator <= 0:
        return None
    return float(tn / denominator)


def evaluate_predictions(
    *,
    split_name: str,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_score: np.ndarray,
    threshold: float,
    support_ids: list[str],
    explanations: list[dict[str, Any]],
) -> EvaluationResult:
    metric_values: dict[str, float | None] = {
        "accuracy": None,
        "balanced_accuracy": None,
        "precision": None,
        "recall": None,
        "specificity": None,
        "f1": None,
        "roc_auc": None,
        "pr_auc": None,
        "log_loss": None,
    }
    support = int(len(y_true))
    if support:
        metric_values["accuracy"] = float(accuracy_score(y_true, y_pred))
        metric_values["balanced_accuracy"] = float(balanced_accuracy_score(y_true, y_pred))
        metric_values["precision"] = float(precision_score(y_true, y_pred, zero_division=0))
        metric_values["recall"] = float(recall_score(y_true, y_pred, zero_division=0))
        metric_values["f1"] = float(f1_score(y_true, y_pred, zero_division=0))
        matrix = confusion_matrix(y_true, y_pred, labels=[0, 1])
        metric_values["specificity"] = _specificity_from_confusion_matrix(matrix)
        if len(set(y_true.tolist())) == 2:
            metric_values["roc_auc"] = float(roc_auc_score(y_true, y_score))
            metric_values["pr_auc"] = float(average_precision_score(y_true, y_score))
            metric_values["log_loss"] = float(log_loss(y_true, np.column_stack([1 - y_score, y_score]), labels=[0, 1]))
    predictions: list[dict[str, Any]] = []
    for example_id, truth, prediction, score, explanation in zip(support_ids, y_true.tolist(), y_pred.tolist(), y_score.tolist(), explanations):
        predictions.append(
            {
                "dataset_example_id": example_id,
                "true_label": "positive" if int(truth) == 1 else "negative",
                "predicted_label": "positive" if int(prediction) == 1 else "negative",
                "positive_score": float(score),
                "decision_threshold": threshold,
                "is_correct": int(truth) == int(prediction),
                "explanation_json": explanation,
            }
        )
    return EvaluationResult(split_name=split_name, metric_values=metric_values, support=support, predictions=predictions)
