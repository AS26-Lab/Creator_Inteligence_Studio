from __future__ import annotations

import io
import json
import logging
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from creator_intelligence_studio.application.services.catalog_service import build_catalog_service
from creator_intelligence_studio.application.services.creator_corpus_service import build_creator_corpus_service
from creator_intelligence_studio.application.services.creator_voice_evidence_service import (
    CreatorVoiceEvidenceRequest,
    build_creator_voice_evidence_service,
)
from creator_intelligence_studio.domain.creator_corpus import CorpusDocumentType, CorpusSourceType, CorpusVersionSourceKind
from creator_intelligence_studio.domain.creator_preferences import CreatorConfirmedPreference
from creator_intelligence_studio.domain.creator_preferences.value_objects import CreatorPreferenceScope, CreatorPreferenceType
from creator_intelligence_studio.domain.creator_voice import CreatorVoiceEvidenceType, CreatorVoiceExclusionReason
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.persistence.database import build_database
from creator_intelligence_studio.infrastructure.persistence.migrations import run_migrations
from creator_intelligence_studio.infrastructure.persistence.sqlite_creator_preference_repository import SQLiteCreatorPreferenceRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_creator_corpus_repository import SQLiteCreatorCorpusRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_project_repository import SQLiteProjectRepository
from creator_intelligence_studio.domain.projects.entities import Project, ProjectStatus, ProjectType
from creator_intelligence_studio.presentation.cli.cli import build_parser
from creator_intelligence_studio.presentation.cli.voice_cli import handle_voice_command
from creator_intelligence_studio.shared.dates import utc_now

_BASELINE_VOICE_FIXTURE: SimpleNamespace | None = None


def make_settings():
    return AppSettings(
        application_name="Creator Intelligence Studio",
        environment="test",
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
    )


def _make_preference(*, creator_id: str, preference_key: str, value_json: dict[str, object], scope: CreatorPreferenceScope, project_id: str | None = None, workflow_type: str | None = None) -> CreatorConfirmedPreference:
    now = utc_now()
    return CreatorConfirmedPreference(
        id=str(uuid4()),
        preference_key=preference_key,
        creator_id=creator_id,
        project_id=project_id,
        workflow_type=workflow_type,
        scope=scope,
        preference_type=CreatorPreferenceType.CONTENT_LENGTH_PREFERENCE,
        value_json=json.dumps(value_json, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        source_candidate_id=None,
        confirmed_by="tester",
        confirmed_at=now,
        active=True,
        provenance_json=json.dumps({"source": "unit-test"}, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        created_at=now,
        updated_at=now,
    )


def _make_words(total: int, replacements: dict[int, str] | None = None) -> str:
    replacements = replacements or {}
    tokens = [f"w{i}" for i in range(1, total + 1)]
    for index, value in replacements.items():
        tokens[index] = value
    return " ".join(tokens)


def _ensure_baseline_voice_fixture() -> SimpleNamespace:
    global _BASELINE_VOICE_FIXTURE
    if _BASELINE_VOICE_FIXTURE is not None:
        return _BASELINE_VOICE_FIXTURE
    baseline_root = Path(tempfile.mkdtemp(prefix="voice-baseline-"))
    settings = make_settings()
    from creator_intelligence_studio.shared.paths import ProjectPaths

    paths = ProjectPaths.from_settings(baseline_root, settings)
    paths.ensure_runtime_directories()
    database = build_database(settings, paths)
    with database.connect() as connection:
        run_migrations(connection)
    catalog = build_catalog_service(
        settings=settings,
        paths=paths,
        database=database,
        logger=logging.getLogger("voice-test"),
    )
    creator_a = catalog.create_creator(display_name="Creator A")
    creator_b = catalog.create_creator(display_name="Creator B")
    project_repo = SQLiteProjectRepository(database)
    project_a = project_repo.create(
        Project(
            id=str(uuid4()),
            creator_id=creator_a.id,
            name="Project A",
            description=None,
            project_type=ProjectType.MIXED,
            status=ProjectStatus.ACTIVE,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
    )
    project_b = project_repo.create(
        Project(
            id=str(uuid4()),
            creator_id=creator_b.id,
            name="Project B",
            description=None,
            project_type=ProjectType.MIXED,
            status=ProjectStatus.ACTIVE,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
    )
    _BASELINE_VOICE_FIXTURE = SimpleNamespace(
        root=baseline_root,
        settings=settings,
        database_path=paths.database_path,
        creator_a=creator_a,
        creator_b=creator_b,
        project_a=project_a,
        project_b=project_b,
    )
    return _BASELINE_VOICE_FIXTURE


def _build_voice_fixture(temp_dir: str):
    baseline = _ensure_baseline_voice_fixture()
    settings = make_settings()
    root = Path(temp_dir)
    from creator_intelligence_studio.shared.paths import ProjectPaths

    paths = ProjectPaths.from_settings(root, settings)
    paths.ensure_runtime_directories()
    shutil.copy2(baseline.database_path, paths.database_path)
    database = build_database(settings, paths)
    project_repo = SQLiteProjectRepository(database)
    corpus = build_creator_corpus_service(
        settings=settings,
        paths=paths,
        repository=SQLiteCreatorCorpusRepository(database),
        project_repository=project_repo,
    )
    preference_repo = SQLiteCreatorPreferenceRepository(database)
    voice_service = build_creator_voice_evidence_service(
        corpus_repository=corpus.repository,
        preference_repository=preference_repo,
        project_repository=project_repo,
        logger=logging.getLogger("voice-test"),
    )
    return SimpleNamespace(
        settings=settings,
        paths=paths,
        database=database,
        creator_a=baseline.creator_a,
        creator_b=baseline.creator_b,
        project_a=baseline.project_a,
        project_b=baseline.project_b,
        corpus=corpus,
        preference_repo=preference_repo,
        voice_service=voice_service,
    )


class CreatorVoiceEvidenceTests(unittest.TestCase):
    def test_current_creator_authentic_evidence_is_selected_and_preferences_remain_separate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = _build_voice_fixture(temp_dir)
            corpus = fixture.corpus
            creator_id = fixture.creator_a.id
            preference = _make_preference(
                creator_id=creator_id,
                preference_key="voice.shorter.global",
                value_json={"preference_type": "content_length_preference", "direction": "shorter"},
                scope=CreatorPreferenceScope.CREATOR_GLOBAL,
            )
            fixture.preference_repo.upsert_confirmed_preference(preference)
            original = corpus.ingest_text_document(
                creator_id=creator_id,
                document_type=CorpusDocumentType.SCRIPT,
                title="Original",
                content="uno dos tres cuatro cinco",
                language="es",
                source_kind=CorpusVersionSourceKind.ORIGINAL,
                source_asset_type=CorpusSourceType.IMPORTED_TEXT,
                source_asset_original_name="original.txt",
            )
            duplicate = corpus.ingest_text_document(
                creator_id=creator_id,
                document_type=CorpusDocumentType.NOTE,
                title="Duplicate",
                content="uno dos tres cuatro cinco",
                language="es",
                source_kind=CorpusVersionSourceKind.ORIGINAL,
                source_asset_type=CorpusSourceType.IMPORTED_TEXT,
                source_asset_original_name="duplicate.txt",
            )
            transcript = corpus.ingest_text_document(
                creator_id=creator_id,
                document_type=CorpusDocumentType.TRANSCRIPT,
                title="Transcripcion",
                content="hola mundo desde la transcripcion",
                language="es",
                source_kind=CorpusVersionSourceKind.TRANSCRIPTION,
                source_asset_type=CorpusSourceType.TRANSCRIPT,
                source_asset_original_name="transcript.txt",
                segments=[
                    {"sequence": 0, "start_seconds": 0.0, "end_seconds": 1.0, "text": "hola mundo", "confidence": 0.97, "review_state": "transcribed"},
                    {"sequence": 1, "start_seconds": 1.0, "end_seconds": 2.0, "text": "desde la transcripcion", "confidence": 0.96, "review_state": "transcribed"},
                ],
            )

            before_docs = len(corpus.list_documents(creator_id))
            before_prefs = len(fixture.preference_repo.list_confirmed_preferences(creator_id, active=True))
            snapshot = fixture.voice_service.build_snapshot({"creator_id": creator_id})
            after_docs = len(corpus.list_documents(creator_id))
            after_prefs = len(fixture.preference_repo.list_confirmed_preferences(creator_id, active=True))

            self.assertEqual(before_docs, after_docs)
            self.assertEqual(before_prefs, after_prefs)
            self.assertEqual(snapshot.creator_id, creator_id)
            self.assertIn(CreatorVoiceEvidenceType.CREATOR_WRITTEN.value, snapshot.category_counts)
            self.assertIn(CreatorVoiceEvidenceType.CREATOR_SPOKEN.value, snapshot.category_counts)
            self.assertIn(CreatorVoiceEvidenceType.CONFIRMED_PREFERENCE.value, snapshot.category_counts)
            self.assertEqual(snapshot.category_counts[CreatorVoiceEvidenceType.CONFIRMED_PREFERENCE.value], 1)
            self.assertGreaterEqual(snapshot.quality_counts["high"], 2)
            self.assertGreaterEqual(snapshot.evidence_count, 3)
            self.assertIn("duplicate", snapshot.excluded_counts)
            self.assertEqual(snapshot.content_fingerprint, fixture.voice_service.build_snapshot({"creator_id": creator_id}).content_fingerprint)
            self.assertTrue(any(item.evidence_type == CreatorVoiceEvidenceType.CONFIRMED_PREFERENCE for item in snapshot.evidence_items))
            self.assertTrue(any(item.evidence_type == CreatorVoiceEvidenceType.CREATOR_SPOKEN for item in snapshot.evidence_items))

    def test_ai_generated_rewritten_imported_unknown_and_archived_content_are_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = _build_voice_fixture(temp_dir)
            corpus = fixture.corpus
            creator_id = fixture.creator_a.id
            ai_generated = corpus.ingest_text_document(
                creator_id=creator_id,
                document_type=CorpusDocumentType.SCRIPT,
                title="AI Generated",
                content="texto generado por ia",
                language="es",
                source_kind=CorpusVersionSourceKind.AI_GENERATED,
                source_asset_type=CorpusSourceType.IMPORTED_TEXT,
                source_asset_original_name="ai.txt",
            )
            ai_rewritten = corpus.ingest_text_document(
                creator_id=creator_id,
                document_type=CorpusDocumentType.SCRIPT,
                title="AI Rewritten",
                content="texto reescrito por ia",
                language="es",
                source_kind=CorpusVersionSourceKind.AI_REWRITE,
                source_asset_type=CorpusSourceType.IMPORTED_TEXT,
                source_asset_original_name="rewrite.txt",
            )
            imported_unknown = corpus.ingest_text_document(
                creator_id=creator_id,
                document_type=CorpusDocumentType.NOTE,
                title="Unknown",
                content="texto importado",
                language="es",
                source_kind=CorpusVersionSourceKind.IMPORT,
                source_asset_type=CorpusSourceType.IMPORTED_TEXT,
                source_asset_original_name="imported.txt",
            )
            archived = corpus.ingest_text_document(
                creator_id=creator_id,
                document_type=CorpusDocumentType.SCRIPT,
                title="Archived",
                content="contenido autentico archivado",
                language="es",
                source_kind=CorpusVersionSourceKind.ORIGINAL,
                source_asset_type=CorpusSourceType.IMPORTED_TEXT,
                source_asset_original_name="archived.txt",
            )
            corpus.archive_document(archived.document.id)

            snapshot = fixture.voice_service.build_snapshot({"creator_id": creator_id})
            reasons = {item.reason for item in snapshot.excluded_candidates}

            self.assertIn(CreatorVoiceExclusionReason.AI_GENERATED.value, reasons)
            self.assertIn(CreatorVoiceExclusionReason.AI_REWRITTEN.value, reasons)
            self.assertIn(CreatorVoiceExclusionReason.UNSUPPORTED_AUTHORSHIP.value, reasons)
            self.assertIn(CreatorVoiceExclusionReason.ARCHIVED.value, reasons)
            self.assertTrue(all(item.id not in {ai_generated.version.id, ai_rewritten.version.id, imported_unknown.version.id, archived.version.id} for item in snapshot.evidence_items))

    def test_voice_learning_policy_blocks_low_confidence_and_needs_review_segments(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = _build_voice_fixture(temp_dir)
            corpus = fixture.corpus
            creator_id = fixture.creator_a.id
            low_confidence = corpus.ingest_text_document(
                creator_id=creator_id,
                document_type=CorpusDocumentType.TRANSCRIPT,
                title="Low confidence",
                content="hola mundo incompleto",
                language="es",
                source_kind=CorpusVersionSourceKind.TRANSCRIPTION,
                source_asset_type=CorpusSourceType.TRANSCRIPT,
                source_asset_original_name="low.txt",
                segments=[
                    {"sequence": 0, "start_seconds": 0.0, "end_seconds": 1.0, "text": "hola mundo", "confidence": 0.35, "review_state": "transcribed"},
                ],
            )
            needs_review = corpus.ingest_text_document(
                creator_id=creator_id,
                document_type=CorpusDocumentType.TRANSCRIPT,
                title="Needs review",
                content="segmento dudoso",
                language="es",
                source_kind=CorpusVersionSourceKind.TRANSCRIPTION,
                source_asset_type=CorpusSourceType.TRANSCRIPT,
                source_asset_original_name="review.txt",
                segments=[
                    {"sequence": 0, "start_seconds": 0.0, "end_seconds": 1.0, "text": "segmento dudoso", "confidence": 0.88, "review_state": "needs_review"},
                ],
            )

            snapshot = fixture.voice_service.build_snapshot({"creator_id": creator_id})
            reasons = {item.reason for item in snapshot.excluded_candidates}

            self.assertIn(CreatorVoiceExclusionReason.LOW_CONFIDENCE.value, reasons)
            self.assertIn(CreatorVoiceExclusionReason.NEEDS_REVIEW.value, reasons)
            self.assertNotIn(low_confidence.version.id, {item.version_id for item in snapshot.evidence_items})
            self.assertNotIn(needs_review.version.id, {item.version_id for item in snapshot.evidence_items})

    def test_current_version_policy_and_ai_contamination_are_conservative(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = _build_voice_fixture(temp_dir)
            corpus = fixture.corpus
            creator_id = fixture.creator_a.id
            ai_minimal = corpus.ingest_text_document(
                creator_id=creator_id,
                document_type=CorpusDocumentType.SCRIPT,
                title="AI minimal",
                content=_make_words(100),
                language="es",
                source_kind=CorpusVersionSourceKind.AI_GENERATED,
                source_asset_type=CorpusSourceType.IMPORTED_TEXT,
                source_asset_original_name="minimal.txt",
            )
            ai_minimal_edit = corpus.append_document_version(
                document_id=ai_minimal.document.id,
                creator_id=creator_id,
                content=_make_words(100, {3: "changed3", 10: "changed10", 20: "changed20", 30: "changed30", 40: "changed40", 50: "changed50", 60: "changed60", 70: "changed70"}),
                source_kind=CorpusVersionSourceKind.USER_EDIT,
                language="es",
                created_by=creator_id,
            )
            ai_heavy = corpus.ingest_text_document(
                creator_id=creator_id,
                document_type=CorpusDocumentType.SCRIPT,
                title="AI heavy",
                content=_make_words(100),
                language="es",
                source_kind=CorpusVersionSourceKind.AI_GENERATED,
                source_asset_type=CorpusSourceType.IMPORTED_TEXT,
                source_asset_original_name="heavy.txt",
            )
            ai_heavy_edit = corpus.append_document_version(
                document_id=ai_heavy.document.id,
                creator_id=creator_id,
                content=_make_words(100, {index: f"heavy{index}" for index in range(1, 81)}),
                source_kind=CorpusVersionSourceKind.USER_EDIT,
                language="es",
                created_by=creator_id,
            )

            snapshot = fixture.voice_service.build_snapshot({"creator_id": creator_id, "include_historical_versions": True})
            selected = {item.version_id: item for item in snapshot.evidence_items if item.evidence_type == CreatorVoiceEvidenceType.CREATOR_EDITED}

            self.assertIn(ai_minimal_edit.version.id, selected)
            self.assertIn(ai_heavy_edit.version.id, selected)
            self.assertLess(selected[ai_minimal_edit.version.id].evidence_weight, selected[ai_heavy_edit.version.id].evidence_weight)
            self.assertIn(CreatorVoiceExclusionReason.AI_GENERATED.value, {item.reason for item in snapshot.excluded_candidates})
            self.assertNotIn(CreatorVoiceExclusionReason.HISTORICAL_VERSION.value, {item.reason for item in snapshot.excluded_candidates})

    def test_project_scope_isolated_and_global_supplement_is_opt_in(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = _build_voice_fixture(temp_dir)
            corpus = fixture.corpus
            creator_id = fixture.creator_a.id
            project_doc = corpus.ingest_text_document(
                creator_id=creator_id,
                project_id=fixture.project_a.id,
                document_type=CorpusDocumentType.SCRIPT,
                title="Project script",
                content="contenido del proyecto",
                language="es",
                source_kind=CorpusVersionSourceKind.ORIGINAL,
                source_asset_type=CorpusSourceType.IMPORTED_TEXT,
                source_asset_original_name="project.txt",
            )
            global_doc = corpus.ingest_text_document(
                creator_id=creator_id,
                document_type=CorpusDocumentType.SCRIPT,
                title="Global script",
                content="contenido global",
                language="es",
                source_kind=CorpusVersionSourceKind.ORIGINAL,
                source_asset_type=CorpusSourceType.IMPORTED_TEXT,
                source_asset_original_name="global.txt",
            )

            project_snapshot = fixture.voice_service.build_snapshot({"creator_id": creator_id, "project_id": fixture.project_a.id})
            project_ids = {item.project_id for item in project_snapshot.evidence_items if item.evidence_type != CreatorVoiceEvidenceType.CONFIRMED_PREFERENCE}

            self.assertEqual(project_ids, {fixture.project_a.id})
            self.assertIn(CreatorVoiceExclusionReason.WRONG_SCOPE.value, {item.reason for item in project_snapshot.excluded_candidates})
            self.assertNotIn(global_doc.document.id, {item.document_id for item in project_snapshot.evidence_items})
            self.assertIn(project_doc.document.id, {item.document_id for item in project_snapshot.evidence_items})

    def test_language_scope_preserves_language_distribution_without_translation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = _build_voice_fixture(temp_dir)
            corpus = fixture.corpus
            creator_id = fixture.creator_a.id
            spanish = corpus.ingest_text_document(
                creator_id=creator_id,
                document_type=CorpusDocumentType.SCRIPT,
                title="Español",
                content="hola mundo creador",
                language="es",
                source_kind=CorpusVersionSourceKind.ORIGINAL,
                source_asset_type=CorpusSourceType.IMPORTED_TEXT,
                source_asset_original_name="es.txt",
            )
            english = corpus.ingest_text_document(
                creator_id=creator_id,
                document_type=CorpusDocumentType.SCRIPT,
                title="English",
                content="hello world creator",
                language="en",
                source_kind=CorpusVersionSourceKind.ORIGINAL,
                source_asset_type=CorpusSourceType.IMPORTED_TEXT,
                source_asset_original_name="en.txt",
            )

            snapshot = fixture.voice_service.build_snapshot({"creator_id": creator_id, "language": "es"})
            languages = {item.language for item in snapshot.evidence_items if item.language}

            self.assertEqual(languages, {"es"})
            self.assertIn(CreatorVoiceExclusionReason.WRONG_LANGUAGE.value, {item.reason for item in snapshot.excluded_candidates})
            self.assertIn(spanish.document.id, {item.document_id for item in snapshot.evidence_items})
            self.assertNotIn(english.document.id, {item.document_id for item in snapshot.evidence_items})

    def test_creator_b_cannot_pollute_creator_a_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = _build_voice_fixture(temp_dir)
            corpus = fixture.corpus
            creator_a = fixture.creator_a.id
            creator_b = fixture.creator_b.id
            a_doc = corpus.ingest_text_document(
                creator_id=creator_a,
                document_type=CorpusDocumentType.SCRIPT,
                title="Creator A",
                content="contenido A",
                language="es",
                source_kind=CorpusVersionSourceKind.ORIGINAL,
                source_asset_type=CorpusSourceType.IMPORTED_TEXT,
                source_asset_original_name="a.txt",
            )
            b_doc = corpus.ingest_text_document(
                creator_id=creator_b,
                document_type=CorpusDocumentType.SCRIPT,
                title="Creator B",
                content="contenido B",
                language="es",
                source_kind=CorpusVersionSourceKind.ORIGINAL,
                source_asset_type=CorpusSourceType.IMPORTED_TEXT,
                source_asset_original_name="b.txt",
            )

            snapshot = fixture.voice_service.build_snapshot({"creator_id": creator_a})

            self.assertIn(a_doc.document.id, {item.document_id for item in snapshot.evidence_items})
            self.assertNotIn(b_doc.document.id, {item.document_id for item in snapshot.evidence_items})
            self.assertTrue(all(item.creator_id == creator_a for item in snapshot.evidence_items))
            self.assertTrue(all(item.creator_id == creator_a for item in snapshot.excluded_candidates))

    def test_duplicate_content_and_snapshot_rebuild_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = _build_voice_fixture(temp_dir)
            corpus = fixture.corpus
            creator_id = fixture.creator_a.id
            first = corpus.ingest_text_document(
                creator_id=creator_id,
                document_type=CorpusDocumentType.SCRIPT,
                title="First",
                content="repetido repetido repetido",
                language="es",
                source_kind=CorpusVersionSourceKind.ORIGINAL,
                source_asset_type=CorpusSourceType.IMPORTED_TEXT,
                source_asset_original_name="first.txt",
            )
            second = corpus.ingest_text_document(
                creator_id=creator_id,
                document_type=CorpusDocumentType.NOTE,
                title="Second",
                content="repetido repetido repetido",
                language="es",
                source_kind=CorpusVersionSourceKind.ORIGINAL,
                source_asset_type=CorpusSourceType.IMPORTED_TEXT,
                source_asset_original_name="second.txt",
            )

            snapshot_a = fixture.voice_service.build_snapshot({"creator_id": creator_id})
            snapshot_b = fixture.voice_service.build_snapshot({"creator_id": creator_id})

            self.assertEqual(snapshot_a.content_fingerprint, snapshot_b.content_fingerprint)
            self.assertIn(CreatorVoiceExclusionReason.DUPLICATE.value, {item.reason for item in snapshot_a.excluded_candidates})
            self.assertLessEqual(len({item.content_hash for item in snapshot_a.evidence_items}), len(snapshot_a.evidence_items))
            selected_documents = {item.document_id for item in snapshot_a.evidence_items}
            self.assertEqual(len(selected_documents & {first.document.id, second.document.id}), 1)
            self.assertNotEqual(first.document.id in selected_documents, second.document.id in selected_documents)

    def test_cli_json_surface_is_safe(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["voice", "evidence-snapshot", "--creator-id", "creator-a", "--json"])
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = _build_voice_fixture(temp_dir)
            stdout = io.StringIO()
            stderr = io.StringIO()
            exit_code = handle_voice_command(args, service=fixture.voice_service, stdout=stdout, stderr=stderr)
        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertIn("summary", payload)
        self.assertIn("snapshot", payload)


if __name__ == "__main__":
    unittest.main()
