from __future__ import annotations

import io
import json
import logging
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from PySide6.QtWidgets import QApplication

from creator_intelligence_studio.application.services.catalog_service import build_catalog_service
from creator_intelligence_studio.application.services.creator_language_service import build_creator_language_service
from creator_intelligence_studio.application.services.creator_memory_service import CreatorMemoryService
from creator_intelligence_studio.domain.creator_language.analysis_types import CreatorLanguageQueryFilters
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.creator_language import (
    analyze_filler_words,
    analyze_narrative_structure,
    analyze_sentence_style,
    segment_sentences,
    tokenize_language_text,
)
from creator_intelligence_studio.infrastructure.persistence.database import build_database
from creator_intelligence_studio.infrastructure.persistence.migrations import run_migrations
from creator_intelligence_studio.infrastructure.persistence.sqlite_creator_language_repository import (
    SQLiteCreatorLanguageRepository,
)
from creator_intelligence_studio.infrastructure.persistence.sqlite_creator_memory_repository import (
    SQLiteCreatorMemoryRepository,
)
from creator_intelligence_studio.presentation.cli.cli import build_parser, dispatch
from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel
from creator_intelligence_studio.presentation.desktop.views.creator_language_view import CreatorLanguageView
from creator_intelligence_studio.presentation.desktop.views.task_center_view import TaskCenterView
from creator_intelligence_studio.shared.paths import ProjectPaths


def make_settings() -> AppSettings:
    return AppSettings(
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
        database_filename="creator_intelligence_studio.db",
        database_timeout_seconds=5.0,
        audio_normalization_sample_rate_hz=16000,
        audio_extraction_timeout_seconds=60.0,
        audio_cache_version="v1",
        preferred_audio_language=None,
    )


def _make_workspace(*, catalog, language_service, memory_service, settings: AppSettings, paths: ProjectPaths) -> WorkspaceViewModel:
    diagnostic = SimpleNamespace(
        application_name="Creator Intelligence Studio",
        application_version="0.1.0",
        project_root=paths.project_root,
        os_name="Windows",
        os_version="11",
        os_architecture="x86_64",
        python_version="3.11.9",
        python_executable="python.exe",
        cpu_reported="CPU",
        logical_processors=8,
        nvidia_smi_available=False,
        preferred_compute_backend="cuda",
        state=SimpleNamespace(ready_for_basic_mode=True, cuda_driver_detected=False, cuda_runtime_not_verified=True, warnings=()),
        warnings=(),
        errors=(),
    )
    return WorkspaceViewModel(
        service=catalog,
        media_service=SimpleNamespace(verify_media_tools=lambda: SimpleNamespace(available=True, warnings=(), ffmpeg=SimpleNamespace(available=True), ffprobe=SimpleNamespace(available=True))),
        audio_service=SimpleNamespace(
            prepare_audio=lambda *args, **kwargs: SimpleNamespace(status=SimpleNamespace(value="not_prepared"), is_stale=False),
            get_prepared_audio=lambda *args, **kwargs: None,
            is_prepared_audio_stale=lambda *args, **kwargs: False,
            verify_prepared_audio=lambda *args, **kwargs: SimpleNamespace(status=SimpleNamespace(value="not_prepared"), is_stale=False),
            delete_prepared_audio_cache=lambda *args, **kwargs: SimpleNamespace(deleted_record=False, deleted_files=()),
        ),
        transcription_service=SimpleNamespace(),
        acoustic_service=SimpleNamespace(),
        visual_service=SimpleNamespace(),
        diagnostic=diagnostic,
        settings=settings,
        paths=paths,
        analytics_service=SimpleNamespace(),
        analytics_lab_service=SimpleNamespace(),
        experiment_service=SimpleNamespace(),
        creator_memory_service=memory_service,
        creator_language_service=language_service,
        render_service=SimpleNamespace(),
        subtitle_service=SimpleNamespace(),
        personalization_service=SimpleNamespace(),
        model_service=SimpleNamespace(),
        evaluation_service=SimpleNamespace(),
    )


def _build_fixture(root: Path):
    settings = make_settings()
    paths = ProjectPaths.from_settings(root, settings)
    paths.ensure_runtime_directories()
    database = build_database(settings, paths)
    with database.connect() as connection:
        run_migrations(connection)
    catalog = build_catalog_service(settings, paths, logger=logging.getLogger("creator-language-test"), database=database)
    creator_a = catalog.create_creator(display_name="Creator A")
    creator_b = catalog.create_creator(display_name="Creator B")
    memory_service = CreatorMemoryService(
        settings=settings,
        paths=paths,
        repository=SQLiteCreatorMemoryRepository(database),
        logger=logging.getLogger("creator-language-test"),
    )
    language_service = build_creator_language_service(
        settings=settings,
        paths=paths,
        repository=SQLiteCreatorLanguageRepository(database),
        database=database,
        creator_memory_service=memory_service,
        logger=logging.getLogger("creator-language-test"),
    )
    workspace = _make_workspace(
        catalog=catalog,
        language_service=language_service,
        memory_service=memory_service,
        settings=settings,
        paths=paths,
    )
    return SimpleNamespace(
        root=root,
        settings=settings,
        paths=paths,
        database=database,
        catalog=catalog,
        creator_a=creator_a,
        creator_b=creator_b,
        memory_service=memory_service,
        language_service=language_service,
        workspace=workspace,
    )


class CreatorLanguageAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._qt_app = QApplication.instance() or QApplication([])

    def test_tokenization_sentence_style_and_filler_analysis(self) -> None:
        text = "Ey, eh, visita https://example.com #Shorts @Heybermu. O sea, esto es brutal! ¿Tú ves? Básicamente, vamos directo."
        tokens = tokenize_language_text(text)
        sentences = segment_sentences(text)
        fillers = analyze_filler_words(text)
        style = analyze_sentence_style(text)
        narrative = analyze_narrative_structure(text, platform="youtube_short", content_type="short_video")

        self.assertEqual(tokens.language_guess, "es")
        self.assertGreater(len(tokens.tokens), 5)
        self.assertGreaterEqual(len(sentences), 3)
        self.assertGreater(fillers["total"], 0)
        self.assertGreater(style["question_ratio"], 0.0)
        self.assertGreater(style["exclamation_ratio"], 0.0)
        self.assertIn("opening", narrative)
        self.assertIn("closing", narrative)

    def test_migration_v20_analysis_profile_retrieval_and_export(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = _build_fixture(Path(temp_dir))
            workspace = fixture.workspace
            workspace.select_creator(fixture.creator_a.id)
            corpus_a = fixture.language_service.create_corpus(
                creator_id=fixture.creator_a.id,
                name="Corpus A",
                description="Corpus mixto de prueba.",
                language="es",
                platform=None,
                content_type=None,
                topic="humor",
            )
            corpus_b = fixture.language_service.create_corpus(
                creator_id=fixture.creator_b.id,
                name="Corpus B",
                description="Corpus formal de prueba.",
                language="es",
                platform="youtube_longform",
                content_type="longform_video",
                topic="analitico",
            )
            fixture.language_service.add_corpus_source(
                corpus_id=corpus_a.id,
                source_type="manual_text",
                source_id="a-1",
                text_snapshot="Ey, eh, vamos directo al caos. Mira esto. Literal, es una locura.",
                language="es",
                platform="youtube_short",
                content_type="short_video",
                topic="humor",
            )
            fixture.language_service.add_corpus_source(
                corpus_id=corpus_a.id,
                source_type="manual_text",
                source_id="a-2",
                text_snapshot="O sea, pues, primero pasa esto, luego esto otro. ¿Ves? Cerramos rapido.",
                language="es",
                platform="tiktok",
                content_type="short_video",
                topic="humor",
            )
            fixture.language_service.add_corpus_source(
                corpus_id=corpus_b.id,
                source_type="manual_text",
                source_id="b-1",
                text_snapshot="En este video vamos a explicar paso a paso el contexto, el ejemplo y el cierre.",
                language="es",
                platform="youtube_longform",
                content_type="longform_video",
                topic="analitico",
            )
            fixture.language_service.add_corpus_source(
                corpus_id=corpus_b.id,
                source_type="manual_text",
                source_id="b-2",
                text_snapshot="Primero definimos el problema, despues vemos la evidencia y al final resumimos.",
                language="es",
                platform="youtube_longform",
                content_type="longform_video",
                topic="analitico",
            )

            detail_a = fixture.language_service.analyze_corpus(corpus_a.id)
            profile_a = fixture.language_service.get_profile_detail(fixture.creator_a.id)
            analysis_run = fixture.language_service.get_analysis_run(detail_a.run.id)
            metrics = fixture.language_service.list_metrics(detail_a.run.id)
            patterns = fixture.language_service.list_patterns(fixture.creator_a.id, detail_a.run.id)
            candidates = fixture.language_service.list_candidates(fixture.creator_a.id)
            retrieved = fixture.language_service.retrieve_creator_context(
                fixture.creator_a.id,
                CreatorLanguageQueryFilters(
                    creator_id=fixture.creator_a.id,
                    query="directo",
                    platform="youtube_short",
                    status="observed",
                ),
            )
            retrieved_other_creator = fixture.language_service.retrieve_creator_context(
                fixture.creator_b.id,
                CreatorLanguageQueryFilters(
                    creator_id=fixture.creator_b.id,
                    query="caos",
                    platform="youtube_short",
                    status="observed",
                ),
            )
            export_json = fixture.language_service.export(creator_id=fixture.creator_a.id, format_name="json", destination=Path(temp_dir) / "exports")
            export_txt = fixture.language_service.export(creator_id=fixture.creator_a.id, format_name="txt", destination=Path(temp_dir) / "exports")
            export_csv = fixture.language_service.export(creator_id=fixture.creator_a.id, format_name="csv", destination=Path(temp_dir) / "exports")
            first_candidate = candidates[0]
            reviewed_candidate = fixture.language_service.review_candidate(
                first_candidate.id,
                decision="approve_with_changes",
                reason="Se ajusta al perfil observado.",
                modified_value_json=json.dumps({"scope": "creator_general"}, ensure_ascii=False),
            )
            snapshot_before = fixture.language_service.list_profile_snapshots(fixture.creator_a.id)
            duplicate_snapshot = fixture.language_service.create_profile_snapshot(fixture.creator_a.id)
            snapshot_after_duplicate = fixture.language_service.list_profile_snapshots(fixture.creator_a.id)

            fixture.language_service.add_corpus_source(
                corpus_id=corpus_a.id,
                source_type="manual_text",
                source_id="a-3",
                text_snapshot="Y bueno, este cierre deja la puerta abierta para la siguiente parte.",
                language="es",
                platform="youtube_short",
                content_type="short_video",
                topic="humor",
            )
            detail_b = fixture.language_service.analyze_corpus(corpus_a.id, force_recompute=True)
            profile_history = fixture.language_service.list_profile_history(fixture.creator_a.id)
            comparison = fixture.language_service.compare_profile_versions(fixture.creator_a.id, profile_history[-1].profile_version, profile_history[0].profile_version)

            with fixture.database.connect() as connection:
                versions = [row[0] for row in connection.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()]
                tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}

            self.assertEqual(versions[-1], 24)
            self.assertIn("creator_language_corpora", tables)
            self.assertIn("creator_language_profile_snapshots", tables)
            self.assertEqual(len(fixture.language_service.list_corpora(fixture.creator_a.id)), 1)
            self.assertEqual(len(fixture.language_service.list_corpora(fixture.creator_b.id)), 1)
            self.assertIsNotNone(analysis_run)
            self.assertGreater(len(metrics), 0)
            self.assertGreater(len(patterns), 0)
            self.assertGreater(len(candidates), 0)
            self.assertGreater(len(retrieved), 0)
            self.assertEqual(reviewed_candidate.status.value, "approved_with_changes")
            self.assertEqual(len(snapshot_before), len(snapshot_after_duplicate))
            self.assertEqual(duplicate_snapshot.id, snapshot_before[0].id)
            self.assertEqual(len(profile_history), 2)
            self.assertGreater(len(comparison.changed_sections), 0)
            self.assertIn("_language_", export_json.path)
            self.assertTrue(Path(export_json.path).exists())
            self.assertTrue(Path(export_txt.path).exists())
            self.assertTrue(Path(export_csv.path).exists())
            self.assertIsNotNone(profile_a.profile)
            self.assertGreater(detail_b.run.token_count, 0)
            self.assertTrue(all(result.payload.get("creator_id") in {None, fixture.creator_a.id} for result in retrieved))
            self.assertEqual(len(retrieved_other_creator), 0)

    def test_cli_gui_and_task_center_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = _build_fixture(Path(temp_dir))
            workspace = fixture.workspace
            workspace.select_creator(fixture.creator_a.id)
            corpus = fixture.language_service.create_corpus(
                creator_id=fixture.creator_a.id,
                name="Corpus CLI",
                language="es",
                platform=None,
            )
            fixture.language_service.add_corpus_source(
                corpus_id=corpus.id,
                source_type="manual_text",
                source_id="cli-1",
                text_snapshot="Hola, eh, vamos directo. Esto funciona.",
                language="es",
                platform="youtube_short",
                content_type="short_video",
                topic="prueba",
            )
            workspace.analyze_creator_language_corpus(corpus.id)
            workspace.create_creator_language_profile_snapshot(fixture.creator_a.id)
            workspace.export_creator_language(creator_id=fixture.creator_a.id, format_name="json", destination=Path(temp_dir) / "exports")

            parser = build_parser()
            args = parser.parse_args(["creator-language", "profile", "--creator-id", fixture.creator_a.id, "--json"])
            stdout = io.StringIO()
            stderr = io.StringIO()
            code = dispatch(
                args,
                service=fixture.catalog,
                media_service=SimpleNamespace(),
                audio_service=SimpleNamespace(),
                transcription_service=SimpleNamespace(),
                acoustic_service=SimpleNamespace(),
                visual_service=SimpleNamespace(),
                multimodal_service=SimpleNamespace(),
                clip_service=SimpleNamespace(),
                analytics_service=SimpleNamespace(),
                analytics_lab_service=SimpleNamespace(),
                experiment_service=SimpleNamespace(),
                creator_memory_service=fixture.memory_service,
                creator_language_service=fixture.language_service,
                diagnostic=SimpleNamespace(ready_for_basic_mode=True),
                stdout=stdout,
                stderr=stderr,
                render_service=SimpleNamespace(),
                subtitle_service=SimpleNamespace(),
                personalization_service=SimpleNamespace(),
                model_service=SimpleNamespace(),
                evaluation_service=SimpleNamespace(),
            )

            language_view = CreatorLanguageView(workspace)
            task_center = TaskCenterView(workspace)
            task_center.refresh()
            language_view.refresh()

            self.assertEqual(code, 0)
            self.assertIn(fixture.creator_a.id, stdout.getvalue())
            self.assertGreaterEqual(language_view.tabs.count(), 9)
            self.assertGreaterEqual(task_center.table.rowCount(), 1)
            self.assertTrue(any(task.payload.get("kind") == "creator_language_analysis" for task in workspace.background_tasks()))
            self.assertTrue(any(task.payload.get("kind") == "creator_language_profile_snapshot" for task in workspace.background_tasks()))
            self.assertTrue(any(task.payload.get("kind") == "creator_language_export" for task in workspace.background_tasks()))

    def test_csv_injection_guard(self) -> None:
        from creator_intelligence_studio.application.services.creator_language_service import _sanitize_csv

        self.assertEqual(_sanitize_csv("=CMD(1)"), "'=CMD(1)")
        self.assertEqual(_sanitize_csv("+SUM(1,2)"), "'+SUM(1,2)")
        self.assertEqual(_sanitize_csv("@IMPORT"), "'@IMPORT")
        self.assertEqual(_sanitize_csv("-42"), "-42")
