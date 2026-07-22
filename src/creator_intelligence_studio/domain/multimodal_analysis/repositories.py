"""Contratos de persistencia para analisis multimodal."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .entities import MultimodalAnalysis, MultimodalMomentCandidate, MultimodalTimelineWindow


class MultimodalAnalysisRepository(ABC):
    """Persistencia de analisis multimodal."""

    @abstractmethod
    def upsert(
        self,
        analysis: MultimodalAnalysis,
        windows: list[MultimodalTimelineWindow],
        candidates: list[MultimodalMomentCandidate],
    ) -> MultimodalAnalysis:
        raise NotImplementedError

    @abstractmethod
    def get_by_video_asset_id(self, video_asset_id: str) -> MultimodalAnalysis | None:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, multimodal_analysis_id: str) -> MultimodalAnalysis | None:
        raise NotImplementedError

    @abstractmethod
    def list_windows(self, multimodal_analysis_id: str) -> list[MultimodalTimelineWindow]:
        raise NotImplementedError

    @abstractmethod
    def list_candidates(self, multimodal_analysis_id: str) -> list[MultimodalMomentCandidate]:
        raise NotImplementedError

    @abstractmethod
    def get_candidate_by_id(self, candidate_id: str) -> MultimodalMomentCandidate | None:
        raise NotImplementedError

    @abstractmethod
    def delete_by_video_asset_id(self, video_asset_id: str) -> bool:
        raise NotImplementedError

