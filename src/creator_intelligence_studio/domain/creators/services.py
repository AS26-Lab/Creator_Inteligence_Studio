"""Servicios de dominio para creadores."""

from __future__ import annotations

import re
import uuid
from datetime import datetime

from creator_intelligence_studio.domain.creators.entities import Creator, CreatorStatus
from creator_intelligence_studio.domain.errors import ConflictError, ValidationError
from creator_intelligence_studio.shared.dates import utc_now

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def normalize_slug(value: str) -> str:
    """Normaliza un slug para hacerlo estable y portable."""

    slug = value.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    if not slug:
        raise ValidationError("El slug no puede quedar vacío.")
    if not SLUG_PATTERN.fullmatch(slug):
        raise ValidationError("El slug contiene caracteres no permitidos.")
    return slug


def validate_display_name(display_name: str) -> str:
    """Valida el nombre visible del creador."""

    value = display_name.strip()
    if not value:
        raise ValidationError("El nombre del creador no puede quedar vacío.")
    return value


def generate_creator_id() -> str:
    """Genera un UUID estable para un creador."""

    return str(uuid.uuid4())


def build_creator(
    *,
    display_name: str,
    slug: str,
    description: str | None = None,
    creator_id: str | None = None,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
    status: CreatorStatus = CreatorStatus.ACTIVE,
) -> Creator:
    """Construye una entidad Creator validada."""

    return Creator(
        id=creator_id or generate_creator_id(),
        display_name=validate_display_name(display_name),
        slug=normalize_slug(slug),
        description=description.strip() if isinstance(description, str) and description.strip() else None,
        created_at=created_at or utc_now(),
        updated_at=updated_at or utc_now(),
        status=status,
    )


def next_available_slug(base_slug: str, existing_slugs: set[str]) -> str:
    """Genera un slug único a partir de una base."""

    slug = normalize_slug(base_slug)
    if slug not in existing_slugs:
        return slug
    index = 2
    while f"{slug}-{index}" in existing_slugs:
        index += 1
    return f"{slug}-{index}"


def ensure_active_creator(creator: Creator | None) -> Creator:
    """Garantiza que el creador exista y esté activo."""

    if creator is None:
        raise ConflictError("El creador solicitado no existe.")
    if creator.status != CreatorStatus.ACTIVE:
        raise ConflictError("El creador está archivado y no puede usarse.")
    return creator

