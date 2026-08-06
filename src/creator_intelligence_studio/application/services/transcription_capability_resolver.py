"""Resolucion determinista de capacidad de transcripcion local."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

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
from creator_intelligence_studio.infrastructure.media.ffmpeg_locator import MediaToolLocator
from creator_intelligence_studio.infrastructure.transcription.model_manager import TranscriptionModelManager
from creator_intelligence_studio.shared.paths import ProjectPaths


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


@dataclass(frozen=True, slots=True)
class TranscriptionCapabilityReport:
    """Resultado tecnico de evaluacion de capacidad local."""

    readiness: str
    requested_profile: str
    selected_profile: TranscriptionProfileDefinition | None
    recommended_profile: TranscriptionProfileDefinition | None
    selected_model_component: ComponentCatalogEntry | None
    selected_device: str
    compute_type: str | None
    ffmpeg_status: ComponentInstallationStatus
    ffprobe_status: ComponentInstallationStatus
    runtime_status: RuntimeCheckStatus
    model_status: ComponentInstallationStatus
    gpu_status: HardwareCapabilityState
    missing_component_ids: tuple[str, ...] = ()
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    estimated_required_disk_bytes: int | None = None
    available_disk_bytes: int | None = None
    suggested_actions: tuple[str, ...] = ()
    evidence_references: tuple[str, ...] = ()
    resolver_version: int = 1
    profile_version: int = 1

    def to_dict(self) -> dict[str, object]:
        return {
            "readiness": self.readiness,
            "requested_profile": self.requested_profile,
            "selected_profile": self.selected_profile.to_dict() if self.selected_profile else None,
            "recommended_profile": self.recommended_profile.to_dict() if self.recommended_profile else None,
            "selected_model_component": self.selected_model_component.to_dict() if self.selected_model_component else None,
            "selected_device": self.selected_device,
            "compute_type": self.compute_type,
            "ffmpeg_status": self.ffmpeg_status.value,
            "ffprobe_status": self.ffprobe_status.value,
            "runtime_status": self.runtime_status.value,
            "model_status": self.model_status.value,
            "gpu_status": self.gpu_status.value,
            "missing_component_ids": list(self.missing_component_ids),
            "blocking_reasons": list(self.blocking_reasons),
            "warnings": list(self.warnings),
            "estimated_required_disk_bytes": self.estimated_required_disk_bytes,
            "available_disk_bytes": self.available_disk_bytes,
            "suggested_actions": list(self.suggested_actions),
            "evidence_references": list(self.evidence_references),
            "resolver_version": self.resolver_version,
            "profile_version": self.profile_version,
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
        requested = profiles.get(requested_key)
        requested_model_component_id = requested.model_component_id if requested and requested.model_component_id else None
        requested_model_installation = self._resolve_installation(
            requested_model_component_id or self._model_component_id("small"),
            installations,
        )
        ffmpeg_installation = self._resolve_installation("ffmpeg", installations)
        ffprobe_installation = self._resolve_installation("ffprobe", installations)
        runtime_installation = self._resolve_installation("transcription-runtime.ctranslate2", installations)

        recommended = requested
        warnings: list[str] = []
        blocking: list[str] = []
        missing: list[str] = []
        actions: list[str] = []

        available_models = [profile for profile in profiles.values() if profile.model_component_id]
        if requested is None:
            warnings.append("El perfil solicitado no existe en el catalogo local.")
            recommended = profiles.get("balanced") or profiles.get("fast") or next(iter(available_models), None)
        elif requested_key == "balanced" and requested_model_installation.installation_status != ComponentInstallationStatus.READY:
            fast_profile = profiles.get("fast")
            fast_model_component_id = fast_profile.model_component_id if fast_profile and fast_profile.model_component_id else self._model_component_id("base")
            fast_installation = self._resolve_installation(fast_model_component_id, installations)
            if fast_profile is not None and fast_installation.installation_status == ComponentInstallationStatus.READY:
                recommended = fast_profile

        selected_profile = recommended or requested
        target_profile = selected_profile or requested or profiles.get("balanced") or next(iter(available_models), None)
        model_component_id = target_profile.model_component_id if target_profile and target_profile.model_component_id else self._model_component_id("small")
        selected_model_component = catalog.get_entry(model_component_id)
        model_installation = self._resolve_installation(model_component_id, installations)

        if ffmpeg_installation.installation_status not in {ComponentInstallationStatus.READY, ComponentInstallationStatus.EXTERNALLY_DETECTED, ComponentInstallationStatus.MANAGED}:
            missing.append("ffmpeg")
            blocking.append("Falta instalar o detectar FFmpeg para preparar audio desde video.")
            actions.append("Instala FFmpeg o configura una ruta valida antes de continuar.")
        if ffprobe_installation.installation_status not in {ComponentInstallationStatus.READY, ComponentInstallationStatus.EXTERNALLY_DETECTED, ComponentInstallationStatus.MANAGED}:
            missing.append("ffprobe")
            blocking.append("Falta instalar o detectar FFprobe para inspeccionar medios.")
            actions.append("Instala FFprobe o configura una ruta valida antes de continuar.")
        if runtime_installation.installation_status not in {ComponentInstallationStatus.READY, ComponentInstallationStatus.EXTERNALLY_DETECTED, ComponentInstallationStatus.MANAGED}:
            missing.append("transcription-runtime.ctranslate2")
            blocking.append("Falta el runtime local de transcripcion.")
            actions.append("Instala el runtime de transcripcion antes de continuar.")
        if model_installation.installation_status not in {ComponentInstallationStatus.READY, ComponentInstallationStatus.EXTERNALLY_DETECTED, ComponentInstallationStatus.MANAGED}:
            missing.append(model_component_id)
            blocking.append("Falta instalar el modelo de transcripcion solicitado.")
            if selected_profile and selected_profile.profile_id != requested_key:
                actions.append(f"Usa el perfil {selected_profile.display_name} mientras instalas el perfil solicitado.")
            else:
                actions.append("Usa Componentes locales para instalar el modelo solicitado.")

        runtime_state = runtime_installation.health_status
        gpu_status = hardware_profile.gpu.status if hardware_profile is not None else HardwareCapabilityState.UNKNOWN
        benchmark_record = self._latest_benchmark_record(target_profile.model_component_id if target_profile else None)
        benchmark_device = None
        benchmark_status = None
        benchmark_evidence: list[str] = []
        if benchmark_record is not None:
            metadata = dict(benchmark_record.metadata or {})
            benchmark_device = str(metadata.get("actual_device") or metadata.get("requested_device") or "").strip().lower() or None
            benchmark_status = str(metadata.get("status") or benchmark_record.status.value).strip().lower() or None
            benchmark_evidence.append(f"benchmark_status={benchmark_status}")
            if metadata.get("benchmark_id"):
                benchmark_evidence.append(f"benchmark_id={metadata['benchmark_id']}")
            if metadata.get("selected_compute_type"):
                benchmark_evidence.append(f"benchmark_compute_type={metadata['selected_compute_type']}")
            if benchmark_device in {"gpu", "cuda"} and benchmark_status in {"completed", "completed_with_warnings"}:
                gpu_status = HardwareCapabilityState.DETECTED
        if hardware_profile is not None and hardware_profile.gpu.status == HardwareCapabilityState.REPORTED_NOT_TESTED:
            warnings.append("Se detecto una GPU NVIDIA, pero falta ejecutar una prueba de transcripcion para confirmarla.")
        available_disk = available_disk_bytes
        if available_disk is None and hardware_profile is not None:
            available_disk = max((volume.free_bytes or 0) for volume in hardware_profile.disk_volumes) if hardware_profile.disk_volumes else None
        required_disk = selected_profile.estimated_disk_bytes if selected_profile else None
        if required_disk is not None and available_disk is not None and available_disk < required_disk:
            blocking.append("No hay suficiente espacio para el perfil solicitado.")
            actions.append("Libera espacio o cambia la carpeta de modelos.")
            missing.append("disk_space")

        selected_device = preferred_device.strip().lower() if preferred_device else "auto"
        if selected_device not in {"auto", "cpu", "gpu"}:
            selected_device = "auto"
        compute_type = selected_profile.cpu_compute_type if selected_device == "cpu" else selected_profile.gpu_compute_type if selected_profile and selected_device == "gpu" else selected_profile.cpu_compute_type if selected_profile else None

        if blocking:
            readiness = "missing_components"
            if hardware_profile is not None and hardware_profile.gpu.status == HardwareCapabilityState.REPORTED_NOT_TESTED:
                readiness = "limited_mode"
        elif warnings:
            readiness = "ready_with_warnings"
        else:
            readiness = "ready"
        if hardware_profile is not None and hardware_profile.gpu.status != HardwareCapabilityState.REPORTED_NOT_TESTED:
            if selected_device == "gpu" and hardware_profile.gpu.status not in {HardwareCapabilityState.DETECTED, HardwareCapabilityState.REPORTED_NOT_TESTED}:
                selected_device = "cpu"
                compute_type = selected_profile.cpu_compute_type if selected_profile else None
        if hardware_profile is not None and hardware_profile.gpu.status == HardwareCapabilityState.REPORTED_NOT_TESTED and selected_device == "gpu" and not (
            benchmark_record is not None and benchmark_device in {"gpu", "cuda"} and benchmark_status in {"completed", "completed_with_warnings"}
        ):
            selected_device = "cpu"
            compute_type = selected_profile.cpu_compute_type if selected_profile else None
            warnings.append("Se detecto una GPU, pero el perfil todavia no puede certificarla; se usara CPU por seguridad.")
        if benchmark_record is not None and benchmark_device in {"gpu", "cuda"} and benchmark_status in {"completed", "completed_with_warnings"} and selected_device in {"auto", "gpu"}:
            selected_device = "gpu"
            compute_type = str((benchmark_record.metadata or {}).get("selected_compute_type") or compute_type or selected_profile.gpu_compute_type or selected_profile.cpu_compute_type or "int8_float16")
            warnings = [warning for warning in warnings if "GPU NVIDIA" not in warning]
        if not blocking:
            readiness = "ready_with_warnings" if warnings else "ready"

        if not blocking and selected_profile and selected_profile.profile_id == "fast":
            actions.append("El perfil Rapido esta listo para usarse con CPU.")

        evidence = [
            f"catalog_version={catalog.catalog_version}",
            f"profile_version={selected_profile.version if selected_profile else 'unknown'}",
            f"runtime_status={runtime_state.value}",
            f"gpu_status={gpu_status.value}",
        ]
        evidence.extend(benchmark_evidence)
        return TranscriptionCapabilityReport(
            readiness=readiness,
            requested_profile=requested_key,
            selected_profile=selected_profile,
            recommended_profile=recommended or requested or selected_profile,
            selected_model_component=selected_model_component,
            selected_device=selected_device,
            compute_type=compute_type,
            ffmpeg_status=ffmpeg_installation.installation_status,
            ffprobe_status=ffprobe_installation.installation_status,
            runtime_status=runtime_state,
            model_status=model_installation.installation_status,
            gpu_status=gpu_status,
            missing_component_ids=tuple(dict.fromkeys(missing)),
            blocking_reasons=tuple(dict.fromkeys(blocking)),
            warnings=tuple(dict.fromkeys(warnings)),
            estimated_required_disk_bytes=required_disk,
            available_disk_bytes=available_disk,
            suggested_actions=tuple(dict.fromkeys(actions)),
            evidence_references=tuple(evidence),
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
