"""Tipos de alternativas."""

from __future__ import annotations

from enum import Enum


class AlternativeType(str, Enum):
    LOWER_RISK = "lower_risk_alternative"
    LOWER_EFFORT = "lower_effort_alternative"
    HIGHER_LEARNING_VALUE = "higher_learning_value_alternative"
    EVERGREEN = "evergreen_alternative"
    PLATFORM = "platform_alternative"
    FORMAT = "format_alternative"
    AUDIENCE = "audience_alternative"
    PACKAGING = "packaging_alternative"
    TIMING = "timing_alternative"
    RESEARCH_FIRST = "research_first_alternative"
    DO_NOTHING = "do_nothing_alternative"
