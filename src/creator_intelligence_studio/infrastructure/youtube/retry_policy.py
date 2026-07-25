"""Politica de reintento para lecturas de YouTube."""

from __future__ import annotations

import random


TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}


def is_retryable_status(status_code: int) -> bool:
    return status_code in TRANSIENT_STATUS_CODES


def backoff_delay(*, attempt: int, base_seconds: float = 0.5, max_seconds: float = 30.0, jitter: float = 0.2) -> float:
    raw = min(max_seconds, base_seconds * (2 ** max(0, attempt - 1)))
    spread = raw * jitter
    return max(0.0, raw + random.uniform(-spread, spread))

