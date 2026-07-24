"""Tipologia inicial de findings para Analytics Lab."""

from __future__ import annotations

from .value_objects import AnalyticsFindingType


FINDING_TYPE_DESCRIPTIONS: dict[AnalyticsFindingType, str] = {
    AnalyticsFindingType.FACT: "Hecho observacional trazable.",
    AnalyticsFindingType.COMPARISON: "Comparacion contra cohorte o segmento.",
    AnalyticsFindingType.ANOMALY: "Patron anomalo o inesperado.",
    AnalyticsFindingType.PATTERN: "Patron repetido o consistente.",
    AnalyticsFindingType.INFERENCE: "Interpretacion provisional basada en hechos.",
    AnalyticsFindingType.HYPOTHESIS: "Hipotesis verificable sin causalidad afirmada.",
    AnalyticsFindingType.DATA_QUALITY_WARNING: "Advertencia de calidad o comparabilidad.",
}

