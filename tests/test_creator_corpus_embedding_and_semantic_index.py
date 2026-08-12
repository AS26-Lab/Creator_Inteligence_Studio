from __future__ import annotations

import tempfile
import unittest
from dataclasses import dataclass

import numpy as np

from creator_intelligence_studio.application.services.creator_corpus_embedding_service import CreatorCorpusEmbeddingService
from creator_intelligence_studio.application.services.creator_corpus_retrieval_service import CreatorCorpusRetrievalService
from creator_intelligence_studio.application.services.creator_corpus_semantic_index_service import (
    CreatorCorpusSemanticIndexService,
)
from creator_intelligence_studio.domain.creator_corpus import CorpusDocumentType, CorpusVersionSourceKind
from creator_intelligence_studio.domain.creator_corpus.retrieval import CorpusRetrievalQuery
from creator_intelligence_studio.domain.semantic_embedding.model_sources import (
    SEMANTIC_MODEL_COMPONENT_ID,
    SEMANTIC_MODEL_REVISION,
    build_default_semantic_embedding_model_manifest,
)
from creator_intelligence_studio.infrastructure.persistence.sqlite_creator_corpus_repository import SQLiteCreatorCorpusRepository
from tests.test_creator_corpus_foundation import _build_context


SEMANTIC_DIMENSION = build_default_semantic_embedding_model_manifest().embedding_dimension


class CreatorEmbeddingModelContractTests(unittest.TestCase):
    def test_semantic_embedding_model_manifest_is_pinned_and_cpu_selected(self) -> None:
        manifest = build_default_semantic_embedding_model_manifest()

        self.assertEqual(manifest.component_id, SEMANTIC_MODEL_COMPONENT_ID)
        self.assertEqual(manifest.repository, "intfloat/multilingual-e5-small")
        self.assertEqual(manifest.revision, SEMANTIC_MODEL_REVISION)
        self.assertEqual(manifest.license, "mit")
        self.assertEqual(manifest.selected_cpu_artifact.relative_path, "onnx/model.onnx")
        self.assertEqual(manifest.selected_cpu_artifact.expected_sha256, "ca456c06b3a9505ddfd9131408916dd79290368331e7d76bb621f1cba6bc8665")
        self.assertEqual(manifest.accelerator_artifact.required_cpu_feature, "avx512_vnni")
        self.assertIn("model.onnx", manifest.source_url_for("onnx/model.onnx"))
        self.assertIn(SEMANTIC_MODEL_REVISION, manifest.source_page)
        self.assertNotIn("/main", manifest.source_page)
        self.assertEqual(manifest.embedding_dimension, 384)
        self.assertEqual(manifest.max_tokens, 512)
        self.assertGreater(manifest.total_expected_bytes or 0, 0)

    def test_embedding_health_is_missing_without_downloaded_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            _, paths, _, _, _ = _build_context(temp_dir)
            service = CreatorCorpusEmbeddingService(paths=paths)

            health = service.health()

            self.assertEqual(health.status, "missing")
            self.assertEqual(health.expected_dimension, 384)
            self.assertFalse(health.vector_finite)
            self.assertFalse(health.normalization_ok)
            self.assertTrue(health.missing_files)


@dataclass
class _FakeEmbeddingHealth:
    status: str = "ready"

    def to_dict(self) -> dict[str, object]:
        return {"status": self.status}


class _FakeEmbeddingService:
    def health(self) -> _FakeEmbeddingHealth:
        return _FakeEmbeddingHealth()

    def embed(self, texts, *, query_mode: bool = True):
        vectors = []
        for text in texts:
            lowered = (text or "").lower()
            vector = np.zeros((SEMANTIC_DIMENSION,), dtype=np.float32)
            if "siga viendo" in lowered or "retencion" in lowered:
                vector[0] = 1.0
            elif "explico" in lowered or "dificiles" in lowered:
                vector[1] = 1.0
            elif "short" in lowered:
                vector[2] = 1.0
            else:
                vector[3] = 1.0
            vector /= np.linalg.norm(vector)
            vectors.append(vector)
        return np.vstack(vectors) if vectors else np.zeros((0, SEMANTIC_DIMENSION), dtype=np.float32)


class CreatorSemanticIndexTests(unittest.TestCase):
    def test_semantic_index_build_and_search_are_creator_scoped(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            _, paths, database, catalog, corpus = _build_context(temp_dir)
            creator_a = catalog.create_creator(display_name="Creator A")
            creator_b = catalog.create_creator(display_name="Creator B")

            target = corpus.ingest_text_document(
                creator_id=creator_a.id,
                document_type=CorpusDocumentType.SCRIPT,
                title="Retencion de audiencia",
                content="La retencion de audiencia mejora cuando el short engancha desde el principio.",
                language="es",
                source_kind=CorpusVersionSourceKind.ORIGINAL,
                source_asset_type=None,
            )
            corpus.ingest_text_document(
                creator_id=creator_b.id,
                document_type=CorpusDocumentType.SCRIPT,
                title="Retencion de audiencia",
                content="La retencion de audiencia mejora cuando el short engancha desde el principio.",
                language="es",
                source_kind=CorpusVersionSourceKind.ORIGINAL,
                source_asset_type=None,
            )
            index_service = CreatorCorpusSemanticIndexService(
                paths=paths,
                corpus_repository=SQLiteCreatorCorpusRepository(database),
                embedding_service=_FakeEmbeddingService(),
            )

            build_result = index_service.build_index(creator_a.id)
            search_result = index_service.search(
                CorpusRetrievalQuery(
                    creator_id=creator_a.id,
                    query_text="como hago que la gente siga viendo",
                    limit=5,
                )
            )
            health = index_service.health(creator_a.id)

            self.assertEqual(build_result["status"], "ready")
            self.assertEqual(health.status, "active")
            self.assertEqual(search_result.used_mode, "semantic")
            self.assertGreaterEqual(len(search_result.results), 1)
            self.assertEqual(search_result.results[0].document_id, target.document.id)
            self.assertNotIn(creator_b.id, {item.creator_id for item in search_result.results})
            del index_service, catalog, corpus, database

    def test_hybrid_retrieval_degrades_to_lexical_when_semantic_component_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            _, paths, database, catalog, corpus = _build_context(temp_dir)
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
            retrieval = CreatorCorpusRetrievalService(
                repository=SQLiteCreatorCorpusRepository(database),
                semantic_index_service=CreatorCorpusSemanticIndexService(
                    paths=paths,
                    corpus_repository=SQLiteCreatorCorpusRepository(database),
                    embedding_service=CreatorCorpusEmbeddingService(paths=paths),
                ),
            )

            result = retrieval.search(
                CorpusRetrievalQuery(
                    creator_id=creator.id,
                    query_text="retencion de audiencia",
                    limit=5,
                ),
                retrieval_mode="hybrid_if_available",
            )

            self.assertEqual(result.retrieval_mode_used, "lexical_fallback")
            self.assertEqual(result.results[0].document_id, exact.document.id)
            del retrieval, catalog, corpus, database


if __name__ == "__main__":
    unittest.main()
