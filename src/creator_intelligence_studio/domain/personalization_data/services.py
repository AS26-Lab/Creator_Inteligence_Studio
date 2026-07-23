"""Funciones de dominio para datasets de personalizacion."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .entities import CreatorDatasetSnapshot
from .value_objects import PersonalizationDatasetOptions, PersonalizationDatasetStatus, normalize_personalization_dataset_options


def _json_dumps(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def build_personalization_configuration_fingerprint(options: PersonalizationDatasetOptions) -> str:
    normalized = normalize_personalization_dataset_options(options)
    return hashlib.sha256(_json_dumps(normalized.to_dict()).encode("utf-8")).hexdigest()


def build_personalization_source_fingerprint(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_json_dumps(payload).encode("utf-8")).hexdigest()


def is_personalization_dataset_stale(
    snapshot: CreatorDatasetSnapshot | None,
    *,
    source_fingerprint: str | None,
    configuration_fingerprint: str | None = None,
) -> bool:
    if snapshot is None:
        return True
    if snapshot.status in {PersonalizationDatasetStatus.FAILED, PersonalizationDatasetStatus.STALE}:
        return True
    if source_fingerprint is None:
        return True
    if snapshot.source_fingerprint != source_fingerprint:
        return True
    if configuration_fingerprint is not None and snapshot.configuration_fingerprint != configuration_fingerprint:
        return True
    return False
