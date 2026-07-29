from __future__ import annotations

import logging
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from creator_intelligence_studio.application.services.analytics_import_service import AnalyticsImportService
from creator_intelligence_studio.application.services.analytics_query_service import AnalyticsQueryService
from creator_intelligence_studio.application.services.catalog_service import build_catalog_service
from creator_intelligence_studio.infrastructure.analytics.csv_importer import load_csv_table
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.persistence.database import build_database
from creator_intelligence_studio.infrastructure.persistence.migrations import run_migrations
from creator_intelligence_studio.infrastructure.persistence.sqlite_analytics_repository import SQLiteAnalyticsRepository
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


def write_minimal_xlsx(path: Path, rows: list[list[object]]) -> None:
    sheet_rows: list[str] = []
    for row_index, row in enumerate(rows, start=1):
        cells: list[str] = []
        for col_index, value in enumerate(row, start=1):
            col = ""
            n = col_index
            while n:
                n, rem = divmod(n - 1, 26)
                col = chr(65 + rem) + col
            cell_ref = f"{col}{row_index}"
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                cells.append(f'<c r="{cell_ref}"><v>{value}</v></c>')
            else:
                cells.append(f'<c r="{cell_ref}" t="inlineStr"><is><t>{escape(str(value))}</t></is></c>')
        sheet_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(sheet_rows)}</sheetData>'
        "</worksheet>"
    )
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets>'
        "</workbook>"
    )
    rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        "</Relationships>"
    )
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("xl/workbook.xml", workbook_xml)
        zf.writestr("xl/_rels/workbook.xml.rels", rels_xml)
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)


class AnalyticsDataFoundationTests(unittest.TestCase):
    def test_migration_v15_tables_exist(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings = make_settings()
            paths = ProjectPaths.from_settings(root, settings)
            database = build_database(settings, paths)
            with database.connect() as connection:
                run_migrations(connection)
                versions = [row[0] for row in connection.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()]
                tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            self.assertEqual(versions[-1], 30)
            self.assertIn("analytics_publications", tables)
            self.assertIn("analytics_metric_snapshots", tables)
            self.assertIn("analytics_imports", tables)

    def test_csv_import_reuse_and_publication_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings = make_settings()
            paths = ProjectPaths.from_settings(root, settings)
            paths.ensure_runtime_directories()
            database = build_database(settings, paths)
            with database.connect() as connection:
                run_migrations(connection)
            catalog = build_catalog_service(settings, paths, logger=logging.getLogger("test"), database=database)
            creator = catalog.create_creator(display_name="Analytics Tester")
            repository = SQLiteAnalyticsRepository(database)
            service = AnalyticsImportService(
                settings=settings,
                paths=paths,
                catalog_service=catalog,
                repository=repository,
                database=database,
                logger=logging.getLogger("test"),
            )
            csv_path = root / "analytics.csv"
            csv_path.write_text(
                "title,video_id,published_at,duration_seconds,views,impressions,ctr,average_view_duration_seconds,watch_time_minutes,subscribers_gained,likes,comments,shares\n"
                "Demo Longform,yt_demo_001,2026-07-01T12:00:00,420,1000,5000,0.042,185,350,12,120,14,9\n",
                encoding="utf-8",
            )
            first = service.import_csv(creator_id=creator.id, file=csv_path, platform="youtube_longform")
            second = service.import_csv(creator_id=creator.id, file=csv_path, platform="youtube_longform")

            self.assertFalse(first.reused)
            self.assertTrue(second.reused)
            self.assertEqual(first.import_record.id, second.import_record.id)
            self.assertEqual(first.summary.publications_created, 1)
            self.assertGreater(first.summary.snapshots_created, 0)
            publication = service.list_publications(creator.id)[0]
            latest = service.get_latest_metrics(publication.id)
            self.assertIn("views", latest)

    def test_xlsx_import_and_csv_export_are_safe(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings = make_settings()
            paths = ProjectPaths.from_settings(root, settings)
            paths.ensure_runtime_directories()
            database = build_database(settings, paths)
            with database.connect() as connection:
                run_migrations(connection)
            catalog = build_catalog_service(settings, paths, logger=logging.getLogger("test"), database=database)
            creator = catalog.create_creator(display_name="Analytics Tester")
            repository = SQLiteAnalyticsRepository(database)
            service = AnalyticsImportService(
                settings=settings,
                paths=paths,
                catalog_service=catalog,
                repository=repository,
                database=database,
                logger=logging.getLogger("test"),
            )
            query_service = AnalyticsQueryService(service)
            xlsx_path = root / "analytics.xlsx"
            write_minimal_xlsx(
                xlsx_path,
                [
                    ["title", "video_id", "published_at", "views", "reach", "likes"],
                    ["=CMD(1)", "yt_demo_002", "2026-07-07T12:00:00", 42, 10, 3],
                ],
            )
            result = service.import_excel(creator_id=creator.id, file=xlsx_path, platform="instagram_reel")
            export = query_service.export_normalized_data(creator_id=creator.id, format_name="csv")
            export_text = Path(export.path).read_text(encoding="utf-8")

            self.assertEqual(result.import_record.source_type.value, "xlsx")
            self.assertGreaterEqual(result.summary.accepted_rows, 0)
            self.assertIn("'=CMD(1)", export_text)

    def test_csv_loader_fingerprints_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "sample.csv"
            path.write_text("title,views\nDemo,10\n", encoding="utf-8")
            table = load_csv_table(path)
            self.assertEqual(table.source_type, "csv")
            self.assertEqual(table.headers, ("title", "views"))
            self.assertEqual(len(table.rows), 1)
