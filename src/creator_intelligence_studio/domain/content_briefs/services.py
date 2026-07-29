"""Utilidades del dominio de Content Briefs."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def _json_default(value: Any):
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if hasattr(value, "value"):
        return value.value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def build_brief_fingerprint(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=_json_default)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

