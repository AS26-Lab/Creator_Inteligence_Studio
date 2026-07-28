"""Registro de adaptadores de fuentes de mercado."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .file_source_adapter import FileSourceAdapter
from .manual_source_adapter import ManualSourceAdapter
from .source_adapter import MarketSourceAdapter
from .youtube_public_adapter import YouTubePublicAdapter


@dataclass(frozen=True, slots=True)
class SourceRegistry:
    adapters: dict[str, MarketSourceAdapter]

    def get(self, source_type: str) -> MarketSourceAdapter | None:
        return self.adapters.get(source_type)


def build_default_source_registry(*, youtube_api_key: str | None = None) -> SourceRegistry:
    adapters: dict[str, MarketSourceAdapter] = {
        "manual": ManualSourceAdapter(),
        "file": FileSourceAdapter(),
        "youtube_public": YouTubePublicAdapter(api_key=youtube_api_key),
    }
    return SourceRegistry(adapters=adapters)

