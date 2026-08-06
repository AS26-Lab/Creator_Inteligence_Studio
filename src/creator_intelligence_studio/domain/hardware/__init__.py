"""Dominio de inventario de hardware local."""

from .entities import (
    DiskVolumeSummary,
    GpuSummary,
    HardwareCapabilityState,
    HardwareProfile,
)
from .repositories import HardwareInventoryRepository

__all__ = [
    "DiskVolumeSummary",
    "GpuSummary",
    "HardwareCapabilityState",
    "HardwareInventoryRepository",
    "HardwareProfile",
]
