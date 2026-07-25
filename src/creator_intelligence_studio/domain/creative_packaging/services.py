"""Reglas de dominio para packaging creativo."""

from __future__ import annotations

import hashlib
import json


def _stable_json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def build_creative_packaging_fingerprint(payload: dict[str, object]) -> str:
    return hashlib.sha256(_stable_json(payload).encode("utf-8")).hexdigest()

