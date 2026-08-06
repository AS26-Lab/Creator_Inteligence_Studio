"""Inventario ligero y determinista de hardware local."""

from __future__ import annotations

import ctypes
import logging
import os
import platform
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from creator_intelligence_studio.domain.components.entities import RuntimeCheckRecord, RuntimeCheckStatus
from creator_intelligence_studio.domain.hardware.entities import (
    DiskVolumeSummary,
    GpuSummary,
    HardwareCapabilityState,
    HardwareProfile,
)
from creator_intelligence_studio.infrastructure.persistence.sqlite_component_manager_repository import SQLiteComponentManagerRepository
from creator_intelligence_studio.shared.paths import ProjectPaths


@dataclass(frozen=True, slots=True)
class HardwareCapabilityReport:
    """Resultado de inventario y comprobacion de runtime."""

    hardware_profile: HardwareProfile
    runtime_check: RuntimeCheckRecord

    def to_dict(self) -> dict[str, object]:
        return {
            "hardware_profile": self.hardware_profile.to_dict(),
            "runtime_check": self.runtime_check.to_dict(),
        }


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _safe_disk_usage(path: Path) -> tuple[int | None, int | None]:
    try:
        usage = shutil.disk_usage(path)
    except Exception:
        return None, None
    return usage.free, usage.total


def _system_ram_bytes() -> tuple[int | None, int | None]:
    if os.name == "nt":
        try:
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = MEMORYSTATUSEX()
            status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return int(status.ullTotalPhys), int(status.ullAvailPhys)
        except Exception:
            return None, None
    elif hasattr(os, "sysconf"):
        try:
            pagesize = os.sysconf("SC_PAGE_SIZE")
            phys_pages = os.sysconf("SC_PHYS_PAGES")
            avphys_pages = os.sysconf("SC_AVPHYS_PAGES")
            if isinstance(pagesize, int) and isinstance(phys_pages, int) and isinstance(avphys_pages, int):
                return pagesize * phys_pages, pagesize * avphys_pages
        except (ValueError, OSError, AttributeError):
            return None, None
    return None, None


def _detect_nvidia_gpu() -> GpuSummary:
    executable = shutil.which("nvidia-smi")
    if executable is None:
        return GpuSummary(
            vendor=None,
            name=None,
            driver_version=None,
            vram_total_bytes=None,
            cuda_visible=False,
            status=HardwareCapabilityState.NOT_DETECTED,
            notes="nvidia-smi no esta disponible.",
        )
    try:
        completed = subprocess.run(
            [
                executable,
                "--query-gpu=name,driver_version,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return GpuSummary(
            vendor="nvidia",
            name=None,
            driver_version=None,
            vram_total_bytes=None,
            cuda_visible=True,
            status=HardwareCapabilityState.UNKNOWN,
            notes=f"nvidia-smi excedio el tiempo permitido: {exc.timeout}s.",
        )
    except Exception as exc:
        return GpuSummary(
            vendor="nvidia",
            name=None,
            driver_version=None,
            vram_total_bytes=None,
            cuda_visible=True,
            status=HardwareCapabilityState.DEGRADED,
            notes=str(exc),
        )
    if completed.returncode != 0:
        return GpuSummary(
            vendor="nvidia",
            name=None,
            driver_version=None,
            vram_total_bytes=None,
            cuda_visible=True,
            status=HardwareCapabilityState.DEGRADED,
            notes=completed.stderr.strip() or completed.stdout.strip() or "nvidia-smi devolvio error.",
        )
    line = completed.stdout.strip().splitlines()[0] if completed.stdout.strip() else ""
    if not line:
        return GpuSummary(
            vendor="nvidia",
            name=None,
            driver_version=None,
            vram_total_bytes=None,
            cuda_visible=True,
            status=HardwareCapabilityState.UNKNOWN,
            notes="nvidia-smi no devolvio informacion util.",
        )
    parts = [part.strip() for part in line.split(",")]
    name = parts[0] if len(parts) > 0 else None
    driver = parts[1] if len(parts) > 1 else None
    vram_text = parts[2] if len(parts) > 2 else None
    try:
        vram_bytes = int(float(vram_text) * 1024 * 1024) if vram_text else None
    except ValueError:
        vram_bytes = None
    return GpuSummary(
        vendor="nvidia",
        name=name or None,
        driver_version=driver or None,
        vram_total_bytes=vram_bytes,
        cuda_visible=True,
        status=HardwareCapabilityState.REPORTED_NOT_TESTED,
        notes="GPU NVIDIA detectada; falta prueba funcional de transcripcion.",
    )


def _ctranslate2_cuda_status() -> tuple[HardwareCapabilityState, str | None, str | None]:
    try:
        import ctranslate2  # type: ignore

        device_count = 0
        supported: tuple[str, ...] = ()
        try:
            device_count = int(ctranslate2.get_cuda_device_count())
        except Exception:
            device_count = 0
        if device_count > 0:
            try:
                supported = tuple(str(item) for item in ctranslate2.get_supported_compute_types("cuda"))
            except Exception:
                supported = ()
            return HardwareCapabilityState.REPORTED_NOT_TESTED, getattr(ctranslate2, "__version__", None), f"device_count={device_count}; supported={list(supported)}"
        return HardwareCapabilityState.NOT_DETECTED, getattr(ctranslate2, "__version__", None), "CUDA no reportada por CTranslate2."
    except Exception as exc:
        return HardwareCapabilityState.FAILED, None, str(exc)


class HardwareCapabilityService:
    """Inventario tecnico local sin benchmark pesado."""

    def __init__(
        self,
        *,
        paths: ProjectPaths,
        repository: SQLiteComponentManagerRepository | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.paths = paths
        self.repository = repository
        self.logger = logger or logging.getLogger("creator_intelligence_studio.components.hardware")

    def collect_inventory(self, *, persist: bool = False) -> HardwareProfile:
        platform_name = platform.system() or os.name
        architecture = platform.machine() or platform.architecture()[0]
        cpu_logical = os.cpu_count()
        ram_total, ram_available = _system_ram_bytes()
        gpu = _detect_nvidia_gpu()
        ctranslate2_state, ctranslate2_version, ctranslate2_notes = _ctranslate2_cuda_status()
        cuda_reported = ctranslate2_notes if gpu.cuda_visible else None
        volumes = []
        for volume_path in (self.paths.data_directory, self.paths.models_directory, Path(tempfile.gettempdir())):
            free_bytes, total_bytes = _safe_disk_usage(volume_path)
            volumes.append(
                DiskVolumeSummary(
                    path=str(volume_path),
                    free_bytes=free_bytes,
                    total_bytes=total_bytes,
                    status=HardwareCapabilityState.DETECTED if free_bytes is not None else HardwareCapabilityState.UNKNOWN,
                    notes=None if free_bytes is not None else "No se pudo leer el volumen.",
                )
            )
        status = HardwareCapabilityState.REPORTED_NOT_TESTED if gpu.status == HardwareCapabilityState.REPORTED_NOT_TESTED else (
            HardwareCapabilityState.NOT_DETECTED if gpu.status == HardwareCapabilityState.NOT_DETECTED else gpu.status
        )
        profile = HardwareProfile(
            generated_at=_utc_now(),
            platform=platform_name,
            architecture=architecture,
            cpu_logical_count=cpu_logical,
            cpu_summary=f"{platform_name} {architecture}; logical={cpu_logical}" if cpu_logical is not None else None,
            ram_total_bytes=ram_total,
            ram_available_bytes=ram_available,
            gpu=gpu,
            driver_summary=gpu.driver_version,
            cuda_reported=cuda_reported,
            ctranslate2_cuda_status=ctranslate2_state,
            disk_volumes=tuple(volumes),
            detection_source="local",
            status=status,
            warnings=(
                "Se detecto una GPU NVIDIA, pero todavia no se ha comprobado que funcione con el motor de transcripcion.",
            )
            if gpu.status == HardwareCapabilityState.REPORTED_NOT_TESTED
            else (),
            errors=(),
            created_at=_utc_now(),
            updated_at=_utc_now(),
        )
        if persist and self.repository is not None:
            self.repository.upsert_hardware_profile(profile)
        return profile

    def collect_runtime_check(self, *, persist: bool = False) -> RuntimeCheckRecord:
        state, version, notes = _ctranslate2_cuda_status()
        record = RuntimeCheckRecord(
            component_id="transcription-runtime.ctranslate2",
            status=state,
            runtime_importable=state != HardwareCapabilityState.FAILED,
            runtime_version=version,
            device_count=1 if state == HardwareCapabilityState.REPORTED_NOT_TESTED else 0,
            supported_compute_types=("int8", "int8_float16") if state == HardwareCapabilityState.REPORTED_NOT_TESTED else (),
            notes=notes,
            warning_message=(
                "Se detecto capacidad CUDA reportada, pero todavia no existe prueba funcional."
                if state == HardwareCapabilityState.REPORTED_NOT_TESTED
                else None
            ),
            error_code=None if state != HardwareCapabilityState.FAILED else "runtime_import_failed",
            error_message=notes if state == HardwareCapabilityState.FAILED else None,
            metadata={"runtime_version": version} if version else {},
            checked_at=_utc_now(),
            created_at=_utc_now(),
            updated_at=_utc_now(),
        )
        if persist and self.repository is not None:
            self.repository.upsert_runtime_check(record)
        return record
