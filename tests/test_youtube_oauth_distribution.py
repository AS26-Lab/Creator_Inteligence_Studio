from __future__ import annotations

import io
import json
import tempfile
import unittest
import urllib.parse
import threading
from urllib.error import HTTPError
from pathlib import Path
from datetime import timedelta
from unittest.mock import patch

from creator_intelligence_studio.infrastructure.packaging import WindowsAppRuntimeManifest
from creator_intelligence_studio.infrastructure.youtube.credential_store import WindowsSecureCredentialStore, build_default_youtube_credential_store
from creator_intelligence_studio.infrastructure.youtube.oauth_client import (
    DEFAULT_LOOPBACK_TIMEOUT_SECONDS,
    DesktopYouTubeOAuthClient,
    OAuthFlowError,
    OAuthFlowStageOutcome,
    OAuthLoopbackSession,
    OAuthAuthorizationResult,
)
from creator_intelligence_studio.infrastructure.youtube.oauth_config import load_google_desktop_client_bootstrap
from creator_intelligence_studio.presentation.cli.integrations_cli import _auth_session_path, _store_active_auth_session
from creator_intelligence_studio.shared.dates import utc_now
from scripts import build_windows_app as build_windows_app_script


def _write_minimal_config(
    project_root: Path,
    *,
    youtube_oauth_client_id: str | None = None,
    youtube_oauth_client_secret: str | None = None,
) -> None:
    config_dir = project_root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "application_name": "Creator Intelligence Studio",
        "environment": "development",
        "log_level": "INFO",
        "data_directory": "data",
        "logs_directory": "logs",
        "models_directory": "models",
        "artifacts_directory": "artifacts",
        "preferred_compute_backend": "cuda",
        "allow_cpu_basic_mode": True,
        "external_ai_enabled": False,
        "youtube_oauth_client_id": youtube_oauth_client_id,
        "youtube_oauth_client_secret": youtube_oauth_client_secret,
    }
    (config_dir / "default.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _fixed_manifest(bundle_root: Path) -> WindowsAppRuntimeManifest:
    return WindowsAppRuntimeManifest(
        runtime_format_version=1,
        application_name="Creator Intelligence Studio",
        application_version="0.1.0",
        creator_intelligence_studio_version="0.1.0",
        packaging_tool=None,
        packaging_tool_version=None,
        python_version="3.11.9",
        faster_whisper_version="1.2.1",
        ctranslate2_version="4.8.1",
        platform="Windows",
        architecture="x86_64",
        cpu_supported=True,
        gpu_supported=False,
        build_revision="abc1234",
        build_timestamp="2026-08-16T00:00:00+00:00",
        bundle_kind="onedir",
        notices_reference="docs/TRANSCRIPTION_RUNTIME_LICENSING.md",
        runtime_root=str(bundle_root / "runtime"),
        libraries_root=str(bundle_root / "libraries"),
        resources_root=str(bundle_root / "resources"),
    )


class _FakeHTTPServer:
    def __init__(self, address, handler_cls) -> None:
        self.server_address = ("localhost", 54321)
        self._handler_cls = handler_cls
        self.shutdown_called = False
        self.server_closed = False

    def serve_forever(self, poll_interval: float = 0.5) -> None:  # noqa: ARG002
        callback_state = None
        for cell in self._handler_cls.do_GET.__closure__ or ():
            value = cell.cell_contents
            if hasattr(value, "state"):
                callback_state = value.state
                break
        if callback_state is None:
            raise AssertionError("No se pudo resolver el state de OAuth desde la clausura.")
        handler = self._handler_cls.__new__(self._handler_cls)
        handler.path = f"/callback?state={urllib.parse.quote(callback_state)}&code=auth-code-123"
        handler.send_response = lambda status: None
        handler.end_headers = lambda: None
        handler.wfile = io.BytesIO()
        handler.log_message = lambda *args, **kwargs: None
        self._handler_cls.do_GET(handler)

    def shutdown(self) -> None:
        self.shutdown_called = True

    def server_close(self) -> None:
        self.server_closed = True


class _FakeThread:
    def join(self, timeout: float | None = None) -> None:  # noqa: ARG002
        return


class YouTubeOAuthDistributionTests(unittest.TestCase):
    def test_pkce_begin_authorization_uses_loopback_and_challenge(self) -> None:
        client = DesktopYouTubeOAuthClient()
        result = client.begin_authorization(client_id="client-id", scopes=("scope-a", "scope-b"))

        self.assertEqual(result.redirect_uri, "http://127.0.0.1/callback")
        self.assertIsNotNone(result.code_verifier)
        self.assertGreaterEqual(len(result.code_verifier or ""), 43)
        self.assertIn("code_challenge=", result.authorization_url)
        self.assertIn("code_challenge_method=S256", result.authorization_url)
        self.assertIn("redirect_uri=http%3A%2F%2F127.0.0.1%2Fcallback", result.authorization_url)

    def test_exchange_code_omits_secret_and_includes_verifier_when_present(self) -> None:
        client = DesktopYouTubeOAuthClient()
        captured: dict[str, object] = {}

        class _Response:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
                return False

            def read(self):
                return json.dumps(
                    {
                        "access_token": "access-token",
                        "refresh_token": "refresh-token",
                        "token_type": "Bearer",
                        "expires_in": 3600,
                        "scope": "scope-a scope-b",
                    }
                ).encode("utf-8")

        def _fake_urlopen(request, timeout=30):  # noqa: ARG001
            captured["body"] = request.data.decode("utf-8")
            captured["method"] = "POST" if request.data is not None else "GET"
            captured["content_type"] = dict(request.header_items()).get("Content-type") or dict(request.header_items()).get("Content-Type")
            return _Response()

        with patch("creator_intelligence_studio.infrastructure.youtube.oauth_client.urllib.request.urlopen", side_effect=_fake_urlopen):
            result = client.exchange_code(
                client_id="client-id",
                client_secret=None,
                code="auth-code",
                redirect_uri="http://127.0.0.1/callback",
                code_verifier="verifier-123",
            )

        payload = urllib.parse.parse_qs(str(captured["body"]))
        self.assertEqual(payload["client_id"], ["client-id"])
        self.assertEqual(payload["code"], ["auth-code"])
        self.assertEqual(payload["redirect_uri"], ["http://127.0.0.1/callback"])
        self.assertEqual(payload["code_verifier"], ["verifier-123"])
        self.assertNotIn("client_secret", payload)
        self.assertEqual(captured.get("method"), "POST")
        self.assertEqual(captured.get("content_type"), "application/x-www-form-urlencoded")
        self.assertEqual(result.access_token, "access-token")

    def test_exchange_code_omits_empty_client_secret(self) -> None:
        client = DesktopYouTubeOAuthClient()
        captured: dict[str, object] = {}

        class _Response:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
                return False

            def read(self):
                return json.dumps(
                    {
                        "access_token": "access-token",
                        "refresh_token": "refresh-token",
                        "token_type": "Bearer",
                        "expires_in": 3600,
                        "scope": "scope-a",
                    }
                ).encode("utf-8")

        def _fake_urlopen(request, timeout=30):  # noqa: ARG001
            captured["body"] = request.data.decode("utf-8")
            captured["method"] = "POST" if request.data is not None else "GET"
            captured["content_type"] = dict(request.header_items()).get("Content-type") or dict(request.header_items()).get("Content-Type")
            return _Response()

        with patch("creator_intelligence_studio.infrastructure.youtube.oauth_client.urllib.request.urlopen", side_effect=_fake_urlopen):
            client.exchange_code(
                client_id="client-id",
                client_secret="",
                code="auth-code",
                redirect_uri="http://127.0.0.1/callback",
                code_verifier="verifier-123",
            )

        payload = urllib.parse.parse_qs(str(captured["body"]))
        self.assertNotIn("client_secret", payload)
        self.assertEqual(captured.get("method"), "POST")
        self.assertEqual(captured.get("content_type"), "application/x-www-form-urlencoded")

    def test_refresh_token_includes_client_secret_when_present(self) -> None:
        client = DesktopYouTubeOAuthClient()
        captured: dict[str, object] = {}

        class _Response:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
                return False

            def read(self):
                return json.dumps(
                    {
                        "access_token": "refreshed-access-token",
                        "refresh_token": "refresh-token",
                        "token_type": "Bearer",
                        "expires_in": 3600,
                        "scope": "scope-a scope-b",
                    }
                ).encode("utf-8")

        def _fake_urlopen(request, timeout=30):  # noqa: ARG001
            captured["body"] = request.data.decode("utf-8")
            captured["method"] = "POST" if request.data is not None else "GET"
            captured["content_type"] = dict(request.header_items()).get("Content-type") or dict(request.header_items()).get("Content-Type")
            return _Response()

        with patch("creator_intelligence_studio.infrastructure.youtube.oauth_client.urllib.request.urlopen", side_effect=_fake_urlopen):
            result = client.refresh_token(
                client_id="client-id",
                client_secret="client-secret",
                refresh_token="refresh-token",
            )

        payload = urllib.parse.parse_qs(str(captured["body"]))
        self.assertEqual(payload["client_id"], ["client-id"])
        self.assertEqual(payload["grant_type"], ["refresh_token"])
        self.assertEqual(payload["refresh_token"], ["refresh-token"])
        self.assertEqual(payload["client_secret"], ["client-secret"])
        self.assertEqual(captured.get("method"), "POST")
        self.assertEqual(captured.get("content_type"), "application/x-www-form-urlencoded")
        self.assertEqual(result.access_token, "refreshed-access-token")

    def test_pkce_verifier_matches_generated_challenge_across_token_exchange(self) -> None:
        client = DesktopYouTubeOAuthClient()
        auth = client.begin_authorization(client_id="client-id", scopes=("scope-a",))
        captured: dict[str, object] = {}

        class _Response:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
                return False

            def read(self):
                return json.dumps(
                    {
                        "access_token": "access-token",
                        "refresh_token": "refresh-token",
                        "token_type": "Bearer",
                        "expires_in": 3600,
                        "scope": "scope-a",
                    }
                ).encode("utf-8")

        def _fake_urlopen(request, timeout=30):  # noqa: ARG001
            captured["body"] = request.data.decode("utf-8")
            return _Response()

        with patch("creator_intelligence_studio.infrastructure.youtube.oauth_client.urllib.request.urlopen", side_effect=_fake_urlopen):
            client.exchange_code(
                client_id="client-id",
                client_secret=None,
                code="auth-code",
                redirect_uri=auth.redirect_uri,
                code_verifier=auth.code_verifier,
            )

        payload = urllib.parse.parse_qs(str(captured["body"]))
        self.assertEqual(payload["code_verifier"], [auth.code_verifier])
        self.assertEqual(client._build_code_challenge(auth.code_verifier), urllib.parse.parse_qs(auth.authorization_url.split("?", 1)[1])["code_challenge"][0])

    def test_decode_http_error_preserves_google_oauth_error_description(self) -> None:
        client = DesktopYouTubeOAuthClient()
        body = io.BytesIO(
            json.dumps(
                {
                    "error": "invalid_request",
                    "error_description": "The redirect URI is missing or invalid.",
                }
            ).encode("utf-8")
        )
        error = HTTPError(
            url="https://oauth2.googleapis.com/token",
            code=400,
            msg="Bad Request",
            hdrs=None,
            fp=body,
        )

        status, error_type, description = client._decode_http_error(error)

        self.assertEqual(status, 400)
        self.assertEqual(error_type, "invalid_request")
        self.assertEqual(description, "The redirect URI is missing or invalid.")

    def test_authorize_interactively_uses_ephemeral_localhost_callback(self) -> None:
        client = DesktopYouTubeOAuthClient()
        opened_urls: list[str] = []

        with patch("creator_intelligence_studio.infrastructure.youtube.oauth_client.ThreadingHTTPServer", _FakeHTTPServer), patch(
            "creator_intelligence_studio.infrastructure.youtube.oauth_client.webbrowser.open",
            side_effect=lambda url: opened_urls.append(url) or True,
        ):
            result, code = client.authorize_interactively(client_id="client-id", scopes=("scope-a",))

        self.assertEqual(code, "auth-code-123")
        self.assertTrue(opened_urls)
        self.assertIn("code_challenge=", opened_urls[0])
        self.assertIn("http%3A%2F%2F127.0.0.1%3A54321%2Fcallback", opened_urls[0])
        self.assertEqual(result.redirect_uri, "http://127.0.0.1:54321/callback")
        self.assertIsNotNone(result.code_verifier)

    def test_authorize_interactively_ignores_empty_callback_hits(self) -> None:
        client = DesktopYouTubeOAuthClient()
        opened_urls: list[str] = []

        class _NoisyHTTPServer(_FakeHTTPServer):
            def serve_forever(self, poll_interval: float = 0.5) -> None:  # noqa: ARG002
                callback_state = None
                for cell in self._handler_cls.do_GET.__closure__ or ():
                    value = cell.cell_contents
                    if hasattr(value, "state"):
                        callback_state = value.state
                        break
                if callback_state is None:
                    raise AssertionError("No se pudo resolver el state de OAuth desde la clausura.")
                handler = self._handler_cls.__new__(self._handler_cls)
                handler.send_response = lambda status: None
                handler.end_headers = lambda: None
                handler.wfile = io.BytesIO()
                handler.log_message = lambda *args, **kwargs: None
                handler.path = "/callback"
                self._handler_cls.do_GET(handler)
                handler.path = f"/callback?state={urllib.parse.quote(callback_state)}&code=auth-code-456"
                self._handler_cls.do_GET(handler)

        with patch("creator_intelligence_studio.infrastructure.youtube.oauth_client.ThreadingHTTPServer", _NoisyHTTPServer), patch(
            "creator_intelligence_studio.infrastructure.youtube.oauth_client.webbrowser.open",
            side_effect=lambda url: opened_urls.append(url) or True,
        ):
            result, code = client.authorize_interactively(client_id="client-id", scopes=("scope-a",))

        self.assertEqual(code, "auth-code-456")
        self.assertTrue(opened_urls)
        self.assertIn("http%3A%2F%2F127.0.0.1%3A54321%2Fcallback", opened_urls[0])
        self.assertEqual(result.redirect_uri, "http://127.0.0.1:54321/callback")
        self.assertIsNotNone(result.code_verifier)

    def test_authorize_interactively_uses_extended_loopback_timeout(self) -> None:
        client = DesktopYouTubeOAuthClient()
        observed_timeouts: list[float] = []

        class _Session:
            def __init__(self) -> None:
                self.authorization = client.begin_authorization(client_id="client-id", scopes=("scope-a",))

            def wait_for_code(self, timeout: float = 120.0) -> str:  # noqa: ARG002
                observed_timeouts.append(timeout)
                return "auth-code"

            def close(self) -> None:
                return

        with patch.object(client, "start_loopback_authorization", return_value=_Session()):
            result, code = client.authorize_interactively(client_id="client-id", scopes=("scope-a",))

        self.assertEqual(code, "auth-code")
        self.assertEqual(observed_timeouts, [DEFAULT_LOOPBACK_TIMEOUT_SECONDS])
        self.assertTrue(result.code_verifier)

    def test_start_loopback_authorization_records_listener_and_persists_diagnostics(self) -> None:
        client = DesktopYouTubeOAuthClient()
        with tempfile.TemporaryDirectory() as temp_dir:
            diagnostic_path = Path(temp_dir) / "youtube_auth_session.json"
            session = client.start_loopback_authorization(
                client_id="client-id",
                scopes=("scope-a",),
                open_browser=False,
                diagnostic_path=diagnostic_path,
            )
            self.assertEqual(session.listener_host, "127.0.0.1")
            self.assertEqual(session.listener_address_family, "AF_INET")
            self.assertFalse(session.browser_launch_requested)
            self.assertIsNone(session.browser_launch_result)
            with urllib.request.urlopen(
                f"{session.authorization.redirect_uri}?state={urllib.parse.quote(session.authorization.state)}&code=synthetic-code",
                timeout=5,
            ) as response:
                self.assertEqual(response.status, 200)
            code = session.wait_for_code(timeout=5)
            session.close()

            self.assertEqual(code, "synthetic-code")
            payload = json.loads(diagnostic_path.read_text(encoding="utf-8"))
            self.assertTrue(payload["callback_received"])
            self.assertEqual(payload["listener_host"], "127.0.0.1")
            self.assertEqual(payload["listener_address_family"], "AF_INET")
            self.assertEqual(payload["final_stage"], "authorization_code_received")
            self.assertEqual(payload["last_completed_stage"], "authorization_code_received")
            self.assertNotIn("access_token", json.dumps(payload, ensure_ascii=False))

    def test_store_active_auth_session_preserves_existing_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            connector = type("ConnectorStub", (), {"_data_root": Path(temp_dir) / "integrations" / "youtube"})()
            path = _auth_session_path(connector, "creator-a")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(
                    {
                        "creator_id": "creator-a",
                        "callback_received": True,
                        "stages": [{"stage": "callback_received", "status": "succeeded"}],
                        "final_stage": "authorization_code_received",
                        "last_completed_stage": "state_validated",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            _store_active_auth_session(
                connector,
                "creator-a",
                started_at=utc_now(),
                expires_at=utc_now() + timedelta(minutes=10),
            )

            payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertTrue(payload["callback_received"])
        self.assertEqual(payload["final_stage"], "authorization_code_received")
        self.assertEqual(payload["last_completed_stage"], "state_validated")
        self.assertEqual(payload["status"], "active")
        self.assertEqual(payload["connector_id"], "youtube.connector")

    def test_loopback_session_reports_missing_code_as_diagnostic_failure(self) -> None:
        session = OAuthLoopbackSession(
            authorization=OAuthAuthorizationResult(
                authorization_url="https://auth.local/start",
                state="state-1",
                redirect_uri="http://127.0.0.1:54321/callback",
                code_verifier="verifier-1",
            ),
            _server=_FakeHTTPServer(("", 0), handler_cls=type("H", (), {})),
            _thread=_FakeThread(),
            _done=threading.Event(),
            _result={},
            _diagnostics=[],
            listener_host="127.0.0.1",
            listener_port=54321,
            listener_address_family="AF_INET",
            browser_launch_requested=False,
            browser_launch_result=None,
        )
        session._done.set()

        with self.assertRaises(OAuthFlowError) as ctx:
            session.wait_for_code(timeout=0.01)

        self.assertEqual(ctx.exception.stage, "authorization_code_received")
        self.assertEqual(ctx.exception.error_type, "missing_code")
        self.assertNotIn("access_token", json.dumps(ctx.exception.to_dict(), ensure_ascii=False))

    def test_loopback_session_reports_state_mismatch_failure(self) -> None:
        session = OAuthLoopbackSession(
            authorization=OAuthAuthorizationResult(
                authorization_url="https://auth.local/start",
                state="state-1",
                redirect_uri="http://127.0.0.1:54321/callback",
                code_verifier="verifier-1",
            ),
            _server=_FakeHTTPServer(("", 0), handler_cls=type("H", (), {})),
            _thread=_FakeThread(),
            _done=threading.Event(),
            _result={"error": "state_mismatch", "stage": "state_validated"},
            _diagnostics=[
                OAuthFlowStageOutcome(stage="callback_received", status="succeeded"),
                OAuthFlowStageOutcome(stage="state_validated", status="failed", error_type="state_mismatch"),
            ],
            listener_host="127.0.0.1",
            listener_port=54321,
            listener_address_family="AF_INET",
            browser_launch_requested=False,
            browser_launch_result=None,
        )
        session._done.set()

        with self.assertRaises(OAuthFlowError) as ctx:
            session.wait_for_code(timeout=0.01)

        self.assertEqual(ctx.exception.stage, "state_validated")
        self.assertEqual(ctx.exception.error_type, "state_mismatch")
        self.assertEqual(ctx.exception.diagnostics[-1].stage, "state_validated")

    def test_default_youtube_credential_store_prefers_windows_secure_storage(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, patch.object(WindowsSecureCredentialStore, "is_available", return_value=True):
            store = build_default_youtube_credential_store(Path(temp_dir), environment="production")

        self.assertIsInstance(store, WindowsSecureCredentialStore)

    def test_developer_json_bootstrap_reports_public_identity_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bootstrap_path = root / "ClientGoogle.json"
            bootstrap_path.write_text(
                json.dumps(
                    {
                        "installed": {
                            "client_id": "client-id.apps.googleusercontent.com",
                            "client_secret": "super-secret",
                        }
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            bootstrap = load_google_desktop_client_bootstrap(bootstrap_path)
            public = bootstrap.to_public_dict()

        self.assertEqual(bootstrap.client_id, "client-id.apps.googleusercontent.com")
        self.assertEqual(bootstrap.client_secret, "super-secret")
        self.assertTrue(bootstrap.client_secret_present)
        self.assertEqual(public["source_kind"], "developer_json")
        self.assertEqual(public["client_id"], "client-id.apps.googleusercontent.com")
        self.assertTrue(public["client_secret_present"])

    def test_build_script_bootstraps_bundle_config_without_copying_developer_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            staging_root = root / "dist"
            _write_minimal_config(root, youtube_oauth_client_id=None)
            developer_json = root / "ClientGoogle.json"
            developer_json.write_text(
                json.dumps(
                    {
                        "installed": {
                            "client_id": "client-id.apps.googleusercontent.com",
                            "client_secret": "super-secret",
                        }
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            with patch.object(build_windows_app_script, "build_windows_runtime_manifest", side_effect=lambda **kwargs: _fixed_manifest(Path(kwargs["bundle_root"]))):
                report = build_windows_app_script.build_windows_app(
                    project_root=root,
                    staging_root=staging_root,
                    invoke_packager=False,
                    youtube_oauth_client_json=developer_json,
                )

            bundle_default_config = staging_root / "CreatorIntelligenceStudio" / "config" / "default.json"
            bundle_payload = json.loads(bundle_default_config.read_text(encoding="utf-8"))
            copied_files = [path.name for path in (staging_root / "CreatorIntelligenceStudio").rglob("*") if path.is_file()]

        self.assertTrue(report.success, report.blockers)
        self.assertEqual(bundle_payload["youtube_oauth_client_id"], "client-id.apps.googleusercontent.com")
        self.assertEqual(bundle_payload["youtube_oauth_client_secret"], "super-secret")
        self.assertNotIn("ClientGoogle.json", copied_files)

    def test_build_script_rejects_missing_release_oauth_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            staging_root = root / "dist"
            _write_minimal_config(root, youtube_oauth_client_id=None)
            with patch.object(build_windows_app_script, "build_windows_runtime_manifest", side_effect=lambda **kwargs: _fixed_manifest(Path(kwargs["bundle_root"]))):
                report = build_windows_app_script.build_windows_app(
                    project_root=root,
                    staging_root=staging_root,
                    invoke_packager=False,
                )

        self.assertFalse(report.success)
        self.assertTrue(
            any("youtube_oauth_client_id" in blocker or "client_secret" in blocker for blocker in report.blockers)
        )


if __name__ == "__main__":
    unittest.main()
