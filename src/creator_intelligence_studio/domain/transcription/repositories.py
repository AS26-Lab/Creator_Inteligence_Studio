"""Contratos de persistencia para transcripcion local."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .entities import Transcription, TranscriptionSegment


class TranscriptionRepository(ABC):
    """Contrato para persistencia de transcripciones."""

    @abstractmethod
    def upsert(self, transcription: Transcription, segments: list[TranscriptionSegment]) -> Transcription:
        raise NotImplementedError

    @abstractmethod
    def get_by_video_asset_id(self, video_asset_id: str) -> Transcription | None:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, transcription_id: str) -> Transcription | None:
        raise NotImplementedError

    @abstractmethod
    def list_segments(self, transcription_id: str) -> list[TranscriptionSegment]:
        raise NotImplementedError

    @abstractmethod
    def delete_by_video_asset_id(self, video_asset_id: str) -> bool:
        raise NotImplementedError


