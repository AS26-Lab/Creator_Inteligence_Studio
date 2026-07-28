"""Servicio oficial de investigacion publica en YouTube."""

from __future__ import annotations

from typing import Any

from creator_intelligence_studio.infrastructure.market_sources.youtube_public_adapter import YouTubePublicAdapter


class YouTubePublicResearchService:
    def __init__(self, adapter: YouTubePublicAdapter) -> None:
        self.adapter = adapter

    def search_videos(self, **kwargs: Any):
        return self.adapter.search_videos(**kwargs)

    def list_channels(self, **kwargs: Any):
        return self.adapter.list_channels(**kwargs)

    def list_videos(self, **kwargs: Any):
        return self.adapter.list_videos(**kwargs)

    def list_playlists(self, **kwargs: Any):
        return self.adapter.list_playlists(**kwargs)

    def list_playlist_items(self, **kwargs: Any):
        return self.adapter.list_playlist_items(**kwargs)

    def list_video_categories(self, **kwargs: Any):
        return self.adapter.list_video_categories(**kwargs)

    def most_popular(self, **kwargs: Any):
        return self.adapter.most_popular(**kwargs)

