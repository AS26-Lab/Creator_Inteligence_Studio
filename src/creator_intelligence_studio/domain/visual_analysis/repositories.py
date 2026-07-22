"""Contratos de persistencia para analisis visual."""

from __future__ import annotations

from typing import Protocol

from .entities import VisualAnalysis, VisualEvent, VisualScene, VisualTimelineWindow


class VisualAnalysisRepository(Protocol):
    """Persistencia de analisis visual."""

    def upsert(
        self,
        analysis: VisualAnalysis,
        windows: list[VisualTimelineWindow],
        scenes: list[VisualScene],
        events: list[VisualEvent],
    ) -> VisualAnalysis: ...

    def get_by_video_asset_id(self, video_asset_id: str) -> VisualAnalysis | None: ...

    def list_windows(self, visual_analysis_id: str) -> list[VisualTimelineWindow]: ...

    def list_scenes(self, visual_analysis_id: str) -> list[VisualScene]: ...

    def list_events(self, visual_analysis_id: str) -> list[VisualEvent]: ...

    def delete_by_video_asset_id(self, video_asset_id: str) -> bool: ...
