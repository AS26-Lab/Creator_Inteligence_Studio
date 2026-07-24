from __future__ import annotations

import csv
import io
import json
import logging
import tempfile
import unittest
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from PySide6.QtWidgets import QApplication

from creator_intelligence_studio.application.bootstrap import BootstrapContext, ServiceContext
from creator_intelligence_studio.application.services.analytics_import_service import AnalyticsImportService, AnalyticsQueryService
from creator_intelligence_studio.application.services.analytics_lab_service import AnalyticsLabService
from creator_intelligence_studio.application.services.catalog_service import build_catalog_service
from creator_intelligence_studio.infrastructure.analytics_lab.anomaly_detector import detect_anomalies
from creator_intelligence_studio.infrastructure.analytics_lab.metric_aggregator import (
    derived_metric_payloads,
    median_absolute_deviation,
    robust_z_score,
)
from creator_intelligence_studio.infrastructure.analytics_lab.percentile_calculator import calculate_percentile
from creator_intelligence_studio.infrastructure.analytics_lab.report_builder import write_report
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.persistence.database import build_database
from creator_intelligence_studio.infrastructure.persistence.migrations import run_migrations
from creator_intelligence_studio.infrastructure.persistence.sqlite_analytics_lab_repository import SQLiteAnalyticsLabRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_analytics_repository import SQLiteAnalyticsRepository
from creator_intelligence_studio.presentation.cli.cli import build_parser, dispatch
from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel
from creator_intelligence_studio.presentation.desktop.views.analytics_lab_view import AnalyticsLabView
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
    )


def write_csv_file(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _column_name(index: int) -> str:
    letters = ""
    value = index
    while value:
        value, remainder = divmod(value - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def write_xlsx_file(path: Path, sheets: dict[str, list[list[object]]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    def cell_xml(ref: str, value: object) -> str:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return f'<c r="{ref}"><v>{value}</v></c>'
        return f'<c r="{ref}" t="inlineStr"><is><t>{str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")}</t></is></c>'

    sheet_paths: list[str] = []
    sheet_xml_parts: list[str] = []
    workbook_sheets: list[str] = []
    rels: list[str] = []
    for index, (sheet_name, rows) in enumerate(sheets.items(), start=1):
        sheet_path = f"xl/worksheets/sheet{index}.xml"
        sheet_paths.append(sheet_path)
        rows_xml = []
        for row_index, row in enumerate(rows, start=1):
            cells = []
            for col_index, value in enumerate(row, start=1):
                ref = f"{_column_name(col_index)}{row_index}"
                cells.append(cell_xml(ref, value))
            rows_xml.append(f'<row r="{row_index}">{"".join(cells)}</row>')
        sheet_xml_parts.append(
            f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f'<sheetData>{"".join(rows_xml)}</sheetData>'
            f"</worksheet>"
        )
        workbook_sheets.append(f'<sheet name="{sheet_name}" sheetId="{index}" r:id="rId{index}"/>')
        rels.append(
            f'<Relationship Id="rId{index}" '
            f'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{index}.xml"/>'
        )

    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets>{"".join(workbook_sheets)}</sheets>'
        "</workbook>"
    )
    rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'{"".join(rels)}'
        "</Relationships>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        + "".join(
            f'<Override PartName="/xl/worksheets/sheet{i}.xml" '
            f'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            for i in range(1, len(sheet_paths) + 1)
        )
        + "</Types>"
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        "</Relationships>"
    )
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", root_rels)
        zf.writestr("xl/workbook.xml", workbook_xml)
        zf.writestr("xl/_rels/workbook.xml.rels", rels_xml)
        for sheet_path, sheet_xml in zip(sheet_paths, sheet_xml_parts, strict=True):
            zf.writestr(sheet_path, sheet_xml)


def make_fixture(root: Path):
    settings = make_settings()
    paths = ProjectPaths.from_settings(root, settings)
    paths.ensure_runtime_directories()
    database = build_database(settings, paths)
    with database.connect() as connection:
        run_migrations(connection)
    catalog = build_catalog_service(settings, paths, logger=logging.getLogger("analytics-lab-test"), database=database)
    creator = catalog.create_creator(display_name="Analytics Lab Creator")
    import_repository = SQLiteAnalyticsRepository(database)
    import_service = AnalyticsImportService(
        settings=settings,
        paths=paths,
        catalog_service=catalog,
        repository=import_repository,
        database=database,
        logger=logging.getLogger("analytics-lab-test"),
    )
    query_service = AnalyticsQueryService(import_service)
    lab_service = AnalyticsLabService(
        analytics_service=query_service,
        repository=SQLiteAnalyticsLabRepository(database),
        paths=paths,
        logger=logging.getLogger("analytics-lab-test"),
    )
    channels = {
        platform: import_service.create_channel(
            creator_id=creator.id,
            platform=platform,
            name=f"{platform} channel",
            timezone_name="America/Mexico_City",
            is_primary=True,
        )
        for platform in ("youtube_longform", "youtube_short", "instagram_reel", "tiktok")
    }
    return SimpleNamespace(
        root=root,
        settings=settings,
        paths=paths,
        database=database,
        catalog=catalog,
        creator=creator,
        import_service=import_service,
        query_service=query_service,
        lab_service=lab_service,
        channels=channels,
    )


def longform_rows() -> list[dict[str, object]]:
    rows = []
    for index in range(1, 9):
        rows.append(
            {
                "title": f"Longform {index}",
                "video_id": f"lf_{index}",
                "published_at": f"2026-07-{index:02d}T12:00:00+00:00",
                "duration_seconds": 420 + index * 15,
                "content_type": "longform_video",
                "views": 800 + index * 250,
                "impressions": 5000 + index * 100,
                "ctr": 0.82 if index == 1 else (0.24 if index == 2 else 0.08 + index * 0.01),
                "average_view_duration_seconds": 180 + index * 4,
                "watch_time_minutes": 320 + index * 12,
                "completion_rate": 0.31 if index == 1 else (0.81 if index == 2 else 0.45 + index * 0.03),
                "subscribers_gained": 4 + index,
                "likes": 90 + index * 7,
                "comments": 10 + index,
                "shares": 5 + index,
            }
        )
    return rows


def shorts_rows() -> list[dict[str, object]]:
    rows = []
    for index in range(1, 11):
        rows.append(
            {
                "title": f"Short {index}",
                "video_id": f"sh_{index}",
                "published_at": f"2026-07-{index:02d}T15:30:00+00:00",
                "duration_seconds": 28 + index,
                "content_type": "short_video",
                "views": 1200 + index * 180,
                "engaged_views": 700 + index * 70,
                "average_percentage_viewed": 0.52 + index * 0.02,
                "completion_rate": 0.49 + index * 0.02,
                "subscribers_gained": 1 + index % 3,
                "likes": 60 + index * 5,
                "comments": 4 + index % 4,
                "shares": 2 + index,
            }
        )
    rows[0]["views"] = 50
    rows[0]["shares"] = 12
    rows[0]["average_percentage_viewed"] = 0.91
    rows[0]["completion_rate"] = 0.93
    return rows


def reel_rows() -> list[dict[str, object]]:
    rows = []
    for index in range(1, 11):
        rows.append(
            {
                "title": f"Reel {index}",
                "video_id": f"re_{index}",
                "published_at": f"2026-07-{index:02d}T09:15:00+00:00",
                "duration_seconds": 22 + index,
                "content_type": "reel",
                "views": 1500 + index * 120,
                "reach": 1300 + index * 100,
                "average_watch_time_seconds": 13 + index * 0.6,
                "completion_rate": 0.38 + index * 0.03,
                "likes": 110 + index * 9,
                "comments": 12 + index,
                "shares": 4 + index,
                "saves": 6 + index,
                "profile_visits": 20 + index * 2,
                "follows": 5 + index % 4,
            }
        )
    return rows


def tiktok_rows() -> list[dict[str, object]]:
    rows = []
    for index in range(1, 11):
        rows.append(
            {
                "title": f"TikTok {index}",
                "video_id": f"tt_{index}",
                "published_at": f"2026-07-{index:02d}T18:45:00+00:00",
                "duration_seconds": 18 + index,
                "content_type": "tiktok",
                "views": 2000 + index * 140,
                "average_watch_time_seconds": 11 + index * 0.5,
                "completion_rate": 0.42 + index * 0.025,
                "likes": 140 + index * 11,
                "comments": 20 + index,
                "shares": 8 + index,
                "saves": 5 + index,
                "profile_views": 30 + index * 3,
                "followers_gained": 3 + index % 5,
                "total_play_time_minutes": 420 + index * 18,
            }
        )
    return rows


def import_platform_data(fixture, platform: str, rows: list[dict[str, object]], filename: str) -> object:
    path = fixture.root / filename
    fieldnames = list(rows[0].keys())
    write_csv_file(path, rows, fieldnames)
    return fixture.import_service.import_csv(
        creator_id=fixture.creator.id,
        file=path,
        platform=platform,
    )


def import_history_snapshots(fixture) -> None:
    path1 = fixture.root / "lf_hist_day1.csv"
    path7 = fixture.root / "lf_hist_day7.csv"
    path30 = fixture.root / "lf_hist_day30.csv"
    rows_day1 = [
        {
            "title": "Longform 1",
            "video_id": "lf_1",
            "published_at": "2026-07-01T12:00:00+00:00",
            "duration_seconds": 510,
            "content_type": "longform_video",
            "views": 1000,
            "impressions": 4500,
            "ctr": 0.14,
            "average_view_duration_seconds": 170,
            "watch_time_minutes": 300,
            "completion_rate": 0.52,
            "subscribers_gained": 5,
            "likes": 100,
            "comments": 10,
            "shares": 7,
        }
    ]
    rows_day7 = [dict(rows_day1[0], views=8000, watch_time_minutes=1800, completion_rate=0.61)]
    rows_day30 = [dict(rows_day1[0], views=16000, watch_time_minutes=3600, completion_rate=0.64)]
    write_csv_file(path1, rows_day1, list(rows_day1[0].keys()))
    write_csv_file(path7, rows_day7, list(rows_day7[0].keys()))
    write_csv_file(path30, rows_day30, list(rows_day30[0].keys()))
    fixture.import_service.import_csv(
        creator_id=fixture.creator.id,
        file=path1,
        platform="youtube_longform",
    )
    fixture.import_service.import_csv(
        creator_id=fixture.creator.id,
        file=path7,
        platform="youtube_longform",
    )
    fixture.import_service.import_csv(
        creator_id=fixture.creator.id,
        file=path30,
        platform="youtube_longform",
    )


def make_workspace(fixture):
    settings = fixture.settings
    paths = fixture.paths
    diagnostic = SimpleNamespace(
        application_name="Creator Intelligence Studio",
        application_version="0.1.0",
        project_root=fixture.root,
        os_name="Windows",
        os_version="11",
        os_architecture="x86_64",
        python_version="3.11.9",
        python_executable="python.exe",
        cpu_reported="CPU",
        logical_processors=8,
        nvidia_smi_available=True,
        gpu_devices=(SimpleNamespace(name="GPU", memory_total_mib=8192, driver_version="576.52"),),
        nvidia_driver_version="576.52",
        cuda_version_reported="12.9",
        git_available=True,
        git_version="git version 2.54.0",
        free_space_bytes=1_000_000,
        preferred_compute_backend="cuda",
        state=SimpleNamespace(ready_for_basic_mode=True, cuda_driver_detected=True, cuda_runtime_not_verified=True, warnings=()),
        warnings=(),
        errors=(),
    )
    workspace = WorkspaceViewModel(
        service=fixture.catalog,
        media_service=SimpleNamespace(verify_media_tools=lambda: SimpleNamespace(available=True, warnings=(), ffmpeg=SimpleNamespace(available=True), ffprobe=SimpleNamespace(available=True))),
        audio_service=SimpleNamespace(prepare_audio=lambda *args, **kwargs: SimpleNamespace(status=SimpleNamespace(value="not_prepared"), is_stale=False)),
        transcription_service=SimpleNamespace(),
        acoustic_service=SimpleNamespace(),
        visual_service=SimpleNamespace(),
        diagnostic=diagnostic,
        settings=settings,
        paths=paths,
        analytics_service=fixture.import_service,
        analytics_lab_service=fixture.lab_service,
    )
    workspace.select_creator(fixture.creator.id)
    return workspace


class AnalyticsLabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._qt_app = QApplication.instance() or QApplication([])

    def test_migration_v16_tables_exist(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fixture = make_fixture(root)
            with fixture.database.connect() as connection:
                versions = [row[0] for row in connection.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()]
                tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            self.assertEqual(versions[-1], 16)
            self.assertIn("analytics_cohort_definitions", tables)
            self.assertIn("analytics_analysis_runs", tables)
            self.assertIn("analytics_findings", tables)
            self.assertIn("analytics_report_runs", tables)

    def test_lab_analysis_findings_report_and_cache(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fixture = make_fixture(root)
            import_platform_data(fixture, "youtube_longform", longform_rows(), "longform.csv")
            import_platform_data(fixture, "youtube_short", shorts_rows(), "shorts.csv")
            import_platform_data(fixture, "instagram_reel", reel_rows(), "reels.csv")
            import_platform_data(fixture, "tiktok", tiktok_rows(), "tiktok.csv")
            import_history_snapshots(fixture)

            cohort = fixture.lab_service.create_cohort(
                creator_id=fixture.creator.id,
                name="Longform growth",
                description="Videos de YouTube longform de crecimiento.",
                platform="youtube_longform",
                content_type="longform_video",
                duration_min_seconds=300,
                duration_max_seconds=900,
            )
            run = fixture.lab_service.analyze_cohort(cohort.id)
            cached = fixture.lab_service.analyze_cohort(cohort.id)
            publications = fixture.import_service.list_publications(fixture.creator.id)
            target_publication = next(pub for pub in publications if pub.platform == "youtube_longform" and pub.title == "Longform 1")
            comparison = fixture.lab_service.compare_publication(target_publication.id, cohort.id)
            findings = fixture.lab_service.list_findings(fixture.creator.id)
            report = fixture.lab_service.generate_weekly_report(
                creator_id=fixture.creator.id,
                period_start="2026-07-01",
                period_end="2026-07-31",
            )
            report_detail = fixture.lab_service.get_report_detail(report.id)
            confirmed = fixture.lab_service.confirm_finding(findings[0].id)
            rejected = fixture.lab_service.reject_finding(findings[0].id)
            latest_metrics = fixture.import_service.get_latest_metrics(target_publication.id)
            history = fixture.import_service.list_metric_snapshots(target_publication.id)

            self.assertIn(run.status.value, {"completed", "completed_with_warnings"})
            self.assertEqual(run.id, cached.id)
            self.assertGreater(comparison.publication_count, 0)
            self.assertTrue(any(finding.finding_type.value == "fact" for finding in findings))
            self.assertTrue(any(finding.finding_type.value == "comparison" for finding in findings))
            self.assertTrue(any(finding.finding_type.value == "anomaly" for finding in findings))
            self.assertTrue(any(finding.finding_type.value == "pattern" for finding in findings))
            self.assertTrue(any(finding.finding_type.value == "inference" for finding in findings))
            self.assertTrue(any(finding.finding_type.value == "hypothesis" for finding in findings))
            self.assertEqual(confirmed.status.value, "confirmed")
            self.assertEqual(rejected.status.value, "rejected")
            self.assertGreater(report.finding_count, 0)
            self.assertTrue(Path(report.output_json_path).exists())
            self.assertTrue(Path(report.output_txt_path).exists())
            self.assertTrue(Path(report.output_csv_path).exists())
            self.assertGreaterEqual(len(history), 3)
            self.assertIn("views", latest_metrics)
            self.assertEqual(len(report_detail["items"]), 10)

            updated_path = fixture.root / "longform_updated.csv"
            write_csv_file(
                updated_path,
                [
                    {
                        "title": "Longform 1",
                        "video_id": "lf_1",
                        "published_at": "2026-07-01T12:00:00+00:00",
                        "duration_seconds": 435,
                        "content_type": "longform_video",
                        "views": 99999,
                        "impressions": 999999,
                        "ctr": 0.91,
                        "average_view_duration_seconds": 210,
                        "watch_time_minutes": 6000,
                        "completion_rate": 0.28,
                        "subscribers_gained": 80,
                        "likes": 320,
                        "comments": 41,
                        "shares": 33,
                    }
                ],
                [
                    "title",
                    "video_id",
                    "published_at",
                    "duration_seconds",
                    "content_type",
                    "views",
                    "impressions",
                    "ctr",
                    "average_view_duration_seconds",
                    "watch_time_minutes",
                    "completion_rate",
                    "subscribers_gained",
                    "likes",
                    "comments",
                    "shares",
                ],
            )
            fixture.import_service.import_csv(
                creator_id=fixture.creator.id,
                file=updated_path,
                platform="youtube_longform",
            )
            fresh_path = fixture.root / "longform_fresh.csv"
            write_csv_file(
                fresh_path,
                [
                    {
                        "title": "Longform 9",
                        "video_id": "lf_9_new",
                        "published_at": "2026-07-09T12:00:00+00:00",
                        "duration_seconds": 480,
                        "content_type": "longform_video",
                        "views": 12000,
                        "impressions": 42000,
                        "ctr": 0.19,
                        "average_view_duration_seconds": 200,
                        "watch_time_minutes": 2400,
                        "completion_rate": 0.57,
                        "subscribers_gained": 18,
                        "likes": 210,
                        "comments": 24,
                        "shares": 12,
                    }
                ],
                [
                    "title",
                    "video_id",
                    "published_at",
                    "duration_seconds",
                    "content_type",
                    "views",
                    "impressions",
                    "ctr",
                    "average_view_duration_seconds",
                    "watch_time_minutes",
                    "completion_rate",
                    "subscribers_gained",
                    "likes",
                    "comments",
                    "shares",
                ],
            )
            fixture.import_service.import_csv(
                creator_id=fixture.creator.id,
                file=fresh_path,
                platform="youtube_longform",
            )
            rerun = fixture.lab_service.analyze_cohort(cohort.id)
            self.assertNotEqual(run.id, rerun.id)

    def test_math_helpers_anomalies_and_csv_safety(self) -> None:
        self.assertEqual(calculate_percentile([], 50), None)
        self.assertEqual(calculate_percentile([10], 50), 10.0)
        self.assertGreater(median_absolute_deviation([1, 1, 2, 2, 100]), 0)
        self.assertGreater(robust_z_score(100, [1, 2, 3, 4, 5]), 0)
        derived = derived_metric_payloads({"views": 100, "likes": 20, "comments": 5, "shares": 10, "saves": 3, "subscribers_gained": 4, "followers_gained": 2, "watch_time_minutes": 50}, published_at=datetime.now(timezone.utc))
        self.assertIn("engagement_rate_by_views", derived)
        anomalies = detect_anomalies(
            publication_id="pub-1",
            metrics={"ctr": 0.9, "completion_rate": 0.3, "views": 100, "shares": 20},
            cohort_percentiles={},
            warnings=["missing_expected_metric"],
        )
        anomaly_types = {item.anomaly_type for item in anomalies}
        self.assertIn("strong_ctr_weak_retention", anomaly_types)
        self.assertIn("high_engagement_low_reach", anomaly_types)
        self.assertIn("missing_expected_metric", anomaly_types)
        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = Path(temp_dir) / "analytics_lab_report.csv"
            payload = {
                "report_run": {"title": "Lab"},
                "sections": [{"name": "=CMD(1)", "title": "+SUM(1,1)", "body": "@IMPORT('x')"}],
                "findings": [],
                "warnings": [],
                "confidence": [],
                "limitations": [],
            }
            write_report(report_path, payload, format_name="csv")
            text = report_path.read_text(encoding="utf-8")
        self.assertIn("'=CMD(1)", text)
        self.assertIn("'+SUM(1,1)", text)
        self.assertIn("'@IMPORT('x')", text)

    def test_cli_gui_and_task_center_wiring(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fixture = make_fixture(root)
            import_platform_data(fixture, "youtube_longform", longform_rows(), "longform.csv")
            cohort = fixture.lab_service.create_cohort(
                creator_id=fixture.creator.id,
                name="Longform cohort",
                description="Cohorte para CLI y GUI.",
                platform="youtube_longform",
                content_type="longform_video",
            )
            fixture.lab_service.analyze_cohort(cohort.id)
            fixture.lab_service.generate_weekly_report(
                creator_id=fixture.creator.id,
                period_start="2026-07-01",
                period_end="2026-07-31",
            )

            parser = build_parser()
            args = parser.parse_args(["analytics", "cohorts", "--creator-id", fixture.creator.id])
            stdout = io.StringIO()
            stderr = io.StringIO()
            code = dispatch(
                args,
                service=MagicMock(),
                media_service=MagicMock(),
                audio_service=MagicMock(),
                transcription_service=MagicMock(),
                acoustic_service=MagicMock(),
                visual_service=MagicMock(),
                multimodal_service=MagicMock(),
                clip_service=MagicMock(),
                analytics_service=fixture.import_service,
                analytics_lab_service=fixture.lab_service,
                diagnostic=SimpleNamespace(ready_for_basic_mode=True),
                stdout=stdout,
                stderr=stderr,
                render_service=MagicMock(),
                subtitle_service=MagicMock(),
                personalization_service=MagicMock(),
                model_service=MagicMock(),
                evaluation_service=MagicMock(),
            )
            self.assertEqual(code, 0)
            self.assertIn("Longform cohort", stdout.getvalue())

            workspace = make_workspace(fixture)
            analytics_view = AnalyticsLabView(workspace)
            task_center = TaskCenterView(workspace)
            task_center.refresh()
            self.assertGreaterEqual(analytics_view.cohorts_table.rowCount(), 1)
            self.assertGreaterEqual(analytics_view.findings_table.rowCount(), 1)
            self.assertGreaterEqual(analytics_view.reports_table.rowCount(), 1)
            self.assertGreaterEqual(task_center.table.rowCount(), 1)

    def test_xlsx_multi_sheet_import(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fixture = make_fixture(root)
            workbook = fixture.root / "analytics.xlsx"
            write_xlsx_file(
                workbook,
                {
                    "Longform": [
                        ["title", "video_id", "published_at", "duration_seconds", "content_type", "views", "impressions", "ctr", "watch_time_minutes", "completion_rate", "subscribers_gained", "likes", "comments", "shares"],
                        ["XLSX Longform", "xls_1", "2026-07-01T12:00:00+00:00", 420, "longform_video", 2000, 6000, 0.11, 320, 0.62, 15, 140, 20, 11],
                    ],
                    "Reels": [
                        ["title", "video_id", "published_at", "duration_seconds", "content_type", "views", "reach", "average_watch_time_seconds", "completion_rate", "likes", "comments", "shares", "saves", "profile_visits", "follows"],
                        ["XLSX Reel", "xls_2", "2026-07-02T09:00:00+00:00", 31, "reel", 1800, 1500, 18, 0.58, 110, 13, 8, 7, 24, 6],
                    ],
                },
            )
            result = fixture.import_service.import_excel(
                creator_id=fixture.creator.id,
                file=workbook,
                platform="instagram_reel",
                sheet_name="Reels",
            )
            self.assertGreaterEqual(result.summary.accepted_rows, 1)
            self.assertEqual(result.import_record.source_type.value, "xlsx")
