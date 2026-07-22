"""Utilidades de fechas UTC."""

from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Devuelve la hora actual en UTC."""

    return datetime.now(timezone.utc)


def to_iso_z(value: datetime | None) -> str | None:
    """Convierte una fecha UTC a ISO 8601 con sufijo Z."""

    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def from_iso_z(value: str | None) -> datetime | None:
    """Convierte un ISO 8601 con sufijo Z a datetime UTC."""

    if value is None:
        return None
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)

