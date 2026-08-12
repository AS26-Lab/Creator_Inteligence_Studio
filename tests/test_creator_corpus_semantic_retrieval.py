from __future__ import annotations

import tempfile
import unittest

from creator_intelligence_studio.application.services.creator_corpus_retrieval_service import CreatorCorpusRetrievalService
from creator_intelligence_studio.application.services.creator_corpus_semantic_evaluation_service import (
    CreatorCorpusSemanticEvaluationService,
    SemanticMatchMode,
    SemanticRetrievalCase,
)
from creator_intelligence_studio.domain.creator_corpus import CorpusDocumentType, CorpusVersionSourceKind
from creator_intelligence_studio.infrastructure.persistence.sqlite_creator_corpus_repository import SQLiteCreatorCorpusRepository
from tests.test_creator_corpus_foundation import _build_context


class _KeywordSemanticScorer:
    def score(self, query_text: str, candidates):
        query = query_text.lower()
        scores: list[float] = []
        for candidate in candidates:
            text = f"{candidate.title} {candidate.text}".lower()
            score = 0.01
            if "siga viendo" in query and "retencion" in text:
                score = 0.95
            if "siga viendo" in query and "short" in text:
                score = max(score, 0.35)
            if "explico cosas dificiles" in query and "explico cosas dificiles" in text:
                score = 0.96
            if "contenido estrategico" in query and "draft" in text:
                score = 0.9
            if "retencion de audiencia" in query and "draft" in text:
                score = 0.98
            if "short de 30 segundos" in query and "short" in text:
                score = 0.97
            scores.append(score)
        return scores


class CreatorCorpusSemanticRetrievalTests(unittest.TestCase):
    def test_semantic_unavailable_preserves_lexical_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            _, _, database, catalog, corpus = _build_context(temp_dir)
            retrieval = CreatorCorpusRetrievalService(repository=SQLiteCreatorCorpusRepository(database))
            # Rebuild the evaluator without a semantic scorer to prove lexical fallback remains intact.
            evaluator = CreatorCorpusSemanticEvaluationService(retrieval_service=retrieval, semantic_scorer=None)
            creator = catalog.create_creator(display_name="Creator A")
            corpus.ingest_text_document(
                creator_id=creator.id,
                document_type=CorpusDocumentType.SCRIPT,
                title="Retencion de audiencia",
                content="La retencion de audiencia mejora cuando el short engancha desde el principio.",
                language="es",
                source_kind=CorpusVersionSourceKind.ORIGINAL,
                source_asset_type=None,
            )

            report = evaluator.evaluate(
                (
                    SemanticRetrievalCase(
                        case_id="exact",
                        creator_id=creator.id,
                        query_text="retencion de audiencia",
                        expected_document_ids=(),
                    ),
                )
            )

            self.assertEqual(report.semantic_status, "unavailable")
            self.assertIsNone(report.metrics.semantic_top1_hit_rate)
            self.assertEqual(report.cases[0].semantic_document_ids, ())
            self.assertEqual(report.cases[0].hybrid_document_ids, report.cases[0].lexical_document_ids)

    def test_semantic_and_hybrid_improve_paraphrase_retrieval_without_cross_creator_leakage(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            _, _, database, catalog, corpus = _build_context(temp_dir)
            retrieval = CreatorCorpusRetrievalService(repository=SQLiteCreatorCorpusRepository(database))
            evaluator = CreatorCorpusSemanticEvaluationService(retrieval_service=retrieval, semantic_scorer=_KeywordSemanticScorer())
            creator_a = catalog.create_creator(display_name="Creator A")
            creator_b = catalog.create_creator(display_name="Creator B")
            project = catalog.create_project(creator_reference=creator_a.id, name="Project A", project_type="long_form")

            exact = corpus.ingest_text_document(
                creator_id=creator_a.id,
                project_id=project.id,
                document_type=CorpusDocumentType.SCRIPT,
                title="Retencion de audiencia",
                content="La retencion de audiencia mejora cuando el short engancha desde el principio.",
                language="es",
                source_kind=CorpusVersionSourceKind.ORIGINAL,
                source_asset_type=None,
            )
            concept = corpus.ingest_text_document(
                creator_id=creator_a.id,
                project_id=project.id,
                document_type=CorpusDocumentType.SCRIPT,
                title="Explicacion sencilla",
                content="Cuando explico cosas dificiles uso ejemplos claros y lenguaje directo.",
                language="es",
                source_kind=CorpusVersionSourceKind.ORIGINAL,
                source_asset_type=None,
            )
            short = corpus.ingest_text_document(
                creator_id=creator_a.id,
                project_id=project.id,
                document_type=CorpusDocumentType.NOTE,
                title="Short 30s",
                content="Un short de 30 segundos con un gancho fuerte y una idea unica.",
                language="es",
                source_kind=CorpusVersionSourceKind.ORIGINAL,
                source_asset_type=None,
            )
            draft = corpus.ingest_text_document(
                creator_id=creator_a.id,
                document_type=CorpusDocumentType.NOTE,
                title="Draft AI",
                content="Generic video marketing tips about content strategy.",
                language="en",
                source_kind=CorpusVersionSourceKind.AI_GENERATED,
                source_asset_type=None,
            )
            creator_b_doc = corpus.ingest_text_document(
                creator_id=creator_b.id,
                project_id=project.id,
                document_type=CorpusDocumentType.SCRIPT,
                title="Retencion de audiencia",
                content="La retencion de audiencia mejora cuando el short engancha desde el principio.",
                language="es",
                source_kind=CorpusVersionSourceKind.ORIGINAL,
                source_asset_type=None,
            )
            corpus.archive_document(draft.document.id)

            report = evaluator.evaluate(
                (
                    SemanticRetrievalCase(
                        case_id="paraphrase",
                        creator_id=creator_a.id,
                        query_text="como hago que la gente siga viendo",
                        expected_document_ids=(exact.document.id,),
                        project_id=project.id,
                        document_types=(CorpusDocumentType.SCRIPT, CorpusDocumentType.NOTE),
                    ),
                    SemanticRetrievalCase(
                        case_id="conceptual",
                        creator_id=creator_a.id,
                        query_text="mi estilo cuando explico cosas dificiles",
                        expected_document_ids=(concept.document.id,),
                        project_id=project.id,
                        document_types=(CorpusDocumentType.SCRIPT, CorpusDocumentType.NOTE),
                    ),
                    SemanticRetrievalCase(
                        case_id="exact",
                        creator_id=creator_a.id,
                        query_text="retencion de audiencia",
                        expected_document_ids=(exact.document.id,),
                        project_id=project.id,
                        document_types=(CorpusDocumentType.SCRIPT, CorpusDocumentType.NOTE),
                    ),
                    SemanticRetrievalCase(
                        case_id="short",
                        creator_id=creator_a.id,
                        query_text="short de 30 segundos",
                        expected_document_ids=(short.document.id,),
                        project_id=project.id,
                        document_types=(CorpusDocumentType.SCRIPT, CorpusDocumentType.NOTE),
                    ),
                )
            )

            results = {case.case.case_id: case for case in report.cases}
            self.assertEqual(results["paraphrase"].lexical_document_ids[:1], ())
            self.assertEqual(results["paraphrase"].semantic_document_ids[0], exact.document.id)
            self.assertEqual(results["paraphrase"].hybrid_document_ids[0], exact.document.id)
            self.assertEqual(results["conceptual"].semantic_document_ids[0], concept.document.id)
            self.assertEqual(results["short"].hybrid_document_ids[0], short.document.id)
            self.assertNotIn(creator_b_doc.document.id, results["paraphrase"].semantic_document_ids)
            self.assertNotIn(creator_b_doc.document.id, results["conceptual"].semantic_document_ids)
            self.assertNotIn(creator_b_doc.document.id, results["short"].semantic_document_ids)
            self.assertEqual(report.semantic_status, "ready")
            self.assertGreater(report.metrics.semantic_top5_recall or 0.0, report.metrics.lexical_top5_recall)
            self.assertEqual(report.cases[0].semantic_status, "ready")
            self.assertEqual(report.cases[2].hybrid_document_ids[0], exact.document.id)

    def test_evaluation_report_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            _, _, database, catalog, corpus = _build_context(temp_dir)
            retrieval = CreatorCorpusRetrievalService(repository=SQLiteCreatorCorpusRepository(database))
            evaluator = CreatorCorpusSemanticEvaluationService(retrieval_service=retrieval, semantic_scorer=_KeywordSemanticScorer())
            creator = catalog.create_creator(display_name="Creator A")
            corpus.ingest_text_document(
                creator_id=creator.id,
                document_type=CorpusDocumentType.SCRIPT,
                title="Retencion de audiencia",
                content="La retencion de audiencia mejora cuando el short engancha desde el principio.",
                language="es",
                source_kind=CorpusVersionSourceKind.ORIGINAL,
                source_asset_type=None,
            )
            case = SemanticRetrievalCase(
                case_id="deterministic",
                creator_id=creator.id,
                query_text="retencion de audiencia",
                expected_document_ids=(),
            )
            first = evaluator.evaluate((case,)).to_dict()
            second = evaluator.evaluate((case,)).to_dict()
            for payload in (first, second):
                payload["metrics"].pop("lexical_latency_ms", None)
                payload["metrics"].pop("semantic_latency_ms", None)
                payload["metrics"].pop("hybrid_latency_ms", None)
                for item in payload["cases"]:
                    item.pop("lexical_latency_ms", None)
                    item.pop("semantic_latency_ms", None)
                    item.pop("hybrid_latency_ms", None)
            self.assertEqual(first, second)

    def test_hybrid_fusion_preserves_exact_lexical_match_against_semantic_noise(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            _, _, database, catalog, corpus = _build_context(temp_dir)
            retrieval = CreatorCorpusRetrievalService(repository=SQLiteCreatorCorpusRepository(database))

            class _NoisyScorer:
                def score(self, query_text: str, candidates):
                    scores = []
                    for candidate in candidates:
                        if "draft" in f"{candidate.title} {candidate.text}".lower():
                            scores.append(0.99)
                        elif "retencion de audiencia" in f"{candidate.title} {candidate.text}".lower():
                            scores.append(0.2)
                        else:
                            scores.append(0.01)
                    return scores

            evaluator = CreatorCorpusSemanticEvaluationService(retrieval_service=retrieval, semantic_scorer=_NoisyScorer())
            creator = catalog.create_creator(display_name="Creator A")
            exact = corpus.ingest_text_document(
                creator_id=creator.id,
                document_type=CorpusDocumentType.SCRIPT,
                title="Retencion de audiencia",
                content="La retencion de audiencia mejora cuando el short engancha desde el principio.",
                language="es",
                source_kind=CorpusVersionSourceKind.ORIGINAL,
                source_asset_type=None,
            )
            corpus.ingest_text_document(
                creator_id=creator.id,
                document_type=CorpusDocumentType.NOTE,
                title="Draft AI",
                content="Generic video marketing tips about content strategy.",
                language="en",
                source_kind=CorpusVersionSourceKind.AI_GENERATED,
                source_asset_type=None,
            )

            report = evaluator.evaluate(
                (
                    SemanticRetrievalCase(
                        case_id="exact",
                        creator_id=creator.id,
                        query_text="retencion de audiencia",
                        expected_document_ids=(exact.document.id,),
                        document_types=(CorpusDocumentType.SCRIPT, CorpusDocumentType.NOTE),
                    ),
                )
            )
            case_result = report.cases[0]
            self.assertEqual(case_result.lexical_document_ids[0], exact.document.id)
            self.assertEqual(case_result.hybrid_document_ids[0], exact.document.id)
            self.assertEqual(case_result.semantic_document_ids[0], exact.document.id)
            self.assertEqual(case_result.hybrid_document_ids, tuple(case_result.hybrid_document_ids))
            self.assertEqual(case_result.semantic_document_ids, tuple(case_result.semantic_document_ids))
            self.assertEqual(case_result.semantic_status, "ready")
            self.assertTrue(case_result.hybrid_top1_hit)
            self.assertEqual(SemanticMatchMode.HYBRID.value, "hybrid")


if __name__ == "__main__":
    unittest.main()
