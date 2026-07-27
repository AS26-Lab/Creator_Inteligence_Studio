"""Funciones comunes para consolidacion de plataformas."""

from __future__ import annotations

import json
from hashlib import sha256

from .connection_types import CommonConnectionStatus, PlatformKind
from .health_types import HealthStatus


def normalize_platform_identifier(value: str | PlatformKind) -> str:
    if isinstance(value, PlatformKind):
        return value.value
    return str(value).strip().lower()


def classify_native_connection_status(platform: PlatformKind, native_status: str) -> CommonConnectionStatus:
    status = str(native_status).lower()
    if status in {"verified", "connected", "active", "enabled"}:
        return CommonConnectionStatus.CONNECTED
    if status in {"connected_with_warnings", "warnings"}:
        return CommonConnectionStatus.CONNECTED_WITH_WARNINGS
    if status in {"pending", "authenticating", "connecting"}:
        return CommonConnectionStatus.CONNECTING
    if status in {"expired", "token_expired"}:
        return CommonConnectionStatus.EXPIRED
    if status in {"revoked", "authorization_revoked", "product_not_approved", "scope_not_approved"}:
        return CommonConnectionStatus.REVOKED if status == "revoked" else CommonConnectionStatus.PRODUCT_APPROVAL_REQUIRED
    if status in {"insufficient_scope", "insufficient_permissions"}:
        return CommonConnectionStatus.INSUFFICIENT_PERMISSIONS
    if status in {"app_review_required"}:
        return CommonConnectionStatus.APP_REVIEW_REQUIRED
    if status in {"not_configured"}:
        return CommonConnectionStatus.NOT_CONFIGURED
    if status in {"disconnected", "inactive"}:
        return CommonConnectionStatus.DISCONNECTED
    if status in {"unavailable"}:
        return CommonConnectionStatus.UNAVAILABLE
    if status in {"error", "failed"}:
        return CommonConnectionStatus.ERROR
    return CommonConnectionStatus.UNKNOWN


def classify_health_status(*, connected: bool, warnings: int, errors: int, disconnected: bool = False) -> HealthStatus:
    if disconnected:
        return HealthStatus.DISCONNECTED
    if errors > 0:
        return HealthStatus.DEGRADED if warnings > 0 else HealthStatus.ACTION_REQUIRED
    if warnings > 0:
        return HealthStatus.HEALTHY_WITH_WARNINGS
    return HealthStatus.HEALTHY if connected else HealthStatus.UNKNOWN


def build_platform_fingerprint(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)
    return sha256(canonical.encode("utf-8")).hexdigest()
