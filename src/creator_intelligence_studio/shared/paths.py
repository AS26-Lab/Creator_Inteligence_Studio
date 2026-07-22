"""Resolucion centralizada de rutas del proyecto."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from creator_intelligence_studio.infrastructure.configuration.settings import (
        AppSettings,
    )


def discover_project_root(start: Path | None = None) -> Path:
    """Encuentra la raiz del proyecto buscando archivos de referencia."""

    candidate = (start or Path(__file__).resolve()).resolve()
    if candidate.is_file():
        candidate = candidate.parent

    for current in (candidate, *candidate.parents):
        if (current / "pyproject.toml").exists() and (current / "docs").exists():
            return current
    raise FileNotFoundError("No se pudo determinar la raiz del proyecto.")


def resolve_configured_path(project_root: Path, configured_value: str) -> Path:
    """Resuelve una ruta configurada sin asumir una unidad fija."""

    candidate = Path(configured_value).expanduser()
    if candidate.is_absolute():
        return candidate
    return (project_root / candidate).resolve()


@dataclass(frozen=True)
class ProjectPaths:
    """Rutas principales del proyecto."""

    project_root: Path
    config_directory: Path
    data_directory: Path
    logs_directory: Path
    models_directory: Path
    artifacts_directory: Path

    @classmethod
    def from_settings(cls, project_root: Path, settings: AppSettings) -> "ProjectPaths":
        """Construye las rutas del proyecto a partir de la configuracion."""

        resolved = settings.resolved_directories(project_root)
        return cls(
            project_root=project_root,
            config_directory=project_root / "config",
            data_directory=resolved["data_directory"],
            logs_directory=resolved["logs_directory"],
            models_directory=resolved["models_directory"],
            artifacts_directory=resolved["artifacts_directory"],
        )

    def ensure_runtime_directories(self) -> None:
        """Crea los directorios operativos necesarios."""

        for directory in (
            self.data_directory,
            self.logs_directory,
            self.models_directory,
            self.artifacts_directory,
        ):
            directory.mkdir(parents=True, exist_ok=True)

    def free_space_bytes(self) -> int | None:
        """Devuelve el espacio libre de la unidad del proyecto."""

        try:
            return shutil.disk_usage(self.project_root).free
        except Exception:
            return None
