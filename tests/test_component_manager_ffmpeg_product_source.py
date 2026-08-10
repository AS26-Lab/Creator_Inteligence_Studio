from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from creator_intelligence_studio.application.services.component_manager_service import ComponentManagerService
from creator_intelligence_studio.domain.components.downloads import ComponentDownloadStatus
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
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
            self.assertTrue(str(request.source_url).startswith("https://"))
            self.assertEqual(request.expected_sha256, "6b4edff47f121d2ed218b1b19d17f67aed08f9f1c9cbcee576fd0548a748c412")
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


if __name__ == "__main__":
    unittest.main()
