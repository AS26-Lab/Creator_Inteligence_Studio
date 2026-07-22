"""Contratos de persistencia para analisis acustico."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .entities import AcousticAnalysis, AcousticEvent, AcousticTimelineWindow


class AcousticAnalysisRepository(ABC):
    """Contrato para persistencia de analisis acustico."""

    @abstractmethod
    def upsert(
        self,
        analysis: AcousticAnalysis,
        windows: list[AcousticTimelineWindow],
        events: list[AcousticEvent],
    ) -> AcousticAnalysis:
        raise NotImplementedError

    @abstractmethod
    def get_by_video_asset_id(self, video_asset_id: str) -> AcousticAnalysis | None:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, acoustic_analysis_id: str) -> AcousticAnalysis | None:
        raise NotImplementedError

    @abstractmethod
    def list_windows(self, acoustic_analysis_id: str) -> list[AcousticTimelineWindow]:
        raise NotImplementedError

    @abstractmethod
    def list_events(self, acoustic_analysis_id: str) -> list[AcousticEvent]:
        raise NotImplementedError

    @abstractmethod
    def delete_by_video_asset_id(self, video_asset_id: str) -> bool:
        raise NotImplementedError
