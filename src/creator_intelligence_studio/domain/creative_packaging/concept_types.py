"""Tipos para conceptos creativos."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CreativeConceptResult:
    concept_type: str
    title: str
    premise: str
    subject_description: str
    action_description: str
    composition_description: str
    emotion_description: str
    background_description: str
    color_guidance: str
    text_guidance: str
    visual_hierarchy: str
    relation_to_title: str
    brand_alignment_notes: str
    audience_fit_notes: str
    platform_fit_notes: str
    differentiation_notes: str
    authenticity_notes: str
    risks: tuple[str, ...]
    reference_requirements: tuple[str, ...]
    confidence_level: str
    limitations: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "concept_type": self.concept_type,
            "title": self.title,
            "premise": self.premise,
            "subject_description": self.subject_description,
            "action_description": self.action_description,
            "composition_description": self.composition_description,
            "emotion_description": self.emotion_description,
            "background_description": self.background_description,
            "color_guidance": self.color_guidance,
            "text_guidance": self.text_guidance,
            "visual_hierarchy": self.visual_hierarchy,
            "relation_to_title": self.relation_to_title,
            "brand_alignment_notes": self.brand_alignment_notes,
            "audience_fit_notes": self.audience_fit_notes,
            "platform_fit_notes": self.platform_fit_notes,
            "differentiation_notes": self.differentiation_notes,
            "authenticity_notes": self.authenticity_notes,
            "risks": list(self.risks),
            "reference_requirements": list(self.reference_requirements),
            "confidence_level": self.confidence_level,
            "limitations": list(self.limitations),
        }

