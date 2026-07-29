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
from creator_intelligence_studio.application.services.creator_memory_service import CreatorMemoryService
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.persistence.database import build_database
from creator_intelligence_studio.infrastructure.persistence.migrations import run_migrations
from creator_intelligence_studio.infrastructure.persistence.sqlite_creator_memory_repository import (
    SQLiteCreatorMemoryRepository,
)
from creator_intelligence_studio.presentation.cli.cli import build_parser, dispatch
from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel
from creator_intelligence_studio.presentation.desktop.views.creator_memory_view import CreatorMemoryView
from creator_intelligence_studio.presentation.desktop.views.creator_profile_view import CreatorProfileView
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
    )


def make_workspace(*, catalog, creator_memory_service: CreatorMemoryService, settings: AppSettings, paths: ProjectPaths) -> WorkspaceViewModel:
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
    workspace = WorkspaceViewModel(
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
        creator_memory_service=creator_memory_service,
    )
    return workspace


class CreatorMemoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._qt_app = QApplication.instance() or QApplication([])

    def _build_fixture(self, root: Path):
        settings = make_settings()
        paths = ProjectPaths.from_settings(root, settings)
        paths.ensure_runtime_directories()
        database = build_database(settings, paths)
        with database.connect() as connection:
            run_migrations(connection)
        catalog = build_catalog_service(settings, paths, logger=logging.getLogger("creator-memory-test"), database=database)
        creator = catalog.create_creator(display_name="Creator A")
        memory_service = CreatorMemoryService(
            settings=settings,
            paths=paths,
            repository=SQLiteCreatorMemoryRepository(database),
            logger=logging.getLogger("creator-memory-test"),
        )
        return SimpleNamespace(
            settings=settings,
            paths=paths,
            database=database,
            catalog=catalog,
            creator=creator,
            memory_service=memory_service,
        )

    def test_migration_v18_profile_roundtrip_and_export(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = self._build_fixture(Path(temp_dir))
            profile = fixture.memory_service.update_creator_profile(
                creator_id=fixture.creator.id,
                display_name="Creator A",
                summary="Humor absurdo y aperturas directas.",
                primary_language="es",
                secondary_languages=json.dumps(["en"], ensure_ascii=False),
                default_tone="absurd",
                default_formality="informal",
                objectives=json.dumps([{"type": "shortform_discovery", "platform": "youtube_short", "priority": 1, "status": "active"}], ensure_ascii=False),
            )
            trait = fixture.memory_service.create_trait(
                creator_id=fixture.creator.id,
                trait_type="humor",
                trait_key="absurd_humor",
                display_name="Humor absurdo",
                scope="creator_general",
                confidence_level="medium",
                status="provisional",
            )
            fixture.memory_service.add_trait_evidence(
                trait_id=trait.id,
                source_type="manual_observation",
                source_id="source-1",
                quoted_text="Eso fue absurdamente gracioso.",
            )
            fixture.memory_service.create_vocabulary_entry(
                creator_id=fixture.creator.id,
                term="buenisimo",
                vocabulary_type="catchphrase",
                frequency_count=3,
                confidence_level="medium",
            )
            fixture.memory_service.create_vocabulary_entry(
                creator_id=fixture.creator.id,
                term="=CMD(1)",
                vocabulary_type="avoided_term",
                frequency_count=1,
            )
            example = fixture.memory_service.create_example(
                creator_id=fixture.creator.id,
                example_type="good_humor",
                category="humor",
                title="Example 1",
                source_type="manual_observation",
                approval_status="approved",
            )
            fixture.memory_service.review_example(example.id, approval_status="needs_review", reason="Revisar contexto.")
            rule = fixture.memory_service.create_style_rule(
                creator_id=fixture.creator.id,
                rule_type="observed",
                statement="En Shorts entra al conflicto rapido.",
                scope="platform_specific",
                platform="youtube_short",
                confidence_level="low",
            )
            fixture.memory_service.review_style_rule(rule.id, decision="confirm", reason="Se repite en ejemplos.")
            fixture.memory_service.create_limit(
                creator_id=fixture.creator.id,
                limit_type="personal_boundary",
                category="privacy",
                statement="No hablar de datos privados.",
                severity="strong",
            )
            snapshot_1 = fixture.memory_service.create_profile_snapshot(fixture.creator.id)
            fixture.memory_service.update_creator_profile(
                creator_id=fixture.creator.id,
                display_name="Creator A",
                summary="Humor absurdo, más directo.",
                primary_language="es",
                secondary_languages=json.dumps(["en"], ensure_ascii=False),
                default_tone="absurd",
                default_formality="informal",
                objectives=json.dumps([{"type": "shortform_discovery", "platform": "youtube_short", "priority": 1, "status": "active"}], ensure_ascii=False),
            )
            snapshot_2 = fixture.memory_service.create_profile_snapshot(fixture.creator.id)
            comparison = fixture.memory_service.compare_profile_snapshots(fixture.creator.id, snapshot_1.id, snapshot_2.id)
            retrieval = fixture.memory_service.retrieve_creator_context(
                fixture.creator.id,
                {
                    "query": "absurd",
                    "platform": "youtube_short",
                    "content_type": None,
                },
            )
            trait_export = fixture.memory_service.export_csv(fixture.creator.id, "traits")
            vocab_export = fixture.memory_service.export_csv(fixture.creator.id, "vocabulary")
            detail = fixture.memory_service.get_profile_detail(fixture.creator.id)

            with fixture.database.connect() as connection:
                versions = [row[0] for row in connection.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()]
                tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}

            self.assertEqual(versions[-1], 30)
            self.assertIn("creator_profiles", tables)
            self.assertIn("creator_traits", tables)
            self.assertIn("creator_profile_snapshots", tables)
            self.assertEqual(profile.creator_id, fixture.creator.id)
            self.assertGreaterEqual(len(detail.traits), 1)
            self.assertGreaterEqual(len(detail.examples), 1)
            self.assertGreaterEqual(len(detail.vocabulary), 2)
            self.assertGreaterEqual(len(detail.rules), 1)
            self.assertGreaterEqual(len(detail.limits), 1)
            self.assertGreaterEqual(len(retrieval), 1)
            self.assertIn("changed_fields", comparison.to_dict())
            self.assertIn("'=CMD(1)", vocab_export)
            self.assertIn("Humor", trait_export)

    def test_creator_memory_cli_and_gui_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = self._build_fixture(Path(temp_dir))
            fixture.memory_service.update_creator_profile(
                creator_id=fixture.creator.id,
                display_name="Creator A",
                summary="Perfil de prueba.",
                primary_language="es",
                secondary_languages="[]",
                default_tone="directo",
                default_formality="informal",
                objectives="[]",
            )
            fixture.memory_service.create_trait(
                creator_id=fixture.creator.id,
                trait_type="tone",
                trait_key="direct_tone",
                display_name="Tono directo",
                scope="creator_general",
                confidence_level="low",
                status="observed",
            )
            workspace = make_workspace(catalog=fixture.catalog, creator_memory_service=fixture.memory_service, settings=fixture.settings, paths=fixture.paths)
            workspace.select_creator(fixture.creator.id)
            profile_view = CreatorProfileView(workspace)
            memory_view = CreatorMemoryView(workspace)
            profile_view.refresh()
            memory_view.refresh()

            parser = build_parser()
            args = parser.parse_args(["creator-memory", "profile", "--creator-id", fixture.creator.id, "--json"])
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
                diagnostic=SimpleNamespace(ready_for_basic_mode=True),
                stdout=stdout,
                stderr=stderr,
                render_service=SimpleNamespace(),
                subtitle_service=SimpleNamespace(),
                personalization_service=SimpleNamespace(),
                model_service=SimpleNamespace(),
                evaluation_service=SimpleNamespace(),
            )

            self.assertEqual(code, 0)
            self.assertIn("Creator A", stdout.getvalue())
            self.assertGreaterEqual(memory_view.traits_table.rowCount(), 1)
            self.assertGreaterEqual(memory_view.tabs.count(), 9)
            self.assertEqual(profile_view.display_name.text(), "Creator A")
