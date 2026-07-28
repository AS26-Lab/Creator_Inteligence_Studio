"""Tipos de fuentes y nivel de confianza."""

from __future__ import annotations

from enum import Enum


class SourceType(str, Enum):
    MANUAL = "manual"
    FILE = "file"
    YOUTUBE_PUBLIC = "youtube_public"
    OFFICIAL_API = "official_api"
    OFFICIAL_PUBLIC_SOURCE = "official_public_source"
    CREATOR_PROVIDED_EXPORT = "creator_provided_export"
    CREATOR_MANUAL_OBSERVATION = "creator_manual_observation"
    AUTHORIZED_REFERENCE = "authorized_reference"
    THIRD_PARTY_REPORT = "third_party_report"
    UNKNOWN = "unknown"


class TrustLevel(str, Enum):
    OFFICIAL_API = "official_api"
    OFFICIAL_PUBLIC_SOURCE = "official_public_source"
    CREATOR_PROVIDED_EXPORT = "creator_provided_export"
    CREATOR_MANUAL_OBSERVATION = "creator_manual_observation"
    AUTHORIZED_REFERENCE = "authorized_reference"
    THIRD_PARTY_REPORT = "third_party_report"
    UNKNOWN = "unknown"

