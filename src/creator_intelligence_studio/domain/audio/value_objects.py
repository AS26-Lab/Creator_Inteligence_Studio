"""Objetos de valor para preparacion tecnica de audio."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class AudioStreamCandidate:
    """Candidato tipado para la seleccion de un stream de audio."""

    index: int
    codec_name: str | None
    codec_long_name: str | None
    channels: int | None
    channel_layout: str | None
    sample_rate_hz: int | None
    language: str | None
    is_default: bool
    tags: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "codec_name": self.codec_name,
            "codec_long_name": self.codec_long_name,
            "channels": self.channels,
            "channel_layout": self.channel_layout,
            "sample_rate_hz": self.sample_rate_hz,
            "language": self.language,
            "is_default": self.is_default,
            "tags": dict(self.tags),
        }


@dataclass(frozen=True, slots=True)
class AudioPreparationConfig:
    """Configuracion explicita de normalizacion de audio."""

    sample_rate_hz: int = 16000
    channels: int = 1
    bit_depth: int = 16
    cache_version: str = "v1"
    preferred_language: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "sample_rate_hz": self.sample_rate_hz,
            "channels": self.channels,
            "bit_depth": self.bit_depth,
            "cache_version": self.cache_version,
            "preferred_language": self.preferred_language,
        }
