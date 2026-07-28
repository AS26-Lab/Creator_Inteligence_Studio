"""Utilidades y valores comunes del dominio de mercado."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any


def current_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def json_loads(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return fallback
    return fallback if parsed is None else parsed


def normalize_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def normalize_url(value: str | None) -> str | None:
    normalized = normalize_text(value)
    return normalized or None


def normalize_identifier(value: str | None) -> str:
    return normalize_text(value).lower()


def normalize_platform(value: str | None) -> str:
    return normalize_identifier(value)


def safe_slug(value: str | None) -> str:
    normalized = normalize_identifier(value)
    slug = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    return slug or "market"


def build_market_fingerprint(*parts: object) -> str:
    payload = "|".join("" if part is None else str(part) for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

