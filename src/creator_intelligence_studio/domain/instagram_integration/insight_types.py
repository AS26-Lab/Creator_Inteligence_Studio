"""Tipos de insights de Instagram."""

from __future__ import annotations

from enum import Enum


class InstagramInsightScope(str, Enum):
    ACCOUNT = "account"
    MEDIA = "media"


class InstagramInsightPeriod(str, Enum):
    DAY = "day"
    WEEK = "week"
    DAYS_28 = "days_28"
    MONTH = "month"
    LIFETIME = "lifetime"
    TOTAL_OVER_RANGE = "total_over_range"

