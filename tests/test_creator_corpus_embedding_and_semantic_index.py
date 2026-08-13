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
        self.assertEqual(manifest.selected_cpu_artifact.expected_bytes, 470_268_510)
        self.assertEqual(manifest.artifacts[0].relative_path, "onnx/config.json")
        self.assertEqual(manifest.artifacts[0].expected_sha256, "bbb7c1333fc4b3e27fbc9cd5d2070aabcc1d4dfb99917c3633e772f97545a6b6")
        self.assertEqual(manifest.artifacts[2].relative_path, "onnx/sentencepiece.bpe.model")
        self.assertEqual(manifest.artifacts[2].expected_sha256, "cfc8146abe2a0488e9e2a0c56de7952f7c11ab059eca145a0a727afce0db2865")
        self.assertEqual(manifest.artifacts[3].relative_path, "onnx/special_tokens_map.json")
        self.assertEqual(manifest.artifacts[3].expected_sha256, "d05497f1da52c5e09554c0cd874037a083e1dc1b9cfd48034d1c717f1afc07a7")
        self.assertEqual(manifest.artifacts[4].relative_path, "onnx/tokenizer.json")
        self.assertEqual(manifest.artifacts[4].expected_sha256, "0b44a9d7b51c3c62626640cda0e2c2f70fdacdc25bbbd68038369d14ebdf4c39")
        self.assertEqual(manifest.artifacts[5].relative_path, "onnx/tokenizer_config.json")
        self.assertEqual(manifest.artifacts[5].expected_sha256, "a1d6bc8734a6f635dc158508bef000f8e2e5a759c7d92f984b2c86e5ff53425b")
        self.assertEqual(manifest.accelerator_artifact.required_cpu_feature, "avx512_vnni")
        self.assertIn("model.onnx", manifest.source_url_for("onnx/model.onnx"))
        self.assertIn(SEMANTIC_MODEL_REVISION, manifest.source_page)
        self.assertNotIn("/main", manifest.source_page)
        self.assertEqual(manifest.embedding_dimension, 384)
        self.assertEqual(manifest.max_tokens, 512)
        self.assertEqual(manifest.total_expected_bytes, 492_421_554)
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

    def test_semantic_index_rebuild_is_atomic_when_cancelled(self) -> None:
        class _CancelledToken:
            def cancelled(self) -> bool:
                return True

        with tempfile.TemporaryDirectory() as temp_dir:
            _, paths, database, catalog, corpus = _build_context(temp_dir)
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
            index_service = CreatorCorpusSemanticIndexService(
                paths=paths,
                corpus_repository=SQLiteCreatorCorpusRepository(database),
                embedding_service=_FakeEmbeddingService(),
            )

            first = index_service.build_index(creator.id)
            before = index_service.health(creator.id)
            cancelled = index_service.build_index(creator.id, cancellation_token=_CancelledToken())
            after = index_service.health(creator.id)

            self.assertEqual(first["status"], "ready")
            self.assertEqual(cancelled["status"], "interrupted")
            self.assertEqual(before.generation_id, after.generation_id)
            self.assertEqual(after.status, "active")

    def test_semantic_index_health_detects_corrupt_vectors(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            _, paths, database, catalog, corpus = _build_context(temp_dir)
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
            index_service = CreatorCorpusSemanticIndexService(
                paths=paths,
                corpus_repository=SQLiteCreatorCorpusRepository(database),
                embedding_service=_FakeEmbeddingService(),
            )

            build_result = index_service.build_index(creator.id)
            self.assertEqual(build_result["status"], "ready")
            with index_service._connect() as connection:
                connection.execute(
                    "UPDATE semantic_index_chunks SET vector_blob = ? WHERE creator_id = ?",
                    (b"\x00\x01", creator.id),
                )

            health = index_service.health(creator.id)

            self.assertEqual(health.status, "repair_required")
            self.assertGreaterEqual(health.stale_chunk_count + health.orphan_chunk_count, 0)

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
