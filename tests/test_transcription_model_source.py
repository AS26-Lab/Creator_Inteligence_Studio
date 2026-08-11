from __future__ import annotations

import hashlib
import tempfile
import types
import unittest
from datetime import datetime, timezone
from pathlib import Path

from creator_intelligence_studio.application.services.component_manager_service import ComponentManagerService
from creator_intelligence_studio.application.services.transcription_model_source_service import TranscriptionModelProductSourceService
from creator_intelligence_studio.domain.components.downloads import VerifiedComponentArtifact
from creator_intelligence_studio.domain.components.catalog import build_default_component_catalog
from creator_intelligence_studio.domain.transcription.model_sources import get_transcription_model_source_manifest
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.downloads.repository import FileSystemComponentDownloadRepository
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


class _FakeModelDownloadService:
    def __init__(self, *, repo: FileSystemComponentDownloadRepository, source_artifact: VerifiedComponentArtifact) -> None:
        self.repository = repo
        self._source_artifact = source_artifact
        self._download_ids: list[str] = []

    def start_download(self, request):
        download_id = f"download-{len(self._download_ids) + 1}"
        self._download_ids.append(download_id)
        return types.SimpleNamespace(download_id=download_id, status=types.SimpleNamespace(value="running"))

    def wait_for_terminal(self, download_id: str, timeout_seconds: float = 30.0):
        return types.SimpleNamespace(status=types.SimpleNamespace(value="completed"), error=None)

    def verified_artifact(self, download_id: str):
        if download_id not in self._download_ids:
            record = self.repository.get_record(download_id)
            if record is None:
                return None
            return VerifiedComponentArtifact(
                download_id=record.download_id,
                component_id=record.component_id,
                verified_artifact_path=record.verified_artifact_path,
                partial_path=record.partial_path,
                sha256=record.verified_sha256 or "",
                size_bytes=record.verified_size_bytes or 0,
                created_at=record.created_at or datetime.now(tz=timezone.utc),
                verified_at=record.verified_at or datetime.now(tz=timezone.utc),
                source_url=record.source_url,
            )
        return self._source_artifact

    def list_downloads(self):
        return self.repository.list_records()


class _FakeRepository:
    def __init__(self, catalog) -> None:
        self._catalog = catalog

    def get_catalog_entry(self, component_id: str):
        return self._catalog.get_entry(component_id)

    def get_catalog(self):
        return self._catalog

    def get_installation(self, component_id: str):
        return None


class TranscriptionModelSourceTests(unittest.TestCase):
    def test_manifest_for_balanced_model_is_exactly_pinned(self) -> None:
        manifest = get_transcription_model_source_manifest("transcription-model.small")
        self.assertIsNotNone(manifest)
        assert manifest is not None
        self.assertEqual(manifest.repository, "Systran/faster-whisper-small")
        self.assertEqual(manifest.revision, "536b0662742c02347bc0e980a01041f333bce120")
        self.assertEqual(manifest.license, "mit")
        self.assertEqual(manifest.total_expected_bytes, 486212372)
        self.assertEqual(len(manifest.files), 4)
        self.assertEqual(
            tuple(Path(file.relative_path).name for file in manifest.files),
            ("config.json", "tokenizer.json", "vocabulary.txt", "model.bin"),
        )
        self.assertTrue(all(file.relative_path.startswith("models--Systran--faster-whisper-small/snapshots/536b0662742c02347bc0e980a01041f333bce120/") for file in manifest.files))
        self.assertNotEqual(manifest.expected_sha256, "0" * 64)

    def test_product_model_download_persists_verified_record_and_rehydrates_after_restart(self) -> None:
        manifest = get_transcription_model_source_manifest("transcription-model.small")
        assert manifest is not None

        with tempfile.TemporaryDirectory() as temp_dir:
            paths = _paths(temp_dir)
            repo = FileSystemComponentDownloadRepository(paths.downloads_directory)
            source_root = Path(temp_dir) / "source"
            source_root.mkdir()
            source_artifact_path = source_root / "source.zip"
            source_artifact_path.write_bytes(b"source artifact bytes")
            source_artifact = VerifiedComponentArtifact(
                download_id="source-download",
                component_id="transcription-model.small",
                verified_artifact_path=str(source_artifact_path),
                partial_path=None,
                sha256=hashlib.sha256(source_artifact_path.read_bytes()).hexdigest(),
                size_bytes=source_artifact_path.stat().st_size,
                created_at=datetime.now(tz=timezone.utc),
                verified_at=datetime.now(tz=timezone.utc),
                source_url=manifest.source_page,
            )

            fake_download_service = _FakeModelDownloadService(repo=repo, source_artifact=source_artifact)
            catalog = build_default_component_catalog()
            service = TranscriptionModelProductSourceService(
                paths=paths,
                repository=_FakeRepository(catalog),
                download_service=fake_download_service,
            )

            original_sha256_file = module_sha256 = None
            original_sha256 = None
            import creator_intelligence_studio.application.services.transcription_model_source_service as module
            original_sha256_file = module._sha256_file
            original_sha256 = hashlib.sha256
            expected_hashes = {
                "config.json": "b55496ac7940a7ae47d2c01eab40edfd8701feec1229d9cce3b40014383fb828",
                "tokenizer.json": "fb7b63191e9bb045082c79fd742a3106a12c99513ab30df4a0d47fa6cb6fd0ab",
                "vocabulary.txt": "34ce3fe1c5041027b3f8d42912270993f986dbc4bb34cf27f951e34a1e453913",
                "model.bin": "3e305921506d8872816023e4c273e75d2419fb89b24da97b4fe7bce14170d671",
            }

            def fake_sha256_file(path: Path) -> str:
                if path.name in expected_hashes:
                    return expected_hashes[path.name]
                digest = original_sha256()
                with path.open("rb") as handle:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                        digest.update(chunk)
                return digest.hexdigest()

            # Patch the hash helper at the module boundary so the unit test can validate persistence without network.
            module._sha256_file = fake_sha256_file  # type: ignore[assignment]
            try:
                result = service.download("transcription-model.small")
            finally:
                module._sha256_file = original_sha256_file  # type: ignore[assignment]

            self.assertEqual(result.status, "completed")
            self.assertIsNotNone(result.verified_artifact)
            self.assertTrue(Path(result.verified_artifact.verified_artifact_path).exists())
            persisted = repo.list_records()
            self.assertEqual(len(persisted), 1)
            self.assertEqual(persisted[0].component_id, "transcription-model.small")
            self.assertEqual(persisted[0].status.value, "completed")
            self.assertEqual(persisted[0].verified_sha256, result.verified_artifact.sha256)

            restarted_service = ComponentManagerService(
                paths=paths,
                repository=_FakeRepository(catalog),
            )
            restarted_service.download_service = fake_download_service
            cached_artifact = restarted_service.latest_verified_model_artifact("transcription-model.small")
            self.assertIsNotNone(cached_artifact)
            assert cached_artifact is not None
            self.assertEqual(Path(cached_artifact.verified_artifact_path).name, Path(result.verified_artifact.verified_artifact_path).name)


if __name__ == "__main__":
    unittest.main()
