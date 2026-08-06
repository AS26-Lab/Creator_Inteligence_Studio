"""Contratos de persistencia para componentes locales."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .entities import (
    ComponentCatalog,
    ComponentCatalogEntry,
    ComponentEvent,
    ComponentInstallation,
    RuntimeCheckRecord,
)
from creator_intelligence_studio.domain.hardware.entities import HardwareProfile
from creator_intelligence_studio.domain.transcription.profiles import TranscriptionProfileDefinition


class ComponentManagerRepository(ABC):
    """Contrato unico para lectura/escritura de foundation v32-A."""

    @abstractmethod
    def get_catalog(self) -> ComponentCatalog:
        raise NotImplementedError

    @abstractmethod
    def list_catalog_entries(self) -> tuple[ComponentCatalogEntry, ...]:
        raise NotImplementedError

    @abstractmethod
    def get_catalog_entry(self, component_id: str) -> ComponentCatalogEntry | None:
        raise NotImplementedError

    @abstractmethod
    def upsert_catalog_entry(self, entry: ComponentCatalogEntry) -> ComponentCatalogEntry:
        raise NotImplementedError

    @abstractmethod
    def list_installations(self) -> tuple[ComponentInstallation, ...]:
        raise NotImplementedError

    @abstractmethod
    def get_installation(self, component_id: str) -> ComponentInstallation | None:
        raise NotImplementedError

    @abstractmethod
    def upsert_installation(self, installation: ComponentInstallation) -> ComponentInstallation:
        raise NotImplementedError

    @abstractmethod
    def list_hardware_profiles(self) -> tuple[HardwareProfile, ...]:
        raise NotImplementedError

    @abstractmethod
    def upsert_hardware_profile(self, profile: HardwareProfile) -> HardwareProfile:
        raise NotImplementedError

    @abstractmethod
    def latest_hardware_profile(self) -> HardwareProfile | None:
        raise NotImplementedError

    @abstractmethod
    def list_transcription_profiles(self) -> tuple[TranscriptionProfileDefinition, ...]:
        raise NotImplementedError

    @abstractmethod
    def get_transcription_profile(self, profile_id: str) -> TranscriptionProfileDefinition | None:
        raise NotImplementedError

    @abstractmethod
    def upsert_transcription_profile(self, profile: TranscriptionProfileDefinition) -> TranscriptionProfileDefinition:
        raise NotImplementedError

    @abstractmethod
    def list_runtime_checks(self) -> tuple[RuntimeCheckRecord, ...]:
        raise NotImplementedError

    @abstractmethod
    def upsert_runtime_check(self, record: RuntimeCheckRecord) -> RuntimeCheckRecord:
        raise NotImplementedError

    @abstractmethod
    def append_event(self, event: ComponentEvent) -> ComponentEvent:
        raise NotImplementedError

    @abstractmethod
    def list_events(self) -> tuple[ComponentEvent, ...]:
        raise NotImplementedError
