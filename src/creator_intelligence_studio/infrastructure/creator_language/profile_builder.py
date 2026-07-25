"""Construccion de resumen de perfil narrativo."""

from __future__ import annotations

from creator_intelligence_studio.domain.creator_language.narrative_types import NarrativeProfileSummary, NarrativeSectionSummary


def _section_from_payload(label: str, payload: dict[str, object]) -> NarrativeSectionSummary:
    return NarrativeSectionSummary(
        label=label,
        pattern_key=str(payload.get("pattern_key", label.lower())),
        description=str(payload.get("description", "")),
        frequency_count=int(payload.get("frequency_count", 0) or 0),
        supporting_example_count=int(payload.get("supporting_example_count", 0) or 0),
        contradicting_example_count=int(payload.get("contradicting_example_count", 0) or 0),
        confidence_level=str(payload.get("confidence_level", "low")),
        examples=tuple(),
        warnings=tuple(payload.get("warnings", []) if isinstance(payload.get("warnings", []), list) else []),
    )


def build_language_profile_summary(profile_payload: dict[str, object]) -> NarrativeProfileSummary:
    opening = tuple(_section_from_payload("Apertura", payload) for payload in profile_payload.get("opening", []))
    development = tuple(_section_from_payload("Desarrollo", payload) for payload in profile_payload.get("development", []))
    explanation = tuple(_section_from_payload("Explicacion", payload) for payload in profile_payload.get("explanation", []))
    humor = tuple(_section_from_payload("Humor", payload) for payload in profile_payload.get("humor", []))
    pacing = tuple(_section_from_payload("Ritmo", payload) for payload in profile_payload.get("pacing", []))
    closing = tuple(_section_from_payload("Cierre", payload) for payload in profile_payload.get("closing", []))
    platform_differences = tuple(_section_from_payload("Plataforma", payload) for payload in profile_payload.get("platform_differences", []))
    content_type_differences = tuple(_section_from_payload("Contenido", payload) for payload in profile_payload.get("content_type_differences", []))
    limitations = tuple(profile_payload.get("limitations", []))
    summary = str(profile_payload.get("summary", "Perfil narrativo heuristico."))
    return NarrativeProfileSummary(
        opening=opening,
        development=development,
        explanation=explanation,
        humor=humor,
        pacing=pacing,
        closing=closing,
        platform_differences=platform_differences,
        content_type_differences=content_type_differences,
        limitations=limitations,
        summary=summary,
    )
