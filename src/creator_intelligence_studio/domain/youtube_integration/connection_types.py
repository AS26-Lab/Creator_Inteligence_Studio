"""Tipos cerrados de conexion y enlace de YouTube."""

from __future__ import annotations

from enum import Enum


class YouTubeConnectionStatus(str, Enum):
    DISCONNECTED = "disconnected"
    PENDING = "pending"
    CONNECTED = "connected"
    VERIFIED = "verified"
    REVOKED = "revoked"
    ERROR = "error"


class YouTubeCredentialBackend(str, Enum):
    SYSTEM = "system"
    ENCRYPTED_LOCAL = "encrypted_local"
    DEVELOPMENT_PLAIN = "development_plain"


class YouTubeRemoteContentType(str, Enum):
    YOUTUBE_LONGFORM = "youtube_longform"
    YOUTUBE_SHORT = "youtube_short"
    PROBABLE_SHORT = "probable_short"
    LIVE = "live"
    UPCOMING = "upcoming"
    UNKNOWN = "unknown"


class YouTubeLinkMethod(str, Enum):
    EXACT_YOUTUBE_ID = "exact_youtube_id"
    MANUAL = "manual"
    EXACT_FILENAME_HINT = "exact_filename_hint"
    NORMALIZED_TITLE_AND_DATE = "normalized_title_and_date"
    METADATA_MATCH = "metadata_match"
    PROBABLE_MATCH = "probable_match"

