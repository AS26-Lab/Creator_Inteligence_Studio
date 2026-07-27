"""Configuracion centralizada de Graph API para Instagram."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True, slots=True)
class InstagramApiVersionConfig:
    configured_version: str = "v25.0"
    minimum_supported_version: str = "v23.0"
    documentation_checked_at: str = "2026-07-27T00:00:00Z"
    deprecation_status: str = "current"

    @property
    def unsupported_version_warning(self) -> str | None:
        if self.configured_version < self.minimum_supported_version:
            return (
                f"Graph API {self.configured_version} is below the minimum supported "
                f"version {self.minimum_supported_version}."
            )
        return None


DEFAULT_INSTAGRAM_API_VERSION = InstagramApiVersionConfig()

