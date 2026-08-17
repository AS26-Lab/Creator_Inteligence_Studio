"""Valores y reglas de dominio para Instagram."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Protocol

from .connection_types import InstagramAuthProvider


READ_ONLY_SCOPES: tuple[str, ...] = (
    "instagram_business_basic",
    "instagram_business_manage_insights",
)

FORBIDDEN_WRITE_SCOPES = {
    "instagram_business_content_publish",
    "instagram_business_manage_comments",
    "instagram_business_manage_messages",
    "instagram_manage_comments",
    "instagram_manage_messages",
    "pages_manage_posts",
    "ads_management",
    "ads_read",
    "pages_manage_metadata",
}


def build_instagram_fingerprint(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_instagram_credential_reference(*, creator_id: str, instagram_user_id: str, provider: InstagramAuthProvider = InstagramAuthProvider.INSTAGRAM_LOGIN) -> str:
    return f"instagram:{provider.value}:{creator_id}:{instagram_user_id}"


def is_write_scope(scope: str) -> bool:
    normalized = scope.strip().lower()
    return normalized in FORBIDDEN_WRITE_SCOPES or "publish" in normalized or "manage_messages" in normalized or "manage_comments" in normalized


@dataclass(frozen=True, slots=True)
class InstagramOAuthAuthorizationResult:
    authorization_url: str
    state: str
    redirect_uri: str
    provider: InstagramAuthProvider
    code_challenge: str | None = None


@dataclass(frozen=True, slots=True)
class InstagramOAuthTokenResult:
    access_token: str
    refresh_token: str | None
    token_type: str
    expires_in: int | None
    granted_scopes: tuple[str, ...]
    instagram_user_id: str | None = None
    expires_at: str | None = None


class InstagramAuthProviderClient(Protocol):
    def begin_authorization(self, *, client_id: str, scopes: tuple[str, ...], redirect_uri: str | None = None, state: str | None = None) -> InstagramOAuthAuthorizationResult: ...
    def exchange_code(self, *, client_id: str, client_secret: str | None, code: str, redirect_uri: str) -> InstagramOAuthTokenResult: ...
    def refresh_token(self, *, client_id: str, client_secret: str | None, refresh_token: str) -> InstagramOAuthTokenResult: ...
    def revoke(self, token: str) -> bool: ...
    def verify_token(self, token: str, scopes: tuple[str, ...]) -> dict[str, object]: ...
