"""Funciones de soporte para Strategic Planning."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def build_planning_fingerprint(payload: Any) -> str:
    """Construye un fingerprint estable para contexto y planes."""

    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
