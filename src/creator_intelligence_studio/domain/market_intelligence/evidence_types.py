"""Tipos de evidencia para inteligencia de mercado."""

from __future__ import annotations

from enum import Enum


class EvidenceType(str, Enum):
    DIRECT_OBSERVATION = "direct_observation"
    PUBLIC_METADATA = "public_metadata"
    PUBLIC_METRIC_SNAPSHOT = "public_metric_snapshot"
    CREATOR_OWNED_ANALYTICS = "creator_owned_analytics"
    MANUAL_IMPORT = "manual_import"
    REPEATED_PATTERN = "repeated_pattern"
    TEMPORAL_CHANGE = "temporal_change"
    CROSS_SOURCE_CONFIRMATION = "cross_source_confirmation"
    HUMAN_NOTE = "human_note"
    INFERRED_RELATIONSHIP = "inferred_relationship"
    CONTRADICTORY_EVIDENCE = "contradictory_evidence"

