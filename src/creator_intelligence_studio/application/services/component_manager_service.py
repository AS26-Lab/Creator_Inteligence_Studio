"""Facade ligera para catalogo, inventario y resolucion de capacidad."""

from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass
from pathlib import Path

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
from creator_intelligence_studio.domain.media.value_objects import MediaToolInfo
from creator_intelligence_studio.domain.transcription.value_objects import TranscriptionModelStatus
from creator_intelligence_studio.infrastructure.media.ffmpeg_locator import MediaToolLocator
from creator_intelligence_studio.infrastructure.downloads.repository import FileSystemComponentDownloadRepository
from creator_intelligence_studio.application.services.transcription_installation_service import (
    ManagedTranscriptionModelInstaller,
    ManagedTranscriptionRuntimeInstaller,
    TranscriptionInstallResult,
)
from creator_intelligence_studio.infrastructure.transcription.model_manager import TranscriptionModelManager
from creator_intelligence_studio.shared.paths import ProjectPaths

from .download_manager_service import ComponentDownloadManagerService, DownloadStatusSummary
from .ffmpeg_component_service import (
    FFmpegInstallResult,
    FFmpegManagedComponentService,
    FFmpegRemovalResult,
    FFmpegResolutionReport,
)
from .transcription_runtime_benchmark_service import TranscriptionRuntimeBenchmarkService
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
        self.ffmpeg_service = FFmpegManagedComponentService(paths=paths, repository=repository, logger=self.logger)
        self.download_service = ComponentDownloadManagerService(
            paths=paths,
            repository=FileSystemComponentDownloadRepository(paths.downloads_directory),
            component_repository=repository,
            logger=self.logger,
        )
        self.transcription_runtime_installer = ManagedTranscriptionRuntimeInstaller(paths=paths, repository=repository, logger=self.logger)
        self.transcription_model_installer = ManagedTranscriptionModelInstaller(paths=paths, repository=repository, model_manager=self.model_manager, logger=self.logger)
        self.tool_locator = MediaToolLocator(project_root=paths.project_root)
        self.hardware_service = HardwareCapabilityService(paths=paths, repository=repository, logger=self.logger)
        self.resolver = TranscriptionCapabilityResolver(
            repository=repository,
            paths=paths,
            model_manager=self.model_manager,
            logger=self.logger,
            tool_locator=self.tool_locator,
        )
        self.benchmark_service = TranscriptionRuntimeBenchmarkService(
            paths=paths,
            repository=repository,
            model_manager=self.model_manager,
            resolver=self.resolver,
            hardware_service=self.hardware_service,
            logger=self.logger,
        )

    def resolve_media_tools(self, *, prefer_external: bool = False):
        return self.ffmpeg_service.resolve_media_tools(prefer_external=prefer_external)

    def ffmpeg_status(self) -> FFmpegResolutionReport:
        return self.ffmpeg_service.status()

    def ffmpeg_verify(self) -> FFmpegResolutionReport:
        return self.ffmpeg_service.status()

    def ffmpeg_install_local(self, source_path: str | Path) -> FFmpegInstallResult:
        return self.ffmpeg_service.install_local(source_path)

    def ffmpeg_repair_local(self, source_path: str | Path | None = None) -> FFmpegInstallResult:
        return self.ffmpeg_service.repair_local(source_path)

    def ffmpeg_remove(self) -> FFmpegRemovalResult:
        return self.ffmpeg_service.remove()

    def download_start(self, request):
        return self.download_service.start_download(request)

    def download_status(self, download_id: str) -> DownloadStatusSummary | None:
        return self.download_service.status(download_id)

    def download_pause(self, download_id: str):
        return self.download_service.pause(download_id)

    def download_resume(self, download_id: str):
        return self.download_service.resume(download_id)

    def download_cancel(self, download_id: str):
        return self.download_service.cancel(download_id)

    def list_downloads(self):
        return self.download_service.list_downloads()

    def transcription_runtime_install_local(self, component_id: str, source_path: str | Path, *, revision: str = "1", artifact=None) -> TranscriptionInstallResult:
        return self.transcription_runtime_installer.install_local(component_id, source_path, revision=revision, artifact=artifact)

    def transcription_model_install_local(self, component_id: str, source_path: str | Path, *, revision: str, artifact=None) -> TranscriptionInstallResult:
        return self.transcription_model_installer.install_local(component_id, source_path, revision=revision, artifact=artifact)

    def catalog(self) -> ComponentCatalog:
        catalog = self.repository.get_catalog()
        if not catalog.entries:
            return build_default_component_catalog()
        return catalog

    def _tool_installation(self, component_id: str, *, tool: MediaToolInfo) -> ComponentInstallation:
        available = tool.available
        path = tool.path
        version = tool.version
        error_message = tool.error_message
        installation_type = tool.installation_type or ("managed" if tool.managed else "externally_detected")
        managed = bool(tool.managed)
        if available:
            status = ComponentInstallationStatus.READY
            health_status = RuntimeCheckStatus.READY
        elif tool.health_status in {"partial", "missing"}:
            status = ComponentInstallationStatus.MISSING
            health_status = RuntimeCheckStatus.NOT_CHECKED
        elif tool.health_status in {"corrupt", "executable_failed", "probe_failed", "timed_out"}:
            status = ComponentInstallationStatus.REPAIR_REQUIRED if managed else ComponentInstallationStatus.INVALID
            health_status = RuntimeCheckStatus.FAILED
        elif tool.health_status == "incompatible":
            status = ComponentInstallationStatus.INCOMPATIBLE
            health_status = RuntimeCheckStatus.INCOMPATIBLE
        else:
            status = ComponentInstallationStatus.MISSING
            health_status = RuntimeCheckStatus.NOT_CHECKED
        return ComponentInstallation(
            component_id=component_id,
            installation_status=status,
            installed_version=version,
            revision=None,
            install_type=ComponentInstallKind.MANAGED if managed else ComponentInstallKind.EXTERNALLY_DETECTED,
            location_path=path,
            location_reference="managed_root" if managed and path else ("path" if path else None),
            detected_at=None,
            verified_at=None,
            health_status=health_status,
            source=tool.source or "ffmpeg_locator",
            managed=managed,
            last_error_message=error_message,
            metadata={
                "version": version,
                "installation_type": installation_type,
                "health_status": tool.health_status,
                "reason": tool.reason,
            } if version or tool.health_status or tool.reason else {},
        )

    def inspect_installations(self) -> tuple[ComponentInstallation, ...]:
        catalog = self.catalog()
        tools = self.resolve_media_tools()
        installations: list[ComponentInstallation] = []
        for entry in catalog.entries:
            if entry.category == ComponentCategory.FFMPEG:
                tool = tools.ffmpeg if entry.component_id == "ffmpeg" else tools.ffprobe
                installations.append(
                    self._tool_installation(
                        entry.component_id,
                        tool=tool,
                    )
                )
                continue
            if entry.category == ComponentCategory.TRANSCRIPTION_RUNTIME:
                installation = self.repository.get_installation(entry.component_id)
                if installation is not None:
                    installations.append(installation)
                    continue
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
                installation = self.repository.get_installation(entry.component_id)
                if installation is not None:
                    installations.append(installation)
                    continue
                model_name = entry.component_id.split(".", 1)[-1]
                model_info = self.model_manager.inspect_model_availability(model_name)
                status_map = {
                    TranscriptionModelStatus.INSTALLED: ComponentInstallationStatus.READY,
                    TranscriptionModelStatus.LEGACY_CACHE: ComponentInstallationStatus.READY,
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
                        install_type=ComponentInstallKind.MANAGED if model_info.managed else ComponentInstallKind.EXTERNALLY_DETECTED,
                        location_path=model_info.path,
                        location_reference="managed_root" if model_info.managed else ("legacy_cache" if model_info.status == TranscriptionModelStatus.LEGACY_CACHE else ("cache" if model_info.path else None)),
                        detected_at=None,
                        verified_at=None,
                        health_status=RuntimeCheckStatus.READY if model_info.installed else RuntimeCheckStatus.NOT_CHECKED,
                        source=model_info.source or "model_manager.inspect_model_availability",
                        managed=bool(model_info.managed),
                        last_error_code=model_info.error_code,
                        last_error_message=model_info.error_message,
                        metadata={
                            "profile": model_info.profile,
                            "notes": model_info.notes or "",
                            "installation_type": model_info.installation_type,
                            "revision": model_info.revision,
                            "source": model_info.source,
                        },
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

    def run_transcription_benchmark(
        self,
        *,
        profile: str = "balanced",
        preferred_device: str = "auto",
        model_component_id: str | None = None,
        timeout_seconds: float = 30.0,
        fixture_id: str = "synthetic_voice_v1",
        persist_result: bool = True,
        force_refresh: bool = False,
    ):
        return self.benchmark_service.run_benchmark(
            requested_profile=profile,
            requested_device=preferred_device,
            model_component_id=model_component_id,
            timeout_seconds=timeout_seconds,
            fixture_id=fixture_id,
            persist_result=persist_result,
            force_refresh=force_refresh,
        )

    def latest_transcription_benchmark(self):
        return self.benchmark_service.latest_benchmark()

    def describe_transcription_benchmark(self):
        return self.benchmark_service.present(self.latest_transcription_benchmark())

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
