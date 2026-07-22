"""Comandos de inspeccion tecnica de medios."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InspectVideoCommand:
    video_id: str
    force: bool = False


@dataclass(frozen=True, slots=True)
class ShowVideoInspectionCommand:
    video_id: str

