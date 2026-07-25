"""Tipos para prompts creativos."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CreativePromptResult:
    prompt_text: str
    negative_guidance: str | None
    reference_instructions: dict[str, object]
    tool_usage_notes: dict[str, object]
    expected_output_notes: str
    reference_package: dict[str, object]
    confidence_level: str
    limitations: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "prompt_text": self.prompt_text,
            "negative_guidance": self.negative_guidance,
            "reference_instructions": self.reference_instructions,
            "tool_usage_notes": self.tool_usage_notes,
            "expected_output_notes": self.expected_output_notes,
            "reference_package": self.reference_package,
            "confidence_level": self.confidence_level,
            "limitations": list(self.limitations),
        }

