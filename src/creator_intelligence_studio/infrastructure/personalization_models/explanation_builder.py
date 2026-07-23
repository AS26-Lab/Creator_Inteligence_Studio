"""Explicaciones tecnicas para predicciones personalizadas."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True, slots=True)
class PersonalizationPredictionExplanation:
    score: float
    threshold: float
    bias: float
    top_positive_features: tuple[dict[str, Any], ...]
    top_negative_features: tuple[dict[str, Any], ...]
    feature_contributions: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "score": self.score,
            "threshold": self.threshold,
            "bias": self.bias,
            "top_positive_features": [dict(item) for item in self.top_positive_features],
            "top_negative_features": [dict(item) for item in self.top_negative_features],
            "feature_contributions": [dict(item) for item in self.feature_contributions],
        }


def build_weight_explanations(feature_names: tuple[str, ...], coefficients: np.ndarray) -> tuple[dict[str, Any], ...]:
    contributions: list[dict[str, Any]] = []
    for name, value in zip(feature_names, coefficients.tolist() if hasattr(coefficients, "tolist") else list(coefficients)):
        contributions.append({"feature": name, "coefficient": float(value), "magnitude": float(abs(value)), "direction": "positive" if value >= 0 else "negative"})
    return tuple(sorted(contributions, key=lambda item: item["magnitude"], reverse=True))


def build_prediction_explanation(
    *,
    feature_names: tuple[str, ...],
    raw_feature_values: np.ndarray,
    transformed_values: np.ndarray,
    coefficients: np.ndarray,
    intercept: float,
    threshold: float,
) -> PersonalizationPredictionExplanation:
    weighted = coefficients * transformed_values
    contributions = []
    for name, raw_value, transformed_value, coefficient, contribution in zip(feature_names, raw_feature_values.tolist(), transformed_values.tolist(), coefficients.tolist(), weighted.tolist()):
        contributions.append(
            {
                "feature": name,
                "raw_value": None if raw_value is None else float(raw_value),
                "transformed_value": float(transformed_value),
                "coefficient": float(coefficient),
                "contribution": float(contribution),
                "direction": "positive" if contribution >= 0 else "negative",
            }
        )
    ordered = sorted(contributions, key=lambda item: abs(item["contribution"]), reverse=True)
    positives = tuple(item for item in ordered if item["contribution"] >= 0)[:5]
    negatives = tuple(item for item in ordered if item["contribution"] < 0)[:5]
    score = float(1.0 / (1.0 + np.exp(-(intercept + float(np.sum(weighted))))))
    return PersonalizationPredictionExplanation(
        score=score,
        threshold=threshold,
        bias=float(intercept),
        top_positive_features=positives,
        top_negative_features=negatives,
        feature_contributions=tuple(ordered),
    )
