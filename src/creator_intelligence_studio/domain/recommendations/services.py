"""Funciones de dominio para recomendaciones."""

from __future__ import annotations

import hashlib
import json


def build_recommendation_fingerprint(payload: object) -> str:
    normalized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
