"""Tipos cerrados para la consolidacion de conexiones de plataforma."""

from __future__ import annotations

from enum import Enum


class PlatformKind(str, Enum):
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    MANUAL_OTHER = "manual_other"


class ConnectorType(str, Enum):
    NATIVE = "native"
    MANUAL = "manual"


class CommonConnectionStatus(str, Enum):
    NOT_CONFIGURED = "not_configured"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    CONNECTED_WITH_WARNINGS = "connected_with_warnings"
    EXPIRED = "expired"
    REVOKED = "revoked"
    INSUFFICIENT_PERMISSIONS = "insufficient_permissions"
    APP_REVIEW_REQUIRED = "app_review_required"
    PRODUCT_APPROVAL_REQUIRED = "product_approval_required"
    UNAVAILABLE = "unavailable"
    ERROR = "error"
    UNKNOWN = "unknown"
