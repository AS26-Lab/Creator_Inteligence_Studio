"""Estimador local de cuota para investigacion publica de YouTube."""

from __future__ import annotations


class YouTubeQuotaTracker:
    def estimate(self, *, operation_key: str, request_count: int = 1) -> int:
        base_costs = {
            "search.list": 100,
            "videos.list": 1,
            "channels.list": 1,
            "playlists.list": 1,
            "playlistItems.list": 1,
            "videoCategories.list": 1,
            "mostPopular": 1,
        }
        return int(base_costs.get(operation_key, 1) * max(1, request_count))

