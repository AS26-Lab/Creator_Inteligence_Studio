from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from creator_intelligence_studio.application.services.transcription_service import TranscriptionService
from creator_intelligence_studio.domain.audio.entities import PreparedAudioAsset, PreparedAudioStatus
from creator_intelligence_studio.domain.transcription.entities import TranscriptionStatus
from creator_intelligence_studio.domain.transcription.value_objects import TranscriptionOptions
from creator_intelligence_studio.infrastructure.transcription.model_manager import TranscriptionModelManager
from tests.test_transcription_service import FakeBackendEngine, build_environment, write_wav


class TranscriptionNoHiddenDownloadTests(unittest.TestCase):
    def test_missing_model_does_not_trigger_hidden_download(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings, paths, catalog, video_repository, prepared_audio_repository, transcription_repository = build_environment(root)
            creator = catalog.create_creator(display_name="Uno")
            project = catalog.create_project(creator_reference=creator.id, name="Proyecto", project_type="long_form")
            sample = root / "sample.mp4"
            sample.write_bytes(b"video-bytes")
            video = catalog.register_video(project_id=project.id, file_path=str(sample), title="Video")

            audio_path = root / "cache" / "videos" / video.id / "audio" / "normalized_v1.wav"
            write_wav(audio_path)
            prepared_audio = PreparedAudioAsset(
                id="audio-1",
                video_asset_id=video.id,
                source_inspection_id=None,
                status=PreparedAudioStatus.COMPLETED,
                relative_cache_path=str(audio_path.relative_to(root / "cache")),
                metadata_relative_path=f"videos/{video.id}/audio/metadata.json",
                format_name="wav",
                codec_name="pcm_s16le",
                sample_rate_hz=16000,
                channels=1,
                channel_layout="mono",
                bit_depth=16,
                duration_seconds=2.0,
                file_size_bytes=audio_path.stat().st_size,
                source_file_size_bytes=sample.stat().st_size,
                source_file_modified_at=datetime.now(timezone.utc),
                selected_stream_index=1,
                selected_stream_codec_name="aac",
                selected_stream_channels=2,
                selected_stream_channel_layout="stereo",
                selected_stream_sample_rate_hz=48000,
                selected_stream_language="es",
                selected_stream_is_default=True,
                extraction_started_at=datetime.now(timezone.utc),
                extraction_completed_at=datetime.now(timezone.utc),
                ffmpeg_version="ffmpeg version",
                cache_version="v1",
                normalization_sample_rate_hz=16000,
                normalization_channels=1,
                warning_code=None,
                warning_message=None,
                error_code=None,
                error_message=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            prepared_audio_repository.upsert(prepared_audio)

            fake_engine = FakeBackendEngine(backend_available=True)
            model_manager = TranscriptionModelManager(paths.models_directory)
            service = TranscriptionService(
                settings=settings,
                paths=paths,
                video_repository=video_repository,
                prepared_audio_repository=prepared_audio_repository,
                transcription_repository=transcription_repository,
                model_manager=model_manager,
                engine=fake_engine,  # type: ignore[arg-type]
                logger=None,
            )

            with patch.object(TranscriptionModelManager, "download_model", side_effect=AssertionError("hidden download blocked")):
                report = service.transcribe_video(
                    video.id,
                    TranscriptionOptions(profile="balanced", model_name="small", device="cpu", language="es"),
                )

            self.assertEqual(report.status, TranscriptionStatus.MODEL_UNAVAILABLE)
            self.assertIn("El modelo no esta instalado", report.errors[0])


if __name__ == "__main__":
    unittest.main()
