"""Servicios de dominio para evaluacion operativa."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict

from .entities import OperationalEvaluationScenarioDefinition


def build_operational_evaluation_configuration_fingerprint(payload: dict[str, object]) -> str:
    digest = hashlib.sha256()
    digest.update(json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8"))
    return digest.hexdigest()


def build_scenario_fingerprint(scenario: OperationalEvaluationScenarioDefinition) -> str:
    return build_operational_evaluation_configuration_fingerprint(asdict(scenario))
