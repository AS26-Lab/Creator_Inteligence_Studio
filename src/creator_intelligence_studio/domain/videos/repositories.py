"""Contratos de persistencia para videos."""

from __future__ import annotations

from typing import Protocol

from creator_intelligence_studio.domain.videos.entities import VideoAsset


class VideoRepository(Protocol):
    """Operaciones para almacenar videos."""

    def create(self, video: VideoAsset) -> VideoAsset: ...

    def list_by_project(self, project_id: str) -> list[VideoAsset]: ...

    def get_by_id(self, video_id: str) -> VideoAsset | None: ...

