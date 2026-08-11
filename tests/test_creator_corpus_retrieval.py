from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from creator_intelligence_studio.application.services.creator_corpus_retrieval_service import CreatorCorpusRetrievalService
from creator_intelligence_studio.domain.creator_corpus import (
    CorpusAuthorshipClass,
    CorpusDocumentStatus,
    CorpusDocumentType,
    CorpusRetrievalQuery,
    CorpusRetrievalSort,
    CorpusSourceType,
    CorpusVersionSourceKind,
)
from creator_intelligence_studio.infrastructure.persistence.sqlite_creator_corpus_repository import SQLiteCreatorCorpusRepository
from tests.test_creator_corpus_foundation import (
    _build_context,
    _build_prepared_audio_asset,
    _build_transcription,
    _build_transcription_segments,
    _build_video_asset,
    _write_file,
)
from creator_intelligence_studio.infrastructure.persistence.sqlite_prepared_audio_repository import SQLitePreparedAudioRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_transcription_repository import SQLiteTranscriptionRepository


def _retrieval_context(temp_dir: str):
    settings, paths, database, catalog, corpus = _build_context(temp_dir)
    retrieval = CreatorCorpusRetrievalService(repository=SQLiteCreatorCorpusRepository(database))
    return settings, paths, database, catalog, corpus, retrieval


class CreatorCorpusRetrievalTests(unittest.TestCase):
    def test_current_versions_default_excludes_historical_and_archived_documents(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            _, _, _, catalog, corpus, retrieval = _retrieval_context(temp_dir)
            creator = catalog.create_creator(display_name="Creator A")

            active = corpus.ingest_text_document(
                creator_id=creator.id,
                document_type=CorpusDocumentType.SCRIPT,
                title="Guion principal",
                content="Contenido inicial del guion",
                language="es",
                source_kind=CorpusVersionSourceKind.ORIGINAL,
                source_asset_type=None,
            )
            corpus.append_document_version(
                document_id=active.document.id,
                creator_id=creator.id,
                content="Contenido actualizado del guion",
                source_kind=CorpusVersionSourceKind.USER_EDIT,
                language="es",
                created_by=creator.id,
            )
            archived = corpus.ingest_text_document(
                creator_id=creator.id,
                document_type=CorpusDocumentType.NOTE,
                title="Nota archivada",
                content="Texto que no debe aparecer",
                language="es",
                source_kind=CorpusVersionSourceKind.IMPORT,
                source_asset_type=None,
            )
            corpus.archive_document(archived.document.id)

            result = retrieval.search(CorpusRetrievalQuery(creator_id=creator.id, limit=20))

            self.assertEqual(result.total_count, 1)
            self.assertEqual(result.returned_count, 1)
            self.assertEqual(result.results[0].document_id, active.document.id)
            self.assertTrue(result.results[0].is_current_version)
            self.assertEqual(result.results[0].status, CorpusDocumentStatus.ACTIVE)
            self.assertEqual(result.results[0].version_number, 2)

    def test_text_search_returns_phrase_match_with_bounded_snippet(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            _, _, _, catalog, corpus, retrieval = _retrieval_context(temp_dir)
            creator = catalog.create_creator(display_name="Creator A")

            corpus.ingest_text_document(
                creator_id=creator.id,
                document_type=CorpusDocumentType.SCRIPT,
                title="Lanzamiento del canal",
                content="La frase exacta aparece aqui y luego sigue con mas texto para probar el recorte.",
                language="es",
                source_kind=CorpusVersionSourceKind.ORIGINAL,
                source_asset_type=None,
            )

            result = retrieval.search(
                CorpusRetrievalQuery(
                    creator_id=creator.id,
                    query_text="frase exacta",
                    limit=10,
                )
            )

            self.assertEqual(result.total_count, 1)
            item = result.results[0]
            self.assertIn("Coincidencia exacta de frase", item.relevance_reason)
            self.assertGreaterEqual(len(item.snippet), len("frase exacta"))
            self.assertLessEqual(len(item.snippet), 182)
            self.assertIn("frase exacta", item.snippet.lower())

    def test_segment_search_returns_timestamps_and_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            _, paths, database, catalog, corpus, retrieval = _retrieval_context(temp_dir)
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

            corpus.ingest_transcription(video.id)
            result = retrieval.search(
                CorpusRetrievalQuery(
                    creator_id=creator.id,
                    query_text="hola",
                    limit=10,
                )
            )

            self.assertGreaterEqual(result.total_count, 1)
            item = next(result_item for result_item in result.results if result_item.row_kind == "segment")
            self.assertEqual(item.segment_start_seconds, 0.0)
            self.assertEqual(item.segment_end_seconds, 1.0)
            self.assertIn("transcribed_from", item.provenance_summary)
            self.assertIn("Coincidencia en segmento", item.match_reasons)
            self.assertTrue(item.retrieval_eligible)

    def test_historical_versions_require_explicit_opt_in(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            _, _, _, catalog, corpus, retrieval = _retrieval_context(temp_dir)
            creator = catalog.create_creator(display_name="Creator A")

            first = corpus.ingest_text_document(
                creator_id=creator.id,
                document_type=CorpusDocumentType.NOTE,
                title="Notas",
                content="Version uno",
                language="es",
                source_kind=CorpusVersionSourceKind.IMPORT,
                source_asset_type=None,
            )
            corpus.append_document_version(
                document_id=first.document.id,
                creator_id=creator.id,
                content="Version dos",
                source_kind=CorpusVersionSourceKind.USER_EDIT,
                language="es",
                created_by=creator.id,
            )

            current_only = retrieval.search(CorpusRetrievalQuery(creator_id=creator.id, limit=20))
            historical = retrieval.search(
                CorpusRetrievalQuery(
                    creator_id=creator.id,
                    current_versions_only=False,
                    limit=20,
                    sort=CorpusRetrievalSort.UPDATED_DESC,
                )
            )

            self.assertEqual(current_only.total_count, 1)
            self.assertEqual({item.version_number for item in historical.results}, {1, 2})
            self.assertTrue(all(item.is_current_version for item in current_only.results))

    def test_creator_isolation_blocks_cross_creator_lookups(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            _, _, _, catalog, corpus, retrieval = _retrieval_context(temp_dir)
            creator_a = catalog.create_creator(display_name="Creator A")
            creator_b = catalog.create_creator(display_name="Creator B")
            source_file_a = _write_file(Path(temp_dir) / "source-a.txt", b"Mismo contenido")
            source_file_b = _write_file(Path(temp_dir) / "source-b.txt", b"Mismo contenido")

            result_a = corpus.ingest_text_document(
                creator_id=creator_a.id,
                document_type=CorpusDocumentType.SCRIPT,
                title="Mismo titulo",
                content="Mismo contenido",
                language="es",
                source_kind=CorpusVersionSourceKind.IMPORT,
                source_asset_type=CorpusSourceType.IMPORTED_TEXT,
                source_asset_original_name="source-a.txt",
                source_asset_id=corpus.register_source_asset(
                    creator_id=creator_a.id,
                    source_type=CorpusSourceType.IMPORTED_TEXT,
                    original_name="source-a.txt",
                    local_path=str(source_file_a),
                ).id,
            )
            result_b = corpus.ingest_text_document(
                creator_id=creator_b.id,
                document_type=CorpusDocumentType.SCRIPT,
                title="Mismo titulo",
                content="Mismo contenido",
                language="es",
                source_kind=CorpusVersionSourceKind.IMPORT,
                source_asset_type=CorpusSourceType.IMPORTED_TEXT,
                source_asset_original_name="source-b.txt",
                source_asset_id=corpus.register_source_asset(
                    creator_id=creator_b.id,
                    source_type=CorpusSourceType.IMPORTED_TEXT,
                    original_name="source-b.txt",
                    local_path=str(source_file_b),
                ).id,
            )

            query_a = retrieval.search(
                CorpusRetrievalQuery(
                    creator_id=creator_a.id,
                    query_text="mismo contenido",
                    limit=10,
                )
            )
            lookup_cross_document = retrieval.search(
                CorpusRetrievalQuery(
                    creator_id=creator_a.id,
                    document_id=result_b.document.id,
                    limit=10,
                )
            )
            lookup_cross_source = retrieval.search(
                CorpusRetrievalQuery(
                    creator_id=creator_a.id,
                    source_asset_id=result_b.document.source_asset_id,
                    limit=10,
                )
            )

            self.assertEqual(query_a.total_count, 1)
            self.assertEqual(query_a.results[0].document_id, result_a.document.id)
            self.assertEqual(lookup_cross_document.total_count, 0)
            self.assertEqual(lookup_cross_source.total_count, 0)

    def test_filters_sorting_and_ai_authorship_flags_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            _, _, _, catalog, corpus, retrieval = _retrieval_context(temp_dir)
            creator = catalog.create_creator(display_name="Creator A")
            project = catalog.create_project(creator_reference=creator.id, name="Project A", project_type="long_form")

            corpus.ingest_text_document(
                creator_id=creator.id,
                project_id=project.id,
                document_type=CorpusDocumentType.SCRIPT,
                title="B titulo",
                content="Texto A",
                language="es",
                source_kind=CorpusVersionSourceKind.ORIGINAL,
                source_asset_type=None,
            )
            corpus.ingest_text_document(
                creator_id=creator.id,
                project_id=project.id,
                document_type=CorpusDocumentType.SCRIPT,
                title="A titulo",
                content="Texto B",
                language="es",
                source_kind=CorpusVersionSourceKind.ORIGINAL,
                source_asset_type=None,
            )
            ai_doc = corpus.ingest_text_document(
                creator_id=creator.id,
                project_id=project.id,
                document_type=CorpusDocumentType.SCRIPT,
                title="C titulo",
                content="Texto AI",
                language="es",
                source_kind=CorpusVersionSourceKind.AI_GENERATED,
                source_asset_type=None,
            )

            filtered = retrieval.search(
                CorpusRetrievalQuery(
                    creator_id=creator.id,
                    query_text=None,
                    project_id=project.id,
                    document_types=(CorpusDocumentType.SCRIPT,),
                    authorship_classes=(CorpusAuthorshipClass.AI_GENERATED,),
                    languages=("es",),
                    current_versions_only=False,
                    sort=CorpusRetrievalSort.TITLE,
                    limit=10,
                )
            )
            sorted_result = retrieval.search(
                CorpusRetrievalQuery(
                    creator_id=creator.id,
                    query_text=None,
                    project_id=project.id,
                    current_versions_only=True,
                    sort=CorpusRetrievalSort.TITLE,
                    limit=10,
                )
            )

            self.assertEqual(filtered.total_count, 1)
            self.assertEqual(filtered.results[0].document_id, ai_doc.document.id)
            self.assertEqual(filtered.results[0].authorship_class, CorpusAuthorshipClass.AI_GENERATED)
            self.assertTrue(filtered.results[0].retrieval_eligible)
            self.assertFalse(filtered.results[0].voice_learning_eligible)
            self.assertFalse(filtered.results[0].is_current_version)
            self.assertEqual(sorted_result.results[0].title, "A titulo")
            self.assertEqual(sorted_result.results[1].title, "B titulo")

    def test_pagination_limits_results_deterministically(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            _, _, _, catalog, corpus, retrieval = _retrieval_context(temp_dir)
            creator = catalog.create_creator(display_name="Creator A")

            for index in range(3):
                corpus.ingest_text_document(
                    creator_id=creator.id,
                    document_type=CorpusDocumentType.NOTE,
                    title=f"Nota {index}",
                    content=f"Contenido {index}",
                    language="es",
                    source_kind=CorpusVersionSourceKind.IMPORT,
                    source_asset_type=None,
                )

            first_page = retrieval.search(
                CorpusRetrievalQuery(
                    creator_id=creator.id,
                    limit=2,
                    offset=0,
                    sort=CorpusRetrievalSort.TITLE,
                )
            )
            second_page = retrieval.search(
                CorpusRetrievalQuery(
                    creator_id=creator.id,
                    limit=2,
                    offset=2,
                    sort=CorpusRetrievalSort.TITLE,
                )
            )

            self.assertEqual(first_page.returned_count, 2)
            self.assertEqual(second_page.returned_count, 1)
            self.assertEqual(first_page.total_count, 3)
            self.assertEqual(second_page.total_count, 3)
            self.assertNotEqual(first_page.results[0].document_id, second_page.results[0].document_id)

    def test_index_health_and_rebuild_restore_missing_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            _, _, database, catalog, corpus, retrieval = _retrieval_context(temp_dir)
            creator = catalog.create_creator(display_name="Creator A")
            corpus.ingest_text_document(
                creator_id=creator.id,
                document_type=CorpusDocumentType.SCRIPT,
                title="Scripto",
                content="Texto para indexacion",
                language="es",
                source_kind=CorpusVersionSourceKind.IMPORT,
                source_asset_type=None,
            )

            health_before = retrieval.index_status(creator.id)
            self.assertTrue(health_before.supports_fts5)
            self.assertEqual(health_before.missing_row_count, 0)
            self.assertGreater(health_before.indexed_row_count, 0)

            with database.connect() as connection:
                connection.execute("DELETE FROM creator_corpus_retrieval_index WHERE creator_id = ?", (creator.id,))

            health_after_delete = retrieval.index_status(creator.id)
            self.assertGreater(health_after_delete.missing_row_count, 0)

            rebuilt = retrieval.rebuild_index(creator.id)
            self.assertEqual(rebuilt.missing_row_count, 0)
            self.assertEqual(rebuilt.stale_row_count, 0)
            self.assertEqual(rebuilt.indexed_row_count, rebuilt.expected_row_count)


if __name__ == "__main__":
    unittest.main()
