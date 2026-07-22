"""Comandos de proyecto."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CreateProjectCommand:
    creator_reference: str
    name: str
    project_type: str
    description: str | None = None


@dataclass(frozen=True, slots=True)
class ArchiveProjectCommand:
    project_id: str

