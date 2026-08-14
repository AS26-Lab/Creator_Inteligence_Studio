from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from types import SimpleNamespace

from creator_intelligence_studio.application.services.catalog_service import build_catalog_service
from creator_intelligence_studio.application.services.content_brief_service import build_content_brief_service
from creator_intelligence_studio.application.services.creator_context_assembly_service import build_creator_context_assembly_service
from creator_intelligence_studio.application.services.creator_context_policy import build_default_creator_context_policy_registry
from creator_intelligence_studio.application.services.creator_corpus_retrieval_service import CreatorCorpusRetrievalService
from creator_intelligence_studio.application.services.creator_voice_guidance_service import build_creator_voice_guidance_service
from creator_intelligence_studio.application.services.creator_voice_profile_service import build_creator_voice_profile_service
from creator_intelligence_studio.application.services.creator_voice_workflow_application_service import build_creator_voice_workflow_application_service
from creator_intelligence_studio.application.services.production_preparation_service import build_production_preparation_service
from creator_intelligence_studio.application.services.strategic_planning_service import build_strategic_planning_service
from creator_intelligence_studio.domain.creator_corpus import CorpusDocumentType, CorpusSourceType, CorpusVersionSourceKind
from creator_intelligence_studio.domain.creator_preferences.value_objects import CreatorPreferenceScope
from creator_intelligence_studio.infrastructure.persistence.sqlite_content_brief_repository import SQLiteContentBriefRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_creator_corpus_repository import SQLiteCreatorCorpusRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_creator_preference_repository import SQLiteCreatorPreferenceRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_production_preparation_repository import SQLiteProductionPreparationRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_strategic_planning_repository import SQLiteStrategicPlanningRepository

from tests.test_creator_context_policies import _SnapshotService, _RecommendationService
from tests.test_creator_voice_evidence import _build_voice_fixture, _make_preference, _make_words


def _make_sentence_text(lengths: list[int]) -> str:
    return " ".join(f"{_make_words(length)}." for length in lengths)


def _seed_voice_profile(fixture, *, creator_id: str, project_id: str | None = None, language: str = "es") -> None:
    fixture.corpus.ingest_text_document(
        creator_id=creator_id,
        project_id=project_id,
        document_type=CorpusDocumentType.SCRIPT,
        title="Original script 1",
        content=_make_sentence_text([24, 23, 22, 24]),
        language=language,
        source_kind=CorpusVersionSourceKind.ORIGINAL,
        source_asset_type=CorpusSourceType.IMPORTED_TEXT,
        source_asset_original_name="script-1.txt",
    )
    fixture.corpus.ingest_text_document(
        creator_id=creator_id,
        project_id=project_id,
        document_type=CorpusDocumentType.SCRIPT,
        title="Original script 2",
        content=_make_sentence_text([22, 23, 21, 22]),
        language=language,
        source_kind=CorpusVersionSourceKind.ORIGINAL,
        source_asset_type=CorpusSourceType.IMPORTED_TEXT,
        source_asset_original_name="script-2.txt",
    )
    fixture.corpus.ingest_text_document(
        creator_id=creator_id,
        project_id=project_id,
        document_type=CorpusDocumentType.TRANSCRIPT,
        title="Reviewed speech",
        content=_make_sentence_text([18, 19, 18, 20]),
        language=language,
        source_kind=CorpusVersionSourceKind.TRANSCRIPTION,
        source_asset_type=CorpusSourceType.TRANSCRIPT,
        source_asset_original_name="speech.txt",
        segments=[
            {"sequence": 0, "start_seconds": 0.0, "end_seconds": 1.0, "text": _make_words(18), "confidence": 0.96, "review_state": "transcribed"},
            {"sequence": 1, "start_seconds": 1.0, "end_seconds": 2.0, "text": _make_words(19), "confidence": 0.97, "review_state": "transcribed"},
            {"sequence": 2, "start_seconds": 2.0, "end_seconds": 3.0, "text": _make_words(18), "confidence": 0.96, "review_state": "transcribed"},
            {"sequence": 3, "start_seconds": 3.0, "end_seconds": 4.0, "text": _make_words(20), "confidence": 0.98, "review_state": "transcribed"},
        ],
    )


def _build_workflow_fixture(temp_dir: str):
    voice_fixture = _build_voice_fixture(temp_dir)
    _seed_voice_profile(voice_fixture, creator_id=voice_fixture.creator_a.id, project_id=voice_fixture.project_a.id)
    catalog = build_catalog_service(
        settings=voice_fixture.settings,
        paths=voice_fixture.paths,
        database=voice_fixture.database,
    )
    retrieval = CreatorCorpusRetrievalService(repository=SQLiteCreatorCorpusRepository(voice_fixture.database))
    assembly = build_creator_context_assembly_service(retrieval_service=retrieval)
    policies = build_default_creator_context_policy_registry()
    profile_service = build_creator_voice_profile_service(logger=voice_fixture.voice_service.logger)
    guidance_service = build_creator_voice_guidance_service(logger=voice_fixture.voice_service.logger)
    voice_application_service = build_creator_voice_workflow_application_service(
        evidence_service=voice_fixture.voice_service,
        profile_service=profile_service,
        guidance_service=guidance_service,
        logger=voice_fixture.voice_service.logger,
    )
    snapshot_service = _SnapshotService("snapshot")
    recommendation_service = _RecommendationService()
    brief_service = build_content_brief_service(
        settings=voice_fixture.settings,
        paths=voice_fixture.paths,
        repository=SQLiteContentBriefRepository(voice_fixture.database),
        planning_service=SimpleNamespace(),
        recommendation_service=recommendation_service,
        experiment_service=SimpleNamespace(),
        content_library_service=catalog,
        creator_memory_service=snapshot_service,
        creator_language_service=snapshot_service,
        creator_context_assembly_service=assembly,
        creator_preference_application_service=None,
        creator_voice_workflow_application_service=voice_application_service,
        creator_context_policy_registry=policies,
        audience_service=snapshot_service,
        analytics_service=SimpleNamespace(),
        analytics_lab_service=SimpleNamespace(),
        market_service=SimpleNamespace(),
        platform_service=snapshot_service,
        packaging_service=snapshot_service,
    )
    production_off_service = build_production_preparation_service(
        settings=voice_fixture.settings,
        paths=voice_fixture.paths,
        repository=SQLiteProductionPreparationRepository(voice_fixture.database),
        brief_service=brief_service,
        planning_service=SimpleNamespace(),
        recommendation_service=SimpleNamespace(),
        experiment_service=SimpleNamespace(),
        content_library_service=catalog,
        creator_memory_service=snapshot_service,
        creator_language_service=snapshot_service,
        creator_context_assembly_service=assembly,
        creator_preference_application_service=None,
        creator_voice_workflow_application_service=voice_application_service,
        creator_context_policy_registry=policies,
        audience_service=snapshot_service,
        platform_service=snapshot_service,
        packaging_service=snapshot_service,
        preferences={"creator_voice_guidance_enabled": False},
    )
    production_on_service = build_production_preparation_service(
        settings=voice_fixture.settings,
        paths=voice_fixture.paths,
        repository=SQLiteProductionPreparationRepository(voice_fixture.database),
        brief_service=brief_service,
        planning_service=SimpleNamespace(),
        recommendation_service=SimpleNamespace(),
        experiment_service=SimpleNamespace(),
        content_library_service=catalog,
        creator_memory_service=snapshot_service,
        creator_language_service=snapshot_service,
        creator_context_assembly_service=assembly,
        creator_preference_application_service=None,
        creator_voice_workflow_application_service=voice_application_service,
        creator_context_policy_registry=policies,
        audience_service=snapshot_service,
        platform_service=snapshot_service,
        packaging_service=snapshot_service,
        preferences={"creator_voice_guidance_enabled": True},
    )
    planning_service = build_strategic_planning_service(
        settings=voice_fixture.settings,
        paths=voice_fixture.paths,
        repository=SQLiteStrategicPlanningRepository(voice_fixture.database),
        recommendation_service=recommendation_service,
        creator_memory_service=snapshot_service,
        creator_language_service=snapshot_service,
        creator_context_assembly_service=assembly,
        creator_voice_workflow_application_service=voice_application_service,
        creator_context_policy_registry=policies,
        audience_service=snapshot_service,
        analytics_service=SimpleNamespace(),
        analytics_lab_service=snapshot_service,
        market_service=snapshot_service,
        experiment_service=snapshot_service,
        content_library_service=catalog,
        platform_service=snapshot_service,
    )
    return SimpleNamespace(
        **voice_fixture.__dict__,
        catalog=catalog,
        retrieval=retrieval,
        assembly=assembly,
        policies=policies,
        profile_service=profile_service,
        guidance_service=guidance_service,
        voice_application_service=voice_application_service,
        brief_service=brief_service,
        production_off_service=production_off_service,
        production_on_service=production_on_service,
        planning_service=planning_service,
    )


class CreatorVoiceWorkflowApplicationTests(unittest.TestCase):
    def test_shadow_integration_preserves_brief_and_planning_prompts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = _build_workflow_fixture(temp_dir)
            brief_payload = json.loads(
                fixture.brief_service.create_context_snapshot(
                    fixture.creator_a.id,
                    internal_content_id="content-a",
                    use_creator_context=True,
                ).context_json
            )
            planning_payload = json.loads(
                fixture.planning_service.create_context_snapshot(
                    fixture.creator_a.id,
                    use_creator_context=True,
                ).context_json
            )

            self.assertTrue(brief_payload["creator_voice_application_bundle"]["voice_guidance_shadow"])
            self.assertFalse(brief_payload["creator_voice_application_bundle"]["voice_guidance_applied"])
            self.assertEqual(brief_payload["creator_voice_application_bundle"]["application_state"], "shadow")
            self.assertIn("creator_voice_application_context", brief_payload["creator_context_package"])
            self.assertNotIn("CREATOR VOICE GUIDANCE", brief_payload["creator_context_prompt"])

            self.assertTrue(planning_payload["creator_voice_application_bundle"]["voice_guidance_shadow"])
            self.assertFalse(planning_payload["creator_voice_application_bundle"]["voice_guidance_applied"])
            self.assertEqual(planning_payload["creator_voice_application_bundle"]["application_state"], "shadow")
            self.assertIn("creator_voice_application_context", planning_payload["creator_context_package"])
            self.assertNotIn("CREATOR VOICE GUIDANCE", planning_payload["creator_context_prompt"])

    def test_production_preparation_applies_voice_only_when_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = _build_workflow_fixture(temp_dir)
            brief_request = fixture.brief_service.create_request(
                creator_id=fixture.creator_a.id,
                source_type="manual_request",
                source_id="brief-source-a",
            )
            brief = fixture.brief_service.generate_brief(request_id=brief_request.id)
            brief = fixture.brief_service.review_brief(brief.id, decision="approve", reason="ready", reviewer="tester")

            off_payload = json.loads(
                fixture.production_off_service.create_context_snapshot(
                    fixture.creator_a.id,
                    content_brief_id=brief.id,
                    brief_version=int(getattr(brief, "version", 1) or 1),
                    use_creator_context=True,
                ).context_json
            )
            on_payload = json.loads(
                fixture.production_on_service.create_context_snapshot(
                    fixture.creator_a.id,
                    content_brief_id=brief.id,
                    brief_version=int(getattr(brief, "version", 1) or 1),
                    use_creator_context=True,
                ).context_json
            )

            self.assertFalse(off_payload["creator_voice_application_bundle"]["voice_guidance_applied"])
            self.assertTrue(on_payload["creator_voice_application_bundle"]["voice_guidance_applied"])
            self.assertIn("CREATOR VOICE GUIDANCE", on_payload["creator_context_prompt"])
            self.assertNotIn("CREATOR VOICE GUIDANCE", off_payload["creator_context_prompt"])

    def test_fake_provider_e2e_and_frozen_on_off_comparison_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = _build_workflow_fixture(temp_dir)
            brief_request = fixture.brief_service.create_request(
                creator_id=fixture.creator_a.id,
                source_type="manual_request",
                source_id="brief-source-a",
            )
            brief = fixture.brief_service.generate_brief(request_id=brief_request.id)
            brief = fixture.brief_service.review_brief(brief.id, decision="approve", reason="ready", reviewer="tester")

            on_snapshot_1 = fixture.production_on_service.create_context_snapshot(
                fixture.creator_a.id,
                content_brief_id=brief.id,
                brief_version=int(getattr(brief, "version", 1) or 1),
                use_creator_context=True,
            )
            on_snapshot_2 = fixture.production_on_service.create_context_snapshot(
                fixture.creator_a.id,
                content_brief_id=brief.id,
                brief_version=int(getattr(brief, "version", 1) or 1),
                use_creator_context=True,
            )
            off_snapshot = fixture.production_off_service.create_context_snapshot(
                fixture.creator_a.id,
                content_brief_id=brief.id,
                brief_version=int(getattr(brief, "version", 1) or 1),
                use_creator_context=True,
            )

            on_prompt = json.loads(on_snapshot_1.context_json)["creator_context_prompt"]
            off_prompt = json.loads(off_snapshot.context_json)["creator_context_prompt"]
            fake_provider_hash_on = hashlib.sha256(on_prompt.encode("utf-8")).hexdigest()
            fake_provider_hash_off = hashlib.sha256(off_prompt.encode("utf-8")).hexdigest()

            self.assertEqual(
                json.loads(on_snapshot_1.context_json)["creator_voice_application_bundle"]["bundle_fingerprint"],
                json.loads(on_snapshot_2.context_json)["creator_voice_application_bundle"]["bundle_fingerprint"],
            )
            self.assertEqual(on_prompt, json.loads(on_snapshot_2.context_json)["creator_context_prompt"])
            self.assertNotEqual(fake_provider_hash_on, fake_provider_hash_off)
            self.assertIn("CREATOR VOICE GUIDANCE", on_prompt)
            self.assertNotIn("CREATOR VOICE GUIDANCE", off_prompt)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
