"""Servicios puros del dominio de mercado."""

from __future__ import annotations

from collections.abc import Iterable

from .value_objects import build_market_fingerprint, normalize_text, safe_slug


def build_market_topic_key(*parts: object) -> str:
    return safe_slug("-".join("" if part is None else str(part) for part in parts))


def estimate_evidence_strength(values: Iterable[float | None]) -> float:
    valid = [value for value in values if value is not None]
    if not valid:
        return 0.0
    return min(1.0, len(valid) / 5.0)


def build_comparability_status(*, same_platform: bool, same_semantics: bool, aligned_window: bool) -> str:
    if same_platform and same_semantics and aligned_window:
        return "directly_comparable"
    if same_semantics and aligned_window:
        return "comparable_with_normalization"
    if same_semantics:
        return "directional_only"
    return "not_comparable"

