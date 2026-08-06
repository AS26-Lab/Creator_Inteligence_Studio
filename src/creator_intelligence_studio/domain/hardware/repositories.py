"""Contrato para persistencia de inventario de hardware."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .entities import HardwareProfile


class HardwareInventoryRepository(ABC):
    """Persistencia de snapshots de hardware local."""

    @abstractmethod
    def list_hardware_profiles(self) -> tuple[HardwareProfile, ...]:
        raise NotImplementedError

    @abstractmethod
    def latest_hardware_profile(self) -> HardwareProfile | None:
        raise NotImplementedError

    @abstractmethod
    def upsert_hardware_profile(self, profile: HardwareProfile) -> HardwareProfile:
        raise NotImplementedError
