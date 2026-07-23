"""Carga reproducible de snapshots de dataset para entrenamiento."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from creator_intelligence_studio.application.services.personalization_dataset_service import PersonalizationDatasetService
from creator_intelligence_studio.domain.personalization_data.entities import CreatorDatasetExample, CreatorDatasetSnapshot
from creator_intelligence_studio.domain.personalization_data.value_objects import PersonalizationLabel
from creator_intelligence_studio.domain.personalization_models.errors import PersonalizationModelStateError, PersonalizationModelValidationError
from creator_intelligence_studio.infrastructure.personalization_models.feature_pipeline import (
    FeaturePolicyReport,
    build_feature_matrix,
    build_feature_policy,
)


@dataclass(frozen=True, slots=True)
class PersonalizationTrainingDataset:
    snapshot: CreatorDatasetSnapshot
    examples: tuple[CreatorDatasetExample, ...]
    feature_policy: FeaturePolicyReport
    feature_names: tuple[str, ...]
    X_train: np.ndarray
    y_train: np.ndarray
    sample_weight_train: np.ndarray
    X_validation: np.ndarray
    y_validation: np.ndarray
    sample_weight_validation: np.ndarray
    X_test: np.ndarray
    y_test: np.ndarray
    sample_weight_test: np.ndarray
    train_examples: tuple[CreatorDatasetExample, ...]
    validation_examples: tuple[CreatorDatasetExample, ...]
    test_examples: tuple[CreatorDatasetExample, ...]
    excluded_examples: tuple[CreatorDatasetExample, ...]
    split_counts: dict[str, int]
    label_counts: dict[str, int]
    excluded_count: int
    missing_feature_count: int
    unexpected_feature_names: tuple[str, ...]

    @property
    def has_validation(self) -> bool:
        return self.X_validation.size > 0 and self.y_validation.size > 0

    @property
    def has_test(self) -> bool:
        return self.X_test.size > 0 and self.y_test.size > 0


def _encode_label(example: CreatorDatasetExample) -> int | None:
    if example.label == PersonalizationLabel.POSITIVE:
        return 1
    if example.label == PersonalizationLabel.NEGATIVE:
        return 0
    return None


def _split_examples(examples: list[CreatorDatasetExample]) -> tuple[list[CreatorDatasetExample], list[CreatorDatasetExample], list[CreatorDatasetExample], list[CreatorDatasetExample]]:
    train: list[CreatorDatasetExample] = []
    validation: list[CreatorDatasetExample] = []
    test: list[CreatorDatasetExample] = []
    excluded: list[CreatorDatasetExample] = []
    for example in examples:
        if example.label in {PersonalizationLabel.EXCLUDED, PersonalizationLabel.NEUTRAL_OR_UNCERTAIN} or example.exclusion_reason:
            excluded.append(example)
            continue
        if example.split_name.value == "train":
            train.append(example)
        elif example.split_name.value == "validation":
            validation.append(example)
        elif example.split_name.value == "test":
            test.append(example)
        else:
            excluded.append(example)
    return train, validation, test, excluded


def load_training_dataset(
    *,
    snapshot: CreatorDatasetSnapshot,
    examples: list[CreatorDatasetExample],
    feature_schema,
    strict_feature_policy: bool = True,
) -> PersonalizationTrainingDataset:
    feature_policy = build_feature_policy(feature_schema)
    train_examples, validation_examples, test_examples, excluded_examples = _split_examples(examples)

    def _build_arrays(rows: list[CreatorDatasetExample]) -> tuple[np.ndarray, np.ndarray, np.ndarray, int, tuple[str, ...]]:
        matrix, feature_names, missing_feature_count, unexpected = build_feature_matrix(rows, feature_policy, strict=strict_feature_policy)
        labels: list[int] = []
        weights: list[float] = []
        for row in rows:
            encoded = _encode_label(row)
            if encoded is None:
                raise PersonalizationModelValidationError("Se esperaba solo positive/negative en el conjunto entrenable.")
            labels.append(encoded)
            weights.append(float(row.sample_weight))
        return matrix, np.array(labels, dtype=int), np.array(weights, dtype=float), missing_feature_count, unexpected

    X_train, y_train, w_train, missing_train, unexpected_train = _build_arrays(train_examples)
    X_validation, y_validation, w_validation, missing_validation, unexpected_validation = _build_arrays(validation_examples)
    X_test, y_test, w_test, missing_test, unexpected_test = _build_arrays(test_examples)
    unexpected = tuple(sorted(set(unexpected_train) | set(unexpected_validation) | set(unexpected_test)))
    split_counts = {
        "train": len(train_examples),
        "validation": len(validation_examples),
        "test": len(test_examples),
        "excluded": len(excluded_examples),
    }
    label_counts = {
        "positive": sum(1 for example in examples if example.label == PersonalizationLabel.POSITIVE),
        "negative": sum(1 for example in examples if example.label == PersonalizationLabel.NEGATIVE),
        "neutral_or_uncertain": sum(1 for example in examples if example.label == PersonalizationLabel.NEUTRAL_OR_UNCERTAIN),
        "excluded": sum(1 for example in examples if example.label == PersonalizationLabel.EXCLUDED or example.exclusion_reason),
    }
    return PersonalizationTrainingDataset(
        snapshot=snapshot,
        examples=tuple(examples),
        feature_policy=feature_policy,
        feature_names=tuple(entry.name for entry in feature_policy.entries if entry.included),
        X_train=X_train,
        y_train=y_train,
        sample_weight_train=w_train,
        X_validation=X_validation,
        y_validation=y_validation,
        sample_weight_validation=w_validation,
        X_test=X_test,
        y_test=y_test,
        sample_weight_test=w_test,
        train_examples=tuple(train_examples),
        validation_examples=tuple(validation_examples),
        test_examples=tuple(test_examples),
        excluded_examples=tuple(excluded_examples),
        split_counts=split_counts,
        label_counts=label_counts,
        excluded_count=len(excluded_examples),
        missing_feature_count=missing_train + missing_validation + missing_test,
        unexpected_feature_names=unexpected,
    )
