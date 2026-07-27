"""Estados de ciclo de vida de audiencia observada."""

from __future__ import annotations

from enum import Enum


class AudienceLifecycleStage(str, Enum):
    DISCOVERED = "discovered"
    SAMPLED = "sampled"
    ENGAGED = "engaged"
    CONVERTED = "converted"
    RETURNING = "returning"
    LOYALTY_CANDIDATE = "loyalty_candidate"
    INACTIVE = "inactive"
    UNKNOWN = "unknown"


class AudiencePlatformRole(str, Enum):
    DISCOVERY = "discovery"
    DEPTH = "depth"
    CONVERSION = "conversion"
    LOYALTY = "loyalty"
    COMMUNITY = "community"
    EXPERIMENTATION = "experimentation"
    MIXED = "mixed"
    UNCLEAR = "unclear"


class AudienceContentRole(str, Enum):
    ACQUISITION = "acquisition"
    ENGAGEMENT = "engagement"
    CONVERSION = "conversion"
    LOYALTY = "loyalty"
    AUTHORITY = "authority"
    COMMUNITY = "community"
    BRIDGE_CONTENT = "bridge_content"
    UNCLEAR = "unclear"

