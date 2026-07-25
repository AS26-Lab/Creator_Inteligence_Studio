"""Instrucciones de revision para miniaturas."""

from __future__ import annotations

from creator_intelligence_studio.domain.creative_packaging.evaluation_types import ThumbnailReviewResult
from creator_intelligence_studio.domain.creative_packaging.thumbnail_types import ThumbnailReviewStatus


def build_thumbnail_review_instructions(
    *,
    pair_evaluation: dict[str, object],
    concept: dict[str, object] | None,
    prompt: dict[str, object] | None,
    brand_profile: dict[str, object] | None,
    title: str | None,
    thumbnail: dict[str, object],
) -> ThumbnailReviewResult:
    warnings = list(pair_evaluation.get("warnings", []))
    risks = list(pair_evaluation.get("risks", []))
    strengths = []
    weaknesses = []
    keep = []
    change = []
    if pair_evaluation.get("visual_quality_score", 0) and pair_evaluation.get("visual_quality_score", 0) >= 60:
        strengths.append("Buen contraste y jerarquia general.")
        keep.append("Mantener foco y legibilidad.")
    else:
        weaknesses.append("La miniatura necesita mas claridad tecnica.")
        change.append("Aumentar contraste y nitidez.")
    if pair_evaluation.get("creator_brand_alignment_score", 0) and pair_evaluation.get("creator_brand_alignment_score", 0) >= 60:
        strengths.append("Alineacion razonable con la marca.")
    else:
        weaknesses.append("La miniatura no encaja del todo con la marca.")
        change.append("Ajustar paleta, gesto o densidad visual.")
    if pair_evaluation.get("content_alignment_score", 0) and pair_evaluation.get("content_alignment_score", 0) < 50:
        weaknesses.append("Promesa visual poco consistente con el contenido.")
        change.append("Reducir exageracion o cambiar el sujeto.")
    if risks:
        change.append("Eliminar elementos que copian estilos ajenos o atraen expectativa incorrecta.")
    status = ThumbnailReviewStatus.READY_TO_USE
    if risks:
        status = ThumbnailReviewStatus.NOT_RECOMMENDED
    elif weaknesses:
        status = ThumbnailReviewStatus.NEEDS_REVISION
    revision_instructions = " ".join(
        [
            "Conserva los elementos que funcionan.",
            " ".join(change) if change else "No se requieren cambios mayores.",
            "No copies identidades ajenas ni sobrecargues la imagen.",
        ]
    )
    return ThumbnailReviewResult(
        overall_status=status.value,
        what_works=tuple(str(item) for item in strengths),
        what_does_not=tuple(str(item) for item in weaknesses),
        brand_fit="Alinear con marca" if pair_evaluation.get("creator_brand_alignment_score", 0) < 60 else "Adecuado para la marca",
        content_fit="Revisar promesa y contexto" if pair_evaluation.get("content_alignment_score", 0) < 60 else "Coherente con contenido",
        audience_fit="Ajustar expectativa" if pair_evaluation.get("audience_fit_score", 0) < 60 else "Adecuado para la audiencia",
        platform_fit="Verificar crop y texto" if pair_evaluation.get("platform_fit_score", 0) < 60 else "Adecuado para la plataforma",
        historical_fit="Consultar historial" if pair_evaluation.get("historical_fit_score", 0) < 60 else "Compatible con historial",
        differentiation="Reducir copia visual" if "copying_risk" in risks else "Diferenciacion aceptable",
        promise="Evitar promesa excesiva" if pair_evaluation.get("promise_alignment_score", 0) < 60 else "Promesa alineada",
        risks=tuple(sorted(set(risks))),
        keep=tuple(keep),
        change=tuple(change),
        revision_instructions=revision_instructions,
        another_generation_needed=status != ThumbnailReviewStatus.READY_TO_USE,
        confidence_level="medium" if not risks else "low",
        limitations=("no_image_generation",) if not concept else (),
    )

