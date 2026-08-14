from __future__ import annotations

import io
import tempfile
import unittest
from types import SimpleNamespace
from uuid import uuid4

from creator_intelligence_studio.application.services.creator_voice_guidance_service import build_creator_voice_guidance_service
from creator_intelligence_studio.application.services.creator_voice_profile_service import build_creator_voice_profile_service
from creator_intelligence_studio.domain.creator_corpus import CorpusDocumentType, CorpusSourceType, CorpusVersionSourceKind
from creator_intelligence_studio.domain.creator_voice import (
    CreatorVoiceGuidanceOmissionReason,
    CreatorVoiceGuidanceState,
    CreatorVoiceProfileStatus,
)
from creator_intelligence_studio.domain.errors import DomainError
from creator_intelligence_studio.presentation.cli.cli import build_parser
from creator_intelligence_studio.presentation.cli.voice_cli import handle_voice_command
from creator_intelligence_studio.domain.creator_preferences.value_objects import CreatorPreferenceScope

from tests.test_creator_voice_evidence import _build_voice_fixture, _make_preference, _make_words


def _voice_fixture(temp_dir: str):
    evidence_fixture = _build_voice_fixture(temp_dir)
    profile_service = build_creator_voice_profile_service(logger=evidence_fixture.voice_service.logger)
    guidance_service = build_creator_voice_guidance_service(logger=evidence_fixture.voice_service.logger)
    return SimpleNamespace(
        **evidence_fixture.__dict__,
        profile_service=profile_service,
        guidance_service=guidance_service,
    )


def _make_sentence_text(lengths: list[int]) -> str:
    return " ".join(f"{_make_words(length)}." for length in lengths)


def _seed_profile(
    fixture,
    *,
    creator_id: str,
    language: str = "es",
    project_id: str | None = None,
    workflow_type: str | None = None,
    script_docs: int = 5,
    script_sentence_words: int = 12,
    spoken_sentence_words: int | None = 20,
    spoken_docs: int = 1,
    include_spoken: bool = True,
    preference_direction: str | None = None,
):
    if preference_direction is not None:
        fixture.preference_repo.upsert_confirmed_preference(
            _make_preference(
                creator_id=creator_id,
                preference_key="voice.length.global",
                value_json={"preference_type": "content_length_preference", "direction": preference_direction},
                scope=CreatorPreferenceScope.CREATOR_GLOBAL,
            )
        )
    for index in range(script_docs):
        sentence_words = script_sentence_words + index
        fixture.corpus.ingest_text_document(
            creator_id=creator_id,
            project_id=project_id,
            document_type=CorpusDocumentType.SCRIPT,
            title=f"Script {index + 1}",
            content=_make_sentence_text([sentence_words, sentence_words, sentence_words, sentence_words]),
            language=language,
            source_kind=CorpusVersionSourceKind.ORIGINAL,
            source_asset_type=CorpusSourceType.IMPORTED_TEXT,
            source_asset_original_name=f"script-{index + 1}.txt",
        )
    if include_spoken and spoken_sentence_words is not None:
        for index in range(spoken_docs):
            spoken_lengths = [spoken_sentence_words + index, spoken_sentence_words + index, spoken_sentence_words + index, spoken_sentence_words + index]
            spoken_content = _make_sentence_text(spoken_lengths)
            fixture.corpus.ingest_text_document(
                creator_id=creator_id,
                project_id=project_id,
                document_type=CorpusDocumentType.TRANSCRIPT,
                title=f"Speech {index + 1}",
                content=spoken_content,
                language=language,
                source_kind=CorpusVersionSourceKind.TRANSCRIPTION,
                source_asset_type=CorpusSourceType.TRANSCRIPT,
                source_asset_original_name=f"speech-{index + 1}.txt",
                segments=[
                    {
                        "sequence": idx,
                        "start_seconds": float(idx),
                        "end_seconds": float(idx + 1),
                        "text": sentence,
                        "confidence": 0.96,
                        "review_state": "transcribed",
                    }
                    for idx, sentence in enumerate(spoken_content.split(".")[:-1])
                ],
            )
    snapshot_request = {
        "creator_id": creator_id,
        "project_id": project_id,
        "workflow_type": workflow_type,
        "language": language,
        "include_historical_versions": False,
        "include_creator_global_when_project_scope": True,
        "include_creator_global_when_workflow_scope": True,
        "max_items": 24,
        "max_items_per_source": 3,
        "max_items_per_type": 8,
    }
    snapshot = fixture.voice_service.build_snapshot(snapshot_request)
    profile = fixture.profile_service.build_profile(snapshot)
    return SimpleNamespace(snapshot=snapshot, profile=profile)


class CreatorVoiceGuidanceTests(unittest.TestCase):
    def test_ready_profile_guidance_is_deterministic_and_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = _voice_fixture(temp_dir)
            seeded = _seed_profile(fixture, creator_id=fixture.creator_a.id, script_sentence_words=24, spoken_sentence_words=20, spoken_docs=2)
            request = {
                "creator_id": fixture.creator_a.id,
                "workflow_type": "script_writing",
                "language": "es",
                "profile": seeded.profile,
                "enabled": True,
                "max_items": 4,
                "max_characters": 320,
            }
            bundle_a = fixture.guidance_service.build_guidance(request)
            bundle_b = fixture.guidance_service.build_guidance(request)

            self.assertEqual(seeded.profile.status, CreatorVoiceProfileStatus.READY)
            self.assertEqual(bundle_a.guidance_state, CreatorVoiceGuidanceState.READY)
            self.assertEqual(bundle_a.bundle_fingerprint, bundle_b.bundle_fingerprint)
            self.assertEqual(bundle_a.rendered_guidance, bundle_b.rendered_guidance)
            self.assertLessEqual(len(bundle_a.guidance_items), 4)
            self.assertLessEqual(len(bundle_a.rendered_guidance), 320)
            self.assertTrue(bundle_a.guidance_items)
            self.assertTrue(all(item.creator_id == fixture.creator_a.id for item in bundle_a.guidance_items))

    def test_insufficient_and_disabled_profiles_emit_no_behavioral_guidance(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = _voice_fixture(temp_dir)
            seeded = _seed_profile(fixture, creator_id=fixture.creator_a.id, script_docs=1, script_sentence_words=4, include_spoken=False)
            insufficient = fixture.guidance_service.build_guidance(
                {
                    "creator_id": fixture.creator_a.id,
                    "workflow_type": "script_writing",
                    "language": "es",
                    "profile": seeded.profile,
                }
            )
            off = fixture.guidance_service.build_guidance(
                {
                    "creator_id": fixture.creator_a.id,
                    "workflow_type": "script_writing",
                    "language": "es",
                    "profile": seeded.profile,
                    "enabled": False,
                }
            )

            self.assertEqual(seeded.profile.status, CreatorVoiceProfileStatus.INSUFFICIENT_EVIDENCE)
            self.assertEqual(insufficient.guidance_state, CreatorVoiceGuidanceState.INSUFFICIENT_PROFILE)
            self.assertEqual(len(insufficient.guidance_items), 0)
            self.assertEqual(insufficient.omitted_items[0].reason, CreatorVoiceGuidanceOmissionReason.INSUFFICIENT_PROFILE)
            self.assertEqual(off.guidance_state, CreatorVoiceGuidanceState.DISABLED)
            self.assertEqual(len(off.guidance_items), 0)
            self.assertEqual(off.omitted_items[0].reason, CreatorVoiceGuidanceOmissionReason.DISABLED)

    def test_confirmed_preference_overrides_length_guidance(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = _voice_fixture(temp_dir)
            seeded = _seed_profile(
                fixture,
                creator_id=fixture.creator_a.id,
                script_sentence_words=24,
                spoken_sentence_words=20,
                spoken_docs=2,
                preference_direction="shorter",
            )
            bundle = fixture.guidance_service.build_guidance(
                {
                    "creator_id": fixture.creator_a.id,
                    "workflow_type": "script_writing",
                    "language": "es",
                    "profile": seeded.profile,
                }
            )

            self.assertTrue(any(item.reason == CreatorVoiceGuidanceOmissionReason.PREFERENCE_OVERRIDE for item in bundle.omitted_items))
            self.assertTrue(all(item.guidance_key != "intro_length_tendency" for item in bundle.guidance_items))
            self.assertTrue(any(conflict.override_type == "preference_override" for conflict in bundle.conflicts))

    def test_current_user_and_project_instructions_override_voice(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = _voice_fixture(temp_dir)
            seeded = _seed_profile(fixture, creator_id=fixture.creator_a.id, script_docs=17, script_sentence_words=3, include_spoken=False)
            user_bundle = fixture.guidance_service.build_guidance(
                {
                    "creator_id": fixture.creator_a.id,
                    "workflow_type": "script_writing",
                    "language": "es",
                    "profile": seeded.profile,
                    "current_user_instruction": "Hazlo largo y cinematografico.",
                }
            )
            project_bundle = fixture.guidance_service.build_guidance(
                {
                    "creator_id": fixture.creator_a.id,
                    "workflow_type": "script_writing",
                    "language": "es",
                    "profile": seeded.profile,
                    "project_instruction": "Quiero una apertura larga y detallada.",
                }
            )

            self.assertTrue(any(item.reason == CreatorVoiceGuidanceOmissionReason.USER_OVERRIDE for item in user_bundle.omitted_items))
            self.assertTrue(any(item.reason == CreatorVoiceGuidanceOmissionReason.PROJECT_OVERRIDE for item in project_bundle.omitted_items))
            self.assertTrue(all(item.guidance_key != "intro_length_tendency" for item in user_bundle.guidance_items))
            self.assertTrue(all(item.guidance_key != "intro_length_tendency" for item in project_bundle.guidance_items))

    def test_language_and_scope_are_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = _voice_fixture(temp_dir)
            seeded = _seed_profile(
                fixture,
                creator_id=fixture.creator_a.id,
                language="es",
                project_id=fixture.project_a.id,
                workflow_type="script_writing",
                script_sentence_words=24,
                spoken_sentence_words=20,
                spoken_docs=2,
            )
            wrong_language = fixture.guidance_service.build_guidance(
                {
                    "creator_id": fixture.creator_a.id,
                    "project_id": fixture.project_a.id,
                    "workflow_type": "script_writing",
                    "language": "en",
                    "profile": seeded.profile,
                }
            )
            wrong_scope = fixture.guidance_service.build_guidance(
                {
                    "creator_id": fixture.creator_a.id,
                    "project_id": fixture.project_b.id,
                    "workflow_type": "script_writing",
                    "language": "es",
                    "profile": seeded.profile,
                }
            )

            self.assertEqual(wrong_language.guidance_state, CreatorVoiceGuidanceState.INSUFFICIENT_PROFILE)
            self.assertEqual(wrong_language.omitted_items[0].reason, CreatorVoiceGuidanceOmissionReason.WRONG_LANGUAGE)
            self.assertEqual(wrong_scope.guidance_state, CreatorVoiceGuidanceState.INSUFFICIENT_PROFILE)
            self.assertEqual(wrong_scope.omitted_items[0].reason, CreatorVoiceGuidanceOmissionReason.WRONG_SCOPE)

    def test_written_and_spoken_mode_stay_separate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = _voice_fixture(temp_dir)
            written_seed = _seed_profile(
                fixture,
                creator_id=fixture.creator_a.id,
                script_sentence_words=14,
                include_spoken=False,
            )
            spoken_seed = _seed_profile(
                fixture,
                creator_id=fixture.creator_a.id,
                script_docs=0,
                spoken_sentence_words=22,
                spoken_docs=5,
            )
            written_bundle = fixture.guidance_service.build_guidance(
                {
                    "creator_id": fixture.creator_a.id,
                    "workflow_type": "script_writing",
                    "language": "es",
                    "profile": written_seed.profile,
                }
            )
            spoken_bundle = fixture.guidance_service.build_guidance(
                {
                    "creator_id": fixture.creator_a.id,
                    "workflow_type": "spoken_content",
                    "language": "es",
                    "profile": spoken_seed.profile,
                }
            )

            self.assertTrue(all(item.category.value != "spoken" for item in written_bundle.guidance_items))
            self.assertTrue(any(item.category.value == "spoken" for item in spoken_bundle.guidance_items))

    def test_budget_and_ordering_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = _voice_fixture(temp_dir)
            seeded = _seed_profile(fixture, creator_id=fixture.creator_a.id, script_sentence_words=24, spoken_sentence_words=20, spoken_docs=2)
            bundle = fixture.guidance_service.build_guidance(
                {
                    "creator_id": fixture.creator_a.id,
                    "workflow_type": "script_writing",
                    "language": "es",
                    "profile": seeded.profile,
                    "max_items": 1,
                    "max_characters": 120,
                }
            )

            self.assertEqual(len(bundle.guidance_items), 1)
            self.assertEqual(bundle.guidance_items[0].guidance_key, "intro_length_tendency")
            self.assertTrue(any(item.reason == CreatorVoiceGuidanceOmissionReason.TOO_MUCH_GUIDANCE for item in bundle.omitted_items))

    def test_creator_isolation_rejects_mismatched_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = _voice_fixture(temp_dir)
            creator_a = _seed_profile(fixture, creator_id=fixture.creator_a.id, script_sentence_words=24, spoken_sentence_words=20, spoken_docs=2).profile
            creator_b = _seed_profile(fixture, creator_id=fixture.creator_b.id, script_sentence_words=24, spoken_sentence_words=20, spoken_docs=2).profile

            with self.assertRaises(DomainError):
                fixture.guidance_service.build_guidance(
                    {
                        "creator_id": fixture.creator_a.id,
                        "workflow_type": "script_writing",
                        "language": "es",
                        "profile": creator_b,
                    }
                )
            bundle = fixture.guidance_service.build_guidance(
                {
                    "creator_id": fixture.creator_b.id,
                    "workflow_type": "script_writing",
                    "language": "es",
                    "profile": creator_b,
                }
            )
            self.assertTrue(bundle.guidance_items or bundle.omitted_items)

    def test_guidance_preview_cli_works_in_json_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = _voice_fixture(temp_dir)
            _seed_profile(fixture, creator_id=fixture.creator_a.id, script_sentence_words=24, spoken_sentence_words=20, spoken_docs=2)
            parser = build_parser()
            args = parser.parse_args(
                [
                    "voice",
                    "guidance-preview",
                    "--creator-id",
                    fixture.creator_a.id,
                    "--workflow-type",
                    "script_writing",
                    "--language",
                    "es",
                    "--json",
                ]
            )
            stdout = io.StringIO()
            stderr = io.StringIO()

            exit_code = handle_voice_command(
                args,
                evidence_service=fixture.voice_service,
                profile_service=fixture.profile_service,
                guidance_service=fixture.guidance_service,
                stdout=stdout,
                stderr=stderr,
            )

            self.assertEqual(exit_code, 0)
            payload = stdout.getvalue().strip()
            self.assertTrue(payload)
            self.assertIn("guidance_state", payload)
            self.assertEqual(stderr.getvalue(), "")
