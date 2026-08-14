from __future__ import annotations

import io
import json
import re
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from creator_intelligence_studio.application.services.creator_voice_profile_service import build_creator_voice_profile_service
from creator_intelligence_studio.domain.creator_corpus import CorpusDocumentType, CorpusSourceType, CorpusVersionSourceKind
from creator_intelligence_studio.domain.creator_voice import CreatorVoiceProfileStatus
from creator_intelligence_studio.presentation.cli.cli import build_parser
from creator_intelligence_studio.presentation.cli.voice_cli import handle_voice_command

from tests.test_creator_voice_evidence import _build_voice_fixture, _make_preference
from creator_intelligence_studio.domain.creator_preferences.value_objects import CreatorPreferenceScope


def _make_sentence_text(sentences: list[str]) -> str:
    return " ".join(sentence.rstrip(".!?") + "." for sentence in sentences)


def _profile_fixture(temp_dir: str):
    evidence_fixture = _build_voice_fixture(temp_dir)
    profile_service = build_creator_voice_profile_service(logger=evidence_fixture.voice_service.logger)
    return SimpleNamespace(
        **evidence_fixture.__dict__,
        profile_service=profile_service,
    )


def _feature_map(profile):
    return {feature.feature_key: feature for section in profile.sections for feature in section.features}


class CreatorVoiceProfileTests(unittest.TestCase):
    def test_profile_from_valid_snapshot_is_ready_and_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = _profile_fixture(temp_dir)
            corpus = fixture.corpus
            creator_id = fixture.creator_a.id
            fixture.preference_repo.upsert_confirmed_preference(
                _make_preference(
                    creator_id=creator_id,
                    preference_key="voice.shorter.global",
                    value_json={"preference_type": "content_length_preference", "direction": "shorter"},
                    scope=CreatorPreferenceScope.CREATOR_GLOBAL,
                )
            )
            corpus.ingest_text_document(
                creator_id=creator_id,
                document_type=CorpusDocumentType.SCRIPT,
                title="Original one",
                content=_make_sentence_text([
                    "yo explico el paso uno con calma y con contexto suficiente para seguir el hilo",
                    "tu sigues el orden sin perder la referencia y yo mantengo la claridad",
                    "yo cierro con una idea clara y una salida concreta para continuar",
                    "tu puedes volver al punto principal sin perder el ritmo general",
                    "yo dejo una conclusion estable y facil de recordar",
                ]),
                language="es",
                source_kind=CorpusVersionSourceKind.ORIGINAL,
                source_asset_type=CorpusSourceType.IMPORTED_TEXT,
                source_asset_original_name="original1.txt",
            )
            corpus.ingest_text_document(
                creator_id=creator_id,
                document_type=CorpusDocumentType.SCRIPT,
                title="Original two",
                content=_make_sentence_text([
                    "yo cuento una historia breve pero con suficiente detalle para que tenga sentido",
                    "tu entiendes el punto rapido y yo mantengo el enfoque en la idea central",
                    "seguimos con ritmo estable y un tono constante",
                    "yo repito la parte importante para reforzarla",
                    "tu puedes ver la estructura sin esfuerzo",
                ]),
                language="es",
                source_kind=CorpusVersionSourceKind.ORIGINAL,
                source_asset_type=CorpusSourceType.IMPORTED_TEXT,
                source_asset_original_name="original2.txt",
            )
            corpus.ingest_text_document(
                creator_id=creator_id,
                document_type=CorpusDocumentType.SCRIPT,
                title="Original three",
                content=_make_sentence_text([
                    "yo organizo la idea en bloques claros y faciles de seguir",
                    "tu notas el orden y la secuencia sin perder el detalle",
                    "yo doy contexto adicional para sostener la explicación",
                    "tu puedes anticipar el siguiente punto con facilidad",
                    "yo termino con una frase que cierra bien la sección",
                ]),
                language="es",
                source_kind=CorpusVersionSourceKind.ORIGINAL,
                source_asset_type=CorpusSourceType.IMPORTED_TEXT,
                source_asset_original_name="original3.txt",
            )
            ai_doc = corpus.ingest_text_document(
                creator_id=creator_id,
                document_type=CorpusDocumentType.SCRIPT,
                title="AI base",
                content=_make_sentence_text([
                    "esto era un borrador largo con muchas palabras",
                    "tu lo editas y yo lo convierto en una version mejor",
                ]),
                language="es",
                source_kind=CorpusVersionSourceKind.AI_GENERATED,
                source_asset_type=CorpusSourceType.IMPORTED_TEXT,
                source_asset_original_name="ai.txt",
            )
            corpus.append_document_version(
                document_id=ai_doc.document.id,
                creator_id=creator_id,
                content=_make_sentence_text([
                    "esto fue revisado y ahora tiene una forma mas clara",
                    "yo sigo hablando con un tono estable y directo",
                ]),
                source_kind=CorpusVersionSourceKind.USER_EDIT,
                language="es",
                created_by=creator_id,
            )
            corpus.ingest_text_document(
                creator_id=creator_id,
                document_type=CorpusDocumentType.TRANSCRIPT,
                title="Speech one",
                content=_make_sentence_text([
                    "yo eh explico el contexto con calma y con un ejemplo sencillo",
                    "tu preguntas y yo respondo sin prisa y con un poco mas de detalle",
                    "bueno seguimos hasta cerrar la idea de manera ordenada",
                    "yo repito el punto clave para que quede claro",
                ]),
                language="es",
                source_kind=CorpusVersionSourceKind.TRANSCRIPTION,
                source_asset_type=CorpusSourceType.TRANSCRIPT,
                source_asset_original_name="speech1.txt",
                segments=[
                    {"sequence": 0, "start_seconds": 0.0, "end_seconds": 1.0, "text": "yo eh explico el contexto con calma y con un ejemplo sencillo", "confidence": 0.96, "review_state": "transcribed"},
                    {"sequence": 1, "start_seconds": 1.0, "end_seconds": 2.0, "text": "tu preguntas y yo respondo sin prisa y con un poco mas de detalle", "confidence": 0.95, "review_state": "transcribed"},
                    {"sequence": 2, "start_seconds": 2.0, "end_seconds": 3.0, "text": "bueno seguimos hasta cerrar la idea de manera ordenada", "confidence": 0.97, "review_state": "transcribed"},
                    {"sequence": 3, "start_seconds": 3.0, "end_seconds": 4.0, "text": "yo repito el punto clave para que quede claro", "confidence": 0.96, "review_state": "transcribed"},
                ],
            )
            corpus.ingest_text_document(
                creator_id=creator_id,
                document_type=CorpusDocumentType.TRANSCRIPT,
                title="Speech two",
                content=_make_sentence_text([
                    "yo creo que esto ayuda mucho porque sostiene el mensaje y el ritmo",
                    "tu lo ves y despues lo ajustamos para que quede mejor",
                    "eh terminamos cuando la idea queda bien y no se pierde el enfoque",
                    "yo repito el cierre para que sea facil de recordar",
                ]),
                language="es",
                source_kind=CorpusVersionSourceKind.TRANSCRIPTION,
                source_asset_type=CorpusSourceType.TRANSCRIPT,
                source_asset_original_name="speech2.txt",
                segments=[
                    {"sequence": 0, "start_seconds": 0.0, "end_seconds": 1.0, "text": "yo creo que esto ayuda mucho porque sostiene el mensaje y el ritmo", "confidence": 0.94, "review_state": "transcribed"},
                    {"sequence": 1, "start_seconds": 1.0, "end_seconds": 2.0, "text": "tu lo ves y despues lo ajustamos para que quede mejor", "confidence": 0.95, "review_state": "transcribed"},
                    {"sequence": 2, "start_seconds": 2.0, "end_seconds": 3.0, "text": "eh terminamos cuando la idea queda bien y no se pierde el enfoque", "confidence": 0.96, "review_state": "transcribed"},
                    {"sequence": 3, "start_seconds": 3.0, "end_seconds": 4.0, "text": "yo repito el cierre para que sea facil de recordar", "confidence": 0.96, "review_state": "transcribed"},
                ],
            )

            snapshot = fixture.voice_service.build_snapshot({"creator_id": creator_id})
            profile_a = fixture.profile_service.build_profile(snapshot)
            profile_b = fixture.profile_service.build_profile(snapshot)

            self.assertEqual(profile_a.status, CreatorVoiceProfileStatus.READY)
            self.assertEqual(profile_a.fingerprint, profile_b.fingerprint)
            self.assertEqual(
                {
                    feature.feature_key: feature.to_dict()
                    for section in profile_a.sections
                    for feature in section.features
                },
                {
                    feature.feature_key: feature.to_dict()
                    for section in profile_b.sections
                    for feature in section.features
                },
            )
            self.assertEqual(profile_a.summary, profile_b.summary)
            self.assertGreaterEqual(profile_a.evidence_count, 5)
            self.assertIn("Perfil de voz", profile_a.summary)
            self.assertTrue(profile_a.structured_preferences)
            self.assertFalse(profile_a.structured_preferences[0].conflict)
            self.assertIn("typical_word_count", _feature_map(profile_a))

    def test_insufficient_evidence_and_readiness_threshold_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = _profile_fixture(temp_dir)
            corpus = fixture.corpus
            creator_id = fixture.creator_a.id
            corpus.ingest_text_document(
                creator_id=creator_id,
                document_type=CorpusDocumentType.NOTE,
                title="Tiny",
                content="hola",
                language="es",
                source_kind=CorpusVersionSourceKind.ORIGINAL,
                source_asset_type=CorpusSourceType.IMPORTED_TEXT,
                source_asset_original_name="tiny.txt",
            )

            profile = fixture.profile_service.build_profile(fixture.voice_service.build_snapshot({"creator_id": creator_id}))

            self.assertEqual(profile.status, CreatorVoiceProfileStatus.INSUFFICIENT_EVIDENCE)
            self.assertIn("insufficient_evidence", profile.warnings)
            self.assertTrue(any(section.status == CreatorVoiceProfileStatus.INSUFFICIENT_EVIDENCE for section in profile.sections))

    def test_written_and_spoken_patterns_stay_separate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = _profile_fixture(temp_dir)
            corpus = fixture.corpus
            creator_id = fixture.creator_a.id
            corpus.ingest_text_document(
                creator_id=creator_id,
                document_type=CorpusDocumentType.SCRIPT,
                title="Written",
                content=_make_sentence_text([
                    "yo escribo frases cortas",
                    "tu lees con rapidez",
                    "yo cierro sin rodeos",
                ]),
                language="es",
                source_kind=CorpusVersionSourceKind.ORIGINAL,
                source_asset_type=CorpusSourceType.IMPORTED_TEXT,
                source_asset_original_name="written.txt",
            )
            corpus.ingest_text_document(
                creator_id=creator_id,
                document_type=CorpusDocumentType.TRANSCRIPT,
                title="Spoken",
                content=_make_sentence_text([
                    "yo eh voy explicando el contexto con mas detalle",
                    "tu preguntas y yo respondo de manera mas conversacional",
                    "bueno seguimos hasta que quede claro",
                ]),
                language="es",
                source_kind=CorpusVersionSourceKind.TRANSCRIPTION,
                source_asset_type=CorpusSourceType.TRANSCRIPT,
                source_asset_original_name="spoken.txt",
                segments=[
                    {"sequence": 0, "start_seconds": 0.0, "end_seconds": 1.0, "text": "yo eh voy explicando el contexto con mas detalle", "confidence": 0.96, "review_state": "transcribed"},
                    {"sequence": 1, "start_seconds": 1.0, "end_seconds": 2.0, "text": "tu preguntas y yo respondo de manera mas conversacional", "confidence": 0.95, "review_state": "transcribed"},
                    {"sequence": 2, "start_seconds": 2.0, "end_seconds": 3.0, "text": "bueno seguimos hasta que quede claro", "confidence": 0.97, "review_state": "transcribed"},
                ],
            )

            profile = fixture.profile_service.build_profile(fixture.voice_service.build_snapshot({"creator_id": creator_id}))
            features = _feature_map(profile)

            self.assertIn("spoken_median_sentence_length", features)
            self.assertGreater(features["spoken_median_sentence_length"].value["median"], features["median_sentence_length"].value["median"])
            self.assertGreater(features["spoken_filler_rate"].value["ratio"], 0.0)

    def test_language_and_scope_filters_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = _profile_fixture(temp_dir)
            corpus = fixture.corpus
            creator_id = fixture.creator_a.id
            project_id = fixture.project_a.id
            corpus.ingest_text_document(
                creator_id=creator_id,
                project_id=project_id,
                document_type=CorpusDocumentType.SCRIPT,
                title="Spanish project",
                content=_make_sentence_text([
                    "yo escribo en espanol",
                    "tu lo ves en el proyecto",
                ]),
                language="es",
                source_kind=CorpusVersionSourceKind.ORIGINAL,
                source_asset_type=CorpusSourceType.IMPORTED_TEXT,
                source_asset_original_name="project-es.txt",
            )
            corpus.ingest_text_document(
                creator_id=creator_id,
                document_type=CorpusDocumentType.SCRIPT,
                title="English global",
                content=_make_sentence_text([
                    "i write in english",
                    "you read it globally",
                ]),
                language="en",
                source_kind=CorpusVersionSourceKind.ORIGINAL,
                source_asset_type=CorpusSourceType.IMPORTED_TEXT,
                source_asset_original_name="global-en.txt",
            )

            spanish_profile = fixture.profile_service.build_profile(
                fixture.voice_service.build_snapshot({"creator_id": creator_id, "project_id": project_id, "language": "es"})
            )
            english_profile = fixture.profile_service.build_profile(
                fixture.voice_service.build_snapshot({"creator_id": creator_id, "language": "en"})
            )

            self.assertEqual(spanish_profile.project_id, project_id)
            self.assertEqual(spanish_profile.language, "es")
            self.assertEqual(english_profile.language, "en")
            self.assertNotEqual(spanish_profile.fingerprint, english_profile.fingerprint)
            self.assertTrue(all(pref.scope.value in {"creator_global", "project_specific"} for pref in spanish_profile.structured_preferences))

    def test_confirmed_preferences_remain_separate_and_conflicts_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = _profile_fixture(temp_dir)
            corpus = fixture.corpus
            creator_id = fixture.creator_a.id
            fixture.preference_repo.upsert_confirmed_preference(
                _make_preference(
                    creator_id=creator_id,
                    preference_key="voice.shorter.global",
                    value_json={"preference_type": "content_length_preference", "direction": "shorter"},
                    scope=CreatorPreferenceScope.CREATOR_GLOBAL,
                )
            )
            corpus.ingest_text_document(
                creator_id=creator_id,
                document_type=CorpusDocumentType.SCRIPT,
                title="Long content",
                content=_make_sentence_text([
                    "yo explico con mucho detalle el contexto general del tema",
                    "tu puedes seguir cada paso sin perder la referencia",
                    "yo cierro con una conclusion bastante extensa y clara",
                ]),
                language="es",
                source_kind=CorpusVersionSourceKind.ORIGINAL,
                source_asset_type=CorpusSourceType.IMPORTED_TEXT,
                source_asset_original_name="long.txt",
            )
            profile = fixture.profile_service.build_profile(fixture.voice_service.build_snapshot({"creator_id": creator_id}))

            self.assertTrue(profile.structured_preferences)
            self.assertEqual(profile.structured_preferences[0].preference_type, "content_length_preference")
            self.assertTrue(profile.structured_preferences[0].conflict)
            self.assertIn("confirmed_preference_conflict", profile.warnings)
            self.assertEqual(profile.structured_preferences[0].value["direction"], "shorter")
            self.assertIn("shorter", profile.structured_preferences[0].rendered_text)

    def test_outlier_robustness_duplicate_protection_and_ai_contamination(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = _profile_fixture(temp_dir)
            corpus = fixture.corpus
            creator_id = fixture.creator_a.id
            for index in range(9):
                corpus.ingest_text_document(
                    creator_id=creator_id,
                    document_type=CorpusDocumentType.SCRIPT,
                    title=f"Short {index}",
                    content=_make_sentence_text([
                        f"yo digo corto {index}",
                        f"tu ves corto {index}",
                    ]),
                    language="es",
                    source_kind=CorpusVersionSourceKind.ORIGINAL,
                    source_asset_type=CorpusSourceType.IMPORTED_TEXT,
                    source_asset_original_name=f"short-{index}.txt",
                )
            corpus.ingest_text_document(
                creator_id=creator_id,
                document_type=CorpusDocumentType.SCRIPT,
                title="Long outlier",
                content=_make_sentence_text([
                    "yo explico una historia muy extensa con muchos detalles y contexto",
                    "tu sigues la explicacion mientras yo repito la idea con cuidado",
                    "yo vuelvo a insistir en el mismo punto para que quede claro",
                ]),
                language="es",
                source_kind=CorpusVersionSourceKind.ORIGINAL,
                source_asset_type=CorpusSourceType.IMPORTED_TEXT,
                source_asset_original_name="outlier.txt",
            )
            duplicate = corpus.ingest_text_document(
                creator_id=creator_id,
                document_type=CorpusDocumentType.NOTE,
                title="Duplicate",
                content=_make_sentence_text([
                    "yo digo corto duplicate",
                    "tu ves corto duplicate",
                ]),
                language="es",
                source_kind=CorpusVersionSourceKind.ORIGINAL,
                source_asset_type=CorpusSourceType.IMPORTED_TEXT,
                source_asset_original_name="duplicate.txt",
            )
            base_profile = fixture.profile_service.build_profile(fixture.voice_service.build_snapshot({"creator_id": creator_id}))
            corpus.ingest_text_document(
                creator_id=creator_id,
                document_type=CorpusDocumentType.SCRIPT,
                title="AI contamination",
                content=_make_sentence_text([
                    "esto fue generado por ia con una voz ajena",
                    "tu no deberias usarlo como evidencia",
                ]),
                language="es",
                source_kind=CorpusVersionSourceKind.AI_GENERATED,
                source_asset_type=CorpusSourceType.IMPORTED_TEXT,
                source_asset_original_name="ai.txt",
            )
            after_profile = fixture.profile_service.build_profile(fixture.voice_service.build_snapshot({"creator_id": creator_id}))

            self.assertLess(base_profile.to_dict()["sections"][0]["features"][0]["value"]["median"], 20)
            self.assertEqual(
                {feature.feature_key: feature.to_dict() for section in base_profile.sections for feature in section.features},
                {feature.feature_key: feature.to_dict() for section in after_profile.sections for feature in section.features},
            )
            self.assertIn("ai_contamination_blocked", after_profile.warnings)

    def test_repeated_phrases_filter_private_tokens_and_compare_profiles(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = _profile_fixture(temp_dir)
            corpus = fixture.corpus
            creator_id = fixture.creator_a.id
            corpus.ingest_text_document(
                creator_id=creator_id,
                document_type=CorpusDocumentType.SCRIPT,
                title="Sensitive one",
                content=_make_sentence_text([
                    "contacta por correo test@example.com y revisa el enlace https://example.com/secret",
                    "mi telefono es 555-123-4567 y la clave es abcdef1234567890",
                    "contacta por correo test@example.com y revisa el enlace https://example.com/secret",
                ]),
                language="es",
                source_kind=CorpusVersionSourceKind.ORIGINAL,
                source_asset_type=CorpusSourceType.IMPORTED_TEXT,
                source_asset_original_name="sensitive.txt",
            )
            corpus.ingest_text_document(
                creator_id=creator_id,
                document_type=CorpusDocumentType.SCRIPT,
                title="Sensitive two",
                content=_make_sentence_text([
                    "contacta por correo test@example.com y revisa el enlace https://example.com/secret",
                    "mi telefono es 555-123-4567 y la clave es abcdef1234567890",
                ]),
                language="es",
                source_kind=CorpusVersionSourceKind.ORIGINAL,
                source_asset_type=CorpusSourceType.IMPORTED_TEXT,
                source_asset_original_name="sensitive2.txt",
            )
            corpus.ingest_text_document(
                creator_id=creator_id,
                document_type=CorpusDocumentType.SCRIPT,
                title="Long version",
                content=_make_sentence_text([
                    "yo explico algo diferente con mas palabras",
                    "tu sigues otra ruta",
                    "yo cierro el tema",
                ]),
                language="es",
                source_kind=CorpusVersionSourceKind.ORIGINAL,
                source_asset_type=CorpusSourceType.IMPORTED_TEXT,
                source_asset_original_name="long2.txt",
            )
            base_profile = fixture.profile_service.build_profile(fixture.voice_service.build_snapshot({"creator_id": creator_id}))
            comparison_profile = fixture.profile_service.build_profile(
                fixture.voice_service.build_snapshot({"creator_id": creator_id, "language": "es", "max_items": 12})
            )
            comparison = fixture.profile_service.compare_profiles(base_profile, comparison_profile)

            repeated_feature = _feature_map(base_profile)["repeated_phrases"]
            phrases = [entry["phrase"] for entry in repeated_feature.value]
            self.assertTrue(all("@" not in phrase and "http" not in phrase and not re.search(r"\d", phrase) for phrase in phrases))
            self.assertIsInstance(comparison.changed_features, tuple)

    def test_cli_profile_build_and_compare_are_safe(self) -> None:
        parser = build_parser()
        build_args = parser.parse_args(["voice", "profile-build", "--creator-id", "creator-a", "--json"])
        compare_args = parser.parse_args([
            "voice",
            "profile-compare",
            "--base-creator-id",
            "creator-a",
            "--compare-creator-id",
            "creator-a",
            "--json",
        ])
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = _profile_fixture(temp_dir)
            corpus = fixture.corpus
            creator_id = fixture.creator_a.id
            corpus.ingest_text_document(
                creator_id=creator_id,
                document_type=CorpusDocumentType.SCRIPT,
                title="CLI text",
                content=_make_sentence_text([
                    "yo escribo texto",
                    "tu lo lees",
                    "yo cierro la idea",
                ]),
                language="es",
                source_kind=CorpusVersionSourceKind.ORIGINAL,
                source_asset_type=CorpusSourceType.IMPORTED_TEXT,
                source_asset_original_name="cli.txt",
            )
            stdout = io.StringIO()
            stderr = io.StringIO()
            exit_code = handle_voice_command(
                build_args,
                evidence_service=fixture.voice_service,
                profile_service=fixture.profile_service,
                stdout=stdout,
                stderr=stderr,
            )
            self.assertEqual(exit_code, 0)
            payload = json.loads(stdout.getvalue())
            self.assertIn("profile", payload)

            stdout = io.StringIO()
            stderr = io.StringIO()
            exit_code = handle_voice_command(
                compare_args,
                evidence_service=fixture.voice_service,
                profile_service=fixture.profile_service,
                stdout=stdout,
                stderr=stderr,
            )
            self.assertEqual(exit_code, 0)
            comparison_payload = json.loads(stdout.getvalue())
            self.assertIn("changed_features", comparison_payload)


if __name__ == "__main__":
    unittest.main()
