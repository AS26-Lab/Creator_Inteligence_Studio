"""Tipos de perfil narrativo."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class NarrativeSectionSummary:
    label: str
    pattern_key: str
    description: str
    frequency_count: int
    supporting_example_count: int
    contradicting_example_count: int
    confidence_level: str
    examples: tuple[dict[str, object], ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, object]:
        return {
            "label": self.label,
            "pattern_key": self.pattern_key,
            "description": self.description,
            "frequency_count": self.frequency_count,
            "supporting_example_count": self.supporting_example_count,
            "contradicting_example_count": self.contradicting_example_count,
            "confidence_level": self.confidence_level,
            "examples": list(self.examples),
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True, slots=True)
class NarrativeProfileSummary:
    opening: tuple[NarrativeSectionSummary, ...]
    development: tuple[NarrativeSectionSummary, ...]
    explanation: tuple[NarrativeSectionSummary, ...]
    humor: tuple[NarrativeSectionSummary, ...]
    pacing: tuple[NarrativeSectionSummary, ...]
    closing: tuple[NarrativeSectionSummary, ...]
    platform_differences: tuple[NarrativeSectionSummary, ...]
    content_type_differences: tuple[NarrativeSectionSummary, ...]
    limitations: tuple[str, ...]
    summary: str

    def to_dict(self) -> dict[str, object]:
        return {
            "opening": [item.to_dict() for item in self.opening],
            "development": [item.to_dict() for item in self.development],
            "explanation": [item.to_dict() for item in self.explanation],
            "humor": [item.to_dict() for item in self.humor],
            "pacing": [item.to_dict() for item in self.pacing],
            "closing": [item.to_dict() for item in self.closing],
            "platform_differences": [item.to_dict() for item in self.platform_differences],
            "content_type_differences": [item.to_dict() for item in self.content_type_differences],
            "limitations": list(self.limitations),
            "summary": self.summary,
        }

