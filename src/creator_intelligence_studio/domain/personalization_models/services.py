"""Reglas de dominio para modelos personalizados."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .entities import PersonalizationTrainingRun, PersonalizationModelRegistryEntry
from .value_objects import PersonalizationModelOptions, PersonalizationModelRegistryStatus, PersonalizationModelTrainingStatus, normalize_personalization_model_options


def build_personalization_model_configuration_fingerprint(options: PersonalizationModelOptions) -> str:
    normalized = normalize_personalization_model_options(options)
    payload = json.dumps(normalized.to_dict(), ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_personalization_model_source_fingerprint(payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def is_personalization_model_stale(
    run: PersonalizationTrainingRun,
    *,
    source_fingerprint: str,
    configuration_fingerprint: str,
    artifact_fingerprint: str | None = None,
) -> bool:
    if run.status in {
        PersonalizationModelTrainingStatus.FAILED,
        PersonalizationModelTrainingStatus.CANCELLED,
        PersonalizationModelTrainingStatus.BLOCKED,
    }:
        return True
    if run.source_fingerprint != source_fingerprint:
        return True
    if run.configuration_fingerprint != configuration_fingerprint:
        return True
    if artifact_fingerprint is not None and run.artifact_fingerprint != artifact_fingerprint:
        return True
    return False


def is_model_registry_compatible(entry: PersonalizationModelRegistryEntry | None) -> bool:
    if entry is None:
        return False
    return entry.status in {
        PersonalizationModelRegistryStatus.CANDIDATE,
        PersonalizationModelRegistryStatus.ACTIVE,
        PersonalizationModelRegistryStatus.INACTIVE,
    }
