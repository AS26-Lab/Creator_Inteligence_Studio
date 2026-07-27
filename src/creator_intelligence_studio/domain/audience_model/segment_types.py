"""Tipos de segmentos de audiencia observada."""

from __future__ import annotations

from enum import Enum


class AudienceSegmentType(str, Enum):
    SYSTEM_DEFINED = "system_defined"
    CREATOR_DEFINED = "creator_defined"
    EVIDENCE_SUGGESTED = "evidence_suggested"


class AudienceSegmentScope(str, Enum):
    CREATOR = "creator"
    PLATFORM = "platform"
    CONTENT = "content"
    TOPIC = "topic"
    FORMAT = "format"
    JOURNEY = "journey"
    COHORT = "cohort"
    UNKNOWN = "unknown"

