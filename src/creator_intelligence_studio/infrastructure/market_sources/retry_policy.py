"""Politica simple de retry para consultas publicas."""

from __future__ import annotations

import random


def is_retryable_status(status_code: int) -> bool:
    return status_code == 429 or 500 <= status_code < 600


def backoff_delay(attempt: int) -> float:
    base = min(2 ** max(0, attempt - 1), 60)
    return base + random.random()

