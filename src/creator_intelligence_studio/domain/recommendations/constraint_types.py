"""Tipos de restricciones."""

from __future__ import annotations

from enum import Enum


class ConstraintType(str, Enum):
    CREATOR_BOUNDARY = "creator_boundary"
    CREATOR_PREFERENCE = "creator_preference"
    BRAND_RULE = "brand_rule"
    LANGUAGE_RULE = "language_rule"
    AUDIENCE_RULE = "audience_rule"
    PLATFORM_CAPABILITY = "platform_capability"
    MEASUREMENT_AVAILABILITY = "measurement_availability"
    TIME = "time"
    BUDGET = "budget"
    TEAM = "team"
    EQUIPMENT = "equipment"
    ASSET = "asset"
    RIGHTS = "rights"
    PRIVACY = "privacy"
    SCHEDULING = "scheduling"
    CONTENT_FREQUENCY = "content_frequency"
    OPERATIONAL = "operational"
    UNKNOWN = "unknown"
