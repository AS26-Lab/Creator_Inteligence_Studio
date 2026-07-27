"""Versiones de API activas para TikTok."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TikTokApiVersion:
    configured_version: str = "v2"
    migration_state: str = "v2_active"


DEFAULT_TIKTOK_API_VERSION = TikTokApiVersion()

