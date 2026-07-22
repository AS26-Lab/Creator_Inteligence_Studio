"""Servicios de dominio para proyectos."""

from __future__ import annotations

import uuid
from datetime import datetime

from creator_intelligence_studio.domain.creators.entities import Creator, CreatorStatus
from creator_intelligence_studio.domain.errors import ConflictError, ValidationError
from creator_intelligence_studio.domain.projects.entities import Project, ProjectStatus, ProjectType
from creator_intelligence_studio.shared.dates import utc_now


def validate_project_name(name: str) -> str:
    """Valida el nombre del proyecto."""

    value = name.strip()
    if not value:
        raise ValidationError("El nombre del proyecto no puede quedar vacío.")
    return value


def validate_project_type(project_type: str | ProjectType) -> ProjectType:
    """Valida el tipo de proyecto."""

    if isinstance(project_type, ProjectType):
        return project_type
    try:
        return ProjectType(project_type)
    except ValueError as exc:
        raise ValidationError(
            "El tipo de proyecto no es válido. Use long_form, short_form, mixed o research."
        ) from exc


def generate_project_id() -> str:
    """Genera un UUID estable para un proyecto."""

    return str(uuid.uuid4())


def build_project(
    *,
    creator_id: str,
    name: str,
    description: str | None = None,
    project_type: str | ProjectType = ProjectType.LONG_FORM,
    project_id: str | None = None,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
    status: ProjectStatus = ProjectStatus.ACTIVE,
) -> Project:
    """Construye una entidad Project validada."""

    return Project(
        id=project_id or generate_project_id(),
        creator_id=creator_id,
        name=validate_project_name(name),
        description=description.strip() if isinstance(description, str) and description.strip() else None,
        project_type=validate_project_type(project_type),
        status=status,
        created_at=created_at or utc_now(),
        updated_at=updated_at or utc_now(),
    )


def ensure_active_project(project: Project | None) -> Project:
    """Garantiza que el proyecto exista y esté activo."""

    if project is None:
        raise ConflictError("El proyecto solicitado no existe.")
    if project.status == ProjectStatus.ARCHIVED:
        raise ConflictError("El proyecto está archivado y no acepta nuevos videos.")
    return project


def ensure_creator_active(creator: Creator | None) -> Creator:
    """Garantiza que el creador exista y esté activo."""

    if creator is None:
        raise ConflictError("El creador solicitado no existe.")
    if creator.status != CreatorStatus.ACTIVE:
        raise ConflictError("El creador está archivado y no puede usarse.")
    return creator

