"""Resolucion centralizada de rutas del proyecto y de bundles empaquetados."""

from __future__ import annotations

import os
import sys
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

    if getattr(sys, "frozen", False):
        executable = Path(getattr(sys, "executable", start or Path.cwd())).resolve()
        return executable.parent
    candidate = (start or Path(__file__).resolve()).resolve()
    if candidate.is_file():
        candidate = candidate.parent

    for current in (candidate, *candidate.parents):
        if (current / "pyproject.toml").exists() and (current / "docs").exists():
            return current
    raise FileNotFoundError("No se pudo determinar la raiz del proyecto.")


def is_packaged_application() -> bool:
    """Indica si la ejecucion proviene de un bundle empaquetado."""

    return bool(getattr(sys, "frozen", False))


def resolve_application_data_root(application_name: str) -> Path:
    """Resuelve la raiz writable del usuario para una app empaquetada."""

    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / application_name
    return Path.home() / ".local" / "share" / application_name


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
    components_directory: Path
    downloads_directory: Path
    database_path: Path
    logs_directory: Path
    models_directory: Path
    artifacts_directory: Path

    @classmethod
    def from_settings(cls, project_root: Path, settings: AppSettings) -> "ProjectPaths":
        """Construye las rutas del proyecto a partir de la configuracion."""

        resolved_base = (
            resolve_application_data_root(settings.application_name)
            if is_packaged_application()
            else project_root
        )
        resolved = settings.resolved_directories(resolved_base)
        return cls(
            project_root=project_root,
            config_directory=project_root / "config",
            data_directory=resolved["data_directory"],
            components_directory=resolved["data_directory"] / "components",
            downloads_directory=resolved["data_directory"] / "downloads",
            database_path=resolved["data_directory"] / settings.database_filename,
            logs_directory=resolved["logs_directory"],
            models_directory=resolved["models_directory"],
            artifacts_directory=resolved["artifacts_directory"],
        )

    def ensure_runtime_directories(self) -> None:
        """Crea los directorios operativos necesarios."""

        for directory in (
            self.data_directory,
            self.components_directory,
            self.downloads_directory,
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
