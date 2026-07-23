"""Muestreo liviano de recursos para evaluacion operativa."""

from __future__ import annotations

import ctypes
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ResourceSample:
    ram_total_bytes: int | None
    ram_available_bytes: int | None
    vram_total_mib: int | None
    vram_used_mib: int | None
    vram_free_mib: int | None
    cpu_count: int | None
    disk_free_bytes: int | None

    def to_dict(self) -> dict[str, object]:
        return {
            "ram_total_bytes": self.ram_total_bytes,
            "ram_available_bytes": self.ram_available_bytes,
            "vram_total_mib": self.vram_total_mib,
            "vram_used_mib": self.vram_used_mib,
            "vram_free_mib": self.vram_free_mib,
            "cpu_count": self.cpu_count,
            "disk_free_bytes": self.disk_free_bytes,
        }


def _sample_ram() -> tuple[int | None, int | None]:
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

        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
            return int(stat.ullTotalPhys), int(stat.ullAvailPhys)
    except Exception:
        pass
    return None, None


def _sample_vram() -> tuple[int | None, int | None, int | None]:
    try:
        completed = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=memory.total,memory.used,memory.free",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if completed.returncode != 0 or not completed.stdout.strip():
            return None, None, None
        first_line = completed.stdout.strip().splitlines()[0]
        parts = [part.strip() for part in first_line.split(",")]
        if len(parts) < 3:
            return None, None, None
        return int(parts[0]), int(parts[1]), int(parts[2])
    except Exception:
        return None, None, None


def sample_resources(project_root: Path) -> ResourceSample:
    ram_total, ram_available = _sample_ram()
    vram_total, vram_used, vram_free = _sample_vram()
    return ResourceSample(
        ram_total_bytes=ram_total,
        ram_available_bytes=ram_available,
        vram_total_mib=vram_total,
        vram_used_mib=vram_used,
        vram_free_mib=vram_free,
        cpu_count=os.cpu_count(),
        disk_free_bytes=_disk_free(project_root),
    )


def _disk_free(path: Path) -> int | None:
    try:
        return int(subprocess.run(
            ["powershell", "-NoProfile", "-Command", f"(Get-PSDrive -Name '{path.drive[0]}').Free"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        ).stdout.strip() or 0) or None
    except Exception:
        try:
            import shutil

            return shutil.disk_usage(path).free
        except Exception:
            return None
