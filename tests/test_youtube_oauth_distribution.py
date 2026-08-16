from __future__ import annotations

import io
import json
import tempfile
import unittest
import urllib.parse
from pathlib import Path
from unittest.mock import patch

from creator_intelligence_studio.infrastructure.packaging import WindowsAppRuntimeManifest
from creator_intelligence_studio.infrastructure.youtube.oauth_client import DesktopYouTubeOAuthClient
from creator_intelligence_studio.infrastructure.youtube.oauth_config import load_google_desktop_client_bootstrap
from scripts import build_windows_app as build_windows_app_script


def _write_minimal_config(project_root: Path, *, youtube_oauth_client_id: str | None = None) -> None:
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


class YouTubeOAuthDistributionTests(unittest.TestCase):
    def test_pkce_begin_authorization_uses_loopback_and_challenge(self) -> None:
        client = DesktopYouTubeOAuthClient()
        result = client.begin_authorization(client_id="client-id", scopes=("scope-a", "scope-b"))

        self.assertEqual(result.redirect_uri, "http://localhost/callback")
        self.assertIsNotNone(result.code_verifier)
        self.assertGreaterEqual(len(result.code_verifier or ""), 43)
        self.assertIn("code_challenge=", result.authorization_url)
        self.assertIn("code_challenge_method=S256", result.authorization_url)
        self.assertIn("redirect_uri=http%3A%2F%2Flocalhost%2Fcallback", result.authorization_url)

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
            return _Response()

        with patch("creator_intelligence_studio.infrastructure.youtube.oauth_client.urllib.request.urlopen", side_effect=_fake_urlopen):
            result = client.exchange_code(
                client_id="client-id",
                client_secret=None,
                code="auth-code",
                redirect_uri="http://localhost/callback",
                code_verifier="verifier-123",
            )

        payload = urllib.parse.parse_qs(str(captured["body"]))
        self.assertEqual(payload["client_id"], ["client-id"])
        self.assertEqual(payload["code"], ["auth-code"])
        self.assertEqual(payload["redirect_uri"], ["http://localhost/callback"])
        self.assertEqual(payload["code_verifier"], ["verifier-123"])
        self.assertNotIn("client_secret", payload)
        self.assertEqual(result.access_token, "access-token")

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
        self.assertIn("http%3A%2F%2Flocalhost%3A54321%2Fcallback", opened_urls[0])
        self.assertEqual(result.redirect_uri, "http://localhost:54321/callback")
        self.assertIsNotNone(result.code_verifier)

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
        self.assertTrue(any("youtube_oauth_client_id" in blocker for blocker in report.blockers))


if __name__ == "__main__":
    unittest.main()
