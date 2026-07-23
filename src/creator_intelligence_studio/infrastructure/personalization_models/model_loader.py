"""Carga segura de artefactos activos de modelos personalizados."""

from __future__ import annotations

from pathlib import Path

from creator_intelligence_studio.domain.personalization_models.errors import PersonalizationModelArtifactError
from creator_intelligence_studio.infrastructure.personalization_models.artifact_store import load_model_artifact


def load_active_model_artifact(artifact_root: Path):
    if not artifact_root.exists():
        raise PersonalizationModelArtifactError("No existe un artefacto de modelo activo.")
    return load_model_artifact(artifact_root)
