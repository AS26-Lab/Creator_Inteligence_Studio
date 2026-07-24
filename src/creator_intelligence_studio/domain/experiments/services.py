"""Servicios y helpers puros para Experiments and Verifiable Learning."""

from __future__ import annotations

import json
from hashlib import sha256


def build_experiment_fingerprint(payload: dict[str, object]) -> str:
    normalized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(normalized.encode("utf-8")).hexdigest()

