"""Manifiestos para el componente local de embedding semantico."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any


SEMANTIC_MODEL_COMPONENT_ID = "creator-embedding-model.multilingual-e5-small"
SEMANTIC_MODEL_REPOSITORY = "intfloat/multilingual-e5-small"
SEMANTIC_MODEL_REVISION = "614241f622f53c4eeff9890bdc4f31cfecc418b3"
SEMANTIC_MODEL_SOURCE_PAGE = f"https://huggingface.co/{SEMANTIC_MODEL_REPOSITORY}/tree/{SEMANTIC_MODEL_REVISION}"
SEMANTIC_MODEL_LICENSE = "mit"
SEMANTIC_MODEL_SELECTED_ARTIFACT = "onnx/model.onnx"
SEMANTIC_MODEL_SELECTED_CPU_ARTIFACT = "onnx/model.onnx"
SEMANTIC_MODEL_AVX512_ARTIFACT = "onnx/model_qint8_avx512_vnni.onnx"
SEMANTIC_MODEL_CHUNKING_VERSION = "semantic-chunking-v1"
SEMANTIC_MODEL_EMBEDDING_DIMENSION = 384
SEMANTIC_MODEL_MAX_TOKENS = 512


@dataclass(frozen=True, slots=True)
class SemanticEmbeddingArtifact:
    """Archivo inmutable que forma parte del componente semantico."""

    relative_path: str
    source_url: str
    expected_sha256: str | None
    expected_bytes: int | None
    required_cpu_feature: str | None = None
    is_selected_cpu_artifact: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "relative_path": self.relative_path,
            "source_url": self.source_url,
            "expected_sha256": self.expected_sha256,
            "expected_bytes": self.expected_bytes,
            "required_cpu_feature": self.required_cpu_feature,
            "is_selected_cpu_artifact": self.is_selected_cpu_artifact,
        }


@dataclass(frozen=True, slots=True)
class SemanticEmbeddingModelManifest:
    """Identidad gestionada del modelo local de embeddings."""

    component_id: str
    source_provider: str
    repository: str
    revision: str
    license: str
    source_page: str
    selected_cpu_artifact: SemanticEmbeddingArtifact
    artifacts: tuple[SemanticEmbeddingArtifact, ...]
    accelerator_artifact: SemanticEmbeddingArtifact | None
    embedding_dimension: int
    max_tokens: int
    notes: tuple[str, ...] = ()

    @property
    def total_expected_bytes(self) -> int | None:
        if any(artifact.expected_bytes is None for artifact in self.artifacts):
            return None
        return sum(int(artifact.expected_bytes or 0) for artifact in self.artifacts)

    @property
    def canonical_payload(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "source_provider": self.source_provider,
            "repository": self.repository,
            "revision": self.revision,
            "license": self.license,
            "source_page": self.source_page,
            "selected_cpu_artifact": self.selected_cpu_artifact.to_dict(),
            "accelerator_artifact": self.accelerator_artifact.to_dict() if self.accelerator_artifact else None,
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
            "embedding_dimension": self.embedding_dimension,
            "max_tokens": self.max_tokens,
            "notes": list(self.notes),
        }

    @property
    def expected_sha256(self) -> str:
        import json

        payload = json.dumps(self.canonical_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        return sha256(payload).hexdigest()

    def source_url_for(self, relative_path: str) -> str:
        normalized = relative_path.strip().lstrip("/")
        return f"https://huggingface.co/{self.repository}/resolve/{self.revision}/{normalized}"


@dataclass(frozen=True, slots=True)
class SemanticEmbeddingModelHealth:
    component_id: str
    revision: str
    status: str
    selected_artifact_path: str | None
    tokenizer_path: str | None
    model_path: str | None
    expected_dimension: int
    actual_dimension: int | None
    vector_finite: bool
    normalization_ok: bool
    sample_embedding_checksum: str | None
    missing_files: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    required_cpu_feature: str | None = None
    selected_artifact_sha256: str | None = None
    selected_artifact_bytes: int | None = None
    install_path: str | None = None
    checked_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "revision": self.revision,
            "status": self.status,
            "selected_artifact_path": self.selected_artifact_path,
            "tokenizer_path": self.tokenizer_path,
            "model_path": self.model_path,
            "expected_dimension": self.expected_dimension,
            "actual_dimension": self.actual_dimension,
            "vector_finite": self.vector_finite,
            "normalization_ok": self.normalization_ok,
            "sample_embedding_checksum": self.sample_embedding_checksum,
            "missing_files": list(self.missing_files),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "required_cpu_feature": self.required_cpu_feature,
            "selected_artifact_sha256": self.selected_artifact_sha256,
            "selected_artifact_bytes": self.selected_artifact_bytes,
            "install_path": self.install_path,
            "checked_at": self.checked_at.isoformat().replace("+00:00", "Z") if self.checked_at else None,
        }


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def build_default_semantic_embedding_model_manifest() -> SemanticEmbeddingModelManifest:
    """Devuelve el manifiesto base del modelo local semantico."""

    selected_cpu_artifact = SemanticEmbeddingArtifact(
        relative_path=SEMANTIC_MODEL_SELECTED_ARTIFACT,
        source_url=f"https://huggingface.co/{SEMANTIC_MODEL_REPOSITORY}/resolve/{SEMANTIC_MODEL_REVISION}/{SEMANTIC_MODEL_SELECTED_ARTIFACT}",
        expected_sha256="ca456c06b3a9505ddfd9131408916dd79290368331e7d76bb621f1cba6bc8665",
        expected_bytes=470_268_510,
        required_cpu_feature=None,
        is_selected_cpu_artifact=True,
    )
    qint8_artifact = SemanticEmbeddingArtifact(
        relative_path=SEMANTIC_MODEL_AVX512_ARTIFACT,
        source_url=f"https://huggingface.co/{SEMANTIC_MODEL_REPOSITORY}/resolve/{SEMANTIC_MODEL_REVISION}/{SEMANTIC_MODEL_AVX512_ARTIFACT}",
        expected_sha256="DD476DD0C2514E9B9BE83AEB3853FAC0763E0BDF4A71645407587D77C48A2D88",
        expected_bytes=118_346_824,
        required_cpu_feature="avx512_vnni",
        is_selected_cpu_artifact=False,
    )
    return SemanticEmbeddingModelManifest(
        component_id=SEMANTIC_MODEL_COMPONENT_ID,
        source_provider="huggingface",
        repository=SEMANTIC_MODEL_REPOSITORY,
        revision=SEMANTIC_MODEL_REVISION,
        license=SEMANTIC_MODEL_LICENSE,
        source_page=SEMANTIC_MODEL_SOURCE_PAGE,
        selected_cpu_artifact=selected_cpu_artifact,
        artifacts=(
            SemanticEmbeddingArtifact(
                relative_path="onnx/config.json",
                source_url=f"https://huggingface.co/{SEMANTIC_MODEL_REPOSITORY}/resolve/{SEMANTIC_MODEL_REVISION}/onnx/config.json",
                expected_sha256="bbb7c1333fc4b3e27fbc9cd5d2070aabcc1d4dfb99917c3633e772f97545a6b6",
                expected_bytes=653,
            ),
            selected_cpu_artifact,
            SemanticEmbeddingArtifact(
                relative_path="onnx/sentencepiece.bpe.model",
                source_url=f"https://huggingface.co/{SEMANTIC_MODEL_REPOSITORY}/resolve/{SEMANTIC_MODEL_REVISION}/onnx/sentencepiece.bpe.model",
                expected_sha256="cfc8146abe2a0488e9e2a0c56de7952f7c11ab059eca145a0a727afce0db2865",
                expected_bytes=5_069_051,
            ),
            SemanticEmbeddingArtifact(
                relative_path="onnx/special_tokens_map.json",
                source_url=f"https://huggingface.co/{SEMANTIC_MODEL_REPOSITORY}/resolve/{SEMANTIC_MODEL_REVISION}/onnx/special_tokens_map.json",
                expected_sha256="d05497f1da52c5e09554c0cd874037a083e1dc1b9cfd48034d1c717f1afc07a7",
                expected_bytes=167,
            ),
            SemanticEmbeddingArtifact(
                relative_path="onnx/tokenizer.json",
                source_url=f"https://huggingface.co/{SEMANTIC_MODEL_REPOSITORY}/resolve/{SEMANTIC_MODEL_REVISION}/onnx/tokenizer.json",
                expected_sha256="0b44a9d7b51c3c62626640cda0e2c2f70fdacdc25bbbd68038369d14ebdf4c39",
                expected_bytes=17_082_730,
            ),
            SemanticEmbeddingArtifact(
                relative_path="onnx/tokenizer_config.json",
                source_url=f"https://huggingface.co/{SEMANTIC_MODEL_REPOSITORY}/resolve/{SEMANTIC_MODEL_REVISION}/onnx/tokenizer_config.json",
                expected_sha256="a1d6bc8734a6f635dc158508bef000f8e2e5a759c7d92f984b2c86e5ff53425b",
                expected_bytes=443,
            ),
        ),
        accelerator_artifact=qint8_artifact,
        embedding_dimension=SEMANTIC_MODEL_EMBEDDING_DIMENSION,
        max_tokens=SEMANTIC_MODEL_MAX_TOKENS,
        notes=(
            "The selected universal CPU artifact is model.onnx.",
            "The qint8 AVX512/VNNI artifact is retained as a qualified accelerator-specific variant, not the universal default.",
        ),
    )


def get_semantic_embedding_model_manifest(component_id: str) -> SemanticEmbeddingModelManifest | None:
    normalized = component_id.strip().lower()
    manifest = build_default_semantic_embedding_model_manifest()
    return manifest if manifest.component_id.lower() == normalized else None
