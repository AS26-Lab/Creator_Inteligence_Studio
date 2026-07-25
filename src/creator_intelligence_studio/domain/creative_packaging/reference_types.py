"""Tipos para referencias de packaging."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ReferencePackageResult:
    required: tuple[dict[str, object], ...]
    recommended: tuple[dict[str, object], ...]
    optional: tuple[dict[str, object], ...]
    not_recommended: tuple[dict[str, object], ...]
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "required": list(self.required),
            "recommended": list(self.recommended),
            "optional": list(self.optional),
            "not_recommended": list(self.not_recommended),
            "notes": list(self.notes),
        }

