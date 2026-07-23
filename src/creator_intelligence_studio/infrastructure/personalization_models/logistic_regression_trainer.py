"""Entrenamiento baseline con regresion logistica."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


@dataclass(frozen=True, slots=True)
class TrainingOutcome:
    pipeline: Pipeline
    class_weight: str | None
    coefficient_count: int
    feature_names: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "class_weight": self.class_weight,
            "coefficient_count": self.coefficient_count,
            "feature_names": list(self.feature_names),
        }


def train_logistic_regression_baseline(
    X: np.ndarray,
    y: np.ndarray,
    *,
    regularization_c: float,
    max_iter: int,
    random_seed: int,
    feature_names: tuple[str, ...],
    class_weight_mode: str = "balanced",
) -> TrainingOutcome:
    if X.size == 0:
        raise ValueError("No hay datos para entrenar el baseline.")
    positive = int(np.sum(y == 1))
    negative = int(np.sum(y == 0))
    class_weight: str | None
    if class_weight_mode == "balanced" and positive != negative:
        class_weight = "balanced"
    else:
        class_weight = None
    pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            (
                "model",
                LogisticRegression(
                    C=regularization_c,
                    max_iter=max_iter,
                    random_state=random_seed,
                    class_weight=class_weight,
                    solver="lbfgs",
                ),
            ),
        ]
    )
    pipeline.fit(X, y)
    return TrainingOutcome(
        pipeline=pipeline,
        class_weight=class_weight,
        coefficient_count=int(getattr(pipeline.named_steps["model"], "coef_", np.empty((0, 0))).size),
        feature_names=feature_names,
    )
