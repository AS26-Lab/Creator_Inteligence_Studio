"""Contratos de persistencia para proyectos."""

from __future__ import annotations

from typing import Protocol

from creator_intelligence_studio.domain.projects.entities import Project


class ProjectRepository(Protocol):
    """Operaciones para almacenar proyectos."""

    def create(self, project: Project) -> Project: ...

    def list(self) -> list[Project]: ...

    def list_by_creator(self, creator_id: str) -> list[Project]: ...

    def get_by_id(self, project_id: str) -> Project | None: ...

    def archive(self, project_id: str) -> Project | None: ...

