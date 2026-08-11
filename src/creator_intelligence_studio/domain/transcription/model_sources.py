"""Manifiestos de fuentes productivas para modelos de transcripcion."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any


SMALL_MODEL_REPOSITORY = "Systran/faster-whisper-small"
SMALL_MODEL_REVISION = "536b0662742c02347bc0e980a01041f333bce120"
SMALL_MODEL_SOURCE_PAGE = f"https://huggingface.co/{SMALL_MODEL_REPOSITORY}/tree/{SMALL_MODEL_REVISION}"
SMALL_MODEL_LICENSE = "mit"


@dataclass(frozen=True, slots=True)
class TranscriptionModelSourceFile:
    """Archivo inmutable que forma parte de una fuente productiva de modelo."""

    relative_path: str
    source_url: str
    expected_sha256: str
    expected_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "relative_path": self.relative_path,
            "source_url": self.source_url,
            "expected_sha256": self.expected_sha256,
            "expected_bytes": self.expected_bytes,
        }


@dataclass(frozen=True, slots=True)
class TranscriptionModelSourceManifest:
    """Identidad de una fuente productiva de modelo de transcripcion."""

    model_id: str
    source_provider: str
    repository: str
    revision: str
    license: str
    source_page: str
    files: tuple[TranscriptionModelSourceFile, ...]
    friendly_name: str
    recommended_profile: str

    @property
    def total_expected_bytes(self) -> int:
        return sum(file.expected_bytes for file in self.files)

    @property
    def canonical_payload(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "source_provider": self.source_provider,
            "repository": self.repository,
            "revision": self.revision,
            "license": self.license,
            "source_page": self.source_page,
            "friendly_name": self.friendly_name,
            "recommended_profile": self.recommended_profile,
            "files": [file.to_dict() for file in self.files],
        }

    @property
    def expected_sha256(self) -> str:
        payload = json.dumps(self.canonical_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return sha256(payload).hexdigest()

    def file_manifest(self) -> tuple[dict[str, Any], ...]:
        return tuple(file.to_dict() for file in self.files)

    def source_url_for(self, relative_path: str) -> str:
        normalized = relative_path.strip().lstrip("/")
        return f"https://huggingface.co/{self.repository}/resolve/{self.revision}/{normalized}"


def build_default_transcription_model_source_manifests() -> tuple[TranscriptionModelSourceManifest, ...]:
    """Devuelve la primera fuente productiva aprobada de transcripcion."""

    repository = SMALL_MODEL_REPOSITORY
    revision = SMALL_MODEL_REVISION
    source_page = SMALL_MODEL_SOURCE_PAGE
    files = (
        TranscriptionModelSourceFile(
            relative_path="models--Systran--faster-whisper-small/snapshots/536b0662742c02347bc0e980a01041f333bce120/config.json",
            source_url=f"https://huggingface.co/{repository}/resolve/{revision}/config.json",
            expected_sha256="b55496ac7940a7ae47d2c01eab40edfd8701feec1229d9cce3b40014383fb828",
            expected_bytes=2370,
        ),
        TranscriptionModelSourceFile(
            relative_path="models--Systran--faster-whisper-small/snapshots/536b0662742c02347bc0e980a01041f333bce120/tokenizer.json",
            source_url=f"https://huggingface.co/{repository}/resolve/{revision}/tokenizer.json",
            expected_sha256="fb7b63191e9bb045082c79fd742a3106a12c99513ab30df4a0d47fa6cb6fd0ab",
            expected_bytes=2203239,
        ),
        TranscriptionModelSourceFile(
            relative_path="models--Systran--faster-whisper-small/snapshots/536b0662742c02347bc0e980a01041f333bce120/vocabulary.txt",
            source_url=f"https://huggingface.co/{repository}/resolve/{revision}/vocabulary.txt",
            expected_sha256="34ce3fe1c5041027b3f8d42912270993f986dbc4bb34cf27f951e34a1e453913",
            expected_bytes=459861,
        ),
        TranscriptionModelSourceFile(
            relative_path="models--Systran--faster-whisper-small/snapshots/536b0662742c02347bc0e980a01041f333bce120/model.bin",
            source_url=f"https://huggingface.co/{repository}/resolve/{revision}/model.bin",
            expected_sha256="3e305921506d8872816023e4c273e75d2419fb89b24da97b4fe7bce14170d671",
            expected_bytes=483546902,
        ),
    )
    return (
        TranscriptionModelSourceManifest(
            model_id="transcription-model.small",
            source_provider="huggingface",
            repository=repository,
            revision=revision,
            license=SMALL_MODEL_LICENSE,
            source_page=source_page,
            files=files,
            friendly_name="Modelo de transcripcion - Equilibrado",
            recommended_profile="balanced",
        ),
    )


def get_transcription_model_source_manifest(model_id: str) -> TranscriptionModelSourceManifest | None:
    normalized = model_id.strip().lower()
    return next((manifest for manifest in build_default_transcription_model_source_manifests() if manifest.model_id.lower() == normalized), None)
