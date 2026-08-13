from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from creator_intelligence_studio.application.services.catalog_service import CatalogService, build_catalog_service
from creator_intelligence_studio.application.services.creator_corpus_service import build_creator_corpus_service
from creator_intelligence_studio.domain.audio.entities import PreparedAudioAsset, PreparedAudioStatus
from creator_intelligence_studio.domain.creator_corpus.value_objects import (
    CorpusDocumentStatus,
    CorpusDocumentType,
    CorpusProvenanceRelationType,
    CorpusSourceAssetStatus,
    CorpusSourceType,
    CorpusVersionSourceKind,
)
from creator_intelligence_studio.domain.transcription.entities import Transcription, TranscriptionSegment, TranscriptionStatus
from creator_intelligence_studio.domain.videos.entities import VideoAsset, VideoProcessingStatus, VideoSourceType
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.persistence.database import build_database
from creator_intelligence_studio.infrastructure.persistence.migrations import run_migrations
from creator_intelligence_studio.infrastructure.persistence.sqlite_creator_corpus_repository import SQLiteCreatorCorpusRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_prepared_audio_repository import SQLitePreparedAudioRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_project_repository import SQLiteProjectRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_transcription_repository import SQLiteTranscriptionRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_video_repository import SQLiteVideoRepository
from creator_intelligence_studio.shared.dates import utc_now
from creator_intelligence_studio.shared.paths import ProjectPaths
from tests.test_component_manager_migration import _create_legacy_v32_schema


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


def _build_context(temp_dir: str):
    settings = _settings()
    root = Path(temp_dir)
    paths = ProjectPaths.from_settings(root, settings)
    paths.ensure_runtime_directories()
    database = build_database(settings, paths)
    with database.connect() as connection:
        run_migrations(connection)
    catalog = build_catalog_service(settings=settings, paths=paths, database=database)
    corpus_service = build_creator_corpus_service(
        settings=settings,
        paths=paths,
        repository=SQLiteCreatorCorpusRepository(database),
        project_repository=SQLiteProjectRepository(database),
        video_repository=SQLiteVideoRepository(database),
        transcription_repository=SQLiteTranscriptionRepository(database),
    )
    return settings, paths, database, catalog, corpus_service


def _write_file(path: Path, payload: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


def _build_video_asset(*, project_id: str, source_path: Path, title: str) -> VideoAsset:
    now = utc_now()
    return VideoAsset(
        id=str(uuid4()),
        project_id=project_id,
        title=title,
        source_path=str(source_path),
        original_filename=source_path.name,
        extension=source_path.suffix.lstrip("."),
        file_size_bytes=source_path.stat().st_size,
        file_modified_at=datetime.now(tz=timezone.utc),
        source_type=VideoSourceType.LOCAL_FILE,
        processing_status=VideoProcessingStatus.REGISTERED,
        registered_at=now,
        updated_at=now,
        notes=None,
        file_available=True,
    )


def _build_prepared_audio_asset(video_id: str, audio_path: Path) -> PreparedAudioAsset:
    now = datetime.now(tz=timezone.utc)
    return PreparedAudioAsset(
        id=str(uuid4()),
        video_asset_id=video_id,
        source_inspection_id=None,
        status=PreparedAudioStatus.COMPLETED,
        relative_cache_path=str(audio_path),
        metadata_relative_path=None,
        format_name="wav",
        codec_name="pcm_s16le",
        sample_rate_hz=16000,
        channels=1,
        channel_layout="mono",
        bit_depth=16,
        duration_seconds=2.0,
        file_size_bytes=audio_path.stat().st_size,
        source_file_size_bytes=audio_path.stat().st_size,
        source_file_modified_at=now,
        selected_stream_index=0,
        selected_stream_codec_name="pcm_s16le",
        selected_stream_channels=1,
        selected_stream_channel_layout="mono",
        selected_stream_sample_rate_hz=16000,
        selected_stream_language="es",
        selected_stream_is_default=True,
        extraction_started_at=now,
        extraction_completed_at=now,
        ffmpeg_version="ffmpeg-test",
        cache_version="v1",
        normalization_sample_rate_hz=16000,
        normalization_channels=1,
        warning_code=None,
        warning_message=None,
        error_code=None,
        error_message=None,
        created_at=now,
        updated_at=now,
    )


def _build_transcription(video_id: str, prepared_audio_id: str, *, text: str, language: str = "es") -> Transcription:
    now = datetime.now(tz=timezone.utc)
    return Transcription(
        id=str(uuid4()),
        video_asset_id=video_id,
        prepared_audio_asset_id=prepared_audio_id,
        status=TranscriptionStatus.COMPLETED,
        engine="faster-whisper",
        model_name="small",
        device="cpu",
        compute_type="int8",
        requested_language=language,
        detected_language=language,
        language_probability=0.99,
        full_text=text,
        duration_seconds=2.0,
        processing_time_seconds=0.25,
        real_time_factor=0.125,
        segment_count=2,
        word_timestamps_enabled=False,
        vad_enabled=False,
        source_audio_size_bytes=1024,
        source_audio_modified_at=now,
        source_audio_fingerprint="fingerprint",
        configuration_fingerprint="configuration",
        engine_version="1.2.1",
        model_version="small",
        warning_code=None,
        warning_message=None,
        error_code=None,
        error_message=None,
        started_at=now,
        completed_at=now,
        created_at=now,
        updated_at=now,
    )


def _build_transcription_segments(transcription_id: str) -> list[TranscriptionSegment]:
    now = datetime.now(tz=timezone.utc)
    return [
        TranscriptionSegment(
            id=str(uuid4()),
            transcription_id=transcription_id,
            segment_index=0,
            start_seconds=0.0,
            end_seconds=1.0,
            text="hola",
            confidence=0.99,
            no_speech_probability=0.01,
            temperature=0.0,
            created_at=now,
        ),
        TranscriptionSegment(
            id=str(uuid4()),
            transcription_id=transcription_id,
            segment_index=1,
            start_seconds=1.0,
            end_seconds=2.0,
            text="mundo",
            confidence=0.98,
            no_speech_probability=0.01,
            temperature=0.0,
            created_at=now,
        ),
    ]


class CreatorCorpusFoundationTests(unittest.TestCase):
    def test_creator_isolation_and_text_dedupe(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            _, _, _, catalog, corpus = _build_context(temp_dir)
            creator_a = catalog.create_creator(display_name="Creator A")
            creator_b = catalog.create_creator(display_name="Creator B")

            result_a = corpus.ingest_text_document(
                creator_id=creator_a.id,
                document_type=CorpusDocumentType.SCRIPT,
                title="Same Title",
                content="Mismo contenido",
                source_kind=CorpusVersionSourceKind.IMPORT,
                source_asset_type=CorpusSourceType.IMPORTED_TEXT,
                source_asset_original_name="same.txt",
            )
            result_a_repeat = corpus.ingest_text_document(
                creator_id=creator_a.id,
                document_type=CorpusDocumentType.SCRIPT,
                title="Same Title",
                content="Mismo contenido",
                source_kind=CorpusVersionSourceKind.IMPORT,
                source_asset_type=CorpusSourceType.IMPORTED_TEXT,
                source_asset_original_name="same.txt",
            )
            result_b = corpus.ingest_text_document(
                creator_id=creator_b.id,
                document_type=CorpusDocumentType.SCRIPT,
                title="Same Title",
                content="Mismo contenido",
                source_kind=CorpusVersionSourceKind.IMPORT,
                source_asset_type=CorpusSourceType.IMPORTED_TEXT,
                source_asset_original_name="same.txt",
            )

            self.assertEqual(result_a.document.id, result_a_repeat.document.id)
            self.assertEqual(result_a.version.id, result_a_repeat.version.id)
            self.assertNotEqual(result_a.document.id, result_b.document.id)
            self.assertEqual(len(corpus.list_documents(creator_a.id)), 1)
            self.assertEqual(len(corpus.list_documents(creator_b.id)), 1)
            self.assertEqual(corpus.get_status(creator_a.id).document_count, 1)
            self.assertEqual(corpus.get_status(creator_b.id).document_count, 1)

    def test_source_asset_hash_dedup_is_creator_scoped(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            _, _, _, catalog, corpus = _build_context(temp_dir)
            creator = catalog.create_creator(display_name="Creator A")
            same_bytes_a = _write_file(Path(temp_dir) / "same-a.txt", b"alpha")
            same_bytes_b = _write_file(Path(temp_dir) / "same-b.txt", b"alpha")
            different_bytes_same_name = _write_file(Path(temp_dir) / "same-c.txt", b"beta")

            asset_1 = corpus.register_source_asset(
                creator_id=creator.id,
                source_type=CorpusSourceType.IMPORTED_TEXT,
                original_name="same.txt",
                local_path=str(same_bytes_a),
            )
            asset_2 = corpus.register_source_asset(
                creator_id=creator.id,
                source_type=CorpusSourceType.IMPORTED_TEXT,
                original_name="same.txt",
                local_path=str(same_bytes_b),
            )
            asset_3 = corpus.register_source_asset(
                creator_id=creator.id,
                source_type=CorpusSourceType.IMPORTED_TEXT,
                original_name="same.txt",
                local_path=str(different_bytes_same_name),
            )

            self.assertEqual(asset_1.id, asset_2.id)
            self.assertNotEqual(asset_1.content_hash, asset_3.content_hash)
            self.assertEqual(len(corpus.list_source_assets(creator.id)), 2)
            self.assertEqual(corpus.get_source_asset(asset_1.id).status, CorpusSourceAssetStatus.ACTIVE)

    def test_versioning_and_provenance_preserve_history(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            _, _, _, catalog, corpus = _build_context(temp_dir)
            creator = catalog.create_creator(display_name="Creator A")
            result_v1 = corpus.ingest_text_document(
                creator_id=creator.id,
                document_type=CorpusDocumentType.TRANSCRIPT,
                title="Episode 1",
                content="hola mundo",
                language="es",
                source_kind=CorpusVersionSourceKind.TRANSCRIPTION,
                source_asset_type=CorpusSourceType.TRANSCRIPT,
                source_asset_original_name="episode-1.txt",
                metadata={"engine": "faster-whisper"},
                segments=[
                    {"sequence": 0, "start_seconds": 0.0, "end_seconds": 1.0, "text": "hola", "confidence": 0.9},
                    {"sequence": 1, "start_seconds": 1.0, "end_seconds": 2.0, "text": "mundo", "confidence": 0.8},
                ],
            )
            result_v2 = corpus.append_document_version(
                document_id=result_v1.document.id,
                creator_id=creator.id,
                content="hola mundo corregido",
                source_kind=CorpusVersionSourceKind.USER_EDIT,
                language="es",
                created_by=creator.id,
                metadata={"editor": "user"},
            )

            self.assertEqual(result_v1.version.version_number, 1)
            self.assertEqual(result_v2.version.version_number, 2)
            self.assertEqual(len(corpus.list_versions(result_v1.document.id)), 2)
            self.assertEqual(corpus.get_document(result_v1.document.id).current_version_id, result_v2.version.id)
            self.assertEqual(corpus.list_provenance_edges(result_v2.version.id)[0].relation_type, CorpusProvenanceRelationType.EDITED_FROM)

    def test_transcription_ingestion_preserves_segments_and_restart(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            _, paths, database, catalog, corpus = _build_context(temp_dir)
            creator = catalog.create_creator(display_name="Creator A")
            project = catalog.create_project(creator_reference=creator.id, name="Project A", project_type="long_form")
            source_video = _write_file(Path(temp_dir) / "video.mp4", b"video-bytes")
            video = catalog.register_video(project_id=project.id, file_path=str(source_video), title="Video A")
            audio_file = _write_file(paths.data_directory / "audio" / "video-a.wav", b"audio-bytes")
            prepared_audio_repository = SQLitePreparedAudioRepository(database)
            prepared_audio = _build_prepared_audio_asset(video.id, audio_file)
            prepared_audio_repository.upsert(prepared_audio)
            transcription_repository = SQLiteTranscriptionRepository(database)
            transcription = _build_transcription(video.id, prepared_audio.id, text="hola mundo", language="es")
            transcription_repository.upsert(transcription, _build_transcription_segments(transcription.id))

            result = corpus.ingest_transcription(video.id)
            self.assertEqual(result.document.document_type, CorpusDocumentType.TRANSCRIPT)
            self.assertEqual(result.document.language, "es")
            self.assertEqual(result.version.source_kind, CorpusVersionSourceKind.TRANSCRIPTION)
            self.assertEqual(len(result.segments), 2)
            self.assertEqual(result.segments[0].text, "hola")
            self.assertEqual(result.provenance_edges[0].relation_type, CorpusProvenanceRelationType.TRANSCRIBED_FROM)

            reopened = build_creator_corpus_service(
                settings=_settings(),
                paths=paths,
                repository=SQLiteCreatorCorpusRepository(database),
                project_repository=SQLiteProjectRepository(database),
                video_repository=SQLiteVideoRepository(database),
                transcription_repository=SQLiteTranscriptionRepository(database),
            )
            persisted = reopened.get_document(result.document.id)
            self.assertIsNotNone(persisted)
            self.assertEqual(persisted.current_version_id, result.version.id)
            self.assertEqual(reopened.get_status(creator.id).document_count, 1)

    def test_source_missing_and_archive_keep_derived_text(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            _, _, _, catalog, corpus = _build_context(temp_dir)
            creator = catalog.create_creator(display_name="Creator A")
            source_file = _write_file(Path(temp_dir) / "source.txt", b"source-bytes")
            source_asset = corpus.register_source_asset(
                creator_id=creator.id,
                source_type=CorpusSourceType.MANUAL_TEXT,
                original_name="source.txt",
                local_path=str(source_file),
            )
            result = corpus.ingest_text_document(
                creator_id=creator.id,
                document_type=CorpusDocumentType.NOTE,
                title="Note A",
                content="contenido",
                source_kind=CorpusVersionSourceKind.IMPORT,
                source_asset_id=source_asset.id,
            )

            corpus.mark_source_asset_missing(source_asset.id)
            archived = corpus.archive_document(result.document.id)
            self.assertEqual(corpus.get_source_asset(source_asset.id).status, CorpusSourceAssetStatus.MISSING)
            self.assertEqual(archived.status, CorpusDocumentStatus.ARCHIVED)
            self.assertEqual(corpus.get_document(result.document.id).status, CorpusDocumentStatus.ARCHIVED)
            self.assertEqual(corpus.list_versions(result.document.id)[0].content, "contenido")

    def test_migration_0_to_34_and_32_to_34(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            _, _, database, _, _ = _build_context(temp_dir)
            with database.connect() as connection:
                self.assertEqual(connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0], 37)

        with tempfile.TemporaryDirectory() as temp_dir:
            settings = _settings()
            paths = ProjectPaths.from_settings(Path(temp_dir), settings)
            paths.ensure_runtime_directories()
            database = build_database(settings, paths)
            with database.connect() as connection:
                _create_legacy_v32_schema(connection)
                run_migrations(connection)
                self.assertEqual(connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0], 37)


if __name__ == "__main__":
    unittest.main()
