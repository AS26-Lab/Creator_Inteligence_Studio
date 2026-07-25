"""Construccion de prompts de packaging creativo."""

from __future__ import annotations

from creator_intelligence_studio.domain.creative_packaging.prompt_types import CreativePromptResult
from .prompt_adapter import adapt_prompt_for_tool


def build_creative_prompt(
    *,
    concept: dict[str, object],
    target_tool: str,
    reference_package: dict[str, object],
    title: str | None = None,
    brand_profile: dict[str, object] | None = None,
    language_profile: dict[str, object] | None = None,
    constraints: list[str] | None = None,
) -> CreativePromptResult:
    constraints = constraints or []
    concept_title = str(concept.get("title") or title or "Concepto creativo")
    prompt_parts = [
        f"Concepto: {concept_title}.",
        f"Objetivo visual: {concept.get('premise') or concept.get('summary') or 'Construir una miniatura clara y alineada.'}",
        f"Sujeto: {concept.get('subject_description') or 'Sujeto principal legible.'}",
        f"Accion: {concept.get('action_description') or 'Accion simple y clara.'}",
        f"Composicion: {concept.get('composition_description') or 'Composicion limpia.'}",
        f"Expresion: {concept.get('emotion_description') or 'Expresion autentica.'}",
        f"Fondo: {concept.get('background_description') or 'Fondo simple.'}",
        f"Relacion con el titulo: {concept.get('relation_to_title') or 'Complementa sin repetir.'}",
        f"Guia de marca: {concept.get('brand_alignment_notes') or 'Respetar marca.'}",
        f"Guia de audiencia: {concept.get('audience_fit_notes') or 'Ajustado a la audiencia.'}",
        f"Guia de plataforma: {concept.get('platform_fit_notes') or 'Ajustado a la plataforma.'}",
    ]
    if constraints:
        prompt_parts.append("Restricciones: " + "; ".join(constraints))
    prompt_text = " ".join(prompt_parts)
    negative_guidance = "Evitar copiar identidades ajenas, textos exagerados o composiciones fuera de marca."
    adapted = adapt_prompt_for_tool(prompt_text, target_tool=target_tool, reference_package=reference_package, negative_guidance=negative_guidance)
    expected_output_notes = "Revisar coherencia con marca, contenido, plataforma y legibilidad en pequeno."
    limitations = []
    if not brand_profile:
        limitations.append("incomplete_brand_profile")
    if not reference_package.get("required") and not reference_package.get("recommended"):
        limitations.append("missing_reference")
    return CreativePromptResult(
        prompt_text=adapted["prompt_text"],
        negative_guidance=adapted["negative_guidance"],
        reference_instructions=reference_package,
        tool_usage_notes=adapted["tool_usage_notes"],
        expected_output_notes=expected_output_notes,
        reference_package=reference_package,
        confidence_level="medium" if brand_profile else "low",
        limitations=tuple(sorted(set(limitations))),
    )

