"""Contratos de repositorio para inspecciones de medios."""

from __future__ import annotations

from typing import Protocol

from creator_intelligence_studio.domain.media.entities import VideoInspection


class VideoInspectionRepository(Protocol):
    """Persistencia de inspecciones tecnicas."""

    def upsert(self, inspection: VideoInspection) -> VideoInspection: ...

    def get_by_video_asset_id(self, video_asset_id: str) -> VideoInspection | None: ...

