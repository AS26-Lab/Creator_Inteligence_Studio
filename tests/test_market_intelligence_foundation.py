from __future__ import annotations

import io
import json
import logging
import tempfile
import unittest
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from creator_intelligence_studio.application.services.catalog_service import build_catalog_service
from creator_intelligence_studio.application.services.market_intelligence_service import build_market_intelligence_service
from creator_intelligence_studio.domain.market_intelligence.source_types import SourceType, TrustLevel
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.market_sources.manual_source_adapter import ManualSourceAdapter
from creator_intelligence_studio.infrastructure.market_sources.source_adapter import MarketSourcePage
from creator_intelligence_studio.infrastructure.market_sources.source_registry import SourceRegistry
from creator_intelligence_studio.infrastructure.persistence.database import build_database
from creator_intelligence_studio.infrastructure.persistence.migrations import run_migrations
from creator_intelligence_studio.infrastructure.persistence.sqlite_market_intelligence_repository import SQLiteMarketIntelligenceRepository
from creator_intelligence_studio.presentation.cli.cli import build_parser
from creator_intelligence_studio.presentation.cli.market_cli import handle_market_command
from creator_intelligence_studio.shared.paths import ProjectPaths


def make_settings() -> AppSettings:
    return AppSettings(
        application_name="Creator Intelligence Studio",
        environment="test",
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


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True, slots=True)
class FakeYouTubePublicAdapter:
    source_type: str = "youtube_public"

    def is_available(self) -> bool:
        return True

    def search(self, query: dict[str, object]) -> MarketSourcePage:
        items = (
            {
                "id": {"videoId": "yt-video-1"},
                "snippet": {
                    "title": "Piano para principiantes",
                    "description": "Leccion inicial",
                    "publishedAt": "2026-01-01T00:00:00Z",
                    "thumbnails": {"high": {"url": "https://example.test/thumb-1.jpg"}},
                },
                "statistics": {"viewCount": "1200", "likeCount": "90"},
            },
            {
                "id": {"videoId": "yt-video-2"},
                "snippet": {
                    "title": "Errores comunes de piano",
                    "description": "Evita estos fallos",
                    "publishedAt": "2026-01-02T00:00:00Z",
                    "thumbnails": {"high": {"url": "https://example.test/thumb-2.jpg"}},
                },
                "statistics": {"viewCount": "1800", "likeCount": "140"},
            },
        )
        return MarketSourcePage(items=items, next_cursor="cursor-2", raw_json=json.dumps({"items": items}, ensure_ascii=False))


def make_bundle(root: Path):
    settings = make_settings()
    paths = ProjectPaths.from_settings(root, settings)
    paths.ensure_runtime_directories()
    database = build_database(settings, paths)
    with database.connect() as connection:
        run_migrations(connection)
    catalog = build_catalog_service(settings, paths, database=database, logger=logging.getLogger("test"))
    creator_a = catalog.create_creator(display_name="Creator A")
    creator_b = catalog.create_creator(display_name="Creator B")
    repository = SQLiteMarketIntelligenceRepository(database)
    source_registry = SourceRegistry(
        adapters={
            "manual": ManualSourceAdapter(),
            "youtube_public": FakeYouTubePublicAdapter(),
        }
    )
    market_service = build_market_intelligence_service(
        settings=settings,
        paths=paths,
        repository=repository,
        database=database,
        source_registry=source_registry,
        catalog_service=catalog,
        logger=logging.getLogger("test"),
    )
    return settings, paths, database, catalog, creator_a, creator_b, market_service


class MarketIntelligenceFoundationTests(unittest.TestCase):
    def test_migration_v26_and_idempotence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings, paths = make_settings(), ProjectPaths.from_settings(Path(temp_dir), make_settings())
            paths.ensure_runtime_directories()
            database = build_database(settings, paths)
            with database.connect() as connection:
                run_migrations(connection)
                first = connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0]
                run_migrations(connection)
                second = connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0]
                tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertEqual(first, 26)
            self.assertEqual(second, 26)
            self.assertTrue({"market_definitions", "trend_signals", "opportunity_candidates", "market_reports"}.issubset(tables))

    def test_market_isolation_and_public_research_flow(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            _, _, database, _, creator_a, creator_b, service = make_bundle(Path(temp_dir))
            market = service.create_market_definition(
                creator_id=creator_a.id,
                name="Musica en espanol",
                description="Educacion musical",
                primary_language="es",
                primary_region="MX",
            )
            other_market = service.create_market_definition(
                creator_id=creator_b.id,
                name="Fotografia",
                description="Mercado independiente",
            )
            source = service.register_market_source(
                creator_id=creator_a.id,
                source_type=SourceType.YOUTUBE_PUBLIC.value,
                name="YouTube Public Discovery",
                access_method="official_public_source",
                trust_level=TrustLevel.OFFICIAL_PUBLIC_SOURCE.value,
                permission_status="available",
                enabled=True,
                platform="youtube",
                source_identifier="yt-public",
                source_url="https://www.youtube.com",
            )
            query = service.create_research_query(
                creator_id=creator_a.id,
                platform="youtube",
                market_id=market.id,
                query_text="piano para principiantes",
                language="es",
                region="MX",
                max_results=10,
            )
            run = service.run_research_query(query.id)
            self.assertEqual(run.status, "completed")
            self.assertEqual(run.discovered_count, 2)
            self.assertEqual(run.cursor_json, "cursor-2")
            items = service.list_research_items(run.id)
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0].external_entity_type, "cursor")
            contents = service.list_external_content_items(creator_a.id)
            self.assertEqual({item.external_content_id for item in contents}, {"yt-video-1", "yt-video-2"})
            snapshots = service.list_external_content_snapshots(creator_a.id)
            self.assertEqual(len(snapshots), 2)
            self.assertEqual(service.list_market_definitions(creator_a.id)[0].id, market.id)
            self.assertEqual(service.list_market_definitions(creator_b.id)[0].id, other_market.id)
            self.assertEqual(service.list_market_sources(creator_a.id)[0].id, source.id)
            self.assertEqual(service.list_market_sources(creator_b.id), [])

    def test_trends_patterns_fit_and_safe_export(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            _, _, _, _, creator_a, _, service = make_bundle(Path(temp_dir))
            market = service.create_market_definition(creator_id=creator_a.id, name="Educacion musical")
            source = service.register_market_source(
                creator_id=creator_a.id,
                source_type=SourceType.MANUAL.value,
                name="Notas manuales",
                access_method="manual",
                trust_level=TrustLevel.CREATOR_MANUAL_OBSERVATION.value,
                permission_status="available",
                enabled=True,
                platform="youtube",
            )
            service.record_external_content_from_youtube(
                creator_id=creator_a.id,
                source_id=source.id,
                payload={
                    "id": {"videoId": "pattern-video-1"},
                    "title": "Piano rapido para principiantes",
                    "description": "Formato repetible",
                    "published_at": "2026-01-01T00:00:00Z",
                    "public_metrics": {"view_count": 1000},
                    "topic_labels": ["piano"],
                    "format_labels": ["tutorial"],
                    "source_url": "https://youtube.com/watch?v=pattern-video-1",
                },
            )
            service.record_external_content_from_youtube(
                creator_id=creator_a.id,
                source_id=source.id,
                payload={
                    "id": {"videoId": "pattern-video-2"},
                    "title": "Piano rapido para principiantes",
                    "description": "Formato repetible",
                    "published_at": "2026-01-02T00:00:00Z",
                    "public_metrics": {"view_count": 1200},
                    "topic_labels": ["piano"],
                    "format_labels": ["tutorial"],
                    "source_url": "https://youtube.com/watch?v=pattern-video-2",
                },
            )
            for index, value in enumerate((10, 14, 20), start=1):
                service.record_observation(
                    creator_id=creator_a.id,
                    source_id=source.id,
                    platform="youtube",
                    observation_type="trend",
                    subject_type="content",
                    observed_value={"value": value, "topic": "piano"},
                    evidence_quality="high",
                    confidence_level="medium",
                    status="observed",
                    market_id=market.id,
                    subject_id=f"subject-{index}",
                    period_start=f"2026-01-0{index}T00:00:00Z",
                    period_end=f"2026-01-0{index}T23:59:59Z",
                )
            signals = service.build_trend_signals(creator_a.id, market.id)
            self.assertTrue(signals)
            patterns = service.detect_patterns(creator_a.id, market.id)
            self.assertTrue(patterns)
            candidates = service.build_opportunity_candidates(creator_a.id, market.id)
            self.assertTrue(candidates)
            tasks = service.build_background_tasks(creator_a.id)
            self.assertTrue(any(task["payload"]["kind"] == "market_opportunity_candidate" for task in tasks))
            fit = service.evaluate_creator_market_fit(
                creator_id=creator_a.id,
                target_type="trend_signal",
                target_id=signals[0].id,
                market_topics=["piano"],
                platform_scope=["youtube"],
                evidence_strength=0.8,
                copying_risk=0.1,
            )
            self.assertGreaterEqual(fit.overall_fit, 0.0)
            review = service.review_target(
                creator_id=creator_a.id,
                target_type="trend_signal",
                target_id=signals[0].id,
                decision="approved",
                reason="Encaja con la marca",
            )
            self.assertEqual(review.decision, "approved")
            snapshot = service.snapshot_market(
                creator_id=creator_a.id,
                market_id=market.id,
                snapshot_type="trend_snapshot",
                period_start="2026-01-01T00:00:00Z",
                period_end="2026-01-31T23:59:59Z",
                payload={"signals": [signal.to_dict() for signal in signals]},
            )
            stored = service.store_market_report(
                creator_id=creator_a.id,
                market_id=market.id,
                report_type="market_summary",
                period_start="2026-01-01T00:00:00Z",
                period_end="2026-01-31T23:59:59Z",
                payload={"candidate_titles": [candidate.title for candidate in candidates]},
            )
            exported_json = service.export_market_report(stored.id, "json")
            exported_csv = service.export_market_report(stored.id, "csv")
            self.assertTrue(exported_json.exists())
            self.assertTrue(exported_csv.exists())
            self.assertEqual(service.list_snapshots(creator_a.id, market.id)[0].id, snapshot.id)
            self.assertIn(creator_a.id, json.dumps(stored.to_dict()))

    def test_cli_supports_json_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            _, _, _, _, creator_a, _, service = make_bundle(Path(temp_dir))
            parser = build_parser()
            args = parser.parse_args(["market", "markets", "--creator-id", creator_a.id, "--json"])
            stdout = io.StringIO()
            stderr = io.StringIO()
            code = handle_market_command(args, service=service, stdout=stdout, stderr=stderr)
            self.assertEqual(code, 0)
            payload = json.loads(stdout.getvalue())
            self.assertIsInstance(payload, list)
            self.assertEqual(stderr.getvalue(), "")
