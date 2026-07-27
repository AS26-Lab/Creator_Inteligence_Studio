"""Tipos de sincronizacion para la consolidacion."""

from __future__ import annotations

from enum import Enum


class SyncMode(str, Enum):
    SEQUENTIAL = "sequential"
    LIMITED_PARALLEL = "limited_parallel"
    PLATFORM_ORDERED = "platform_ordered"


class SyncGroupStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    PARTIALLY_COMPLETED = "partially_completed"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    INTERRUPTED = "interrupted"
    CANCELLED = "cancelled"
    FAILED = "failed"


class SyncItemStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"
    INTERRUPTED = "interrupted"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"
