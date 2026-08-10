"""Resolucion determinista de capacidad de transcripcion local."""

from __future__ import annotations

import importlib
import logging
import platform
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from creator_intelligence_studio.domain.components.catalog import build_default_transcription_profiles
from creator_intelligence_studio.domain.components.entities import (
    ComponentCatalog,
    ComponentCatalogEntry,
    ComponentCategory,
    ComponentInstallation,
    ComponentInstallationStatus,
    ComponentInstallKind,
    RuntimeCheckRecord,
    RuntimeCheckStatus,
)
from creator_intelligence_studio.domain.components.repositories import ComponentManagerRepository
from creator_intelligence_studio.domain.hardware.entities import HardwareCapabilityState, HardwareProfile
from creator_intelligence_studio.domain.transcription.profiles import TranscriptionProfileDefinition
from creator_intelligence_studio.domain.transcription.value_objects import (
    TranscriptionModelInfo,
    TranscriptionModelStatus,
    TranscriptionRuntimeDistributionState,
    TranscriptionRuntimeInstallation,
    TranscriptionRuntimeResolution,
)
from creator_intelligence_studio.infrastructure.media.ffmpeg_locator import MediaToolLocator
from creator_intelligence_studio.infrastructure.transcription.model_manager import TranscriptionModelManager
from creator_intelligence_studio.shared.paths import ProjectPaths


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _normalized_architecture(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    if normalized in {"amd64", "x64", "x86_64"}:
        return "x86_64"
    return normalized


@dataclass(frozen=True, slots=True)
class CapabilitySuggestedAction:
    action_id: str
    action_type: str
    target_component: str | None = None
    target_profile: str | None = None
    priority: int = 0
    blocking: bool = False
    display_label: str = ""
    description: str = ""
    requires_network_future: bool = False
    requires_user_confirmation: bool = False
    available_now: bool = True
    reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "target_component": self.target_component,
            "target_profile": self.target_profile,
            "priority": self.priority,
            "blocking": self.blocking,
            "display_label": self.display_label,
            "description": self.description,
            "requires_network_future": self.requires_network_future,
            "requires_user_confirmation": self.requires_user_confirmation,
            "available_now": self.available_now,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class TranscriptionCapabilityReport:
    """Resultado tecnico de evaluacion de capacidad local."""

    resolution_id: str = ""
    generated_at: datetime = field(default_factory=_utc_now)
    current_user_preferences: dict[str, object] = field(default_factory=dict)
    readiness: str = "unknown"
    can_transcribe_now: bool = False
    requested_profile: str = "balanced"
    requested_device: str = "auto"
    selected_profile: TranscriptionProfileDefinition | None = None
    recommended_profile: TranscriptionProfileDefinition | None = None
    selected_model_component: ComponentCatalogEntry | None = None
    selected_model_component_id: str | None = None
    selected_model_installation_id: str | None = None
    selected_model_path: str | None = None
    selected_model_reference: str | None = None
    selected_runtime_component_id: str | None = None
    selected_runtime_installation_id: str | None = None
    selected_ffmpeg_installation_id: str | None = None
    selected_ffmpeg_source: str | None = None
    runtime_resolution: TranscriptionRuntimeResolution | None = None
    selected_device: str = "cpu"
    compute_type: str | None = None
    internal_compute_configuration: dict[str, object] = field(default_factory=dict)
    ffmpeg_status: ComponentInstallationStatus = ComponentInstallationStatus.UNKNOWN
    ffprobe_status: ComponentInstallationStatus = ComponentInstallationStatus.UNKNOWN
    runtime_status: RuntimeCheckStatus = RuntimeCheckStatus.NOT_CHECKED
    model_status: ComponentInstallationStatus = ComponentInstallationStatus.UNKNOWN
    hardware_status: HardwareCapabilityState = HardwareCapabilityState.UNKNOWN
    gpu_status: HardwareCapabilityState = HardwareCapabilityState.UNKNOWN
    benchmark_status: RuntimeCheckStatus | None = None
    benchmark_age_seconds: float | None = None
    disk_status: dict[str, object] = field(default_factory=dict)
    missing_component_ids: tuple[str, ...] = ()
    blocking_reasons: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    degraded_reasons: tuple[str, ...] = ()
    stale_evidence: tuple[str, ...] = ()
    estimated_required_disk_bytes: int | None = None
    available_disk_bytes: int | None = None
    fallback_available: bool = False
    fallback_profile: str | None = None
    fallback_device: str | None = None
    fallback_reason: str | None = None
    suggested_actions: tuple[str, ...] = ()
    structured_suggested_actions: tuple[CapabilitySuggestedAction, ...] = ()
    evidence_references: tuple[str, ...] = ()
    primary_message: str = ""
    secondary_message: str = ""
    technical_summary: str | None = None
    resolver_version: int = 1
    profile_version: int = 1

    def __post_init__(self) -> None:
        if not self.selected_model_component_id and self.selected_model_component is not None:
            object.__setattr__(self, "selected_model_component_id", self.selected_model_component.component_id)
        if not self.selected_model_reference:
            object.__setattr__(self, "selected_model_reference", self.selected_model_component_id)
        if not self.selected_runtime_component_id:
            object.__setattr__(self, "selected_runtime_component_id", "transcription-runtime.faster-whisper")
        if not self.selected_runtime_installation_id:
            object.__setattr__(self, "selected_runtime_installation_id", self.selected_runtime_component_id)
        if not self.selected_ffmpeg_installation_id and self.ffmpeg_status in {ComponentInstallationStatus.READY, ComponentInstallationStatus.EXTERNALLY_DETECTED, ComponentInstallationStatus.MANAGED}:
            object.__setattr__(self, "selected_ffmpeg_installation_id", "ffmpeg")
        if not self.internal_compute_configuration:
            object.__setattr__(self, "internal_compute_configuration", {"device": self.selected_device, "compute_type": self.compute_type})
        if not self.blockers:
            object.__setattr__(self, "blockers", self.blocking_reasons)
        if not self.primary_message:
            default_message = "Tu computadora esta lista para transcribir."
            if self.readiness == "ready_with_warnings":
                default_message = "Tu computadora puede transcribir con advertencias."
            elif self.readiness == "degraded":
                default_message = "La transcripcion puede continuar con una configuracion alternativa."
            elif self.readiness == "missing_components":
                default_message = "Faltan componentes necesarios para transcribir."
            elif self.readiness == "repair_required":
                default_message = "Un componente administrado necesita reparacion."
            elif self.readiness == "incompatible":
                default_message = "La configuracion actual no es compatible."
            elif self.readiness == "limited_mode":
                default_message = "La transcripcion puede continuar en modo limitado."
            object.__setattr__(self, "primary_message", default_message)
        if not self.secondary_message:
            object.__setattr__(self, "secondary_message", "La descarga, instalacion y benchmark permanecen separados.")

    @staticmethod
    def _model_status_to_component_status(status: TranscriptionModelStatus) -> ComponentInstallationStatus:
        if status in {TranscriptionModelStatus.INSTALLED, TranscriptionModelStatus.LEGACY_CACHE}:
            return ComponentInstallationStatus.READY
        if status in {TranscriptionModelStatus.INCOMPLETE, TranscriptionModelStatus.CORRUPT, TranscriptionModelStatus.ERROR}:
            return ComponentInstallationStatus.REPAIR_REQUIRED
        if status == TranscriptionModelStatus.INCOMPATIBLE:
            return ComponentInstallationStatus.INCOMPATIBLE
        return ComponentInstallationStatus.MISSING

    def to_dict(self) -> dict[str, object]:
        return {
            "resolution_id": self.resolution_id,
            "generated_at": self.generated_at.isoformat(),
            "current_user_preferences": dict(self.current_user_preferences),
            "readiness": self.readiness,
            "can_transcribe_now": self.can_transcribe_now,
            "requested_profile": self.requested_profile,
            "requested_device": self.requested_device,
            "selected_profile": self.selected_profile.to_dict() if self.selected_profile else None,
            "recommended_profile": self.recommended_profile.to_dict() if self.recommended_profile else None,
            "selected_model_component": self.selected_model_component.to_dict() if self.selected_model_component else None,
            "selected_model_component_id": self.selected_model_component_id,
            "selected_model_installation_id": self.selected_model_installation_id,
            "selected_model_path": self.selected_model_path,
            "selected_model_reference": self.selected_model_reference,
            "selected_runtime_component_id": self.selected_runtime_component_id,
            "selected_runtime_installation_id": self.selected_runtime_installation_id,
            "runtime_resolution": self.runtime_resolution.to_dict() if self.runtime_resolution else None,
            "selected_ffmpeg_installation_id": self.selected_ffmpeg_installation_id,
            "selected_ffmpeg_source": self.selected_ffmpeg_source,
            "selected_device": self.selected_device,
            "compute_type": self.compute_type,
            "internal_compute_configuration": dict(self.internal_compute_configuration),
            "ffmpeg_status": self.ffmpeg_status.value,
            "ffprobe_status": self.ffprobe_status.value,
            "runtime_status": self.runtime_status.value,
            "model_status": self.model_status.value,
            "hardware_status": self.hardware_status.value,
            "gpu_status": self.gpu_status.value,
            "benchmark_status": self.benchmark_status.value if self.benchmark_status else None,
            "benchmark_age_seconds": self.benchmark_age_seconds,
            "disk_status": dict(self.disk_status),
            "missing_component_ids": list(self.missing_component_ids),
            "blocking_reasons": list(self.blocking_reasons),
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "degraded_reasons": list(self.degraded_reasons),
            "stale_evidence": list(self.stale_evidence),
            "estimated_required_disk_bytes": self.estimated_required_disk_bytes,
            "available_disk_bytes": self.available_disk_bytes,
            "suggested_actions": list(self.suggested_actions),
            "structured_suggested_actions": [action.to_dict() for action in self.structured_suggested_actions],
            "evidence_references": list(self.evidence_references),
            "fallback_available": self.fallback_available,
            "fallback_profile": self.fallback_profile,
            "fallback_device": self.fallback_device,
            "fallback_reason": self.fallback_reason,
            "primary_message": self.primary_message,
            "secondary_message": self.secondary_message,
            "technical_summary": self.technical_summary,
            "resolver_version": self.resolver_version,
            "profile_version": self.profile_version,
        }


@dataclass(frozen=True, slots=True)
class TranscriptionExecutionPlan:
    resolution_id: str
    generated_at: datetime
    can_transcribe_now: bool
    selected_profile: TranscriptionProfileDefinition | None
    selected_profile_id: str
    selected_device: str
    compute_type: str | None
    selected_model_component_id: str | None
    selected_model_reference: str | None
    selected_model_path: str | None
    selected_runtime_component_id: str | None
    selected_runtime_installation_id: str | None
    runtime_resolution: TranscriptionRuntimeResolution | None
    selected_ffmpeg_installation_id: str | None
    selected_ffmpeg_source: str | None
    ffmpeg_status: ComponentInstallationStatus
    ffprobe_status: ComponentInstallationStatus
    runtime_status: RuntimeCheckStatus
    model_status: ComponentInstallationStatus
    hardware_status: HardwareCapabilityState
    gpu_status: HardwareCapabilityState
    benchmark_status: RuntimeCheckStatus | None
    benchmark_age_seconds: float | None
    disk_status: dict[str, object]
    temporary_space_bytes: int | None
    warnings: tuple[str, ...] = ()
    evidence_versions: tuple[str, ...] = ()
    primary_message: str = ""
    secondary_message: str = ""
    technical_summary: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "resolution_id": self.resolution_id,
            "generated_at": self.generated_at.isoformat(),
            "can_transcribe_now": self.can_transcribe_now,
            "selected_profile": self.selected_profile.to_dict() if self.selected_profile else None,
            "selected_profile_id": self.selected_profile_id,
            "selected_device": self.selected_device,
            "compute_type": self.compute_type,
            "selected_model_component_id": self.selected_model_component_id,
            "selected_model_reference": self.selected_model_reference,
            "selected_model_path": self.selected_model_path,
            "selected_runtime_component_id": self.selected_runtime_component_id,
            "selected_runtime_installation_id": self.selected_runtime_installation_id,
            "runtime_resolution": self.runtime_resolution.to_dict() if self.runtime_resolution else None,
            "selected_ffmpeg_installation_id": self.selected_ffmpeg_installation_id,
            "selected_ffmpeg_source": self.selected_ffmpeg_source,
            "ffmpeg_status": self.ffmpeg_status.value,
            "ffprobe_status": self.ffprobe_status.value,
            "runtime_status": self.runtime_status.value,
            "model_status": self.model_status.value,
            "hardware_status": self.hardware_status.value,
            "gpu_status": self.gpu_status.value,
            "benchmark_status": self.benchmark_status.value if self.benchmark_status else None,
            "benchmark_age_seconds": self.benchmark_age_seconds,
            "disk_status": dict(self.disk_status),
            "temporary_space_bytes": self.temporary_space_bytes,
            "warnings": list(self.warnings),
            "evidence_versions": list(self.evidence_versions),
            "primary_message": self.primary_message,
            "secondary_message": self.secondary_message,
            "technical_summary": self.technical_summary,
        }


@dataclass(frozen=True, slots=True)
class TranscriptionCapabilityPresentation:
    """Mensaje user-friendly derivado del resultado tecnico."""

    title: str
    message: str
    details: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "title": self.title,
            "message": self.message,
            "details": dict(self.details),
        }


class TranscriptionCapabilityResolver:
    """Resuelve capacidad local sin descargas ni red."""

    def __init__(
        self,
        *,
        repository: ComponentManagerRepository,
        paths: ProjectPaths,
        model_manager: TranscriptionModelManager,
        logger: logging.Logger | None = None,
        tool_locator: MediaToolLocator | None = None,
    ) -> None:
        self.repository = repository
        self.paths = paths
        self.model_manager = model_manager
        self.tool_locator = tool_locator or MediaToolLocator(project_root=paths.project_root)
        self.logger = logger or logging.getLogger("creator_intelligence_studio.components.resolver")
        self.version = 1

    def _catalog(self) -> ComponentCatalog:
        return self.repository.get_catalog()

    def _profiles(self) -> dict[str, TranscriptionProfileDefinition]:
        profiles = self.repository.list_transcription_profiles()
        if not profiles:
            profiles = build_default_transcription_profiles()
        return {profile.profile_id: profile for profile in profiles}

    def _installation_map(self) -> dict[str, ComponentInstallation]:
        return {installation.component_id: installation for installation in self.repository.list_installations()}

    def _latest_benchmark_record(self, component_id: str | None) -> RuntimeCheckRecord | None:
        if component_id is None:
            return None
        normalized = component_id.strip().lower()
        benchmark_records = [
            record
            for record in self.repository.list_runtime_checks()
            if record.component_id.strip().lower() == normalized and str((record.metadata or {}).get("check_kind") or "").strip().lower() == "transcription_runtime_benchmark"
        ]
        if not benchmark_records:
            return None
        return max(
            benchmark_records,
            key=lambda record: record.checked_at or record.updated_at or record.created_at or _utc_now(),
        )

    def _model_component_id(self, model_name: str | None) -> str:
        normalized = (model_name or "small").strip().lower()
        return f"transcription-model.{normalized}"

    def _product_source_available(self, entry: ComponentCatalogEntry | None, *, hardware_profile: HardwareProfile | None) -> bool:
        if entry is None:
            return False
        if (entry.source_type or "").strip().lower() != "approved_product_source":
            return False
        if not entry.source_url or not entry.expected_sha256 or entry.expected_download_bytes is None:
            return False
        if hardware_profile is None:
            return False
        expected_platform = (entry.platform or "").strip().lower()
        if expected_platform and expected_platform not in {hardware_profile.platform.strip().lower(), "windows"}:
            return False
        expected_architecture = _normalized_architecture(entry.architecture)
        actual_architecture = _normalized_architecture(hardware_profile.architecture)
        if expected_architecture and expected_architecture != actual_architecture:
            return False
        return True

    def _resolve_installation(self, component_id: str, installations: dict[str, ComponentInstallation]) -> ComponentInstallation:
        installation = installations.get(component_id)
        if installation is not None:
            return installation
        return ComponentInstallation(
            component_id=component_id,
            installation_status=ComponentInstallationStatus.MISSING,
            installed_version=None,
            revision=None,
            install_type=ComponentInstallKind.EXTERNALLY_DETECTED,
            location_path=None,
            location_reference=None,
            detected_at=None,
            verified_at=None,
            health_status=RuntimeCheckStatus.NOT_CHECKED,
            source=None,
            managed=False,
            metadata={},
            created_at=_utc_now(),
            updated_at=_utc_now(),
        )

    def _runtime_module_versions(self) -> tuple[str | None, str | None, str | None, bool, bool, tuple[str, ...], tuple[str, ...]]:
        errors: list[str] = []
        warnings: list[str] = []
        faster_whisper_version: str | None = None
        ctranslate2_version: str | None = None
        faster_whisper_imported = False
        ctranslate2_imported = False
        gpu_supported = False
        try:
            module = importlib.import_module("faster_whisper")
            faster_whisper_version = getattr(module, "__version__", None)
            faster_whisper_imported = True
        except Exception as exc:
            errors.append(str(exc))
        try:
            module = importlib.import_module("ctranslate2")
            ctranslate2_version = getattr(module, "__version__", None)
            ctranslate2_imported = True
            try:
                device_count = int(module.get_cuda_device_count())
            except Exception as exc:
                warnings.append(str(exc))
                device_count = 0
            try:
                supported = tuple(str(item) for item in module.get_supported_compute_types("cuda"))
            except Exception as exc:
                warnings.append(str(exc))
                supported = ()
            gpu_supported = device_count > 0 and ("int8_float16" in supported or "float16" in supported)
        except Exception as exc:
            errors.append(str(exc))
        python_version = platform.python_version()
        cpu_supported = faster_whisper_imported and ctranslate2_imported
        return faster_whisper_version, ctranslate2_version, python_version, cpu_supported, gpu_supported, tuple(dict.fromkeys(warnings)), tuple(dict.fromkeys(errors))

    def _resolve_runtime_installation(
        self,
        installations: dict[str, ComponentInstallation],
        *,
        catalog: ComponentCatalog,
        hardware_profile: HardwareProfile | None,
    ) -> TranscriptionRuntimeInstallation:
        runtime_installation = installations.get("transcription-runtime.faster-whisper") or installations.get("transcription-runtime.ctranslate2")
        entry = catalog.get_entry("transcription-runtime.faster-whisper")
        faster_whisper_version, ctranslate2_version, python_version, cpu_supported, gpu_supported, runtime_warnings, runtime_errors = self._runtime_module_versions()
        platform_name = platform.system() or None
        architecture = platform.machine() or None
        complete_runtime_present = faster_whisper_version is not None and ctranslate2_version is not None
        if runtime_installation is None:
            if complete_runtime_present:
                return TranscriptionRuntimeInstallation(
                    component_id="transcription-runtime.faster-whisper",
                    distribution_state=TranscriptionRuntimeDistributionState.LEGACY_EXTERNAL,
                    runtime_implementation="faster-whisper",
                    faster_whisper_version=faster_whisper_version,
                    ctranslate2_version=ctranslate2_version,
                    python_version=python_version,
                    source_kind="python_import",
                    platform=platform_name,
                    architecture=architecture,
                    cpu_supported=cpu_supported,
                    gpu_supported=gpu_supported,
                    build_revision=entry.build_revision if entry else None,
                    catalog_revision=entry.revision if entry else None,
                    location_path=None,
                    location_reference="python_package",
                    managed=False,
                    notes="Runtime importado desde el entorno de Python actual.",
                    error_message="; ".join(runtime_errors) if runtime_errors else None,
                )
            if faster_whisper_version or ctranslate2_version:
                return TranscriptionRuntimeInstallation(
                    component_id="transcription-runtime.faster-whisper",
                    distribution_state=TranscriptionRuntimeDistributionState.REPAIR_REQUIRED,
                    runtime_implementation="faster-whisper",
                    faster_whisper_version=faster_whisper_version,
                    ctranslate2_version=ctranslate2_version,
                    python_version=python_version,
                    source_kind="python_import",
                    platform=platform_name,
                    architecture=architecture,
                    cpu_supported=False,
                    gpu_supported=False,
                    build_revision=entry.build_revision if entry else None,
                    catalog_revision=entry.revision if entry else None,
                    location_path=None,
                    location_reference="python_package",
                    managed=False,
                    notes="El runtime de transcripcion solo esta parcialmente disponible en el entorno actual.",
                    error_message="; ".join(runtime_errors) if runtime_errors else None,
                )
            return TranscriptionRuntimeInstallation(
                component_id="transcription-runtime.faster-whisper",
                distribution_state=TranscriptionRuntimeDistributionState.MISSING,
                runtime_implementation="faster-whisper",
                faster_whisper_version=None,
                ctranslate2_version=None,
                python_version=python_version,
                source_kind=None,
                platform=platform_name,
                architecture=architecture,
                cpu_supported=False,
                gpu_supported=False,
                build_revision=entry.build_revision if entry else None,
                catalog_revision=entry.revision if entry else None,
                location_path=None,
                location_reference=None,
                managed=None,
                notes="El runtime local de transcripcion no esta instalado.",
                error_message=None,
            )
        if not complete_runtime_present:
            if runtime_installation.installation_status == ComponentInstallationStatus.INCOMPATIBLE:
                state = TranscriptionRuntimeDistributionState.INCOMPATIBLE
            else:
                state = TranscriptionRuntimeDistributionState.REPAIR_REQUIRED
        elif runtime_installation.installation_status in {ComponentInstallationStatus.INVALID, ComponentInstallationStatus.REPAIR_REQUIRED}:
            state = TranscriptionRuntimeDistributionState.REPAIR_REQUIRED
        elif runtime_installation.installation_status == ComponentInstallationStatus.INCOMPATIBLE:
            state = TranscriptionRuntimeDistributionState.INCOMPATIBLE
        elif runtime_installation.managed and (runtime_installation.location_reference or "").strip().lower() == "application_bundle":
            state = TranscriptionRuntimeDistributionState.APPLICATION_BUNDLED
        elif runtime_installation.managed:
            state = TranscriptionRuntimeDistributionState.MANAGED
        else:
            state = TranscriptionRuntimeDistributionState.LEGACY_EXTERNAL
        source_kind = runtime_installation.source or (runtime_installation.metadata.get("installation_type") if runtime_installation.metadata else None) or "python_package"
        if runtime_installation.installation_status == ComponentInstallationStatus.INCOMPATIBLE:
            cpu_supported = False
            gpu_supported = False
        return TranscriptionRuntimeInstallation(
            component_id=runtime_installation.component_id,
            distribution_state=state,
            runtime_implementation="faster-whisper",
            faster_whisper_version=faster_whisper_version,
            ctranslate2_version=ctranslate2_version,
            python_version=python_version,
            source_kind=str(source_kind) if source_kind is not None else None,
            platform=platform_name,
            architecture=architecture,
            cpu_supported=cpu_supported,
            gpu_supported=gpu_supported,
            build_revision=runtime_installation.revision or (entry.build_revision if entry else None),
            catalog_revision=entry.revision if entry else None,
            location_path=runtime_installation.location_path,
            location_reference=runtime_installation.location_reference,
            managed=runtime_installation.managed,
            notes=runtime_installation.last_error_message or (runtime_installation.metadata.get("notes") if runtime_installation.metadata else None),
            error_message=runtime_installation.last_error_message,
        )

    def resolve(
        self,
        *,
        requested_profile: str = "balanced",
        preferred_device: str = "auto",
        available_disk_bytes: int | None = None,
        installations: dict[str, ComponentInstallation] | None = None,
        hardware_profile: HardwareProfile | None = None,
    ) -> TranscriptionCapabilityReport:
        catalog = self._catalog()
        profiles = self._profiles()
        installations = installations or self._installation_map()
        hardware_profile = hardware_profile or self.repository.latest_hardware_profile()
        requested_key = (requested_profile or "balanced").strip().lower()
        requested = profiles.get(requested_key) or profiles.get("balanced") or profiles.get("fast") or next(iter(profiles.values()), None)
        current_preferences = {"requested_profile": requested_profile, "preferred_device": preferred_device}

        def _model_name_for(profile: TranscriptionProfileDefinition | None) -> str | None:
            if profile is None or profile.model_component_id is None:
                return None
            return profile.model_component_id.split(".", 1)[-1]

        def _profile_for_model_name(model_name: str | None) -> TranscriptionProfileDefinition | None:
            if model_name is None:
                return None
            for profile in profiles.values():
                if _model_name_for(profile) == model_name:
                    return profile
            return None

        def _model_info_from_installation(component_id: str, model_name: str) -> TranscriptionModelInfo:
            installation = installations.get(component_id)
            if installation is None:
                return self.model_manager.resolve_installed_model(model_name)
            if installation.installation_status in {
                ComponentInstallationStatus.READY,
                ComponentInstallationStatus.EXTERNALLY_DETECTED,
                ComponentInstallationStatus.MANAGED,
            }:
                model_status = TranscriptionModelStatus.INSTALLED
                installed = True
                notes = "Modelo instalado y verificado localmente."
            elif installation.installation_status in {ComponentInstallationStatus.INVALID, ComponentInstallationStatus.REPAIR_REQUIRED}:
                model_status = TranscriptionModelStatus.CORRUPT
                installed = False
                notes = installation.last_error_message or "El modelo esta incompleto o danado."
            elif installation.installation_status == ComponentInstallationStatus.INCOMPATIBLE:
                model_status = TranscriptionModelStatus.INCOMPATIBLE
                installed = False
                notes = installation.last_error_message or "El modelo no es compatible con este entorno."
            else:
                model_status = TranscriptionModelStatus.NOT_INSTALLED
                installed = False
                notes = installation.last_error_message or "Modelo no instalado."
            return TranscriptionModelInfo(
                model_name=model_name,
                profile=_profile_for_model_name(model_name).profile_id if _profile_for_model_name(model_name) else model_name,
                path=installation.location_path,
                installed=installed,
                notes=notes,
                status=model_status,
                error_code=installation.last_error_code,
                error_message=installation.last_error_message,
                installation_type=installation.install_type.value if installation.install_type else None,
                managed=installation.managed,
                revision=installation.revision,
                source=installation.source,
                component_id=component_id,
            )

        requested_model_name = _model_name_for(requested)
        requested_model_component_id = requested.model_component_id if requested and requested.model_component_id else self._model_component_id("small")
        requested_model_info = _model_info_from_installation(requested_model_component_id, requested_model_name or "small")
        selected_profile = requested
        fallback_profile = None
        fallback_reason = None
        fallback_available = False

        if requested_key == "balanced" and requested_model_info.status not in {TranscriptionModelStatus.INSTALLED, TranscriptionModelStatus.LEGACY_CACHE}:
            fast_profile = profiles.get("fast")
            fast_info = _model_info_from_installation(fast_profile.model_component_id if fast_profile and fast_profile.model_component_id else self._model_component_id("base"), _model_name_for(fast_profile) or "base") if fast_profile else None
            if fast_profile and fast_info and fast_info.status in {TranscriptionModelStatus.INSTALLED, TranscriptionModelStatus.LEGACY_CACHE}:
                selected_profile = fast_profile
                fallback_profile = fast_profile
                fallback_reason = "balanced_missing_fast_available"
                fallback_available = True
        elif requested_key == "maximum_quality" and requested_model_info.status not in {TranscriptionModelStatus.INSTALLED, TranscriptionModelStatus.LEGACY_CACHE}:
            balanced_profile = profiles.get("balanced")
            balanced_info = _model_info_from_installation(balanced_profile.model_component_id if balanced_profile and balanced_profile.model_component_id else self._model_component_id("small"), _model_name_for(balanced_profile) or "small") if balanced_profile else None
            if balanced_profile and balanced_info and balanced_info.status in {TranscriptionModelStatus.INSTALLED, TranscriptionModelStatus.LEGACY_CACHE}:
                selected_profile = balanced_profile
                fallback_profile = balanced_profile
                fallback_reason = "maximum_quality_missing_balanced_available"
                fallback_available = True

        selected_model_name = _model_name_for(selected_profile) or requested_model_name or "small"
        selected_model_component_id = selected_profile.model_component_id if selected_profile and selected_profile.model_component_id else self.model_manager.model_component_id(selected_model_name)
        selected_model_info = _model_info_from_installation(selected_model_component_id, selected_model_name)
        selected_model_component = catalog.get_entry(selected_model_component_id)
        selected_model_path = selected_model_info.path

        ffmpeg_installation = self._resolve_installation("ffmpeg", installations)
        ffprobe_installation = self._resolve_installation("ffprobe", installations)
        runtime_component_id = "transcription-runtime.faster-whisper"
        runtime_installation = self._resolve_runtime_installation(installations, catalog=catalog, hardware_profile=hardware_profile)
        runtime_installation_id = runtime_installation.component_id if runtime_installation.component_id else runtime_component_id
        runtime_status = {
            TranscriptionRuntimeDistributionState.APPLICATION_BUNDLED: RuntimeCheckStatus.READY,
            TranscriptionRuntimeDistributionState.MANAGED: RuntimeCheckStatus.READY,
            TranscriptionRuntimeDistributionState.LEGACY_EXTERNAL: RuntimeCheckStatus.READY,
            TranscriptionRuntimeDistributionState.MISSING: RuntimeCheckStatus.NOT_CHECKED,
            TranscriptionRuntimeDistributionState.INCOMPATIBLE: RuntimeCheckStatus.INCOMPATIBLE,
            TranscriptionRuntimeDistributionState.REPAIR_REQUIRED: RuntimeCheckStatus.FAILED,
        }[runtime_installation.distribution_state]
        ffmpeg_selected = ffmpeg_installation
        ffmpeg_source = ffmpeg_installation.source or "ffmpeg_locator"

        warnings: list[str] = []
        blockers: list[str] = []
        degraded_reasons: list[str] = []
        stale_evidence: list[str] = []
        suggested_actions: list[CapabilitySuggestedAction] = []
        missing: list[str] = []

        ffmpeg_ok = ffmpeg_installation.installation_status in {ComponentInstallationStatus.READY, ComponentInstallationStatus.EXTERNALLY_DETECTED, ComponentInstallationStatus.MANAGED}
        ffprobe_ok = ffprobe_installation.installation_status in {ComponentInstallationStatus.READY, ComponentInstallationStatus.EXTERNALLY_DETECTED, ComponentInstallationStatus.MANAGED}
        runtime_ok = runtime_installation.distribution_state not in {
            TranscriptionRuntimeDistributionState.MISSING,
            TranscriptionRuntimeDistributionState.INCOMPATIBLE,
            TranscriptionRuntimeDistributionState.REPAIR_REQUIRED,
        }
        model_ok = selected_model_info.status in {TranscriptionModelStatus.INSTALLED, TranscriptionModelStatus.LEGACY_CACHE}

        if not ffmpeg_ok:
            missing.append("ffmpeg")
            if ffmpeg_installation.installation_status in {ComponentInstallationStatus.INVALID, ComponentInstallationStatus.REPAIR_REQUIRED}:
                blockers.append("FFmpeg administrado necesita reparacion.")
                suggested_actions.append(CapabilitySuggestedAction("repair_ffmpeg", "repair_component", "ffmpeg", blocking=True, display_label="Reparar FFmpeg", description="Repara la instalacion administrada de FFmpeg.", priority=1, available_now=True, reason="repair_required"))
            elif ffmpeg_installation.installation_status == ComponentInstallationStatus.INCOMPATIBLE:
                blockers.append("FFmpeg es incompatible con este entorno.")
            else:
                blockers.append("Falta FFmpeg.")
                if self._product_source_available(catalog.get_entry("ffmpeg"), hardware_profile=hardware_profile):
                    suggested_actions.append(CapabilitySuggestedAction("download_ffmpeg_product", "download_product_source", "ffmpeg", blocking=True, display_label="Descargar", description="Descarga la fuente productiva aprobada de FFmpeg y FFprobe.", priority=0, available_now=True, reason="product_source_approved", requires_network_future=True, requires_user_confirmation=True))
                suggested_actions.append(CapabilitySuggestedAction("install_ffmpeg", "install_component", "ffmpeg", blocking=True, display_label="Instalar FFmpeg", description="Instala el componente multimedia desde una fuente local.", priority=1, available_now=True, reason="missing_component", requires_user_confirmation=True))
        else:
            suggested_actions.append(CapabilitySuggestedAction("verify_ffmpeg", "verify_component", "ffmpeg", blocking=False, display_label="Comprobar FFmpeg", description="Verifica la instalacion local del componente multimedia.", priority=3, available_now=True, reason="verification_available"))
            if ffmpeg_installation.managed:
                suggested_actions.append(CapabilitySuggestedAction("remove_ffmpeg", "remove_component", "ffmpeg", blocking=True, display_label="Eliminar FFmpeg", description="Elimina la instalacion administrada del componente multimedia.", priority=4, available_now=True, reason="managed_installation", requires_user_confirmation=True))

        if not ffprobe_ok:
            missing.append("ffprobe")
            if ffprobe_installation.installation_status in {ComponentInstallationStatus.INVALID, ComponentInstallationStatus.REPAIR_REQUIRED}:
                blockers.append("FFprobe administrado necesita reparacion.")
                suggested_actions.append(CapabilitySuggestedAction("repair_ffprobe", "repair_component", "ffprobe", blocking=True, display_label="Reparar FFprobe", description="Repara la instalacion administrada de FFprobe.", priority=1, available_now=True, reason="repair_required"))
            elif ffprobe_installation.installation_status == ComponentInstallationStatus.INCOMPATIBLE:
                blockers.append("FFprobe es incompatible con este entorno.")
            else:
                blockers.append("Falta FFprobe.")

        if not runtime_ok:
            missing.append(runtime_component_id)
            if runtime_installation.distribution_state == TranscriptionRuntimeDistributionState.REPAIR_REQUIRED:
                blockers.append("El runtime local necesita reparacion.")
                suggested_actions.append(CapabilitySuggestedAction("repair_runtime", "repair_component", runtime_component_id, blocking=True, display_label="Reparar runtime", description="Repara el runtime de transcripcion.", priority=1, available_now=True, reason="repair_required"))
            elif runtime_installation.distribution_state == TranscriptionRuntimeDistributionState.INCOMPATIBLE:
                blockers.append("El runtime local es incompatible con este entorno.")
            else:
                blockers.append("Falta el runtime local de transcripcion.")
                suggested_actions.append(CapabilitySuggestedAction("install_runtime", "install_component", runtime_component_id, blocking=True, display_label="Instalar runtime", description="Instala el motor local desde una fuente local.", priority=1, available_now=True, reason="missing_component", requires_user_confirmation=True))
        else:
            suggested_actions.append(CapabilitySuggestedAction("verify_runtime", "verify_component", runtime_component_id, blocking=False, display_label="Comprobar runtime", description="Verifica el runtime local de transcripcion.", priority=3, available_now=True, reason="verification_available"))
            if bool(runtime_installation.managed):
                suggested_actions.append(CapabilitySuggestedAction("remove_runtime", "remove_component", runtime_component_id, blocking=True, display_label="Eliminar runtime", description="Elimina la instalacion administrada del runtime.", priority=4, available_now=True, reason="managed_installation", requires_user_confirmation=True))

        if not model_ok:
            missing.append(selected_model_component_id)
            if selected_model_info.status in {TranscriptionModelStatus.CORRUPT, TranscriptionModelStatus.INCOMPLETE, TranscriptionModelStatus.ERROR}:
                if fallback_profile is None:
                    blockers.append("El modelo seleccionado esta incompleto o dañado.")
                    suggested_actions.append(CapabilitySuggestedAction("repair_model", "repair_component", selected_model_component_id, target_profile=requested_key, blocking=True, display_label="Reparar modelo", description="Repara o reinstala el modelo administrado.", priority=1, available_now=True, reason="repair_required"))
                else:
                    degraded_reasons.append("requested_model_corrupt")
                    warnings.append("El modelo solicitado necesita reparacion, pero existe un perfil alternativo funcional.")
            elif selected_model_info.status == TranscriptionModelStatus.INCOMPATIBLE:
                blockers.append("El modelo seleccionado es incompatible con este entorno.")
            else:
                if fallback_profile is None:
                    blockers.append("El modelo no esta instalado. Usa Componentes locales para instalarlo.")
                    suggested_actions.append(CapabilitySuggestedAction("install_model", "install_component", selected_model_component_id, target_profile=requested_key, blocking=True, display_label="Instalar modelo", description="Instala el modelo local desde una fuente local.", priority=1, available_now=True, reason="missing_component", requires_user_confirmation=True))
                else:
                    degraded_reasons.append("requested_model_missing")
        elif selected_model_info.status == TranscriptionModelStatus.LEGACY_CACHE:
            warnings.append("Se esta usando un modelo local existente no administrado.")
        else:
            suggested_actions.append(CapabilitySuggestedAction("verify_model", "verify_component", selected_model_component_id, target_profile=requested_key, blocking=False, display_label="Comprobar modelo", description="Verifica el modelo de transcripcion local.", priority=3, available_now=True, reason="verification_available"))
            if selected_model_info.managed:
                suggested_actions.append(CapabilitySuggestedAction("remove_model", "remove_component", selected_model_component_id, target_profile=requested_key, blocking=True, display_label="Eliminar modelo", description="Elimina la instalacion administrada del modelo.", priority=4, available_now=True, reason="managed_installation", requires_user_confirmation=True))

        benchmark_record = self._latest_benchmark_record(selected_model_component_id)
        benchmark_status = benchmark_record.status if benchmark_record is not None else None
        benchmark_age_seconds: float | None = None
        benchmark_device = None
        benchmark_compute_type = None
        gpu_functionally_proven = False
        if benchmark_record is not None:
            checked_at = benchmark_record.checked_at or benchmark_record.updated_at or benchmark_record.created_at
            if checked_at is not None:
                benchmark_age_seconds = max(0.0, (_utc_now() - checked_at).total_seconds())
            metadata = dict(benchmark_record.metadata or {})
            benchmark_device = str(metadata.get("actual_device") or metadata.get("requested_device") or "").strip().lower() or None
            benchmark_compute_type = str(metadata.get("selected_compute_type") or "").strip().lower() or None
            gpu_functionally_proven = benchmark_device in {"gpu", "cuda"} and benchmark_status in {RuntimeCheckStatus.READY, RuntimeCheckStatus.DEGRADED}
            if metadata.get("model_component_id") and metadata.get("model_component_id") != selected_model_component_id:
                stale_evidence.append("model_component_changed")
            if metadata.get("model_revision") and selected_profile and selected_profile.model_revision and metadata.get("model_revision") != selected_profile.model_revision:
                stale_evidence.append("model_revision_changed")
            if metadata.get("runtime_version") and runtime_installation.ctranslate2_version and metadata.get("runtime_version") != runtime_installation.ctranslate2_version:
                stale_evidence.append("runtime_version_changed")
            if metadata.get("driver_version") and hardware_profile is not None and hardware_profile.gpu.driver_version and metadata.get("driver_version") != hardware_profile.gpu.driver_version:
                stale_evidence.append("driver_version_changed")
            if metadata.get("benchmark_version") and int(metadata.get("benchmark_version") or 0) != self.version:
                stale_evidence.append("benchmark_version_changed")
        if hardware_profile is not None:
            if hardware_profile.gpu.status == HardwareCapabilityState.REPORTED_NOT_TESTED and not gpu_functionally_proven:
                warnings.append("Se detecto una GPU, pero todavia no fue probada funcionalmente.")
            if hardware_profile.status == HardwareCapabilityState.REPORTED_NOT_TESTED and not gpu_functionally_proven:
                warnings.append("La GPU esta detectada pero no validada.")

        available_disk = available_disk_bytes
        if available_disk is None and hardware_profile is not None and hardware_profile.disk_volumes:
            available_disk = max((volume.free_bytes or 0) for volume in hardware_profile.disk_volumes)
        estimated_required_disk_bytes = selected_profile.estimated_disk_bytes if selected_profile else None
        disk_ok = available_disk is None or estimated_required_disk_bytes is None or available_disk >= estimated_required_disk_bytes
        if not disk_ok:
            blockers.append("No hay suficiente espacio para el perfil seleccionado.")
            missing.append("disk_space")
            suggested_actions.append(CapabilitySuggestedAction("free_disk_space", "free_disk_space", priority=1, blocking=True, display_label="Liberar espacio", description="Libera espacio para el perfil solicitado.", available_now=True, reason="insufficient_disk_space"))

        requested_device = (preferred_device or "auto").strip().lower()
        if requested_device not in {"auto", "cpu", "gpu"}:
            requested_device = "auto"
        selected_device = "cpu"
        selected_compute_type = selected_profile.cpu_compute_type if selected_profile else None
        gpu_supported = False
        if benchmark_record is not None and benchmark_device in {"gpu", "cuda"} and benchmark_status in {RuntimeCheckStatus.READY, RuntimeCheckStatus.DEGRADED}:
            gpu_supported = True
        if requested_device == "gpu":
            if gpu_supported:
                selected_device = "gpu"
                selected_compute_type = selected_profile.gpu_compute_type if selected_profile and selected_profile.gpu_compute_type else benchmark_compute_type or selected_compute_type
            else:
                warnings.append("La GPU no pudo ser confirmada funcionalmente.")
                suggested_actions.append(CapabilitySuggestedAction("run_gpu_benchmark", "run_gpu_benchmark", target_profile=selected_profile.profile_id if selected_profile else None, blocking=True, display_label="Probar GPU", description="Ejecuta la prueba funcional de GPU.", available_now=True, reason="gpu_untested"))
        elif requested_device == "cpu":
            selected_device = "cpu"
            selected_compute_type = selected_profile.cpu_compute_type if selected_profile else None
        else:
            if gpu_supported and hardware_profile is not None and hardware_profile.gpu.status == HardwareCapabilityState.DETECTED:
                selected_device = "gpu"
                selected_compute_type = selected_profile.gpu_compute_type if selected_profile and selected_profile.gpu_compute_type else benchmark_compute_type or selected_compute_type
            elif hardware_profile is not None and hardware_profile.gpu.status == HardwareCapabilityState.REPORTED_NOT_TESTED:
                selected_device = "cpu"
                warnings.append("Tu GPU todavia no ha sido comprobada; se usara CPU por ahora.")
            elif benchmark_record is not None and benchmark_device in {"gpu", "cuda"} and benchmark_status in {RuntimeCheckStatus.READY, RuntimeCheckStatus.DEGRADED}:
                selected_device = "gpu"
                selected_compute_type = benchmark_compute_type or selected_compute_type

        fallback_device = requested_device if requested_device != selected_device else None
        fallback_available = fallback_available or bool(fallback_device or fallback_profile)
        if fallback_profile is not None:
            fallback_reason = fallback_reason or "profile_fallback"

        if selected_model_info.status == TranscriptionModelStatus.LEGACY_CACHE and not blockers:
            warnings.append("Se esta usando un modelo local existente no administrado.")

        if benchmark_record is not None and stale_evidence:
            warnings.append("La evidencia funcional local esta desactualizada.")

        if blockers:
            if any("incompatible" in blocker.lower() for blocker in blockers):
                readiness = "incompatible"
            elif any("repar" in blocker.lower() for blocker in blockers):
                readiness = "repair_required"
            elif "La GPU no pudo ser confirmada funcionalmente." in blockers and requested_device == "gpu":
                readiness = "limited_mode"
            else:
                readiness = "missing_components"
            can_transcribe_now = False
        else:
            can_transcribe_now = True
            if fallback_profile is not None or degraded_reasons:
                readiness = "degraded"
            elif warnings:
                readiness = "ready_with_warnings"
            else:
                readiness = "ready"

        if not can_transcribe_now:
            suggested_actions.append(CapabilitySuggestedAction("continue_limited", "continue_limited", blocking=False, display_label="Continuar en modo limitado", description="Sigue usando la aplicacion sin transcripcion local.", priority=99, available_now=True, reason="limited_mode"))

        if selected_profile is None:
            selected_profile = requested
        if fallback_profile is None and selected_profile and selected_profile.profile_id != requested_key:
            fallback_profile = selected_profile
            fallback_reason = fallback_reason or "profile_fallback"
            fallback_available = True

        internal_compute_configuration = {
            "device": selected_device,
            "compute_type": selected_compute_type,
            "requested_device": requested_device,
        }
        disk_status = {
            "available_bytes": available_disk,
            "estimated_required_bytes": estimated_required_disk_bytes,
            "can_transcribe_now": can_transcribe_now,
        }
        evidence = [
            f"catalog_version={catalog.catalog_version}",
            f"profile_version={selected_profile.version if selected_profile else 'unknown'}",
            f"runtime_status={runtime_status.value}",
            f"runtime_distribution={runtime_installation.distribution_state.value}",
            f"gpu_status={(hardware_profile.gpu.status.value if hardware_profile is not None else HardwareCapabilityState.UNKNOWN.value)}",
            f"model_status={selected_model_info.status.value}",
        ]
        if benchmark_record is not None:
            evidence.append(f"benchmark_status={benchmark_record.status.value}")
            if benchmark_age_seconds is not None:
                evidence.append(f"benchmark_age_seconds={int(benchmark_age_seconds)}")
        suggested_action_texts = tuple(action.display_label or action.action_type for action in suggested_actions)
        primary_message = "Tu computadora esta lista para transcribir."
        if readiness == "ready_with_warnings":
            primary_message = "Tu computadora puede transcribir con advertencias."
        elif readiness == "degraded":
            primary_message = "Puedes transcribir ahora con un perfil o dispositivo alternativo."
        elif readiness == "missing_components":
            primary_message = "Faltan componentes para poder transcribir ahora mismo."
        elif readiness == "repair_required":
            primary_message = "Un componente administrado necesita reparacion."
        elif readiness == "incompatible":
            primary_message = "La configuracion actual no es compatible."
        elif readiness == "limited_mode":
            primary_message = "La GPU no esta confirmada; puedes usar CPU o ejecutar la prueba funcional."

        secondary_message = "El resolver usa la evidencia local disponible sin descargas ni instalaciones."

        return TranscriptionCapabilityReport(
            resolution_id=str(uuid4()),
            generated_at=_utc_now(),
            current_user_preferences=current_preferences,
            readiness=readiness,
            can_transcribe_now=can_transcribe_now,
            requested_profile=requested_key,
            requested_device=requested_device,
            selected_profile=selected_profile,
            recommended_profile=fallback_profile or selected_profile,
            selected_model_component=selected_model_component,
            selected_model_component_id=selected_model_component_id,
            selected_model_installation_id=selected_model_component_id,
            selected_model_path=selected_model_path,
            selected_model_reference=selected_model_component_id,
            selected_runtime_component_id=runtime_component_id,
            selected_runtime_installation_id=runtime_installation_id,
            runtime_resolution=TranscriptionRuntimeResolution(
                installation=runtime_installation,
                status=runtime_status.value,
                selected_device=selected_device,
                compute_type=selected_compute_type,
                can_transcribe=can_transcribe_now,
                reason=fallback_reason,
                warnings=tuple(warnings),
                errors=(runtime_installation.error_message,) if runtime_installation.error_message else (),
            ),
            selected_ffmpeg_installation_id=ffmpeg_selected.component_id if ffmpeg_ok else None,
            selected_ffmpeg_source=ffmpeg_source,
            selected_device=selected_device,
            compute_type=selected_compute_type,
            internal_compute_configuration=internal_compute_configuration,
            ffmpeg_status=ffmpeg_installation.installation_status,
            ffprobe_status=ffprobe_installation.installation_status,
            runtime_status=runtime_status,
            model_status=TranscriptionCapabilityReport._model_status_to_component_status(selected_model_info.status),
            hardware_status=hardware_profile.status if hardware_profile is not None else HardwareCapabilityState.UNKNOWN,
            gpu_status=hardware_profile.gpu.status if hardware_profile is not None else HardwareCapabilityState.UNKNOWN,
            benchmark_status=benchmark_status,
            benchmark_age_seconds=benchmark_age_seconds,
            disk_status=disk_status,
            missing_component_ids=tuple(dict.fromkeys(missing)),
            blocking_reasons=tuple(dict.fromkeys(blockers)),
            blockers=tuple(dict.fromkeys(blockers)),
            warnings=tuple(dict.fromkeys(warnings)),
            degraded_reasons=tuple(dict.fromkeys(degraded_reasons)),
            stale_evidence=tuple(dict.fromkeys(stale_evidence)),
            estimated_required_disk_bytes=estimated_required_disk_bytes,
            available_disk_bytes=available_disk,
            fallback_available=fallback_available,
            fallback_profile=fallback_profile.profile_id if fallback_profile else None,
            fallback_device=fallback_device,
            fallback_reason=fallback_reason,
            suggested_actions=suggested_action_texts,
            structured_suggested_actions=tuple(suggested_actions),
            evidence_references=tuple(evidence),
            primary_message=primary_message,
            secondary_message=secondary_message,
            technical_summary=f"selected_model={selected_model_component_id}; device={selected_device}; compute={selected_compute_type}",
            resolver_version=self.version,
            profile_version=selected_profile.version if selected_profile else 1,
        )

    def present(self, report: TranscriptionCapabilityReport) -> TranscriptionCapabilityPresentation:
        if report.readiness == "ready":
            return TranscriptionCapabilityPresentation(
                title="Listo",
                message=f"Tu computadora está lista para transcribir con el perfil {report.selected_profile.display_name if report.selected_profile else report.requested_profile}.",
                details=report.to_dict(),
            )
        if "disk_space" in report.missing_component_ids:
            return TranscriptionCapabilityPresentation(
                title="Espacio insuficiente",
                message="La carpeta de modelos no tiene suficiente espacio.",
                details=report.to_dict(),
            )
        if "ffmpeg" in report.missing_component_ids or "ffprobe" in report.missing_component_ids:
            return TranscriptionCapabilityPresentation(
                title="Componente multimedia faltante",
                message="Falta el componente multimedia necesario para preparar el audio.",
                details=report.to_dict(),
            )
        if "transcription-runtime.ctranslate2" in report.missing_component_ids:
            return TranscriptionCapabilityPresentation(
                title="Motor faltante",
                message="Falta instalar el motor local de transcripcion.",
                details=report.to_dict(),
            )
        if report.model_status != ComponentInstallationStatus.READY:
            return TranscriptionCapabilityPresentation(
                title="Modelo faltante",
                message="Falta instalar el modelo Equilibrado. La descarga todavia no comenzara automaticamente.",
                details=report.to_dict(),
            )
        if report.gpu_status == HardwareCapabilityState.REPORTED_NOT_TESTED:
            return TranscriptionCapabilityPresentation(
                title="GPU no certificada",
                message="Se detectó una GPU NVIDIA, pero todavía no se ha comprobado que funcione con el motor de transcripción.",
                details=report.to_dict(),
            )
        return TranscriptionCapabilityPresentation(
            title="Modo limitado",
            message="La transcripcion puede continuar en modo limitado.",
            details=report.to_dict(),
        )

    def resolve_execution_plan(
        self,
        *,
        requested_profile: str = "balanced",
        preferred_device: str = "auto",
        available_disk_bytes: int | None = None,
        installations: dict[str, ComponentInstallation] | None = None,
        hardware_profile: HardwareProfile | None = None,
        allow_blocked: bool = False,
    ) -> "TranscriptionExecutionPlan":
        resolution = self.resolve(
            requested_profile=requested_profile,
            preferred_device=preferred_device,
            available_disk_bytes=available_disk_bytes,
            installations=installations,
            hardware_profile=hardware_profile,
        )
        if not resolution.can_transcribe_now and not allow_blocked:
            raise RuntimeError("La transcripcion local no puede comenzar con la resolucion actual.")
        return TranscriptionExecutionPlan(
            resolution_id=resolution.resolution_id,
            generated_at=resolution.generated_at,
            can_transcribe_now=resolution.can_transcribe_now,
            selected_profile=resolution.selected_profile,
            selected_profile_id=resolution.selected_profile.profile_id if resolution.selected_profile else resolution.requested_profile,
            selected_device=resolution.selected_device,
            compute_type=resolution.compute_type,
            selected_model_component_id=resolution.selected_model_component_id,
            selected_model_reference=resolution.selected_model_reference,
            selected_model_path=resolution.selected_model_path,
            selected_runtime_component_id=resolution.selected_runtime_component_id,
            selected_runtime_installation_id=resolution.selected_runtime_installation_id,
            selected_ffmpeg_installation_id=resolution.selected_ffmpeg_installation_id,
            selected_ffmpeg_source=resolution.selected_ffmpeg_source,
            ffmpeg_status=resolution.ffmpeg_status,
            ffprobe_status=resolution.ffprobe_status,
            runtime_status=resolution.runtime_status,
            model_status=resolution.model_status,
            hardware_status=resolution.hardware_status,
            gpu_status=resolution.gpu_status,
            benchmark_status=resolution.benchmark_status,
            benchmark_age_seconds=resolution.benchmark_age_seconds,
            disk_status=resolution.disk_status,
            temporary_space_bytes=resolution.estimated_required_disk_bytes,
            warnings=resolution.warnings,
            evidence_versions=resolution.evidence_references,
            primary_message=resolution.primary_message,
            secondary_message=resolution.secondary_message,
            technical_summary=resolution.technical_summary,
        )

    def capability_matrix(
        self,
        *,
        preferred_device: str = "auto",
        available_disk_bytes: int | None = None,
        installations: dict[str, ComponentInstallation] | None = None,
        hardware_profile: HardwareProfile | None = None,
    ) -> dict[str, TranscriptionCapabilityReport]:
        return {
            profile_id: self.resolve(
                requested_profile=profile_id,
                preferred_device=preferred_device,
                available_disk_bytes=available_disk_bytes,
                installations=installations,
                hardware_profile=hardware_profile,
            )
            for profile_id in ("fast", "balanced", "maximum_quality")
        }
