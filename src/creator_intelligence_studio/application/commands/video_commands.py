"""Comandos de video."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RegisterVideoCommand:
    project_id: str
    file_path: str
    title: str
    notes: str | None = None


@dataclass(frozen=True, slots=True)
class VerifyVideoAvailabilityCommand:
    video_id: str

