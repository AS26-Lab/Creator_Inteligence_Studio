"""Cohortes del sistema para Analytics Lab."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AnalyticsSystemCohortPreset:
    name: str
    description: str
    filters: dict[str, object]


SYSTEM_COHORT_PRESETS: tuple[AnalyticsSystemCohortPreset, ...] = (
    AnalyticsSystemCohortPreset(
        name="same_platform_same_content_type",
        description="Publicaciones de la misma plataforma y tipo de contenido.",
        filters={"linked": None},
    ),
    AnalyticsSystemCohortPreset(
        name="same_platform_duration_band",
        description="Publicaciones de la misma plataforma dentro de un rango de duracion comparable.",
        filters={"linked": None},
    ),
    AnalyticsSystemCohortPreset(
        name="same_platform_topic",
        description="Publicaciones de la misma plataforma y tema.",
        filters={"linked": None},
    ),
    AnalyticsSystemCohortPreset(
        name="same_platform_recent_period",
        description="Publicaciones de la misma plataforma en un periodo reciente.",
        filters={"linked": None},
    ),
    AnalyticsSystemCohortPreset(
        name="creator_all_same_format",
        description="Publicaciones del creador con el mismo formato.",
        filters={"linked": None},
    ),
)

