from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import tempfile
import unittest
import warnings
import wave
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from creator_intelligence_studio.application.services.catalog_service import CatalogService
from creator_intelligence_studio.application.services.component_manager_service import ComponentManagerService
from creator_intelligence_studio.application.services.transcription_service import TranscriptionService
from creator_intelligence_studio.domain.audio.entities import PreparedAudioAsset, PreparedAudioStatus
from creator_intelligence_studio.domain.components.catalog import build_default_component_catalog, build_default_transcription_profiles
from creator_intelligence_studio.domain.components.entities import ComponentInstallKind, ComponentInstallation, ComponentInstallationStatus, RuntimeCheckStatus
from creator_intelligence_studio.domain.transcription.value_objects import TranscriptionOptions
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.persistence.database import build_database
from creator_intelligence_studio.infrastructure.persistence.migrations import run_migrations
from creator_intelligence_studio.infrastructure.persistence.sqlite_component_manager_repository import SQLiteComponentManagerRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_creator_repository import SQLiteCreatorRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_prepared_audio_repository import SQLitePreparedAudioRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_project_repository import SQLiteProjectRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_transcription_repository import SQLiteTranscriptionRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_video_repository import SQLiteVideoRepository
from creator_intelligence_studio.shared.paths import ProjectPaths


def _settings() -> AppSettings:
    return AppSettings(
        application_name="Creator Intelligence Studio",
        environment="development",
        log_level="INFO",
        data_directory="data",
        logs_directory="logs",
        models_directory="models",
        artifacts_directory="artifacts",
        preferred_compute_backend="cpu",
        allow_cpu_basic_mode=True,
        external_ai_enabled=False,
        database_filename="creator_intelligence_studio.db",
        database_timeout_seconds=5.0,
        audio_cache_version="v1",
    )


def _write_speech_wav(destination: Path, *, text: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    escaped_path = str(destination).replace("'", "''")
    escaped_text = text.replace("'", "''")
    command = rf"""
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {{
  $synth.SetOutputToWaveFile('{escaped_path}')
  $synth.Speak('{escaped_text}')
}} finally {{
  $synth.Dispose()
}}
"""
    subprocess.run(["powershell.exe", "-NoProfile", "-Command", command], check=True)


def _bundle_env(scratch_root: Path, local_app_data: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["LOCALAPPDATA"] = str(local_app_data)
    env["HF_HOME"] = str(scratch_root / "hf-home")
    env["TRANSFORMERS_CACHE"] = str(scratch_root / "hf-cache")
    env["PYTHONPATH"] = ""
    env["PYTHONHOME"] = ""
    env["VIRTUAL_ENV"] = ""
    env["CONDA_PREFIX"] = ""
    env["PATH"] = r"C:\Windows\System32;C:\Windows;C:\Windows\System32\Wbem"
    return env


@unittest.skipUnless(os.getenv("CIS_RUN_PRODUCT_TRANSCRIPTION_MODEL_DOWNLOAD") == "1", "Real product transcription model download opt-in disabled")
class TranscriptionModelProductSourceIntegrationTests(unittest.TestCase):
    def test_real_product_model_download_install_and_packaged_transcription(self) -> None:
        repo_root = Path(r"H:\ALEJANDRO_2\CreatorIntelligenceStudio")
        bundle_source = repo_root / "dist" / "CreatorIntelligenceStudio"
        self.assertTrue(bundle_source.exists(), f"Missing packaged bundle source: {bundle_source}")

        with tempfile.TemporaryDirectory(prefix="cis-v32o-") as temp_dir:
            scratch_root = Path(temp_dir)
            bundle_root = scratch_root / "CreatorIntelligenceStudio"
            shutil.copytree(bundle_source, bundle_root)
            local_app_data = scratch_root / "LocalAppData"
            local_app_data.mkdir(parents=True, exist_ok=True)

            settings = _settings()
            with patch("creator_intelligence_studio.shared.paths.is_packaged_application", return_value=True):
                os.environ["LOCALAPPDATA"] = str(local_app_data)
                paths = ProjectPaths.from_settings(bundle_root, settings)
            paths.ensure_runtime_directories()

            database = build_database(settings, paths)
            with database.connect() as connection:
                run_migrations(connection)

            component_repository = SQLiteComponentManagerRepository(database)
            creator_repository = SQLiteCreatorRepository(database)
            project_repository = SQLiteProjectRepository(database)
            video_repository = SQLiteVideoRepository(database)
            prepared_audio_repository = SQLitePreparedAudioRepository(database)
            transcription_repository = SQLiteTranscriptionRepository(database)
            for entry in build_default_component_catalog().entries:
                component_repository.upsert_catalog_entry(entry)
            for profile in build_default_transcription_profiles():
                component_repository.upsert_transcription_profile(profile)
            component_repository.upsert_installation(
                ComponentInstallation(
                    component_id="transcription-model.small",
                    installation_status=ComponentInstallationStatus.MISSING,
                    installed_version=None,
                    revision="1",
                    install_type=ComponentInstallKind.MANAGED,
                    location_path=str(paths.models_directory / "transcription" / "faster-whisper" / "transcription-model.small" / "1"),
                    location_reference="managed_root",
                    detected_at=datetime.now(tz=timezone.utc),
                    verified_at=None,
                    health_status=RuntimeCheckStatus.NOT_CHECKED,
                    source=None,
                    managed=True,
                    metadata={},
                    created_at=datetime.now(tz=timezone.utc),
                    updated_at=datetime.now(tz=timezone.utc),
                )
            )

            catalog_service = CatalogService(
                settings=settings,
                paths=paths,
                creator_repository=creator_repository,
                project_repository=project_repository,
                video_repository=video_repository,
                logger=logging.getLogger("cis.v32o.catalog"),
            )
            creator = catalog_service.create_creator(display_name="Validation Creator")
            project = catalog_service.create_project(creator_reference=creator.id, name="Validation Project", project_type="long_form")

            video_source = scratch_root / "sample.mp4"
            video_source.write_bytes(b"video-bytes-for-validation")
            video = catalog_service.register_video(project_id=project.id, file_path=str(video_source), title="Validation Video")

            audio_path = bundle_root / "cache" / "videos" / video.id / "audio" / "normalized_v1.wav"
            _write_speech_wav(audio_path, text="Hola mundo. Esta es una prueba de transcripcion local.")
            relative_audio = Path("videos") / video.id / "audio" / "normalized_v1.wav"
            prepared_audio = PreparedAudioAsset(
                id=f"audio-{video.id}",
                video_asset_id=video.id,
                source_inspection_id=None,
                status=PreparedAudioStatus.COMPLETED,
                relative_cache_path=str(relative_audio),
                metadata_relative_path=f"videos/{video.id}/audio/metadata.json",
                format_name="wav",
                codec_name="pcm_s16le",
                sample_rate_hz=16000,
                channels=1,
                channel_layout="mono",
                bit_depth=16,
                duration_seconds=4.0,
                file_size_bytes=audio_path.stat().st_size,
                source_file_size_bytes=video_source.stat().st_size,
                source_file_modified_at=datetime.now(tz=timezone.utc),
                selected_stream_index=1,
                selected_stream_codec_name="aac",
                selected_stream_channels=2,
                selected_stream_channel_layout="stereo",
                selected_stream_sample_rate_hz=48000,
                selected_stream_language="es",
                selected_stream_is_default=True,
                extraction_started_at=datetime.now(tz=timezone.utc),
                extraction_completed_at=datetime.now(tz=timezone.utc),
                ffmpeg_version="ffmpeg validation",
                cache_version="v1",
                normalization_sample_rate_hz=16000,
                normalization_channels=1,
                warning_code=None,
                warning_message=None,
                error_code=None,
                error_message=None,
                created_at=datetime.now(tz=timezone.utc),
                updated_at=datetime.now(tz=timezone.utc),
            )
            prepared_audio_repository.upsert(prepared_audio)

            component_manager = ComponentManagerService(paths=paths, repository=component_repository, logger=logging.getLogger("cis.v32o.components"))
            product_request = component_manager.product_download_request("transcription-model.small")
            self.assertIsNotNone(product_request)
            assert product_request is not None
            self.assertTrue(str(product_request.source_url).startswith("https://"))
            self.assertIn("huggingface.co", product_request.allowed_domains)
            self.assertIn("hf.co", product_request.allowed_domains)

            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always", ResourceWarning)

                download_result = component_manager.start_product_model_download("transcription-model.small")
                failure_context = {
                    "download_result": download_result.to_dict(),
                    "records": [record.to_dict() for record in component_manager.download_service.list_downloads()],
                }
                self.assertEqual(download_result.status, "completed", json.dumps(failure_context, ensure_ascii=False, indent=2))
                self.assertIsNotNone(download_result.verified_artifact)
                assert download_result.verified_artifact is not None

                install_result = component_manager.transcription_model_installer.install_local(
                    "transcription-model.small",
                    download_result.verified_artifact.verified_artifact_path,
                    artifact=download_result.verified_artifact,
                    revision=download_result.manifest_revision,
                )
                self.assertEqual(install_result.state, "ready", json.dumps(install_result.to_dict(), ensure_ascii=False, indent=2))
                self.assertIsNotNone(install_result.active_path)
                self.assertTrue(component_manager.model_manager.verify_model("small").installed)

                transcription_service = TranscriptionService(
                    settings=settings,
                    paths=paths,
                    video_repository=video_repository,
                    prepared_audio_repository=prepared_audio_repository,
                    transcription_repository=transcription_repository,
                    model_manager=component_manager.model_manager,
                    logger=logging.getLogger("cis.v32o.transcription"),
                )
                report = transcription_service.transcribe_video(
                    video.id,
                    TranscriptionOptions(profile="balanced", model_name="small", device="cpu", language="es"),
                )
                self.assertEqual(report.status.value, "completed", json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
                self.assertIsNotNone(report.transcription)
                self.assertTrue(report.transcription.full_text.strip())

                bundle_env = _bundle_env(scratch_root, local_app_data)
                bundle_exe = bundle_root / "CreatorIntelligenceStudio.exe"
                self.assertTrue(bundle_exe.exists(), f"Missing packaged executable: {bundle_exe}")

                diagnostic = subprocess.run(
                    [str(bundle_exe), "--diagnostic-json"],
                    env=bundle_env,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(diagnostic.returncode, 0, diagnostic.stderr)
                diag_payload = json.loads(diagnostic.stdout)
                self.assertTrue(diag_payload["packaged_application"])
                self.assertIsNotNone(diag_payload["runtime_manifest_path"])

                first = subprocess.run(
                    [
                        str(bundle_exe),
                        "transcription",
                        "transcribe",
                        "--video-id",
                        video.id,
                        "--profile",
                        "balanced",
                        "--model-name",
                        "small",
                        "--device",
                        "cpu",
                        "--language",
                        "es",
                        "--json",
                    ],
                    env=bundle_env,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(first.returncode, 0, first.stderr)
                first_payload = json.loads(first.stdout)
                self.assertEqual(first_payload["status"], "completed")
                self.assertTrue((first_payload.get("transcription") or {}).get("full_text", "").strip())

                second = subprocess.run(
                    [
                        str(bundle_exe),
                        "transcription",
                        "transcribe",
                        "--video-id",
                        video.id,
                        "--profile",
                        "balanced",
                        "--model-name",
                        "small",
                        "--device",
                        "cpu",
                        "--language",
                        "es",
                        "--json",
                    ],
                    env=bundle_env,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(second.returncode, 0, second.stderr)
                second_payload = json.loads(second.stdout)
                self.assertEqual(second_payload["status"], "completed")
                self.assertTrue((second_payload.get("transcription") or {}).get("full_text", "").strip())

            self.assertFalse(
                any(issubclass(item.category, ResourceWarning) for item in caught),
                "La validacion real del modelo no debe dejar ResourceWarning.",
            )


if __name__ == "__main__":
    unittest.main()
