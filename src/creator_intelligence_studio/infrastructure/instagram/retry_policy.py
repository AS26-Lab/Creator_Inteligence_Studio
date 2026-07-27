"""Politica simple de reintentos para Instagram."""

from __future__ import annotations

import random


def is_retryable_status(status_code: int) -> bool:
    return status_code in {429, 500, 502, 503, 504}


def backoff_delay(attempt: int, *, base: float = 0.5, cap: float = 30.0) -> float:
    delay = min(cap, base * (2 ** max(0, attempt - 1)))
    jitter = random.uniform(0.0, min(delay * 0.1, 1.0))
    return delay + jitter

