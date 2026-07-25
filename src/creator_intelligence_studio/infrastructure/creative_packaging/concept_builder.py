"""Construccion de conceptos creativos."""

from __future__ import annotations

import json
from uuid import uuid4

from creator_intelligence_studio.domain.creative_packaging.concept_types import CreativeConceptResult


def _json_dumps(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def build_creative_concepts(
    *,
    creator_id: str,
    platform: str,
    content_type: str,
    topic: str | None,
    title: str | None,
    objective: str | None,
    audience: str | None,
    concept_type: str = "curiosity_driven",
    brand_profile: dict[str, object] | None = None,
    language_profile: dict[str, object] | None = None,
    historical_fit: dict[str, object] | None = None,
    references: list[dict[str, object]] | None = None,
    constraints: list[str] | None = None,
) -> CreativeConceptResult:
    references = references or []
    constraints = constraints or []
    title_text = title or "Concepto sin titulo"
    premise = objective or topic or "Explorar una idea clara y coherente."
    subject_description = (brand_profile or {}).get("subject_guidance") or "Sujeto principal alineado con la marca."
    action_description = "Accion principal legible y concreta."
    composition_description = "Composicion limpia con jerarquia fuerte."
    emotion_description = "Expresion autentica y compatible con la marca."
    background_description = "Fondo simple sin ruido excesivo."
    color_guidance = "Paleta derivada de la marca."
    text_guidance = "Texto minimo o nulo segun la plataforma."
    visual_hierarchy = "Sujeto > idea > texto > fondo."
    relation_to_title = "Complementa el titulo sin repetirlo literalmente."
    brand_alignment_notes = "Usa patrones aprobados y evita elementos prohibidos."
    audience_fit_notes = audience or "Audiencia actual del creador."
    platform_fit_notes = f"Ajustado a {platform} y {content_type}."
    differentiation_notes = "Diferenciacion local sin copiar identidades ajenas."
    authenticity_notes = "Conservar rasgos propios del creador."
    risks = []
    if any("copy" in str(reference.get("reference_purpose") or "").casefold() for reference in references):
        risks.append("copying_risk")
    if constraints:
        risks.extend(constraints)
    reference_requirements = [str(reference.get("reference_type") or "reference") for reference in references]
    confidence_level = "medium" if references else "low"
    limitations = []
    if not brand_profile:
        limitations.append("incomplete_brand_profile")
    return CreativeConceptResult(
        concept_type=concept_type,
        title=title_text,
        premise=premise,
        subject_description=str(subject_description),
        action_description=action_description,
        composition_description=composition_description,
        emotion_description=emotion_description,
        background_description=background_description,
        color_guidance=color_guidance,
        text_guidance=text_guidance,
        visual_hierarchy=visual_hierarchy,
        relation_to_title=relation_to_title,
        brand_alignment_notes=brand_alignment_notes,
        audience_fit_notes=audience_fit_notes,
        platform_fit_notes=platform_fit_notes,
        differentiation_notes=differentiation_notes,
        authenticity_notes=authenticity_notes,
        risks=tuple(sorted(set(risks))),
        reference_requirements=tuple(reference_requirements),
        confidence_level=confidence_level,
        limitations=tuple(sorted(set(limitations))),
    )

