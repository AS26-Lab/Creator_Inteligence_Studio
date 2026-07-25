"""Tipos para alineacion de marca en packaging."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BrandAlignmentResult:
    visual_identity: dict[str, object]
    platform_differences: dict[str, object]
    completeness: float
    warnings: tuple[str, ...]
    summary: str

    def to_dict(self) -> dict[str, object]:
        return {
            "visual_identity": self.visual_identity,
            "platform_differences": self.platform_differences,
            "completeness": self.completeness,
            "warnings": list(self.warnings),
            "summary": self.summary,
        }

