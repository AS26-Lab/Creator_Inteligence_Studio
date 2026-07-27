"""Tipos cerrados para la integracion TikTok."""

from __future__ import annotations

from enum import Enum


class TikTokConnectionStatus(str, Enum):
    PENDING = "pending"
    CONNECTED = "connected"
    VERIFIED = "verified"
    DISCONNECTED = "disconnected"
    REVOKED = "revoked"
    ERROR = "error"


class TikTokAccessLevel(str, Enum):
    LOGIN_KIT_ENABLED = "login_kit_enabled"
    DISPLAY_API_ENABLED = "display_api_enabled"
    SCOPE_APPROVED = "scope_approved"
    DEVELOPMENT_MODE = "development_mode"
    PRODUCTION_MODE = "production_mode"
    APP_REVIEW_REQUIRED = "app_review_required"
    PRODUCT_NOT_APPROVED = "product_not_approved"
    SCOPE_NOT_APPROVED = "scope_not_approved"
    UNKNOWN = "unknown"


class TikTokProductApprovalState(str, Enum):
    LOGIN_KIT_ENABLED = "login_kit_enabled"
    DISPLAY_API_ENABLED = "display_api_enabled"
    SCOPE_APPROVED = "scope_approved"
    DEVELOPMENT_MODE = "development_mode"
    PRODUCTION_MODE = "production_mode"
    APP_REVIEW_REQUIRED = "app_review_required"
    PRODUCT_NOT_APPROVED = "product_not_approved"
    SCOPE_NOT_APPROVED = "scope_not_approved"
    UNKNOWN = "unknown"


class TikTokRemoteStatus(str, Enum):
    PUBLIC = "public"
    UNAVAILABLE = "unavailable"
    NO_LONGER_RETURNED = "no_longer_returned"
    ACCESS_CHANGED = "access_changed"
    UNKNOWN = "unknown"


class TikTokLinkMethod(str, Enum):
    EXACT_TIKTOK_ID = "exact_tiktok_id"
    EXACT_SHARE_URL = "exact_share_url"
    MANUAL = "manual"
    NORMALIZED_DESCRIPTION_AND_DATE = "normalized_description_and_date"
    CREATE_TIME_MATCH = "create_time_match"
    METADATA_MATCH = "metadata_match"
    PROBABLE_MATCH = "probable_match"

