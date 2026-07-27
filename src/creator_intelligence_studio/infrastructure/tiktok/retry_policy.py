"""Politica de reintento para TikTok."""

from __future__ import annotations

import random


def is_retryable_status(status_code: int | None, error_code: str | None = None) -> bool:
    if status_code is None:
        return False
    if status_code in {429}:
        return True
    if 500 <= status_code <= 599:
        return True
    if error_code in {"rate_limit_exceeded", "internal_error", "temporarily_unavailable"}:
        return True
    return False


def backoff_delay(attempt: int, *, base_seconds: float = 0.5, max_seconds: float = 30.0) -> float:
    jitter = random.uniform(0.0, 0.25)
    delay = min(max_seconds, base_seconds * (2 ** max(attempt - 1, 0)))
    return delay + jitter

