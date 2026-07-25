"""Consejero de referencias para prompts y briefs."""

from __future__ import annotations

from creator_intelligence_studio.domain.creative_packaging.reference_types import ReferencePackageResult


def build_reference_package(
    *,
    references: list[dict[str, object]],
    concept_type: str,
    has_creator_face: bool = False,
    has_object_focus: bool = False,
) -> ReferencePackageResult:
    required: list[dict[str, object]] = []
    recommended: list[dict[str, object]] = []
    optional: list[dict[str, object]] = []
    not_recommended: list[dict[str, object]] = []
    notes: list[str] = []
    for reference in references:
        role = str(reference.get("reference_purpose") or reference.get("reference_type") or "reference")
        item = dict(reference)
        if bool(reference.get("represents_creator")) or has_creator_face:
            item["required_level"] = "strongly_recommended"
            required.append(item)
        elif has_object_focus and reference.get("reference_type") in {"product", "instrument", "recurring_object"}:
            item["required_level"] = "required"
            required.append(item)
        elif str(reference.get("approval_status") or "").lower() == "approved":
            item["required_level"] = "recommended"
            recommended.append(item)
        elif str(reference.get("approval_status") or "").lower() == "rejected":
            item["required_level"] = "not_recommended"
            item["risk_notes"] = "Riesgo de copiar identidad o composicion ajena."
            not_recommended.append(item)
        else:
            item["required_level"] = "optional"
            optional.append(item)
        notes.append(f"{role}: extraer principios, no copiar identidad.")
    if not references:
        notes.append("No se requieren referencias obligatoriamente para conceptos abstractos.")
    return ReferencePackageResult(
        required=tuple(required),
        recommended=tuple(recommended),
        optional=tuple(optional),
        not_recommended=tuple(not_recommended),
        notes=tuple(notes),
    )

