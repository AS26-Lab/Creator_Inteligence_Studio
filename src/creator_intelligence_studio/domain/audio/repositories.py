"""Contratos de persistencia para audio preparado."""

from __future__ import annotations

from abc import ABC, abstractmethod

from creator_intelligence_studio.domain.audio.entities import PreparedAudioAsset


class PreparedAudioRepository(ABC):
    """Contrato para persistir artefactos de audio preparados."""

    @abstractmethod
    def upsert(self, asset: PreparedAudioAsset) -> PreparedAudioAsset:
        raise NotImplementedError

    @abstractmethod
    def get_by_video_asset_id(self, video_asset_id: str) -> PreparedAudioAsset | None:
        raise NotImplementedError

    @abstractmethod
    def delete_by_video_asset_id(self, video_asset_id: str) -> bool:
        raise NotImplementedError
