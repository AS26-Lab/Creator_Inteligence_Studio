"""Comandos de aplicacion para analisis visual."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AnalyzeVisualCommand:
    video_id: str
    force: bool = False


@dataclass(frozen=True, slots=True)
class ShowVisualCommand:
    video_id: str


@dataclass(frozen=True, slots=True)
class TimelineVisualCommand:
    video_id: str


@dataclass(frozen=True, slots=True)
class ScenesVisualCommand:
    video_id: str


@dataclass(frozen=True, slots=True)
class EventsVisualCommand:
    video_id: str


@dataclass(frozen=True, slots=True)
class ExportVisualCommand:
    video_id: str
    format: str


@dataclass(frozen=True, slots=True)
class DeleteVisualCommand:
    video_id: str
