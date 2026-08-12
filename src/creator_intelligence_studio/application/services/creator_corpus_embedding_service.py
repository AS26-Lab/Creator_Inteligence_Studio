"""Servicio local de embedding para Creator Corpus."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

from creator_intelligence_studio.domain.semantic_embedding import (
    SemanticEmbeddingModelHealth,
    SemanticEmbeddingModelManifest,
    build_default_semantic_embedding_model_manifest,
)
from creator_intelligence_studio.shared.paths import ProjectPaths


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _l2_normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0.0] = 1.0
    return matrix / norms


@dataclass(slots=True)
class CreatorCorpusEmbeddingService:
    """Carga un modelo ONNX local, tokeniza y emite vectores normalizados."""

    paths: ProjectPaths
    manifest: SemanticEmbeddingModelManifest = build_default_semantic_embedding_model_manifest()
    logger: logging.Logger | None = None

    def __post_init__(self) -> None:
        if self.logger is None:
            self.logger = logging.getLogger("creator_intelligence_studio.creator_corpus.embedding")

    @property
    def model_root(self) -> Path:
        return self.paths.models_directory / "creator-embedding-model" / self.manifest.component_id / self.manifest.revision

    @property
    def selected_artifact_path(self) -> Path:
        return self.model_root / self.manifest.selected_cpu_artifact.relative_path

    @property
    def tokenizer_path(self) -> Path:
        return self.model_root / "onnx" / "tokenizer.json"

    @property
    def config_path(self) -> Path:
        return self.model_root / "onnx" / "config.json"

    @property
    def sentencepiece_path(self) -> Path:
        return self.model_root / "onnx" / "sentencepiece.bpe.model"

    @property
    def special_tokens_map_path(self) -> Path:
        return self.model_root / "onnx" / "special_tokens_map.json"

    @property
    def tokenizer_config_path(self) -> Path:
        return self.model_root / "onnx" / "tokenizer_config.json"

    def required_paths(self) -> tuple[Path, ...]:
        return (
            self.config_path,
            self.selected_artifact_path,
            self.sentencepiece_path,
            self.special_tokens_map_path,
            self.tokenizer_path,
            self.tokenizer_config_path,
        )

    def _missing_files(self) -> tuple[str, ...]:
        missing = [str(path.relative_to(self.model_root)) for path in self.required_paths() if not path.exists()]
        return tuple(missing)

    def _hash_mismatches(self) -> tuple[str, ...]:
        mismatches: list[str] = []
        for artifact in self.manifest.artifacts:
            if artifact.expected_sha256 is None:
                continue
            candidate = self.model_root / artifact.relative_path
            if not candidate.exists():
                continue
            actual = _sha256_file(candidate).lower()
            if actual != artifact.expected_sha256.lower():
                mismatches.append(artifact.relative_path)
        return tuple(mismatches)

    def _load_runtime(self):
        import onnxruntime as ort
        from tokenizers import Tokenizer

        tokenizer = Tokenizer.from_file(str(self.tokenizer_path))
        session = ort.InferenceSession(str(self.selected_artifact_path), providers=["CPUExecutionProvider"])
        return tokenizer, session

    def _prepare_inputs(self, tokenizer, texts: Sequence[str], *, query_mode: bool) -> dict[str, np.ndarray]:
        prefix = "query: " if query_mode else "passage: "
        encoded = [
            tokenizer.encode(
                f"{prefix}{text or ''}",
                add_special_tokens=True,
            )
            for text in texts
        ]
        max_length = min(self.manifest.max_tokens, max(len(item.ids) for item in encoded) if encoded else self.manifest.max_tokens)
        input_ids = np.array([item.ids[:max_length] + [0] * max(0, max_length - len(item.ids)) for item in encoded], dtype=np.int64)
        attention_mask = np.array([item.attention_mask[:max_length] + [0] * max(0, max_length - len(item.attention_mask)) for item in encoded], dtype=np.int64)
        payload: dict[str, np.ndarray] = {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
        }
        token_type_ids = np.zeros_like(input_ids, dtype=np.int64)
        payload["token_type_ids"] = token_type_ids
        return payload

    def _mean_pool(self, last_hidden_state: np.ndarray, attention_mask: np.ndarray) -> np.ndarray:
        masked = last_hidden_state * attention_mask[..., None].astype(last_hidden_state.dtype)
        summed = masked.sum(axis=1)
        counts = np.maximum(attention_mask.sum(axis=1, keepdims=True), 1)
        return summed / counts

    def health(self) -> SemanticEmbeddingModelHealth:
        missing_files = self._missing_files()
        if missing_files:
            return SemanticEmbeddingModelHealth(
                component_id=self.manifest.component_id,
                revision=self.manifest.revision,
                status="missing",
                selected_artifact_path=str(self.selected_artifact_path) if self.selected_artifact_path.exists() else None,
                tokenizer_path=str(self.tokenizer_path) if self.tokenizer_path.exists() else None,
                model_path=str(self.selected_artifact_path) if self.selected_artifact_path.exists() else None,
                expected_dimension=self.manifest.embedding_dimension,
                actual_dimension=None,
                vector_finite=False,
                normalization_ok=False,
                sample_embedding_checksum=None,
                missing_files=missing_files,
                errors=("Faltan archivos requeridos del modelo semantico.",),
                required_cpu_feature=self.manifest.selected_cpu_artifact.required_cpu_feature,
                selected_artifact_sha256=self.manifest.selected_cpu_artifact.expected_sha256,
                selected_artifact_bytes=self.manifest.selected_cpu_artifact.expected_bytes,
                install_path=str(self.model_root),
                checked_at=_now(),
            )
        hash_mismatches = self._hash_mismatches()
        if hash_mismatches:
            return SemanticEmbeddingModelHealth(
                component_id=self.manifest.component_id,
                revision=self.manifest.revision,
                status="repair_required",
                selected_artifact_path=str(self.selected_artifact_path),
                tokenizer_path=str(self.tokenizer_path),
                model_path=str(self.selected_artifact_path),
                expected_dimension=self.manifest.embedding_dimension,
                actual_dimension=None,
                vector_finite=False,
                normalization_ok=False,
                sample_embedding_checksum=None,
                warnings=("Los hashes locales no coinciden con el manifiesto.",),
                errors=hash_mismatches,
                required_cpu_feature=self.manifest.selected_cpu_artifact.required_cpu_feature,
                selected_artifact_sha256=self.manifest.selected_cpu_artifact.expected_sha256,
                selected_artifact_bytes=self.manifest.selected_cpu_artifact.expected_bytes,
                install_path=str(self.model_root),
                checked_at=_now(),
            )
        try:
            tokenizer, session = self._load_runtime()
            sample = self.embed(["diagnostic sample"], query_mode=True)
            actual_dimension = int(sample.shape[1]) if sample.ndim == 2 else None
            finite = bool(np.isfinite(sample).all())
            normalized = bool(np.allclose(np.linalg.norm(sample, axis=1), np.ones(sample.shape[0]), atol=1e-4))
            checksum = _sha256_bytes(sample.astype(np.float32).tobytes())
            status = "ready" if finite and normalized and actual_dimension == self.manifest.embedding_dimension else "stale"
            return SemanticEmbeddingModelHealth(
                component_id=self.manifest.component_id,
                revision=self.manifest.revision,
                status=status,
                selected_artifact_path=str(self.selected_artifact_path),
                tokenizer_path=str(self.tokenizer_path),
                model_path=str(self.selected_artifact_path),
                expected_dimension=self.manifest.embedding_dimension,
                actual_dimension=actual_dimension,
                vector_finite=finite,
                normalization_ok=normalized,
                sample_embedding_checksum=checksum,
                required_cpu_feature=self.manifest.selected_cpu_artifact.required_cpu_feature,
                selected_artifact_sha256=self.manifest.selected_cpu_artifact.expected_sha256,
                selected_artifact_bytes=self.manifest.selected_cpu_artifact.expected_bytes,
                install_path=str(self.model_root),
                checked_at=_now(),
            )
        except Exception as exc:
            return SemanticEmbeddingModelHealth(
                component_id=self.manifest.component_id,
                revision=self.manifest.revision,
                status="failed",
                selected_artifact_path=str(self.selected_artifact_path),
                tokenizer_path=str(self.tokenizer_path),
                model_path=str(self.selected_artifact_path),
                expected_dimension=self.manifest.embedding_dimension,
                actual_dimension=None,
                vector_finite=False,
                normalization_ok=False,
                sample_embedding_checksum=None,
                errors=(str(exc),),
                required_cpu_feature=self.manifest.selected_cpu_artifact.required_cpu_feature,
                selected_artifact_sha256=self.manifest.selected_cpu_artifact.expected_sha256,
                selected_artifact_bytes=self.manifest.selected_cpu_artifact.expected_bytes,
                install_path=str(self.model_root),
                checked_at=_now(),
            )

    def embed(self, texts: Sequence[str], *, query_mode: bool = True) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.manifest.embedding_dimension), dtype=np.float32)
        tokenizer, session = self._load_runtime()
        inputs = self._prepare_inputs(tokenizer, texts, query_mode=query_mode)
        session_inputs = {key: value for key, value in inputs.items() if key in {item.name for item in session.get_inputs()}}
        outputs = session.run(None, session_inputs)
        last_hidden_state = np.asarray(outputs[0], dtype=np.float32)
        if last_hidden_state.ndim == 3:
            pooled = self._mean_pool(last_hidden_state, inputs["attention_mask"])
        elif last_hidden_state.ndim == 2:
            pooled = last_hidden_state
        else:
            raise RuntimeError(f"Salida ONNX inesperada: {last_hidden_state.shape!r}")
        pooled = _l2_normalize(np.asarray(pooled, dtype=np.float32))
        if pooled.shape[1] != self.manifest.embedding_dimension:
            raise RuntimeError(f"Dimension inesperada: {pooled.shape[1]} != {self.manifest.embedding_dimension}")
        return pooled

