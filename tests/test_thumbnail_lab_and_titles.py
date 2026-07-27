from __future__ import annotations

import io
import json
import logging
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from PySide6.QtWidgets import QApplication

from creator_intelligence_studio.application.bootstrap import ServiceContext
from creator_intelligence_studio.application.services.creative_packaging_service import build_creative_packaging_service
from creator_intelligence_studio.infrastructure.persistence.sqlite_creative_packaging_repository import SQLiteCreativePackagingRepository
from creator_intelligence_studio.presentation.cli.cli import build_parser, dispatch
from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel
from creator_intelligence_studio.presentation.desktop.views.task_center_view import TaskCenterView
from creator_intelligence_studio.presentation.desktop.views.thumbnail_lab_view import ThumbnailLabView
from creator_intelligence_studio.shared.paths import ProjectPaths

from tests.test_analytics_lab import make_fixture, make_workspace


def _build_packaging_service(fixture):
    return build_creative_packaging_service(
        settings=fixture.settings,
        paths=fixture.paths,
        repository=SQLiteCreativePackagingRepository(fixture.database),
        database=fixture.database,
        catalog_service=fixture.catalog,
        logger=logging.getLogger("packaging-test"),
    )


class ThumbnailLabAndTitlesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._qt_app = QApplication.instance() or QApplication([])

    def test_migration_v20_packaging_flow_and_csv_injection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = make_fixture(Path(temp_dir))
            service = _build_packaging_service(fixture)

            reference = service.add_reference_asset(
                creator_id=fixture.creator.id,
                reference_type="prior_approved_thumbnail",
                source_type="manual",
                reference_purpose="brand_reference",
                usage_permission="reviewed",
                text_content="Composicion limpia y educativa.",
                platform="youtube_longform",
                content_type="longform_video",
                approval_status="approved",
            )
            brand_profile = service.build_brand_profile(fixture.creator.id)
            title = service.create_title_version(
                creator_id=fixture.creator.id,
                title_text="=CMD(1)",
                platform="youtube_longform",
                content_type="longform_video",
                source_type="manual",
            )
            thumbnail = service.create_thumbnail_version(
                creator_id=fixture.creator.id,
                image_path=None,
                platform="youtube_longform",
                content_type="longform_video",
                source_type="manual",
                concept_id=None,
            )
            title_analysis = service.analyze_title(title.id, force_recompute=True)
            thumbnail_analysis = service.analyze_thumbnail(thumbnail.id, force_recompute=True)
            pair = service.evaluate_pair(title_version_id=title.id, thumbnail_version_id=thumbnail.id)
            concept = service.build_concepts(
                creator_id=fixture.creator.id,
                platform="youtube_longform",
                content_type="longform_video",
                title="Piano limpio",
                objective="Autoridad",
                audience="Aprendizaje",
            )
            prompt = service.build_prompt(concept_id=concept.id, target_tool="chatgpt_images")
            review = service.review_thumbnail(thumbnail_version_id=thumbnail.id, title_version_id=title.id, concept_id=concept.id, prompt_id=prompt.id)
            exported_csv = service.export(creator_id=fixture.creator.id, format_name="csv")
            csv_text = Path(exported_csv.path).read_text(encoding="utf-8")
            detail = service.get_brand_profile_detail(fixture.creator.id)

            with fixture.database.connect() as connection:
                versions = [row[0] for row in connection.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()]
                tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}

            self.assertEqual(versions[-1], 23)
            self.assertIn("packaging_assets", tables)
            self.assertIn("title_versions", tables)
            self.assertIn("thumbnail_versions", tables)
            self.assertIn("packaging_brand_profiles", tables)
            self.assertEqual(reference.creator_id, fixture.creator.id)
            self.assertGreaterEqual(brand_profile.profile_version, 1)
            self.assertGreater(len(title_analysis.metrics), 0)
            self.assertTrue(thumbnail_analysis.warnings)
            self.assertIn(pair.recommendation_status.value, {"approved_as_is", "approved_with_changes", "viable_but_off_brand", "visually_strong_but_misleading", "on_brand_but_weak", "needs_more_context", "not_recommended", "insufficient_evidence"})
            self.assertGreaterEqual(len(detail.references), 1)
            self.assertIn("'=CMD(1)", csv_text)
            self.assertEqual(review.review_type, "thumbnail_review")

    def test_cli_and_views_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = make_fixture(Path(temp_dir))
            service = _build_packaging_service(fixture)
            workspace = make_workspace(fixture)
            workspace.creative_packaging_service = service
            workspace.creator_language_service = None
            workspace.creator_memory_service = None
            thumbnail_view = ThumbnailLabView(workspace)
            task_center = TaskCenterView(workspace)
            thumbnail_view.refresh()
            task_center.refresh()

            parser = build_parser()
            args = parser.parse_args(["packaging", "assets", "--creator-id", fixture.creator.id])
            stdout = io.StringIO()
            stderr = io.StringIO()
            exit_code = dispatch(
                args,
                service=fixture.catalog,
                media_service=SimpleNamespace(),
                audio_service=SimpleNamespace(),
                transcription_service=SimpleNamespace(),
                acoustic_service=SimpleNamespace(),
                visual_service=SimpleNamespace(),
                multimodal_service=SimpleNamespace(),
                clip_service=SimpleNamespace(),
                analytics_service=None,
                analytics_lab_service=None,
                experiment_service=None,
                creator_memory_service=None,
                creator_language_service=None,
                packaging_service=service,
                render_service=None,
                subtitle_service=None,
                personalization_service=None,
                diagnostic=SimpleNamespace(to_json=lambda: "{}" , state=SimpleNamespace(ready_for_basic_mode=True)),
                stdout=stdout,
                stderr=stderr,
                model_service=None,
                evaluation_service=None,
            )

            self.assertEqual(exit_code, 0)
            self.assertEqual(stderr.getvalue(), "")
            payload = json.loads(stdout.getvalue())
            self.assertIsInstance(payload, list)
            self.assertEqual(thumbnail_view.tabs.count(), 11)
