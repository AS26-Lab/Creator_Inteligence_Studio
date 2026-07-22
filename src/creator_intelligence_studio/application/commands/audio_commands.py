"""Comandos de preparacion de audio."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PrepareAudioCommand:
    video_id: str
    force: bool = False


@dataclass(frozen=True, slots=True)
class ShowPreparedAudioCommand:
    video_id: str


@dataclass(frozen=True, slots=True)
class VerifyPreparedAudioCommand:
    video_id: str


@dataclass(frozen=True, slots=True)
class ClearAudioCacheCommand:
    video_id: str
