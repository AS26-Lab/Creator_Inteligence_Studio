"""Generacion de salud consolidada para plataformas."""

from __future__ import annotations

from dataclasses import asdict
from uuid import uuid4

from creator_intelligence_studio.domain.platform_integrations.entities import PlatformConnectionSummary, PlatformConnectionHealth
from creator_intelligence_studio.domain.platform_integrations.health_types import HealthStatus, Severity
from creator_intelligence_studio.shared.dates import utc_now


def build_platform_health_record(
    *,
    creator_id: str,
    platform_connection: PlatformConnectionSummary,
    warnings: list[str] | None = None,
    errors: list[str] | None = None,
    message: str | None = None,
) -> PlatformConnectionHealth:
    warnings = warnings or []
    errors = errors or []
    if platform_connection.status.value in {"disconnected", "revoked"}:
        status = HealthStatus.DISCONNECTED
        severity = Severity.ERROR
    elif errors:
        status = HealthStatus.ACTION_REQUIRED
        severity = Severity.CRITICAL if len(errors) > 1 else Severity.ERROR
    elif warnings:
        status = HealthStatus.HEALTHY_WITH_WARNINGS
        severity = Severity.WARNING
    else:
        status = HealthStatus.HEALTHY
        severity = Severity.INFO
    observed_at = utc_now()
    return PlatformConnectionHealth(
        id=str(uuid4()),
        creator_id=creator_id,
        platform_connection_id=platform_connection.id,
        status=status,
        severity=severity,
        error_code=errors[0] if errors else None,
        message=message or ("; ".join(warnings) if warnings else None),
        details_json=str(
            {
                "platform": platform_connection.platform.value,
                "native_status": platform_connection.native_status,
                "warnings": warnings,
                "errors": errors,
            }
        ),
        checked_at=observed_at,
        created_at=observed_at,
    )
