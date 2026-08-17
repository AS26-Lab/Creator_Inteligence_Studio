"""OAuth de escritorio para YouTube / Google."""

from __future__ import annotations

import base64
import json
import hashlib
import secrets
import threading
from pathlib import Path
import urllib.parse
import urllib.request
import webbrowser
from dataclasses import dataclass
from urllib.error import HTTPError
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Protocol
import socket

from creator_intelligence_studio.domain.youtube_integration.services import READ_ONLY_SCOPES


DEFAULT_LOOPBACK_TIMEOUT_SECONDS = 600.0


@dataclass(frozen=True, slots=True)
class OAuthAuthorizationResult:
    authorization_url: str
    state: str
    redirect_uri: str
    code_verifier: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "authorization_url": self.authorization_url,
            "state": self.state,
            "redirect_uri": self.redirect_uri,
            "code_verifier_present": self.code_verifier is not None,
        }


@dataclass(frozen=True, slots=True)
class OAuthTokenResult:
    access_token: str
    refresh_token: str | None
    token_type: str
    expires_in: int | None
    granted_scopes: tuple[str, ...]
    google_account_identifier: str | None = None


@dataclass(frozen=True, slots=True)
class OAuthFlowStageOutcome:
    stage: str
    status: str
    error_type: str | None = None
    http_status: int | None = None
    error_description: str | None = None
    granted_scopes: tuple[str, ...] = ()
    backend: str | None = None
    account_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "stage": self.stage,
            "status": self.status,
            "error_type": self.error_type,
            "http_status": self.http_status,
            "error_description": self.error_description,
            "granted_scopes": list(self.granted_scopes),
            "backend": self.backend,
            "account_id": self.account_id,
        }


@dataclass(frozen=True, slots=True)
class OAuthFlowDiagnostics:
    stages: tuple[OAuthFlowStageOutcome, ...]

    @property
    def final_stage(self) -> str | None:
        return self.stages[-1].stage if self.stages else None

    @property
    def final_status(self) -> str | None:
        return self.stages[-1].status if self.stages else None

    @property
    def last_completed_stage(self) -> str | None:
        for item in reversed(self.stages):
            if item.status == "succeeded":
                return item.stage
        return None

    @property
    def failure_stage(self) -> str | None:
        for item in reversed(self.stages):
            if item.status == "failed":
                return item.stage
        return None

    @property
    def error_type(self) -> str | None:
        for item in reversed(self.stages):
            if item.status == "failed":
                return item.error_type
        return None

    @property
    def http_status(self) -> int | None:
        for item in reversed(self.stages):
            if item.status == "failed":
                return item.http_status
        return None

    @property
    def error_description(self) -> str | None:
        for item in reversed(self.stages):
            if item.status == "failed":
                return item.error_description
        return None

    @property
    def backend(self) -> str | None:
        for item in reversed(self.stages):
            if item.backend:
                return item.backend
        return None

    @property
    def granted_scopes(self) -> tuple[str, ...]:
        for item in reversed(self.stages):
            if item.granted_scopes:
                return item.granted_scopes
        return ()

    def to_dict(self) -> dict[str, object]:
        return {
            "stages": [item.to_dict() for item in self.stages],
            "final_stage": self.final_stage,
            "final_status": self.final_status,
            "last_completed_stage": self.last_completed_stage,
            "failure_stage": self.failure_stage,
            "error_type": self.error_type,
            "http_status": self.http_status,
            "error_description": self.error_description,
            "backend": self.backend,
            "granted_scopes": list(self.granted_scopes),
        }


class OAuthFlowError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        stage: str,
        error_type: str | None = None,
        http_status: int | None = None,
        error_description: str | None = None,
        granted_scopes: tuple[str, ...] = (),
        backend: str | None = None,
        account_id: str | None = None,
        diagnostics: tuple[OAuthFlowStageOutcome, ...] = (),
    ) -> None:
        super().__init__(message)
        self.stage = stage
        self.error_type = error_type
        self.http_status = http_status
        self.error_description = error_description
        self.granted_scopes = granted_scopes
        self.backend = backend
        self.account_id = account_id
        self.diagnostics = diagnostics

    def to_dict(self) -> dict[str, object]:
        diagnostics = OAuthFlowDiagnostics(self.diagnostics)
        return {
            "stage": self.stage,
            "error_type": self.error_type,
            "http_status": self.http_status,
            "error_description": self.error_description,
            "granted_scopes": list(self.granted_scopes),
            "backend": self.backend,
            "account_id": self.account_id,
            "diagnostics": diagnostics.to_dict(),
        }


def _sanitize_error_description(description: str | None) -> str | None:
    if description is None:
        return None
    text = " ".join(str(description).split()).strip()
    if not text:
        return None
    return text[:240]


@dataclass(slots=True)
class OAuthLoopbackSession:
    authorization: OAuthAuthorizationResult
    _server: ThreadingHTTPServer
    _thread: threading.Thread
    _done: threading.Event
    _result: dict[str, str]
    _diagnostics: list[OAuthFlowStageOutcome]
    listener_host: str
    listener_port: int
    listener_address_family: str
    browser_launch_requested: bool
    browser_launch_result: bool | None
    diagnostic_path: Path | None = None
    _closed: bool = False

    def record_stage(
        self,
        stage: str,
        status: str,
        *,
        error_type: str | None = None,
        http_status: int | None = None,
        error_description: str | None = None,
        granted_scopes: tuple[str, ...] = (),
        backend: str | None = None,
        account_id: str | None = None,
    ) -> None:
        self._diagnostics.append(
            OAuthFlowStageOutcome(
                stage=stage,
                status=status,
                error_type=error_type,
                http_status=http_status,
                error_description=_sanitize_error_description(error_description),
                granted_scopes=granted_scopes,
                backend=backend,
                account_id=account_id,
            )
        )
        self._persist_diagnostics()

    def _persist_diagnostics(self) -> None:
        if self.diagnostic_path is None:
            return
        existing: dict[str, object] = {}
        if self.diagnostic_path.exists():
            try:
                loaded = json.loads(self.diagnostic_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    existing = loaded
            except Exception:
                existing = {}
        snapshot = OAuthFlowDiagnostics(self.diagnostics)
        payload = {
            "redirect_uri": self.authorization.redirect_uri,
            "authorization_state": self.authorization.state,
            "listener_host": self.listener_host,
            "listener_port": self.listener_port,
            "listener_address_family": self.listener_address_family,
            "browser_launch_requested": self.browser_launch_requested,
            "browser_launch_result": self.browser_launch_result,
            "callback_received": any(item.stage == "callback_received" and item.status == "succeeded" for item in self._diagnostics),
            "stages": [item.to_dict() for item in self._diagnostics],
            "final_stage": snapshot.final_stage,
            "final_status": snapshot.final_status,
            "last_completed_stage": snapshot.last_completed_stage,
            "failure_stage": snapshot.failure_stage,
            "error_type": snapshot.error_type,
            "http_status": snapshot.http_status,
            "error_description": snapshot.error_description,
            "backend": snapshot.backend,
            "granted_scopes": list(snapshot.granted_scopes),
        }
        existing.update(payload)
        try:
            self.diagnostic_path.parent.mkdir(parents=True, exist_ok=True)
            self.diagnostic_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    @property
    def diagnostics(self) -> tuple[OAuthFlowStageOutcome, ...]:
        return tuple(self._diagnostics)

    def wait_for_code(self, timeout: float = DEFAULT_LOOPBACK_TIMEOUT_SECONDS) -> str:
        if not self._done.wait(timeout=timeout):
            self.record_stage(
                "authorization_code_received",
                "failed",
                error_type="timeout",
                error_description="No se recibio el codigo de autorizacion.",
            )
            raise OAuthFlowError(
                "No se recibio el codigo de autorizacion.",
                stage="authorization_code_received",
                error_type="timeout",
                error_description="No se recibio el codigo de autorizacion.",
                diagnostics=self.diagnostics,
            )
        if "error" in self._result:
            stage = self._result.get("stage") or "authorization_code_received"
            error_type = self._result.get("error")
            error_description = self._result.get("error_description")
            raise OAuthFlowError(
                f"OAuth cancelado: {error_type}",
                stage=stage,
                error_type=error_type,
                error_description=error_description,
                diagnostics=self.diagnostics,
            )
        code = self._result.get("code")
        if not code:
            self.record_stage(
                "authorization_code_received",
                "failed",
                error_type="missing_code",
                error_description="No se recibio el codigo de autorizacion.",
            )
            raise OAuthFlowError(
                "No se recibio el codigo de autorizacion.",
                stage="authorization_code_received",
                error_type="missing_code",
                error_description="No se recibio el codigo de autorizacion.",
                diagnostics=self.diagnostics,
            )
        return code

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self._server.shutdown()
        except Exception:
            pass
        self._thread.join(timeout=5)
        self._server.server_close()


class YouTubeOAuthClient(Protocol):
    def begin_authorization(self, *, client_id: str, scopes: tuple[str, ...], redirect_uri: str | None = None, state: str | None = None, code_verifier: str | None = None) -> OAuthAuthorizationResult: ...
    def exchange_code(self, *, client_id: str, client_secret: str | None, code: str, redirect_uri: str, code_verifier: str | None = None) -> OAuthTokenResult: ...
    def refresh_token(self, *, client_id: str, client_secret: str | None, refresh_token: str) -> OAuthTokenResult: ...
    def start_loopback_authorization(self, *, client_id: str, scopes: tuple[str, ...], open_browser: bool = True, diagnostic_path: Path | None = None) -> OAuthLoopbackSession: ...
    def authorize_interactively(self, *, client_id: str, scopes: tuple[str, ...], open_browser: bool = True, diagnostic_path: Path | None = None) -> tuple[OAuthAuthorizationResult, str]: ...
    def revoke(self, token: str) -> bool: ...
    def verify_token(self, token: str, scopes: tuple[str, ...]) -> dict[str, object]: ...


class DesktopYouTubeOAuthClient:
    """OAuth para aplicaciones instaladas usando loopback o navegador."""

    AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
    REVOKE_ENDPOINT = "https://oauth2.googleapis.com/revoke"
    VERIFY_ENDPOINT = "https://oauth2.googleapis.com/tokeninfo"

    @staticmethod
    def _generate_code_verifier() -> str:
        verifier = secrets.token_urlsafe(64)
        if len(verifier) < 43:
            verifier = (verifier + secrets.token_urlsafe(64))[:43]
        return verifier[:128]

    @staticmethod
    def _build_code_challenge(code_verifier: str) -> str:
        digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")

    @staticmethod
    def _decode_http_error(exc: Exception) -> tuple[int | None, str | None, str | None]:
        status = getattr(exc, "code", None)
        response = getattr(exc, "read", None)
        if response is None:
            return status, None, None
        try:
            body = response().decode("utf-8")
        except Exception:
            return status, None, None
        if not body:
            return status, None, None
        try:
            payload = json.loads(body)
        except Exception:
            return status, None, _sanitize_error_description(body)
        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, dict):
                message = str(error.get("description") or error.get("message") or "").strip()
                if message:
                    return status, str(error.get("error") or error.get("code") or "oauth_error").strip() or None, _sanitize_error_description(message)
                reason = error.get("error") or error.get("error_description")
                if reason:
                    text = str(reason).strip()
                    return status, text or None, _sanitize_error_description(text)
            if isinstance(error, str) and error.strip():
                error_type = error.strip()
                description = str(payload.get("error_description") or "").strip()
                return status, error_type, _sanitize_error_description(description or error_type)
            description = str(payload.get("error_description") or "").strip()
            if description:
                error_type = str(payload.get("error") or "oauth_error").strip() or None
                return status, error_type, _sanitize_error_description(description)
        return status, None, _sanitize_error_description(body)

    def begin_authorization(self, *, client_id: str, scopes: tuple[str, ...], redirect_uri: str | None = None, state: str | None = None, code_verifier: str | None = None) -> OAuthAuthorizationResult:
        redirect_uri = redirect_uri or "http://127.0.0.1/callback"
        state = state or secrets.token_urlsafe(24)
        code_verifier = code_verifier or self._generate_code_verifier()
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
            "state": state,
            "code_challenge": self._build_code_challenge(code_verifier),
            "code_challenge_method": "S256",
        }
        return OAuthAuthorizationResult(
            authorization_url=f"{self.AUTH_ENDPOINT}?{urllib.parse.urlencode(params)}",
            state=state,
            redirect_uri=redirect_uri,
            code_verifier=code_verifier,
        )

    def exchange_code(self, *, client_id: str, client_secret: str | None, code: str, redirect_uri: str, code_verifier: str | None = None) -> OAuthTokenResult:
        payload_fields = {
            "client_id": client_id,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }
        if code_verifier:
            payload_fields["code_verifier"] = code_verifier
        if client_secret:
            payload_fields["client_secret"] = client_secret
        payload = urllib.parse.urlencode(payload_fields).encode("utf-8")
        request = urllib.request.Request(self.TOKEN_ENDPOINT, data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            status, error_type, description = self._decode_http_error(exc)
            raise OAuthFlowError(
                "OAuth token exchange failed.",
                stage="token_exchange_started",
                error_type=error_type or "http_error",
                http_status=status,
                error_description=description,
            ) from exc
        except Exception as exc:
            raise OAuthFlowError(
                "OAuth token exchange failed.",
                stage="token_exchange_started",
                error_type=type(exc).__name__,
                error_description=_sanitize_error_description(str(exc)),
            ) from exc
        return OAuthTokenResult(
            access_token=body["access_token"],
            refresh_token=body.get("refresh_token"),
            token_type=body.get("token_type", "Bearer"),
            expires_in=body.get("expires_in"),
            granted_scopes=tuple((body.get("scope") or "").split()),
        )

    def refresh_token(self, *, client_id: str, client_secret: str | None, refresh_token: str) -> OAuthTokenResult:
        payload_fields = {
            "client_id": client_id,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        if client_secret:
            payload_fields["client_secret"] = client_secret
        payload = urllib.parse.urlencode(payload_fields).encode("utf-8")
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

    def start_loopback_authorization(self, *, client_id: str, scopes: tuple[str, ...], open_browser: bool = True, diagnostic_path: Path | None = None) -> OAuthLoopbackSession:
        authorization_code: dict[str, str] = {}
        done = threading.Event()
        ready = threading.Event()
        diagnostics: list[OAuthFlowStageOutcome] = []
        persist_snapshot = lambda: None

        def record_stage(
            stage: str,
            status: str,
            *,
            error_type: str | None = None,
            http_status: int | None = None,
            error_description: str | None = None,
            granted_scopes: tuple[str, ...] = (),
            backend: str | None = None,
            account_id: str | None = None,
        ) -> None:
            diagnostics.append(
                OAuthFlowStageOutcome(
                    stage=stage,
                    status=status,
                    error_type=error_type,
                    http_status=http_status,
                    error_description=_sanitize_error_description(error_description),
                    granted_scopes=granted_scopes,
                    backend=backend,
                    account_id=account_id,
                )
            )
            if diagnostic_path is not None:
                persist_snapshot()

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # type: ignore[override]
                parsed = urllib.parse.urlparse(self.path)
                params = urllib.parse.parse_qs(parsed.query)
                has_code = bool(params.get("code", [""])[0])
                has_error = "error" in params
                if not has_code and not has_error:
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b"Waiting for Google authorization redirect.")
                    return
                record_stage("callback_received", "succeeded", backend="loopback")
                if params.get("state", [""])[0] != result.state:
                    record_stage("state_validated", "failed", error_type="state_mismatch", error_description="state mismatch", backend="loopback")
                    authorization_code["error"] = "state_mismatch"
                    authorization_code["stage"] = "state_validated"
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b"state mismatch")
                    done.set()
                    return
                record_stage("state_validated", "succeeded", backend="loopback")
                if has_error:
                    error_type = params["error"][0]
                    error_description = params.get("error_description", [""])[0]
                    record_stage("authorization_code_received", "failed", error_type=error_type, error_description=error_description, backend="loopback")
                    authorization_code["error"] = params["error"][0]
                    authorization_code["stage"] = "authorization_code_received"
                    authorization_code["error_description"] = error_description
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b"Authorization cancelled. You can close this window.")
                    done.set()
                    return
                record_stage("authorization_code_received", "succeeded", backend="loopback")
                authorization_code["code"] = params.get("code", [""])[0]
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Authorization complete. You can close this window.")
                done.set()

            def log_message(self, format, *args):  # noqa: A003
                return

        listener_host = "127.0.0.1"
        server = ThreadingHTTPServer((listener_host, 0), Handler)
        result = self.begin_authorization(
            client_id=client_id,
            scopes=scopes,
            redirect_uri=f"http://127.0.0.1:{server.server_address[1]}/callback",
        )
        listener_address_family_value = getattr(server, "address_family", socket.AF_INET)
        listener_address_family = "AF_INET6" if listener_address_family_value == socket.AF_INET6 else "AF_INET" if listener_address_family_value == socket.AF_INET else str(listener_address_family_value)
        browser_launch_result: bool | None = None

        def _persist_snapshot() -> None:
            if diagnostic_path is None:
                return
            snapshot = OAuthFlowDiagnostics(tuple(diagnostics))
            payload = {
                "authorization_state": result.state,
                "authorization_url": result.authorization_url,
                "redirect_uri": result.redirect_uri,
                "listener_host": listener_host,
                "listener_port": int(server.server_address[1]),
                "listener_address_family": listener_address_family,
                "browser_launch_requested": open_browser,
                "browser_launch_result": browser_launch_result,
                "callback_received": any(item.stage == "callback_received" and item.status == "succeeded" for item in diagnostics),
                "stages": [item.to_dict() for item in diagnostics],
                "final_stage": snapshot.final_stage,
                "final_status": snapshot.final_status,
                "last_completed_stage": snapshot.last_completed_stage,
                "failure_stage": snapshot.failure_stage,
                "error_type": snapshot.error_type,
                "http_status": snapshot.http_status,
                "error_description": snapshot.error_description,
                "backend": snapshot.backend,
                "granted_scopes": list(snapshot.granted_scopes),
            }
            existing: dict[str, object] = {}
            if diagnostic_path.exists():
                try:
                    loaded = json.loads(diagnostic_path.read_text(encoding="utf-8"))
                    if isinstance(loaded, dict):
                        existing = loaded
                except Exception:
                    existing = {}
            existing.update(payload)
            try:
                diagnostic_path.parent.mkdir(parents=True, exist_ok=True)
                diagnostic_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception:
                pass

        persist_snapshot = _persist_snapshot
        persist_snapshot()
        def _serve() -> None:
            ready.set()
            server.serve_forever(poll_interval=0.5)

        thread = threading.Thread(target=_serve, daemon=True)
        thread.start()
        if not ready.wait(timeout=5):
            server.server_close()
            raise TimeoutError("No se pudo iniciar el listener OAuth de YouTube.")
        browser_launch_result: bool | None = None
        if open_browser:
            browser_launch_result = webbrowser.open(result.authorization_url)
        persist_snapshot()
        return OAuthLoopbackSession(
            authorization=result,
            _server=server,
            _thread=thread,
            _done=done,
            _result=authorization_code,
            _diagnostics=diagnostics,
            listener_host=listener_host,
            listener_port=int(server.server_address[1]),
            listener_address_family=listener_address_family,
            browser_launch_requested=open_browser,
            browser_launch_result=browser_launch_result,
            diagnostic_path=diagnostic_path,
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

    def authorize_interactively(self, *, client_id: str, scopes: tuple[str, ...], open_browser: bool = True, diagnostic_path: Path | None = None) -> tuple[OAuthAuthorizationResult, str]:
        session = self.start_loopback_authorization(client_id=client_id, scopes=scopes, open_browser=open_browser, diagnostic_path=diagnostic_path)
        try:
            code = session.wait_for_code(timeout=DEFAULT_LOOPBACK_TIMEOUT_SECONDS)
            return session.authorization, code
        finally:
            session.close()
