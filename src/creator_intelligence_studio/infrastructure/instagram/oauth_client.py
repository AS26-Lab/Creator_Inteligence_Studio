"""OAuth oficial para Instagram con abstraccion de proveedor."""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import threading
import urllib.parse
import urllib.request
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Protocol

from creator_intelligence_studio.domain.instagram_integration.connection_types import InstagramAuthProvider
from creator_intelligence_studio.domain.instagram_integration.errors import InstagramAuthorizationError
from creator_intelligence_studio.domain.instagram_integration.value_objects import (
    InstagramOAuthAuthorizationResult,
    InstagramOAuthTokenResult,
    READ_ONLY_SCOPES,
)


class InstagramOAuthClient(Protocol):
    def begin_authorization(self, *, client_id: str, scopes: tuple[str, ...], redirect_uri: str | None = None, state: str | None = None) -> InstagramOAuthAuthorizationResult: ...
    def exchange_code(self, *, client_id: str, client_secret: str | None, code: str, redirect_uri: str) -> InstagramOAuthTokenResult: ...
    def refresh_token(self, *, client_id: str, client_secret: str | None, refresh_token: str) -> InstagramOAuthTokenResult: ...
    def revoke(self, token: str) -> bool: ...
    def verify_token(self, token: str, scopes: tuple[str, ...]) -> dict[str, object]: ...


def _code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


class InstagramLoginOAuthClient:
    AUTH_ENDPOINT = "https://www.instagram.com/oauth/authorize"
    TOKEN_ENDPOINT = "https://api.instagram.com/oauth/access_token"
    REFRESH_ENDPOINT = "https://graph.instagram.com/refresh_access_token"
    VERIFY_ENDPOINT = "https://graph.instagram.com/me"
    REVOKE_ENDPOINT = "https://graph.instagram.com/revoke"

    def begin_authorization(self, *, client_id: str, scopes: tuple[str, ...], redirect_uri: str | None = None, state: str | None = None) -> InstagramOAuthAuthorizationResult:
        redirect_uri = redirect_uri or "http://127.0.0.1:8765/callback"
        state = state or secrets.token_urlsafe(24)
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": ",".join(scopes),
            "state": state,
        }
        verifier = secrets.token_urlsafe(48)
        params["code_challenge"] = _code_challenge(verifier)
        params["code_challenge_method"] = "S256"
        return InstagramOAuthAuthorizationResult(
            authorization_url=f"{self.AUTH_ENDPOINT}?{urllib.parse.urlencode(params)}",
            state=state,
            redirect_uri=redirect_uri,
            provider=InstagramAuthProvider.INSTAGRAM_LOGIN,
            code_challenge=verifier,
        )

    def exchange_code(self, *, client_id: str, client_secret: str | None, code: str, redirect_uri: str) -> InstagramOAuthTokenResult:
        payload = urllib.parse.urlencode(
            {
                "client_id": client_id,
                "client_secret": client_secret or "",
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            }
        ).encode("utf-8")
        request = urllib.request.Request(self.TOKEN_ENDPOINT, data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
        return InstagramOAuthTokenResult(
            access_token=body["access_token"],
            refresh_token=body.get("refresh_token"),
            token_type=body.get("token_type", "Bearer"),
            expires_in=body.get("expires_in"),
            granted_scopes=tuple((body.get("scope") or "").replace(",", " ").split()),
            instagram_user_id=body.get("user_id") or body.get("instagram_user_id"),
            expires_at=body.get("expires_at"),
        )

    def refresh_token(self, *, client_id: str, client_secret: str | None, refresh_token: str) -> InstagramOAuthTokenResult:
        payload = urllib.parse.urlencode(
            {
                "grant_type": "ig_refresh_token",
                "access_token": refresh_token,
                "client_secret": client_secret or "",
                "client_id": client_id,
            }
        ).encode("utf-8")
        request = urllib.request.Request(self.REFRESH_ENDPOINT, data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
        return InstagramOAuthTokenResult(
            access_token=body["access_token"],
            refresh_token=refresh_token,
            token_type=body.get("token_type", "Bearer"),
            expires_in=body.get("expires_in"),
            granted_scopes=READ_ONLY_SCOPES,
            instagram_user_id=body.get("user_id") or body.get("instagram_user_id"),
            expires_at=body.get("expires_at"),
        )

    def revoke(self, token: str) -> bool:
        payload = urllib.parse.urlencode({"access_token": token}).encode("utf-8")
        request = urllib.request.Request(self.REVOKE_ENDPOINT, data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(request, timeout=30) as response:
            return 200 <= response.status < 300

    def verify_token(self, token: str, scopes: tuple[str, ...]) -> dict[str, object]:
        query = urllib.parse.urlencode({"fields": "id,username,name"})
        request = urllib.request.Request(f"{self.VERIFY_ENDPOINT}?{query}", headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
        return {
            "instagram_user_id": body.get("id"),
            "username": body.get("username"),
            "granted_scopes": scopes,
            "missing_scopes": (),
        }

    def authorize_interactively(self, *, client_id: str, scopes: tuple[str, ...], open_browser: bool = True) -> tuple[InstagramOAuthAuthorizationResult, str]:
        result = self.begin_authorization(client_id=client_id, scopes=scopes)
        authorization_code: dict[str, str] = {}

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # type: ignore[override]
                parsed = urllib.parse.urlparse(self.path)
                params = urllib.parse.parse_qs(parsed.query)
                if params.get("state", [""])[0] != result.state:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b"state mismatch")
                    return
                if "error" in params:
                    authorization_code["error"] = params["error"][0]
                else:
                    authorization_code["code"] = params.get("code", [""])[0]
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Authorization complete. You can close this window.")

            def log_message(self, format, *args):  # noqa: A003
                return

        server = HTTPServer(("127.0.0.1", 8765), Handler)
        thread = threading.Thread(target=server.handle_request, daemon=True)
        thread.start()
        if open_browser:
            webbrowser.open(result.authorization_url)
        thread.join(timeout=120)
        server.server_close()
        if "error" in authorization_code:
            raise InstagramAuthorizationError(f"OAuth cancelado: {authorization_code['error']}")
        if "code" not in authorization_code:
            raise TimeoutError("No se recibio el codigo de autorizacion.")
        return result, authorization_code["code"]
