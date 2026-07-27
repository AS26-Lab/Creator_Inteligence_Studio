"""Comandos de la consolidacion de integraciones de plataforma."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PlatformOverviewCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class PlatformSyncCommand:
    creator_id: str
    platforms: tuple[str, ...]
    mode: str = "sequential"
    incremental: bool = True


@dataclass(frozen=True, slots=True)
class PlatformReportCommand:
    creator_id: str
    report_type: str

