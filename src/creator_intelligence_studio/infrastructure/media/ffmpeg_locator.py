"""Deteccion no destructiva de ffmpeg y ffprobe."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Mapping, Protocol

from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings

from creator_intelligence_studio.domain.media.value_objects import MediaToolInfo


ENV_FFMPEG_PATH = "CIS_FFMPEG_PATH"
ENV_FFPROBE_PATH = "CIS_FFPROBE_PATH"
ENV_FFMPEG_BIN_DIRECTORY = "CIS_FFMPEG_BIN_DIRECTORY"


@dataclass(frozen=True, slots=True)
class MediaTools:
    """Herramientas multimedia detectadas."""

    ffmpeg: MediaToolInfo
    ffprobe: MediaToolInfo
    resolution: object | None = None

    @property
    def available(self) -> bool:
        return self.ffmpeg.available and self.ffprobe.available


class MediaToolResolutionService(Protocol):
    """Contrato minimo para resolucion central de ffmpeg/ffprobe."""

    def resolve_media_tools(self, *, prefer_external: bool = False) -> MediaTools:
        raise NotImplementedError


def _deduplicate_paths(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    result: list[Path] = []
    for path in paths:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        result.append(path)
    return result


def _candidate_executable_names(executable: str) -> tuple[str, ...]:
    if executable.lower().endswith(".exe"):
        return (executable,)
    return (f"{executable}.exe", executable)


def _path_candidates_from_directory(directory: Path | None, executable: str) -> list[Path]:
    if directory is None:
        return []
    return [directory / executable_name for executable_name in _candidate_executable_names(executable)]


class MediaToolLocator:
    """Localiza herramientas multimedia en el sistema local."""

    def __init__(
        self,
        *,
        settings: AppSettings | None = None,
        project_root: Path | None = None,
        env: Mapping[str, str] | None = None,
        resolution_service: MediaToolResolutionService | None = None,
    ) -> None:
        self.settings = settings
        self.project_root = project_root
        self.env = os.environ if env is None else env
        self.resolution_service = resolution_service
        self._portable_directory = (
            (project_root / "tools" / "ffmpeg" / "bin") if project_root is not None else None
        )

    @contextmanager
    def acquire_lease(self, executable: str = "ffmpeg") -> Iterator[None]:
        service = self.resolution_service
        lease = None
        if service is not None:
            ffmpeg_service = getattr(service, "ffmpeg_service", None)
            if ffmpeg_service is not None:
                lease = getattr(ffmpeg_service, "acquire_lease", None)
        if callable(lease):
            with lease(executable):
                yield
        else:
            yield

    def _configured_paths(self, executable: str) -> list[Path]:
        candidates: list[Path] = []
        if self.settings and self.project_root is not None:
            resolved = self.settings.resolved_media_tool_paths(self.project_root)
            explicit_path = resolved.get(f"{executable}_path")
            bin_directory = resolved.get("ffmpeg_bin_directory")
            if explicit_path is not None:
                if explicit_path.is_dir():
                    candidates.extend(_path_candidates_from_directory(explicit_path, executable))
                else:
                    candidates.append(explicit_path)
            if bin_directory is not None:
                candidates.extend(_path_candidates_from_directory(bin_directory, executable))
        return candidates

    def _environment_paths(self, executable: str) -> list[Path]:
        candidates: list[Path] = []
        explicit_value = self.env.get(ENV_FFMPEG_PATH if executable == "ffmpeg" else ENV_FFPROBE_PATH)
        if explicit_value:
            explicit_path = Path(explicit_value).expanduser()
            if explicit_path.is_dir():
                candidates.extend(_path_candidates_from_directory(explicit_path, executable))
            else:
                candidates.append(explicit_path)
        directory_value = self.env.get(ENV_FFMPEG_BIN_DIRECTORY)
        if directory_value:
            directory_path = Path(directory_value).expanduser()
            candidates.extend(_path_candidates_from_directory(directory_path, executable))
        return candidates

    def _path_candidates(self, executable: str) -> list[Path]:
        candidates: list[Path] = []
        candidates.extend(self._configured_paths(executable))
        candidates.extend(self._environment_paths(executable))
        which = shutil.which(executable)
        if which:
            candidates.append(Path(which))
        candidates.extend(_path_candidates_from_directory(self._portable_directory, executable))
        candidates.extend(self._common_windows_paths(executable))
        return _deduplicate_paths(candidates)

    def _common_windows_paths(self, executable: str) -> list[Path]:
        directories: list[Path] = [Path(r"C:\Tools\ffmpeg\bin")]
        for env_var in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)"):
            value = self.env.get(env_var)
            if value:
                directories.append(Path(value) / "ffmpeg" / "bin")
        return [
            directory / executable_name
            for directory in directories
            for executable_name in _candidate_executable_names(executable)
        ]

    def _probe_version(self, executable_path: Path) -> tuple[str | None, str | None]:
        try:
            completed = subprocess.run(
                [str(executable_path), "-version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
            return None, str(exc)
        if completed.returncode != 0:
            return None, completed.stderr.strip() or completed.stdout.strip() or "No se pudo leer la version."
        first_line = completed.stdout.splitlines()[0].strip() if completed.stdout else None
        return first_line or None, None

    def locate(self, executable: str) -> MediaToolInfo:
        if self.resolution_service is not None:
            tools = self.resolution_service.resolve_media_tools(prefer_external=False)
            selected = tools.ffmpeg if executable == "ffmpeg" else tools.ffprobe
            if selected is not None:
                return selected
        for candidate in self._path_candidates(executable):
            if not candidate.exists() or not candidate.is_file():
                continue
            version, error_message = self._probe_version(candidate)
            return MediaToolInfo(
                name=executable,
                path=str(candidate),
                version=version,
                available=version is not None,
                error_message=error_message,
                installation_type="externally_detected",
                source="path_discovery",
                health_status="ready" if version is not None else "failed",
                managed=False,
                component_id=executable,
                reason="external_discovery",
            )
        return MediaToolInfo(
            name=executable,
            path=None,
            version=None,
            available=False,
            error_message=(
                f"No se encontro {executable} en la configuracion, en las variables "
                f"de entorno, en PATH, en {self._portable_directory or 'la carpeta portable'} "
                f"ni en ubicaciones comunes de Windows."
            ),
            installation_type="missing",
            source="unavailable",
            health_status="missing",
            managed=False,
            component_id=executable,
            reason="not_found",
        )

    def discover(self) -> MediaTools:
        return MediaTools(
            ffmpeg=self.locate("ffmpeg"),
            ffprobe=self.locate("ffprobe"),
        )


def discover_media_tools(
    *,
    settings: AppSettings | None = None,
    project_root: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> MediaTools:
    """Detecta ffmpeg y ffprobe con rutas reales si existen."""

    return MediaToolLocator(settings=settings, project_root=project_root, env=env).discover()
