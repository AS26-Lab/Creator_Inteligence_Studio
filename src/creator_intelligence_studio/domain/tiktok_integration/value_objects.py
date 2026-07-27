"""Valores y reglas de dominio para TikTok."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Protocol

from .connection_types import TikTokProductApprovalState


READ_ONLY_SCOPES: tuple[str, ...] = (
    "user.info.basic",
    "user.info.profile",
    "user.info.stats",
    "video.list",
)

FORBIDDEN_WRITE_SCOPES = {
    "video.publish",
    "video.upload",
}

DEFAULT_TIKTOK_API_VERSION = "v2"


def normalize_scopes(scopes: tuple[str, ...] | list[str] | str) -> tuple[str, ...]:
    if isinstance(scopes, str):
        items = [item.strip() for item in scopes.split(",")]
    else:
        items = [str(item).strip() for item in scopes]
    return tuple(item for item in items if item)


def build_tiktok_fingerprint(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def is_write_scope(scope: str) -> bool:
    normalized = scope.strip().lower()
    return normalized in FORBIDDEN_WRITE_SCOPES or normalized.endswith(".write") or "publish" in normalized or "upload" in normalized


@dataclass(frozen=True, slots=True)
class TikTokOAuthAuthorizationResult:
    authorization_url: str
    state: str
    redirect_uri: str
    code_verifier: str | None = None


@dataclass(frozen=True, slots=True)
class TikTokOAuthTokenResult:
    access_token: str
    refresh_token: str | None
    token_type: str
    expires_in: int | None
    refresh_expires_in: int | None
    granted_scopes: tuple[str, ...]
    open_id: str | None = None
    union_id: str | None = None
    expires_at: str | None = None


@dataclass(frozen=True, slots=True)
class TikTokRedirectValidationResult:
    redirect_uri: str
    state: str
    code: str | None
    scopes: tuple[str, ...]
    error: str | None = None
    error_description: str | None = None


@dataclass(frozen=True, slots=True)
class TikTokProductApprovalSummary:
    login_kit_enabled: bool
    display_api_enabled: bool
    scope_approved: bool
    development_mode: bool
    production_mode: bool
    app_review_required: bool
    product_not_approved: bool
    scope_not_approved: bool
    unknown: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "login_kit_enabled": self.login_kit_enabled,
            "display_api_enabled": self.display_api_enabled,
            "scope_approved": self.scope_approved,
            "development_mode": self.development_mode,
            "production_mode": self.production_mode,
            "app_review_required": self.app_review_required,
            "product_not_approved": self.product_not_approved,
            "scope_not_approved": self.scope_not_approved,
            "unknown": self.unknown,
        }


class TikTokRedirectUriValidator(Protocol):
    def validate(self, redirect_uri: str) -> TikTokRedirectValidationResult: ...


def validate_desktop_redirect_uri(redirect_uri: str) -> bool:
    pattern = re.compile(r"^https?://(localhost|127\.0\.0\.1)(?::(\*|\d{1,5}))?(?:/[^?#]*)?/?$")
    return bool(pattern.match(redirect_uri))
