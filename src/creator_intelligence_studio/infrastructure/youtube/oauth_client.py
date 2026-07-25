"""OAuth de escritorio para YouTube / Google."""

from __future__ import annotations

import json
import secrets
import threading
import urllib.parse
import urllib.request
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Protocol

from creator_intelligence_studio.domain.youtube_integration.services import READ_ONLY_SCOPES


@dataclass(frozen=True, slots=True)
class OAuthAuthorizationResult:
    authorization_url: str
    state: str
    redirect_uri: str


@dataclass(frozen=True, slots=True)
class OAuthTokenResult:
    access_token: str
    refresh_token: str | None
    token_type: str
    expires_in: int | None
    granted_scopes: tuple[str, ...]
    google_account_identifier: str | None = None


class YouTubeOAuthClient(Protocol):
    def begin_authorization(self, *, client_id: str, scopes: tuple[str, ...], redirect_uri: str | None = None, state: str | None = None) -> OAuthAuthorizationResult: ...
    def exchange_code(self, *, client_id: str, client_secret: str | None, code: str, redirect_uri: str) -> OAuthTokenResult: ...
    def refresh_token(self, *, client_id: str, client_secret: str | None, refresh_token: str) -> OAuthTokenResult: ...
    def revoke(self, token: str) -> bool: ...
    def verify_token(self, token: str, scopes: tuple[str, ...]) -> dict[str, object]: ...


class DesktopYouTubeOAuthClient:
    """OAuth para aplicaciones instaladas usando loopback o navegador."""

    AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
    REVOKE_ENDPOINT = "https://oauth2.googleapis.com/revoke"
    VERIFY_ENDPOINT = "https://oauth2.googleapis.com/tokeninfo"

    def begin_authorization(self, *, client_id: str, scopes: tuple[str, ...], redirect_uri: str | None = None, state: str | None = None) -> OAuthAuthorizationResult:
        redirect_uri = redirect_uri or "http://127.0.0.1:8765/callback"
        state = state or secrets.token_urlsafe(24)
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
            "state": state,
        }
        return OAuthAuthorizationResult(
            authorization_url=f"{self.AUTH_ENDPOINT}?{urllib.parse.urlencode(params)}",
            state=state,
            redirect_uri=redirect_uri,
        )

    def exchange_code(self, *, client_id: str, client_secret: str | None, code: str, redirect_uri: str) -> OAuthTokenResult:
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
        return OAuthTokenResult(
            access_token=body["access_token"],
            refresh_token=body.get("refresh_token"),
            token_type=body.get("token_type", "Bearer"),
            expires_in=body.get("expires_in"),
            granted_scopes=tuple((body.get("scope") or "").split()),
        )

    def refresh_token(self, *, client_id: str, client_secret: str | None, refresh_token: str) -> OAuthTokenResult:
        payload = urllib.parse.urlencode(
            {
                "client_id": client_id,
                "client_secret": client_secret or "",
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            }
        ).encode("utf-8")
        request = urllib.request.Request(self.TOKEN_ENDPOINT, data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
        return OAuthTokenResult(
            access_token=body["access_token"],
            refresh_token=body.get("refresh_token") or refresh_token,
            token_type=body.get("token_type", "Bearer"),
            expires_in=body.get("expires_in"),
            granted_scopes=tuple((body.get("scope") or "").split()) or READ_ONLY_SCOPES,
        )

    def revoke(self, token: str) -> bool:
        data = urllib.parse.urlencode({"token": token}).encode("utf-8")
        request = urllib.request.Request(self.REVOKE_ENDPOINT, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(request, timeout=30) as response:
            return 200 <= response.status < 300

    def verify_token(self, token: str, scopes: tuple[str, ...]) -> dict[str, object]:
        url = f"{self.VERIFY_ENDPOINT}?access_token={urllib.parse.quote(token)}"
        request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
        granted = tuple((body.get("scope") or "").split())
        missing = [scope for scope in scopes if scope not in granted]
        return {
            "google_account_identifier": body.get("email") or body.get("user_id"),
            "granted_scopes": granted,
            "missing_scopes": tuple(missing),
        }

    def authorize_interactively(self, *, client_id: str, scopes: tuple[str, ...], open_browser: bool = True) -> tuple[OAuthAuthorizationResult, str]:
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
            raise RuntimeError(f"OAuth cancelado: {authorization_code['error']}")
        if "code" not in authorization_code:
            raise TimeoutError("No se recibio el codigo de autorizacion.")
        return result, authorization_code["code"]

