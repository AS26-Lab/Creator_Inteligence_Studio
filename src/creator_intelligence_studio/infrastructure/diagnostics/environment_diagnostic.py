"""Diagnostico no destructivo del entorno."""

from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

from creator_intelligence_studio import APP_NAME, VERSION
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.diagnostics.models import (
    DiagnosticState,
    EnvironmentDiagnostic,
    GpuInfo,
)
from creator_intelligence_studio.shared.paths import ProjectPaths


def _run_command(args: list[str], timeout_seconds: float = 5.0) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


def _parse_nvidia_smi_output(output: str) -> tuple[str | None, str | None, list[GpuInfo], list[str]]:
    warnings: list[str] = []
    cuda_version = None
    driver_version = None
    gpu_devices: list[GpuInfo] = []

    header_match = re.search(r"CUDA Version:\s*([\d.]+)", output)
    if header_match:
        cuda_version = header_match.group(1)

    driver_match = re.search(r"Driver Version:\s*([\d.]+)", output)
    if driver_match:
        driver_version = driver_match.group(1)

    query = _run_command(
        [
            "nvidia-smi",
            "--query-gpu=name,driver_version,memory.total",
            "--format=csv,noheader,nounits",
        ]
    )
    if query and query.returncode == 0 and query.stdout.strip():
        for row in query.stdout.strip().splitlines():
            parts = [part.strip() for part in row.split(",")]
            if not parts:
                continue
            name = parts[0] or "no verificado"
            gpu_driver = parts[1] if len(parts) > 1 else None
            memory_total_mib = None
            if len(parts) > 2:
                try:
                    memory_total_mib = int(float(parts[2]))
                except ValueError:
                    memory_total_mib = None
            gpu_devices.append(
                GpuInfo(
                    name=name,
                    driver_version=gpu_driver or driver_version,
                    memory_total_mib=memory_total_mib,
                )
            )
    else:
        warnings.append("No se pudo consultar la lista detallada de GPUs con nvidia-smi.")

    return cuda_version, driver_version, gpu_devices, warnings


def collect_environment_diagnostic(
    settings: AppSettings,
    paths: ProjectPaths,
) -> EnvironmentDiagnostic:
    """Recopila diagnostico del entorno sin modificar el sistema."""

    os_name = platform.system() or "no verificado"
    os_version = platform.version() or platform.release() or None
    os_architecture = platform.architecture()[0] if platform.architecture() else None
    python_version = platform.python_version()
    python_executable = sys.executable
    cpu_reported = _normalize_text(os.environ.get("PROCESSOR_IDENTIFIER")) or _normalize_text(
        platform.processor()
    )
    logical_processors = os.cpu_count()

    warnings: list[str] = []
    errors: list[str] = []

    project_root = paths.project_root
    disk_usage = None
    try:
        disk_usage = shutil.disk_usage(project_root.anchor or project_root)
    except OSError as exc:
        warnings.append(f"No se pudo medir el espacio libre del proyecto: {exc}")

    git_available = shutil.which("git") is not None
    git_version = None
    if git_available:
        git_result = _run_command(["git", "--version"])
        if git_result and git_result.returncode == 0:
            git_version = _normalize_text(git_result.stdout)
        else:
            warnings.append("Git esta disponible en PATH, pero no se pudo leer su version.")
    else:
        warnings.append("Git no esta disponible en PATH.")

    nvidia_smi_available = shutil.which("nvidia-smi") is not None
    gpu_devices: list[GpuInfo] = []
    cuda_version_reported = None
    nvidia_driver_version = None
    cuda_runtime_not_verified = True
    if nvidia_smi_available:
        nvidia_result = _run_command(["nvidia-smi"])
        if nvidia_result and nvidia_result.returncode == 0:
            cuda_version_reported, nvidia_driver_version, gpu_devices, gpu_warnings = _parse_nvidia_smi_output(
                nvidia_result.stdout
            )
            warnings.extend(gpu_warnings)
            warnings.append(
                "CUDA runtime no verificado; nvidia-smi solo confirma el driver y la GPU detectada."
            )
        else:
            warnings.append(
                "nvidia-smi esta disponible, pero no devolvio una respuesta utilizable."
            )
    else:
        warnings.append("nvidia-smi no esta disponible.")

    state = DiagnosticState(
        ready_for_basic_mode=settings.allow_cpu_basic_mode,
        cuda_driver_detected=bool(gpu_devices),
        cuda_runtime_not_verified=cuda_runtime_not_verified,
        warnings=tuple(warnings),
    )

    return EnvironmentDiagnostic(
        application_name=APP_NAME,
        application_version=VERSION,
        project_root=project_root,
        os_name=os_name,
        os_version=os_version,
        os_architecture=os_architecture,
        python_version=python_version,
        python_executable=python_executable,
        cpu_reported=cpu_reported,
        logical_processors=logical_processors,
        nvidia_smi_available=nvidia_smi_available,
        gpu_devices=tuple(gpu_devices),
        nvidia_driver_version=nvidia_driver_version,
        cuda_version_reported=cuda_version_reported,
        git_available=git_available,
        git_version=git_version,
        free_space_bytes=(disk_usage.free if disk_usage else None),
        preferred_compute_backend=settings.preferred_compute_backend,
        state=state,
        warnings=tuple(warnings),
        errors=tuple(errors),
    )
