"""Comandos de creador."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CreateCreatorCommand:
    display_name: str
    slug: str | None = None
    description: str | None = None


@dataclass(frozen=True, slots=True)
class ArchiveCreatorCommand:
    creator_reference: str

