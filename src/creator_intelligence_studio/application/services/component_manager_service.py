"""Facade ligera para catalogo, inventario y resolucion de capacidad."""

from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass

from creator_intelligence_studio.domain.components.catalog import build_default_component_catalog, build_default_transcription_profiles
from creator_intelligence_studio.domain.components.entities import (
    ComponentCatalog,
    ComponentCategory,
    ComponentEvent,
    ComponentInstallKind,
    ComponentInstallation,
    ComponentInstallationStatus,
    RuntimeCheckStatus,
)
from creator_intelligence_studio.domain.components.repositories import ComponentManagerRepository
from creator_intelligence_studio.domain.transcription.value_objects import TranscriptionModelStatus
from creator_intelligence_studio.infrastructure.media.ffmpeg_locator import MediaToolLocator
from creator_intelligence_studio.infrastructure.transcription.model_manager import TranscriptionModelManager
from creator_intelligence_studio.shared.paths import ProjectPaths

from .hardware_capability_service import HardwareCapabilityReport, HardwareCapabilityService
from .transcription_capability_resolver import TranscriptionCapabilityPresentation, TranscriptionCapabilityReport, TranscriptionCapabilityResolver


@dataclass(frozen=True, slots=True)
class ComponentManagerStatus:
    """Resumen tecnico de componentes sin efectos laterales."""

    catalog: ComponentCatalog
    installations: tuple[ComponentInstallation, ...]
    hardware: HardwareCapabilityReport
    capability: TranscriptionCapabilityReport
    presentation: TranscriptionCapabilityPresentation
    events: tuple[ComponentEvent, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "catalog": self.catalog.to_dict(),
            "installations": [installation.to_dict() for installation in self.installations],
            "hardware": self.hardware.to_dict(),
            "capability": self.capability.to_dict(),
            "presentation": self.presentation.to_dict(),
            "events": [event.to_dict() for event in self.events],
        }


class ComponentManagerService:
    """Orquesta lectura de catalogo, inventario y resolver."""

    def __init__(
        self,
        *,
        paths: ProjectPaths,
        repository: ComponentManagerRepository,
        model_manager: TranscriptionModelManager | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.paths = paths
        self.repository = repository
        self.model_manager = model_manager or TranscriptionModelManager(paths.models_directory)
        self.logger = logger or logging.getLogger("creator_intelligence_studio.components")
        self.tool_locator = MediaToolLocator(project_root=paths.project_root)
        self.hardware_service = HardwareCapabilityService(paths=paths, repository=repository, logger=self.logger)
        self.resolver = TranscriptionCapabilityResolver(
            repository=repository,
            paths=paths,
            model_manager=self.model_manager,
            logger=self.logger,
            tool_locator=self.tool_locator,
        )

    def catalog(self) -> ComponentCatalog:
        catalog = self.repository.get_catalog()
        if not catalog.entries:
            return build_default_component_catalog()
        return catalog

    def _tool_installation(self, component_id: str, *, available: bool, path: str | None, version: str | None, error_message: str | None) -> ComponentInstallation:
        if available:
            status = ComponentInstallationStatus.READY
            health_status = RuntimeCheckStatus.READY
        else:
            status = ComponentInstallationStatus.MISSING
            health_status = RuntimeCheckStatus.NOT_CHECKED
        return ComponentInstallation(
            component_id=component_id,
            installation_status=status,
            installed_version=version,
            revision=None,
            install_type=ComponentInstallKind.EXTERNALLY_DETECTED,
            location_path=path,
            location_reference="path" if path else None,
            detected_at=None,
            verified_at=None,
            health_status=health_status,
            source="ffmpeg_locator",
            managed=False,
            last_error_message=error_message,
            metadata={"version": version} if version else {},
        )

    def inspect_installations(self) -> tuple[ComponentInstallation, ...]:
        catalog = self.catalog()
        tools = self.tool_locator.discover()
        installations: list[ComponentInstallation] = []
        for entry in catalog.entries:
            if entry.category == ComponentCategory.FFMPEG:
                tool = tools.ffmpeg if entry.component_id == "ffmpeg" else tools.ffprobe
                installations.append(
                    self._tool_installation(
                        entry.component_id,
                        available=tool.available,
                        path=tool.path,
                        version=tool.version,
                        error_message=tool.error_message,
                    )
                )
                continue
            if entry.category == ComponentCategory.TRANSCRIPTION_RUNTIME:
                module_name = "faster_whisper" if entry.component_id.endswith("faster-whisper") else "ctranslate2"
                try:
                    module = importlib.import_module(module_name)
                    version = getattr(module, "__version__", None)
                    installations.append(
                        ComponentInstallation(
                            component_id=entry.component_id,
                            installation_status=ComponentInstallationStatus.READY,
                            installed_version=version,
                            revision=entry.revision,
                            install_type=ComponentInstallKind.MANAGED,
                            location_path=None,
                            location_reference="python_package",
                            detected_at=None,
                            verified_at=None,
                            health_status=RuntimeCheckStatus.READY,
                            source="python_import",
                            managed=True,
                            metadata={},
                        )
                    )
                except Exception as exc:
                    installations.append(
                        ComponentInstallation(
                            component_id=entry.component_id,
                            installation_status=ComponentInstallationStatus.MISSING,
                            installed_version=None,
                            revision=None,
                            install_type=ComponentInstallKind.EXTERNALLY_DETECTED,
                            location_path=None,
                            location_reference="python_package",
                            detected_at=None,
                            verified_at=None,
                            health_status=RuntimeCheckStatus.FAILED,
                            source="python_import",
                            managed=False,
                            last_error_message=str(exc),
                            metadata={},
                        )
                    )
                continue
            if entry.category == ComponentCategory.TRANSCRIPTION_MODEL:
                model_name = entry.component_id.split(".", 1)[-1]
                model_info = self.model_manager.inspect_model_availability(model_name)
                status_map = {
                    TranscriptionModelStatus.INSTALLED: ComponentInstallationStatus.READY,
                    TranscriptionModelStatus.NOT_INSTALLED: ComponentInstallationStatus.MISSING,
                    TranscriptionModelStatus.DOWNLOADING: ComponentInstallationStatus.UNKNOWN,
                    TranscriptionModelStatus.INCOMPLETE: ComponentInstallationStatus.INVALID,
                    TranscriptionModelStatus.CORRUPT: ComponentInstallationStatus.INVALID,
                    TranscriptionModelStatus.INCOMPATIBLE: ComponentInstallationStatus.INCOMPATIBLE,
                    TranscriptionModelStatus.ERROR: ComponentInstallationStatus.INVALID,
                }
                installations.append(
                    ComponentInstallation(
                        component_id=entry.component_id,
                        installation_status=status_map.get(model_info.status, ComponentInstallationStatus.UNKNOWN),
                        installed_version=model_info.model_name if model_info.installed else None,
                        revision=entry.revision,
                        install_type=ComponentInstallKind.EXTERNALLY_DETECTED,
                        location_path=model_info.path,
                        location_reference="cache" if model_info.path else None,
                        detected_at=None,
                        verified_at=None,
                        health_status=RuntimeCheckStatus.READY if model_info.installed else RuntimeCheckStatus.NOT_CHECKED,
                        source="model_manager.inspect_model_availability",
                        managed=False,
                        last_error_code=model_info.error_code,
                        last_error_message=model_info.error_message,
                        metadata={"profile": model_info.profile, "notes": model_info.notes or ""},
                    )
                )
                continue
        return tuple(installations)

    def inspect_hardware(self) -> HardwareCapabilityReport:
        hardware = self.hardware_service.collect_inventory(persist=False)
        runtime = self.hardware_service.collect_runtime_check(persist=False)
        return HardwareCapabilityReport(hardware_profile=hardware, runtime_check=runtime)

    def resolve_transcription_capability(
        self,
        *,
        profile: str = "balanced",
        preferred_device: str = "auto",
    ) -> TranscriptionCapabilityReport:
        hardware = self.hardware_service.collect_inventory(persist=False)
        installations = {installation.component_id: installation for installation in self.inspect_installations()}
        available_disk_bytes = max((volume.free_bytes or 0) for volume in hardware.disk_volumes) if hardware.disk_volumes else None
        return self.resolver.resolve(
            requested_profile=profile,
            preferred_device=preferred_device,
            available_disk_bytes=available_disk_bytes,
            installations=installations,
            hardware_profile=hardware,
        )

    def describe_transcription_capability(
        self,
        *,
        profile: str = "balanced",
        preferred_device: str = "auto",
    ) -> TranscriptionCapabilityPresentation:
        return self.resolver.present(self.resolve_transcription_capability(profile=profile, preferred_device=preferred_device))

    def status(self, *, profile: str = "balanced", preferred_device: str = "auto") -> ComponentManagerStatus:
        catalog = self.catalog()
        installations = self.inspect_installations()
        hardware = self.hardware_service.collect_inventory(persist=False)
        runtime = self.hardware_service.collect_runtime_check(persist=False)
        capability = self.resolver.resolve(
            requested_profile=profile,
            preferred_device=preferred_device,
            available_disk_bytes=max((volume.free_bytes or 0) for volume in hardware.disk_volumes) if hardware.disk_volumes else None,
            installations={installation.component_id: installation for installation in installations},
            hardware_profile=hardware,
        )
        presentation = self.resolver.present(capability)
        return ComponentManagerStatus(
            catalog=catalog,
            installations=installations,
            hardware=HardwareCapabilityReport(hardware_profile=hardware, runtime_check=runtime),
            capability=capability,
            presentation=presentation,
            events=self.repository.list_events(),
        )
