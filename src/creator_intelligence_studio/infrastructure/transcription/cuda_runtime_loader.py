"""Localizacion y registro de runtimes NVIDIA dentro del proceso actual."""

from __future__ import annotations

import os
import sys
import sysconfig
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


class CudaRuntimeLoaderError(RuntimeError):
    """No se pudo localizar o registrar el runtime CUDA requerido."""


@dataclass(frozen=True, slots=True)
class CudaRuntimeLocations:
    """Carpetas de DLL detectadas en paquetes NVIDIA."""

    cuda_runtime_bin: Path | None
    cublas_bin: Path | None
    cuda_nvrtc_bin: Path | None
    cudnn_bin: Path | None
    missing: tuple[str, ...]

    @property
    def available(self) -> bool:
        return not self.missing

    @property
    def paths(self) -> tuple[Path, ...]:
        values = [
            path
            for path in (
                self.cuda_runtime_bin,
                self.cublas_bin,
                self.cuda_nvrtc_bin,
                self.cudnn_bin,
            )
            if path is not None
        ]
        return tuple(values)


def _site_packages_root() -> Path:
    purelib = sysconfig.get_paths().get("purelib")
    if purelib:
        return Path(purelib)
    return Path(sys.prefix) / "Lib" / "site-packages"


def _candidate_path(*parts: str) -> Path:
    return _site_packages_root().joinpath(*parts)


def discover_cuda_runtime_locations() -> CudaRuntimeLocations:
    """Busca los directorios de DLL instalados por paquetes nvidia-*."""

    candidates = {
        "cuda_runtime_bin": _candidate_path("nvidia", "cuda_runtime", "bin"),
        "cublas_bin": _candidate_path("nvidia", "cublas", "bin"),
        "cuda_nvrtc_bin": _candidate_path("nvidia", "cuda_nvrtc", "bin"),
        "cudnn_bin": _candidate_path("nvidia", "cudnn", "bin"),
    }
    missing: list[str] = []
    resolved: dict[str, Path | None] = {}
    for key, path in candidates.items():
        if path.exists():
            resolved[key] = path
        else:
            resolved[key] = None
            missing.append(key)
    return CudaRuntimeLocations(
        cuda_runtime_bin=resolved["cuda_runtime_bin"],
        cublas_bin=resolved["cublas_bin"],
        cuda_nvrtc_bin=resolved["cuda_nvrtc_bin"],
        cudnn_bin=resolved["cudnn_bin"],
        missing=tuple(missing),
    )


def _prepend_process_path(paths: Iterable[Path]) -> None:
    current = os.environ.get("PATH", "")
    prefix = os.pathsep.join(str(path) for path in paths)
    if not prefix:
        return
    if current:
        os.environ["PATH"] = prefix + os.pathsep + current
    else:
        os.environ["PATH"] = prefix


def register_cuda_runtime_paths(
    locations: CudaRuntimeLocations,
) -> list[AbstractContextManager[None]]:
    """Registra las rutas NVIDIA solo para el proceso actual."""

    if sys.platform != "win32":
        return []
    paths = locations.paths
    if not paths:
        return []
    handles: list[AbstractContextManager[None]] = []
    for path in paths:
        handles.append(os.add_dll_directory(str(path)))
    _prepend_process_path(paths)
    return handles


