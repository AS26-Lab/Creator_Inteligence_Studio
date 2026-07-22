"""Comandos de aplicacion para analisis acustico."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AnalyzeAcousticCommand:
    video_id: str
    force: bool = False


@dataclass(frozen=True, slots=True)
class ShowAcousticCommand:
    video_id: str


@dataclass(frozen=True, slots=True)
class TimelineAcousticCommand:
    video_id: str


@dataclass(frozen=True, slots=True)
class EventsAcousticCommand:
    video_id: str


@dataclass(frozen=True, slots=True)
class ExportAcousticCommand:
    video_id: str
    format: str


@dataclass(frozen=True, slots=True)
class DeleteAcousticCommand:
    video_id: str
