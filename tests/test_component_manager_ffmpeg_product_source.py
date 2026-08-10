from __future__ import annotations

import io
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from creator_intelligence_studio.application.services.component_manager_service import ComponentManagerService
from creator_intelligence_studio.application.services.ffmpeg_component_service import FFmpegHealthCheckResult, FFmpegVersionInfo
from creator_intelligence_studio.domain.components.downloads import (
    ComponentDownloadOverwritePolicy,
    ComponentDownloadPriority,
    ComponentDownloadProgress,
    ComponentDownloadRecord,
    ComponentDownloadRequest,
    ComponentDownloadRetryPolicy,
    ComponentDownloadStatus,
)
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.downloads.http_transport import HTTPTransportResponse
from creator_intelligence_studio.infrastructure.persistence.database import SQLiteDatabase
from creator_intelligence_studio.infrastructure.persistence.migrations import run_migrations
from creator_intelligence_studio.infrastructure.persistence.sqlite_component_manager_repository import SQLiteComponentManagerRepository
from creator_intelligence_studio.shared.paths import ProjectPaths


def _paths(temp_dir: str) -> ProjectPaths:
    settings = AppSettings(
        application_name="Creator Intelligence Studio",
        environment="development",
        log_level="INFO",
        data_directory="data",
        logs_directory="logs",
        models_directory="models",
        artifacts_directory="artifacts",
        preferred_compute_backend="cuda",
        allow_cpu_basic_mode=True,
        external_ai_enabled=False,
        database_filename="runtime.db",
        database_timeout_seconds=5.0,
        audio_cache_version="v1",
    )
    root = Path(temp_dir)
    paths = ProjectPaths.from_settings(root, settings)
    paths.ensure_runtime_directories()
    return paths


class _NotFoundTransport:
    def open(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        timeout_seconds: float = 30.0,
    ) -> HTTPTransportResponse:
        return HTTPTransportResponse(status_code=404, headers={"content-length": "0"}, url=url, body=io.BytesIO(b""))


class _ReadyHealthChecker:
    def check_bundle(self, *, ffmpeg_path: Path, ffprobe_path: Path, fixture_root: Path) -> FFmpegHealthCheckResult:
        now = datetime.now(tz=timezone.utc)
        return FFmpegHealthCheckResult(
            state="ready",
            ffmpeg_exists=True,
            ffprobe_exists=True,
            ffmpeg_version=FFmpegVersionInfo(raw_line="ffmpeg version 1.2.3", parsed_version="1.2.3", build_metadata=None),
            ffprobe_version=FFmpegVersionInfo(raw_line="ffprobe version 1.2.3", parsed_version="1.2.3", build_metadata=None),
            ffmpeg_path=str(ffmpeg_path),
            ffprobe_path=str(ffprobe_path),
            fixture_path=str(fixture_root / "health-fixtures" / "ffmpeg_health.wav"),
            warnings=(),
            error_message=None,
            detected_architecture="AMD64",
            verified_at=now,
        )


def _product_source_request(*, overwrite_policy: ComponentDownloadOverwritePolicy = ComponentDownloadOverwritePolicy.REJECT) -> ComponentDownloadRequest:
    return ComponentDownloadRequest(
        component_id="ffmpeg",
        catalog_version=1,
        source_url="https://github.com/BtbN/FFmpeg-Builds/releases/download/autobuild-2026-07-31-14-10/ffmpeg-n8.1.2-34-g9b6c8969e0-win64-lgpl-8.1.zip",
        expected_sha256="089e4169e93b2b3f3acbfced3c0704d24276a225641bdda04d796d28b07a2a38",
        expected_download_bytes=145349121,
        destination_logical_location="product_source:ffmpeg",
        priority=ComponentDownloadPriority.NORMAL,
        user_initiated=True,
        retry_policy=ComponentDownloadRetryPolicy(max_attempts=1),
        overwrite_policy=overwrite_policy,
        allowed_domains=("github.com", "release-assets.githubusercontent.com"),
        allow_localhost=False,
        test_mode=True,
    )


@unittest.skipUnless(os.getenv("CIS_RUN_PRODUCT_FFMPEG_DOWNLOAD") == "1", "Real product FFmpeg download opt-in disabled")
class FfmpegProductSourceIntegrationTests(unittest.TestCase):
    def test_real_product_download_verifies_and_installs_managed_ffmpeg(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = _paths(temp_dir)
            db = SQLiteDatabase(Path(temp_dir) / "runtime.db", timeout_seconds=5.0)
            with db.connect() as connection:
                run_migrations(connection)

            repository = SQLiteComponentManagerRepository(db)
            service = ComponentManagerService(paths=paths, repository=repository)

            request = service.product_download_request("ffmpeg")
            self.assertIsNotNone(request)
            assert request is not None
            self.assertTrue(str(request.source_url).startswith("https://"))
            self.assertEqual(request.expected_sha256, "089e4169e93b2b3f3acbfced3c0704d24276a225641bdda04d796d28b07a2a38")
            self.assertIn("github.com", request.allowed_domains)

            record = service.start_product_download("ffmpeg")
            terminal = service.download_service.wait_for_terminal(record.download_id, timeout_seconds=1800)
            self.assertIsNotNone(terminal)
            self.assertEqual(terminal.status, ComponentDownloadStatus.COMPLETED)
            self.assertEqual(terminal.verified_sha256, request.expected_sha256)
            self.assertEqual(terminal.verified_size_bytes, request.expected_download_bytes)

            artifact = service.download_service.verified_artifact(record.download_id)
            self.assertIsNotNone(artifact)
            install = service.ffmpeg_service.install_local(artifact)
            self.assertEqual(install.state, "ready")
            self.assertIsNotNone(install.health)
            self.assertTrue(install.health.healthy)

            media_tools = service.resolve_media_tools()
            self.assertTrue(media_tools.available)
            self.assertIsNotNone(media_tools.resolution)
            self.assertEqual(media_tools.resolution.source, "managed")

    def test_approved_product_source_404_keeps_cached_artifact_installable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = _paths(temp_dir)
            db = SQLiteDatabase(Path(temp_dir) / "runtime.db", timeout_seconds=5.0)
            with db.connect() as connection:
                run_migrations(connection)

            repository = SQLiteComponentManagerRepository(db)
            service = ComponentManagerService(paths=paths, repository=repository)
            service.ffmpeg_service.health_checker = _ReadyHealthChecker()
            service.download_service.transport = _NotFoundTransport()

            cache_source = Path(temp_dir) / "cached-ffmpeg"
            cache_source.mkdir()
            (cache_source / "ffmpeg.exe").write_text("ffmpeg", encoding="utf-8")
            (cache_source / "ffprobe.exe").write_text("ffprobe", encoding="utf-8")
            (cache_source / "LICENSE.txt").write_text("license", encoding="utf-8")
            now = datetime.now(tz=timezone.utc)
            cached_request = _product_source_request()
            cached_record = ComponentDownloadRecord(
                download_id="cached-ffmpeg",
                identity_key=cached_request.identity_key(),
                component_id=cached_request.component_id,
                catalog_version=cached_request.catalog_version,
                source_url=cached_request.source_url,
                expected_sha256=cached_request.expected_sha256,
                expected_download_bytes=cached_request.expected_download_bytes,
                destination_logical_location=cached_request.destination_logical_location,
                priority=cached_request.priority,
                user_initiated=cached_request.user_initiated,
                retry_policy=cached_request.retry_policy,
                overwrite_policy=cached_request.overwrite_policy,
                allowed_domains=cached_request.allowed_domains,
                allow_localhost=cached_request.allow_localhost,
                test_mode=cached_request.test_mode,
                max_redirects=cached_request.max_redirects,
                connect_timeout_seconds=cached_request.connect_timeout_seconds,
                read_timeout_seconds=cached_request.read_timeout_seconds,
                stalled_timeout_seconds=cached_request.stalled_timeout_seconds,
                chunk_size_bytes=cached_request.chunk_size_bytes,
                safety_margin_bytes=cached_request.safety_margin_bytes,
                status=ComponentDownloadStatus.COMPLETED,
                progress=ComponentDownloadProgress(downloaded_bytes=3, total_bytes=3, started_at=now, updated_at=now),
                partial_path=str(cache_source / "cached-ffmpeg.partial"),
                verified_artifact_path=str(cache_source),
                source_etag=None,
                source_last_modified=None,
                bytes_received=3,
                attempts=1,
                max_attempts=1,
                verification_status="verified",
                verified_sha256=cached_request.expected_sha256,
                verified_size_bytes=3,
                error=None,
                created_at=now,
                updated_at=now,
                completed_at=now,
                cancelled_at=None,
                interrupted_at=None,
                resume_requested_at=None,
                pause_requested_at=None,
                cancel_requested_at=None,
                verified_at=now,
                recovered_at=None,
                metadata={},
            )
            service.download_service.repository.save_record(cached_record)

            request = _product_source_request(overwrite_policy=ComponentDownloadOverwritePolicy.REPLACE)
            record = service.download_service.start_download(request)
            terminal = service.download_service.wait_for_terminal(record.download_id, timeout_seconds=10)
            self.assertIsNotNone(terminal)
            assert terminal is not None
            self.assertEqual(terminal.status, ComponentDownloadStatus.FAILED)
            self.assertIsNotNone(terminal.error)
            self.assertEqual(terminal.error.category.value, "http_4xx")
            self.assertEqual(service.catalog().get_entry("ffmpeg").source_url, request.source_url)

            cached = service.latest_verified_artifact("ffmpeg")
            self.assertIsNotNone(cached)
            assert cached is not None

            install = service.ffmpeg_service.install_local(Path(cached.verified_artifact_path))
            self.assertEqual(install.state, "ready")
            media_tools = service.resolve_media_tools()
            self.assertTrue(media_tools.available)


if __name__ == "__main__":
    unittest.main()
