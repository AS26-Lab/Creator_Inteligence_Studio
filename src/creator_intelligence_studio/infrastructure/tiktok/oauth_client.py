"""Cliente OAuth oficial para TikTok Login Kit en escritorio."""

from __future__ import annotations

import json
import hashlib
import base64
import os
import secrets
import urllib.parse
from dataclasses import dataclass
from typing import Callable

from creator_intelligence_studio.domain.tiktok_integration.connection_types import TikTokProductApprovalState
from creator_intelligence_studio.domain.tiktok_integration.errors import TikTokAuthorizationError
from creator_intelligence_studio.domain.tiktok_integration.services import TikTokAuthProviderClient
from creator_intelligence_studio.domain.tiktok_integration.value_objects import (
    TikTokOAuthAuthorizationResult,
    TikTokOAuthTokenResult,
    normalize_scopes,
    validate_desktop_redirect_uri,
)


def _random_state(length: int = 30) -> str:
    return secrets.token_urlsafe(length)


def _random_code_verifier(length: int = 64) -> str:
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"
    return "".join(secrets.choice(alphabet) for _ in range(max(43, min(length, 128))))


def _code_challenge(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


@dataclass(frozen=True, slots=True)
class TikTokOAuthResponse:
    code: str | None
    state: str | None
    scopes: tuple[str, ...]
    error: str | None = None
    error_description: str | None = None


class TikTokDesktopOAuthClient(TikTokAuthProviderClient):
    def __init__(
        self,
        *,
        authorize_url: str = "https://www.tiktok.com/v2/auth/authorize/",
        token_url: str = "https://open.tiktokapis.com/v2/oauth/token/",
        revoke_url: str = "https://open.tiktokapis.com/v2/oauth/revoke/",
        request_sender: Callable[[str, str, dict[str, str], bytes | None], tuple[int, dict[str, str], bytes]] | None = None,
    ) -> None:
        self.authorize_url = authorize_url
        self.token_url = token_url
        self.revoke_url = revoke_url
        self._request_sender = request_sender

    def begin_authorization(
        self,
        *,
        client_id: str,
        scopes: tuple[str, ...],
        redirect_uri: str | None = None,
        state: str | None = None,
        code_verifier: str | None = None,
    ) -> TikTokOAuthAuthorizationResult:
        scopes = normalize_scopes(scopes)
        if not scopes:
            raise TikTokAuthorizationError("Se requieren scopes de lectura aprobados.")
        if redirect_uri is None:
            raise TikTokAuthorizationError("Se requiere un redirect_uri de escritorio registrado.")
        if not validate_desktop_redirect_uri(redirect_uri):
            raise TikTokAuthorizationError("El redirect_uri de escritorio no es valido.")
        state_value = state or _random_state()
        verifier = code_verifier or _random_code_verifier()
        params = {
            "client_key": client_id,
            "response_type": "code",
            "scope": ",".join(scopes),
            "redirect_uri": redirect_uri,
            "state": state_value,
            "code_challenge": _code_challenge(verifier),
            "code_challenge_method": "S256",
        }
        authorization_url = f"{self.authorize_url}?{urllib.parse.urlencode(params)}"
        return TikTokOAuthAuthorizationResult(
            authorization_url=authorization_url,
            state=state_value,
            redirect_uri=redirect_uri,
            code_verifier=verifier,
        )

    def parse_redirect_response(self, query: dict[str, str]) -> dict[str, str | None]:
        return {
            "code": query.get("code"),
            "state": query.get("state"),
            "scopes": query.get("scopes"),
            "error": query.get("error"),
            "error_description": query.get("error_description"),
        }

    def _request(self, method: str, url: str, headers: dict[str, str], body: dict[str, str]) -> dict[str, object]:
        encoded = urllib.parse.urlencode(body).encode("utf-8")
        if self._request_sender is not None:
            status_code, response_headers, response_body = self._request_sender(method, url, headers, encoded)
            del status_code, response_headers
            return json.loads(response_body.decode("utf-8"))
        from urllib import request as urllib_request

        req = urllib_request.Request(url, data=encoded, headers=headers, method=method)
        with urllib_request.urlopen(req, timeout=30) as response:  # pragma: no cover - network path
            return json.loads(response.read().decode("utf-8"))

    def exchange_code(
        self,
        *,
        client_id: str,
        client_secret: str | None,
        code: str,
        redirect_uri: str,
        code_verifier: str | None = None,
    ) -> TikTokOAuthTokenResult:
        if not client_secret and self._request_sender is None:
            raise TikTokAuthorizationError("Se requiere client_secret para el intercambio de codigo.")
        payload = {
            "client_key": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }
        if code_verifier:
            payload["code_verifier"] = code_verifier
        response = self._request("POST", self.token_url, {"Content-Type": "application/x-www-form-urlencoded"}, payload)
        return TikTokOAuthTokenResult(
            access_token=str(response.get("access_token") or ""),
            refresh_token=response.get("refresh_token"),
            token_type=str(response.get("token_type") or "Bearer"),
            expires_in=response.get("expires_in"),
            refresh_expires_in=response.get("refresh_expires_in"),
            granted_scopes=normalize_scopes(response.get("scope") or ()),
            open_id=response.get("open_id"),
            union_id=response.get("union_id"),
            expires_at=response.get("expires_at"),
        )

    def refresh_token(
        self,
        *,
        client_id: str,
        client_secret: str | None,
        refresh_token: str,
    ) -> TikTokOAuthTokenResult:
        if not client_secret and self._request_sender is None:
            raise TikTokAuthorizationError("Se requiere client_secret para renovar el token.")
        response = self._request(
            "POST",
            self.token_url,
            {"Content-Type": "application/x-www-form-urlencoded"},
            {
                "client_key": client_id,
                "client_secret": client_secret,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        )
        return TikTokOAuthTokenResult(
            access_token=str(response.get("access_token") or ""),
            refresh_token=response.get("refresh_token"),
            token_type=str(response.get("token_type") or "Bearer"),
            expires_in=response.get("expires_in"),
            refresh_expires_in=response.get("refresh_expires_in"),
            granted_scopes=normalize_scopes(response.get("scope") or ()),
            open_id=response.get("open_id"),
            union_id=response.get("union_id"),
            expires_at=response.get("expires_at"),
        )

    def revoke(self, *, client_id: str, client_secret: str | None, token: str) -> bool:
        if not client_secret and self._request_sender is None:
            raise TikTokAuthorizationError("Se requiere client_secret para revocar el token.")
        self._request(
            "POST",
            self.revoke_url,
            {"Content-Type": "application/x-www-form-urlencoded"},
            {"client_key": client_id, "client_secret": client_secret, "token": token},
        )
        return True
