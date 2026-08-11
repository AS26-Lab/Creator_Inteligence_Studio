from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from creator_intelligence_studio.domain.creator_corpus import (
    CorpusAuthorshipClass,
    CorpusDocumentType,
    CorpusIngestionPolicy,
    CorpusIngestionRequest,
    CorpusSourceType,
    CorpusVersionSourceKind,
    TEXT_NORMALIZATION_VERSION,
)
from creator_intelligence_studio.domain.errors import ValidationError
from tests.test_creator_corpus_foundation import (
    _build_context,
    _build_prepared_audio_asset,
    _build_transcription,
    _build_transcription_segments,
    _build_video_asset,
    _write_file,
)
from creator_intelligence_studio.infrastructure.persistence.sqlite_prepared_audio_repository import SQLitePreparedAudioRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_project_repository import SQLiteProjectRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_transcription_repository import SQLiteTranscriptionRepository


class CreatorCorpusIngestionTests(unittest.TestCase):
    def test_normalization_preserves_raw_and_normalized_text(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            _, _, _, catalog, corpus = _build_context(temp_dir)
            creator = catalog.create_creator(display_name="Creator A")

            raw = "Hola   mundo\r\n\r\nLinea 2\u0000"
            result = corpus.ingest_text_document(
                creator_id=creator.id,
                document_type=CorpusDocumentType.SCRIPT,
                title="  Script base  ",
                content=raw,
                language="es",
                source_kind=CorpusVersionSourceKind.IMPORT,
                source_asset_type=CorpusSourceType.IMPORTED_TEXT,
                source_asset_original_name="script.txt",
                metadata={"origin": "manual"},
            )

            self.assertEqual(result.version.content, raw)
            self.assertEqual(result.version.raw_content, raw)
            self.assertEqual(result.version.normalized_content, "Hola mundo\n\nLinea 2")
            self.assertEqual(result.version.normalization_version, TEXT_NORMALIZATION_VERSION)
            self.assertEqual(result.version.authorship_class, CorpusAuthorshipClass.IMPORTED_UNKNOWN)
            self.assertTrue(result.eligibility.retrieval_eligible)
            self.assertFalse(result.eligibility.voice_learning_eligible)
            self.assertEqual(result.corpus_message, "Guardado en tu corpus")

    def test_duplicate_normalized_content_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            _, _, _, catalog, corpus = _build_context(temp_dir)
            creator = catalog.create_creator(display_name="Creator A")

            first = corpus.ingest_text_document(
                creator_id=creator.id,
                document_type=CorpusDocumentType.SCRIPT,
                title="Same title",
                content="Hola   mundo",
                language="es",
                source_kind=CorpusVersionSourceKind.IMPORT,
                source_asset_type=CorpusSourceType.IMPORTED_TEXT,
                source_asset_original_name="a.txt",
            )
            second = corpus.ingest_text_document(
                creator_id=creator.id,
                document_type=CorpusDocumentType.SCRIPT,
                title="Same title",
                content="Hola mundo",
                language="es",
                source_kind=CorpusVersionSourceKind.IMPORT,
                source_asset_type=CorpusSourceType.IMPORTED_TEXT,
                source_asset_original_name="a.txt",
            )

            self.assertEqual(first.version.id, second.version.id)
            self.assertFalse(first.deduplicated)
            self.assertTrue(second.deduplicated)
            self.assertEqual(len(corpus.list_versions(first.document.id)), 1)

    def test_transcription_ingestion_marks_low_confidence_segments(self) -> None:
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
            transcription_segments = _build_transcription_segments(transcription.id)
            transcription_repository.upsert(
                transcription,
                transcription_segments,
            )

            result = corpus.ingest_transcription(video.id)

            self.assertEqual(result.version.authorship_class, CorpusAuthorshipClass.TRANSCRIBED_CREATOR_SPEECH)
            self.assertEqual(result.version.normalization_version, TEXT_NORMALIZATION_VERSION)
            self.assertEqual(result.segments[0].text, "hola")
            self.assertTrue(result.segments[0].voice_learning_eligible)
            self.assertTrue(result.segments[0].retrieval_eligible)
            self.assertEqual(result.provenance_edges[0].relation_type.value, "transcribed_from")

    def test_repeated_transcription_changes_create_new_version_not_new_document(self) -> None:
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

            first_transcription = _build_transcription(video.id, prepared_audio.id, text="hola mundo", language="es")
            transcription_repository.upsert(first_transcription, _build_transcription_segments(first_transcription.id))
            first_result = corpus.ingest_transcription(video.id)

            second_transcription = replace(
                _build_transcription(video.id, prepared_audio.id, text="hola mundo corregido", language="es"),
                id=first_transcription.id,
            )
            transcription_repository.upsert(second_transcription, _build_transcription_segments(second_transcription.id))
            second_result = corpus.ingest_transcription(video.id)

            self.assertEqual(first_result.document.id, second_result.document.id)
            self.assertEqual(second_result.version.version_number, 2)
            self.assertEqual(len(corpus.list_versions(first_result.document.id)), 2)

    def test_user_edit_creates_new_version_and_ai_is_not_auto_current(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            _, _, _, catalog, corpus = _build_context(temp_dir)
            creator = catalog.create_creator(display_name="Creator A")

            initial = corpus.ingest_text_document(
                creator_id=creator.id,
                document_type=CorpusDocumentType.SCRIPT,
                title="Working Script",
                content="Version original",
                language="es",
                source_kind=CorpusVersionSourceKind.ORIGINAL,
                source_asset_type=CorpusSourceType.IMPORTED_TEXT,
                source_asset_original_name="script.txt",
            )
            edited = corpus.append_document_version(
                document_id=initial.document.id,
                creator_id=creator.id,
                content="Version original corregida",
                source_kind=CorpusVersionSourceKind.USER_EDIT,
                language="es",
                created_by=creator.id,
                metadata={"reason": "typo"},
            )
            ai_variant = corpus.append_document_version(
                document_id=initial.document.id,
                creator_id=creator.id,
                content="Version original candidata AI",
                source_kind=CorpusVersionSourceKind.AI_GENERATED,
                language="es",
                created_by=creator.id,
                metadata={"model": "test"},
            )

            self.assertEqual(edited.version.version_number, 2)
            self.assertEqual(corpus.get_document(initial.document.id).current_version_id, edited.version.id)
            self.assertNotEqual(corpus.get_document(initial.document.id).current_version_id, ai_variant.version.id)

    def test_creator_isolation_blocks_cross_creator_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            _, _, _, catalog, corpus = _build_context(temp_dir)
            creator_a = catalog.create_creator(display_name="Creator A")
            creator_b = catalog.create_creator(display_name="Creator B")

            source_file = _write_file(Path(temp_dir) / "source.txt", b"alpha")
            source_asset_b = corpus.register_source_asset(
                creator_id=creator_b.id,
                source_type=CorpusSourceType.IMPORTED_TEXT,
                original_name="source.txt",
                local_path=str(source_file),
            )
            doc_b = corpus.ingest_text_document(
                creator_id=creator_b.id,
                document_type=CorpusDocumentType.NOTE,
                title="Note B",
                content="contenido B",
                language="es",
                source_kind=CorpusVersionSourceKind.IMPORT,
                source_asset_id=source_asset_b.id,
            )

            with self.assertRaises(ValidationError):
                corpus.ingest_request(
                    CorpusIngestionRequest(
                        creator_id=creator_a.id,
                        source_type=CorpusSourceType.IMPORTED_TEXT.value,
                        source_reference="shared.txt",
                        document_type=CorpusDocumentType.NOTE.value,
                        title="Note A",
                        language="es",
                        content="contenido A",
                        source_asset_id=source_asset_b.id,
                        source_kind=CorpusVersionSourceKind.IMPORT.value,
                        ingestion_policy=CorpusIngestionPolicy.SKIP_IF_DUPLICATE,
                    )
                )

            with self.assertRaises(ValidationError):
                corpus.append_document_version(
                    document_id=doc_b.document.id,
                    creator_id=creator_a.id,
                    content="intrusion",
                    source_kind=CorpusVersionSourceKind.USER_EDIT,
                    language="es",
                    created_by=creator_a.id,
                )


if __name__ == "__main__":
    unittest.main()
