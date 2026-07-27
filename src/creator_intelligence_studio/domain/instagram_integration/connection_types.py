"""Tipos cerrados para la integracion de Instagram."""

from __future__ import annotations

from enum import Enum


class InstagramAuthProvider(str, Enum):
    INSTAGRAM_LOGIN = "instagram_login"
    FACEBOOK_LOGIN = "facebook_login"


class InstagramConnectionStatus(str, Enum):
    PENDING = "pending"
    CONNECTED = "connected"
    VERIFIED = "verified"
    DISCONNECTED = "disconnected"
    REVOKED = "revoked"
    ERROR = "error"


class InstagramProfessionalAccountType(str, Enum):
    BUSINESS = "business"
    CREATOR = "creator"
    PERSONAL = "personal"
    UNKNOWN = "unknown"


class InstagramAccessLevel(str, Enum):
    STANDARD_ACCESS = "standard_access"
    ADVANCED_ACCESS = "advanced_access"
    DEVELOPMENT_MODE = "development_mode"
    LIVE_MODE = "live_mode"
    TESTER_ACCOUNT_ONLY = "tester_account_only"
    UNKNOWN = "unknown"


class InstagramAppAccessStatus(str, Enum):
    DEVELOPMENT_MODE = "development_mode"
    LIVE_MODE = "live_mode"
    STANDARD_ACCESS = "standard_access"
    ADVANCED_ACCESS = "advanced_access"
    APP_REVIEW_REQUIRED = "app_review_required"
    BUSINESS_VERIFICATION_REQUIRED = "business_verification_required"
    TESTER_ACCOUNT_ONLY = "tester_account_only"
    UNKNOWN = "unknown"


class InstagramMediaType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"
    CAROUSEL_ALBUM = "carousel_album"
    REELS = "reels"
    STORIES = "stories"
    LIVE = "live"
    UNKNOWN = "unknown"


class InstagramContentType(str, Enum):
    INSTAGRAM_REEL = "instagram_reel"
    INSTAGRAM_POST = "instagram_post"
    INSTAGRAM_VIDEO = "instagram_video"
    INSTAGRAM_CAROUSEL = "instagram_carousel"
    INSTAGRAM_STORY = "instagram_story"
    INSTAGRAM_LIVE = "instagram_live"
    INSTAGRAM_UNKNOWN = "instagram_unknown"


class InstagramLinkMethod(str, Enum):
    EXACT_INSTAGRAM_ID = "exact_instagram_id"
    EXACT_PERMALINK = "exact_permalink"
    MANUAL = "manual"
    NORMALIZED_CAPTION_AND_DATE = "normalized_caption_and_date"
    MEDIA_TIMESTAMP = "media_timestamp"
    METADATA_MATCH = "metadata_match"
    PROBABLE_MATCH = "probable_match"

