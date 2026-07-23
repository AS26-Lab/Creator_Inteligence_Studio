"""Almacen local de artefactos de modelos personalizados."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib

from creator_intelligence_studio.domain.personalization_models.errors import PersonalizationModelArtifactError
from creator_intelligence_studio.shared.dates import to_iso_z, utc_now


PersonalizationModelManifestVersion = "1"


@dataclass(frozen=True, slots=True)
class PersonalizationModelManifest:
    manifest_version: str
    creator_id: str
    project_id: str | None
    snapshot_id: str
    training_run_id: str
    model_name: str
    model_family: str
    model_version: str
    trainer_version: str
    feature_schema_version: str
    label_schema_version: str
    configuration_fingerprint: str
    source_fingerprint: str
    artifact_fingerprint: str
    threshold: float
    python_version: str
    platform: str
    dependencies: dict[str, str]
    metrics_summary: dict[str, Any]
    created_at: str

    def to_dict(self) -> dict[str, object]:
        return {
            "manifest_version": self.manifest_version,
            "creator_id": self.creator_id,
            "project_id": self.project_id,
            "snapshot_id": self.snapshot_id,
            "training_run_id": self.training_run_id,
            "model_name": self.model_name,
            "model_family": self.model_family,
            "model_version": self.model_version,
            "trainer_version": self.trainer_version,
            "feature_schema_version": self.feature_schema_version,
            "label_schema_version": self.label_schema_version,
            "configuration_fingerprint": self.configuration_fingerprint,
            "source_fingerprint": self.source_fingerprint,
            "artifact_fingerprint": self.artifact_fingerprint,
            "threshold": self.threshold,
            "python_version": self.python_version,
            "platform": self.platform,
            "dependencies": dict(self.dependencies),
            "metrics_summary": dict(self.metrics_summary),
            "created_at": self.created_at,
        }


@dataclass(frozen=True, slots=True)
class PersonalizationModelArtifact:
    model: Any
    manifest: PersonalizationModelManifest
    manifest_path: Path
    model_path: Path
    metrics_path: Path
    feature_schema_path: Path


def _artifact_fingerprint(model_path: Path, manifest_payload: dict[str, Any]) -> str:
    digest = hashlib.sha256()
    digest.update(model_path.read_bytes())
    digest.update(json.dumps(manifest_payload, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8"))
    return digest.hexdigest()


def _safe_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=path.parent, suffix=".tmp") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True, default=str)
        temp_path = Path(handle.name)
    os.replace(temp_path, path)


def save_model_artifact(
    *,
    artifact_root: Path,
    model: Any,
    manifest: PersonalizationModelManifest,
    metrics_payload: dict[str, Any],
    feature_schema_payload: dict[str, Any],
) -> PersonalizationModelArtifact:
    artifact_root.mkdir(parents=True, exist_ok=True)
    model_path = artifact_root / "model.joblib"
    manifest_path = artifact_root / "manifest.json"
    metrics_path = artifact_root / "metrics.json"
    feature_schema_path = artifact_root / "feature_schema.json"
    temp_model = model_path.with_suffix(".joblib.tmp")
    joblib.dump(model, temp_model)
    os.replace(temp_model, model_path)
    _safe_write_json(metrics_path, metrics_payload)
    _safe_write_json(feature_schema_path, feature_schema_payload)
    manifest_payload = manifest.to_dict()
    manifest_payload["artifact_fingerprint"] = _artifact_fingerprint(model_path, manifest_payload)
    _safe_write_json(manifest_path, manifest_payload)
    verified_manifest = PersonalizationModelManifest(**manifest_payload)
    return PersonalizationModelArtifact(
        model=model,
        manifest=verified_manifest,
        manifest_path=manifest_path,
        model_path=model_path,
        metrics_path=metrics_path,
        feature_schema_path=feature_schema_path,
    )


def verify_model_artifact_path(artifact_root: Path) -> bool:
    return artifact_root.is_dir() and (artifact_root / "model.joblib").exists() and (artifact_root / "manifest.json").exists()


def load_model_artifact(artifact_root: Path) -> PersonalizationModelArtifact:
    manifest_path = artifact_root / "manifest.json"
    model_path = artifact_root / "model.joblib"
    metrics_path = artifact_root / "metrics.json"
    feature_schema_path = artifact_root / "feature_schema.json"
    if not verify_model_artifact_path(artifact_root):
        raise PersonalizationModelArtifactError("El artefacto de modelo no esta completo.")
    with manifest_path.open("r", encoding="utf-8") as handle:
        manifest_payload = json.load(handle)
    verification_payload = dict(manifest_payload)
    verification_payload["artifact_fingerprint"] = ""
    fingerprint = _artifact_fingerprint(model_path, verification_payload)
    if manifest_payload.get("artifact_fingerprint") != fingerprint:
        raise PersonalizationModelArtifactError("El fingerprint del artefacto no coincide.")
    model = joblib.load(model_path)
    manifest = PersonalizationModelManifest(**manifest_payload)
    return PersonalizationModelArtifact(
        model=model,
        manifest=manifest,
        manifest_path=manifest_path,
        model_path=model_path,
        metrics_path=metrics_path,
        feature_schema_path=feature_schema_path,
    )


def build_default_dependencies() -> dict[str, str]:
    deps = {
        "python": platform.python_version(),
        "scikit-learn": __import__("sklearn").__version__,
        "numpy": __import__("numpy").__version__,
        "joblib": __import__("joblib").__version__,
    }
    try:
        deps["scipy"] = __import__("scipy").__version__
    except Exception:  # pragma: no cover - fallback
        deps["scipy"] = "unknown"
    return deps
