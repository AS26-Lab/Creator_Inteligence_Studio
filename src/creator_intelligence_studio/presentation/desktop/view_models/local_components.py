"""View-model for guided local components UI."""

from __future__ import annotations

from dataclasses import dataclass

from creator_intelligence_studio.application.services.component_manager_service import ComponentManagerStatus
from creator_intelligence_studio.application.services.transcription_capability_resolver import (
    TranscriptionCapabilityReport,
    TranscriptionExecutionPlan,
)
from creator_intelligence_studio.domain.components.entities import ComponentInstallation, ComponentInstallationStatus
from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel
from creator_intelligence_studio.shared.dates import to_iso_z


@dataclass(frozen=True, slots=True)
class LocalComponentsActionViewModel:
    action_id: str
    action_type: str
    label: str
    description: str
    available_now: bool
    blocking: bool
    target_component: str | None = None
    target_profile: str | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class LocalComponentsCardViewModel:
    key: str
    title: str
    description: str
    state_label: str
    explanation: str
    primary_action_label: str | None = None
    primary_action_id: str | None = None
    secondary_action_label: str = "Ver detalles"
    secondary_action_id: str = "toggle_details"
    details: tuple[str, ...] = ()
    technical_details: tuple[str, ...] = ()
    accent: str = "accent"


@dataclass(frozen=True, slots=True)
class LocalComponentsProfileOptionViewModel:
    profile_id: str
    title: str
    description: str
    selected: bool
    recommended: bool
    available: bool
    fallback_reason: str | None = None


@dataclass(frozen=True, slots=True)
class LocalComponentsDownloadTaskViewModel:
    task_id: str
    title: str
    status_label: str
    progress_label: str
    speed_label: str
    eta_label: str
    source_label: str
    component_id: str | None = None


@dataclass(frozen=True, slots=True)
class LocalComponentsStatusViewModel:
    readiness: str
    can_transcribe_now: bool
    title: str
    primary_message: str
    secondary_message: str
    selected_profile_label: str
    recommended_profile_label: str
    selected_device_label: str
    compute_type_label: str
    ffmpeg_summary: str
    runtime_summary: str
    model_summary: str
    gpu_summary: str
    component_cards: tuple[LocalComponentsCardViewModel, ...] = ()
    profile_options: tuple[LocalComponentsProfileOptionViewModel, ...] = ()
    suggested_actions: tuple[LocalComponentsActionViewModel, ...] = ()
    download_tasks: tuple[LocalComponentsDownloadTaskViewModel, ...] = ()
    technical_summary: str | None = None
    benchmark_age_label: str | None = None
    disk_label: str | None = None
    summary_details: tuple[str, ...] = ()
    execution_plan: TranscriptionExecutionPlan | None = None
    capability_report: TranscriptionCapabilityReport | None = None
    component_status: ComponentManagerStatus | None = None


def _status_label(installation: ComponentInstallation | None) -> str:
    if installation is None:
        return "No comprobado"
    mapping = {
        ComponentInstallationStatus.READY: "Listo",
        ComponentInstallationStatus.MISSING: "No instalado",
        ComponentInstallationStatus.UNKNOWN: "No comprobado",
        ComponentInstallationStatus.INCOMPATIBLE: "No compatible",
        ComponentInstallationStatus.REPAIR_REQUIRED: "Necesita reparacion",
        ComponentInstallationStatus.INVALID: "Necesita reparacion",
        ComponentInstallationStatus.EXTERNALLY_DETECTED: "Instalacion externa",
        ComponentInstallationStatus.MANAGED: "Listo",
    }
    return mapping.get(installation.installation_status, installation.installation_status.value)


def _installation_explanation(installation: ComponentInstallation | None) -> str:
    if installation is None:
        return "No se encontro evidencia local."
    if installation.installation_status == ComponentInstallationStatus.READY:
        return "La evidencia local confirma que esta disponible."
    if installation.installation_status == ComponentInstallationStatus.EXTERNALLY_DETECTED:
        return "Se detecto una instalacion externa usable."
    if installation.installation_status in {ComponentInstallationStatus.INVALID, ComponentInstallationStatus.REPAIR_REQUIRED}:
        return installation.last_error_message or "Necesita reparacion."
    if installation.installation_status == ComponentInstallationStatus.INCOMPATIBLE:
        return installation.last_error_message or "No es compatible con este equipo."
    if installation.installation_status == ComponentInstallationStatus.MISSING:
        return "Todavia no esta instalado."
    return installation.last_error_message or "Estado no comprobado."


def _profile_title(profile_id: str) -> str:
    return {
        "fast": "Rapido",
        "balanced": "Equilibrado",
        "maximum_quality": "Maxima calidad",
        "custom": "Personalizado",
    }.get(profile_id, profile_id)


def _profile_description(profile_id: str) -> str:
    return {
        "fast": "Menor uso de recursos y mayor velocidad.",
        "balanced": "Recomendado para la mayoria de los equipos.",
        "maximum_quality": "Usa mas recursos para priorizar precision.",
        "custom": "Configuracion personalizada.",
    }.get(profile_id, "Perfil disponible.")


def _action_label(action_type: str) -> str:
    return {
        "run_gpu_benchmark": "Probar GPU",
        "install_component": "Instalar",
        "repair_component": "Reparar",
        "choose_profile": "Usar este perfil",
        "use_cpu": "Usar procesador",
        "use_gpu": "Usar GPU",
        "verify_component": "Comprobar",
        "relocate_component": "Reubicar",
        "free_disk_space": "Liberar espacio",
        "continue_limited": "Continuar en modo limitado",
        "retry_health_check": "Reintentar comprobacion",
        "open_local_install": "Instalar desde archivo local",
    }.get(action_type, action_type.replace("_", " ").title())


def _component_card_from_installation(
    *,
    key: str,
    title: str,
    description: str,
    installation: ComponentInstallation | None,
    primary_action_label: str | None = None,
    primary_action_id: str | None = None,
    details: tuple[str, ...] = (),
) -> LocalComponentsCardViewModel:
    technical: list[str] = []
    if installation is not None:
        if installation.installed_version:
            technical.append(f"Version: {installation.installed_version}")
        if installation.revision:
            technical.append(f"Revision: {installation.revision}")
        if installation.install_type:
            technical.append(f"Tipo: {installation.install_type.value}")
        if installation.location_reference:
            technical.append(f"Referencia: {installation.location_reference}")
        if installation.source:
            technical.append(f"Origen: {installation.source}")
        technical.append(f"Salud: {installation.health_status.value}")
        if installation.verified_at is not None:
            technical.append(f"Verificado: {to_iso_z(installation.verified_at)}")
        if installation.detected_at is not None:
            technical.append(f"Detectado: {to_iso_z(installation.detected_at)}")
    return LocalComponentsCardViewModel(
        key=key,
        title=title,
        description=description,
        state_label=_status_label(installation),
        explanation=_installation_explanation(installation),
        primary_action_label=primary_action_label,
        primary_action_id=primary_action_id,
        details=details,
        technical_details=tuple(technical),
    )


class LocalComponentsViewModel:
    """Read-only presentation layer for local component readiness."""

    def __init__(self, workspace: WorkspaceViewModel) -> None:
        self.workspace = workspace
        self._last_status: LocalComponentsStatusViewModel | None = None

    def load_capability(self, *, profile: str | None = None, preferred_device: str | None = None) -> TranscriptionCapabilityReport | None:
        profile_name = profile or self.workspace.ui_state.transcription_profile
        device_name = preferred_device or self.workspace.ui_state.preferred_transcription_device
        return self.workspace.transcription_capability(profile=profile_name, preferred_device=device_name)

    def _component_status(self, report: TranscriptionCapabilityReport | None) -> ComponentManagerStatus | None:
        profile_name = report.requested_profile if report is not None else self.workspace.ui_state.transcription_profile
        device_name = report.requested_device if report is not None else self.workspace.ui_state.preferred_transcription_device
        return self.workspace.component_manager_status(profile=profile_name, preferred_device=device_name)

    def load_component_cards(
        self,
        report: TranscriptionCapabilityReport | None = None,
        *,
        component_status: ComponentManagerStatus | None = None,
    ) -> tuple[LocalComponentsCardViewModel, ...]:
        capability = report or self.load_capability()
        component_status = component_status or self._component_status(capability)
        installations = {installation.component_id: installation for installation in component_status.installations} if component_status else {}
        ffmpeg = installations.get("ffmpeg")
        ffprobe = installations.get("ffprobe")
        runtime = installations.get("transcription-runtime.faster-whisper") or installations.get("transcription-runtime.ctranslate2")
        model = installations.get(capability.selected_model_component_id) if capability and capability.selected_model_component_id else None
        gpu_state = "No comprobado"
        gpu_explanation = "No se pudo comprobar la GPU."
        if capability is not None:
            gpu_state = {
                "DETECTED": "Lista",
                "REPORTED_NOT_TESTED": "No comprobada",
                "NOT_DETECTED": "No detectada",
                "FAILED": "No disponible",
            }.get(capability.gpu_status.name, "No comprobado")
            gpu_explanation = {
                "DETECTED": "Se detecto una GPU compatible. Puedes probarla para confirmar su funcionamiento.",
                "REPORTED_NOT_TESTED": "Se detecto una GPU compatible, pero aun no fue comprobada.",
                "NOT_DETECTED": "No se detecto una GPU compatible. Puedes seguir usando el procesador.",
                "FAILED": "La prueba de GPU no pudo completarse. Puedes usar el procesador.",
            }.get(capability.gpu_status.name, gpu_explanation)
        gpu_card = LocalComponentsCardViewModel(
            key="gpu",
            title="Aceleracion por GPU",
            description="Comprueba si la GPU esta lista para transcribir.",
            state_label=gpu_state,
            explanation=gpu_explanation,
            primary_action_label="Probar GPU",
            primary_action_id="run_gpu_benchmark",
            technical_details=(
                f"Benchmark: {capability.benchmark_status.value if capability and capability.benchmark_status else 'no verificado'}",
                f"Edad de evidencia: {capability.benchmark_age_seconds:.0f} s" if capability and capability.benchmark_age_seconds is not None else "Edad de evidencia: no verificada",
            ),
        )
        return (
            _component_card_from_installation(
                key="ffmpeg",
                title="Componente multimedia",
                description="Prepara el audio de tus videos para poder analizarlo y transcribirlo.",
                installation=ffmpeg,
                details=(f"FFprobe: {_status_label(ffprobe)}",),
            ),
            _component_card_from_installation(
                key="runtime",
                title="Motor de transcripcion",
                description="Ejecuta la transcripcion local en tu computadora.",
                installation=runtime,
                primary_action_label="Ver detalles",
                primary_action_id="toggle_details",
            ),
            _component_card_from_installation(
                key="model",
                title="Modelo de transcripcion",
                description="Convierte la voz del video en texto.",
                installation=model,
                primary_action_label="Ver detalles",
                primary_action_id="toggle_details",
            ),
            gpu_card,
        )

    def _profile_options(
        self,
        report: TranscriptionCapabilityReport | None,
        *,
        matrix: dict[str, TranscriptionCapabilityReport] | None = None,
    ) -> tuple[LocalComponentsProfileOptionViewModel, ...]:
        matrix = matrix or self.workspace.transcription_capability_matrix(
            preferred_device=report.requested_device if report is not None else self.workspace.ui_state.preferred_transcription_device
        )
        selected_profile_id = report.selected_profile.profile_id if report and report.selected_profile else self.workspace.ui_state.transcription_profile
        recommended_profile_id = report.recommended_profile.profile_id if report and report.recommended_profile else selected_profile_id
        options: list[LocalComponentsProfileOptionViewModel] = []
        for profile_id in ("fast", "balanced", "maximum_quality", "custom"):
            if profile_id != "custom" and profile_id not in matrix:
                continue
            available = profile_id == "custom" or profile_id in matrix
            options.append(
                LocalComponentsProfileOptionViewModel(
                    profile_id=profile_id,
                    title=_profile_title(profile_id),
                    description=_profile_description(profile_id),
                    selected=profile_id == selected_profile_id,
                    recommended=profile_id == recommended_profile_id,
                    available=available,
                    fallback_reason=None if profile_id == selected_profile_id else ("fallback" if available else "missing"),
                )
            )
        return tuple(options)

    def _suggested_actions(self, report: TranscriptionCapabilityReport | None) -> tuple[LocalComponentsActionViewModel, ...]:
        if report is None:
            return ()
        return tuple(
            LocalComponentsActionViewModel(
                action_id=action.action_id,
                action_type=action.action_type,
                label=_action_label(action.action_type),
                description=action.description or action.reason or "",
                available_now=action.available_now,
                blocking=action.blocking,
                target_component=action.target_component,
                target_profile=action.target_profile,
                reason=action.reason,
            )
            for action in report.structured_suggested_actions
        )

    def _download_tasks(self) -> tuple[LocalComponentsDownloadTaskViewModel, ...]:
        tasks: list[LocalComponentsDownloadTaskViewModel] = []
        for task in self.workspace.background_tasks():
            payload = getattr(task, "payload", {}) or {}
            if not isinstance(payload, dict) or payload.get("kind") != "component_download":
                continue
            progress = payload.get("progress") if isinstance(payload.get("progress"), dict) else {}
            downloaded = progress.get("downloaded_bytes")
            total = progress.get("total_bytes")
            percentage = progress.get("percentage")
            speed = progress.get("speed_bytes_per_second")
            eta = progress.get("eta_seconds")
            tasks.append(
                LocalComponentsDownloadTaskViewModel(
                    task_id=task.task_id,
                    title=getattr(task, "title", "Descarga de componente"),
                    status_label=str(getattr(task, "status", "") or ""),
                    progress_label=f"{percentage:.1f}%" if isinstance(percentage, (int, float)) else f"{downloaded or 0} / {total or 'no verificado'}",
                    speed_label=f"{speed:.0f} B/s" if isinstance(speed, (int, float)) else "Velocidad no verificada",
                    eta_label=f"{eta:.1f} s" if isinstance(eta, (int, float)) else "ETA no disponible",
                    source_label=str(payload.get("source_summary") or payload.get("source") or "Origen local"),
                    component_id=str(payload.get("component_id") or getattr(task, "video_title", "") or ""),
                )
            )
        return tuple(tasks)

    def refresh_status(self) -> LocalComponentsStatusViewModel:
        report = self.load_capability()
        component_status = self._component_status(report)
        matrix = self.workspace.transcription_capability_matrix(
            preferred_device=report.requested_device if report is not None else self.workspace.ui_state.preferred_transcription_device
        )
        execution_plan = self.workspace.transcription_execution_plan(
            profile=report.requested_profile if report is not None else self.workspace.ui_state.transcription_profile,
            preferred_device=report.requested_device if report is not None else self.workspace.ui_state.preferred_transcription_device,
        )
        cards = self.load_component_cards(report, component_status=component_status)
        suggested_actions = self._suggested_actions(report)
        profile_options = self._profile_options(report, matrix=matrix)

        installations = {installation.component_id: installation for installation in component_status.installations} if component_status else {}
        ffmpeg = installations.get("ffmpeg")
        ffprobe = installations.get("ffprobe")
        runtime = installations.get("transcription-runtime.faster-whisper") or installations.get("transcription-runtime.ctranslate2")
        model = installations.get(report.selected_model_component_id) if report and report.selected_model_component_id else None

        ffmpeg_summary = "No comprobado"
        if ffmpeg or ffprobe:
            ffmpeg_summary = f"{_status_label(ffmpeg)} / {_status_label(ffprobe)}"
        runtime_summary = _status_label(runtime)
        model_summary = _status_label(model)
        gpu_summary = "No comprobada"
        if report is not None:
            gpu_summary = {
                "DETECTED": "Lista",
                "REPORTED_NOT_TESTED": "No comprobada",
                "NOT_DETECTED": "No detectada",
                "FAILED": "No disponible",
            }.get(report.gpu_status.name, report.gpu_status.name)

        selected_profile_label = report.selected_profile.display_name if report and report.selected_profile else _profile_title(self.workspace.ui_state.transcription_profile)
        recommended_profile_label = report.recommended_profile.display_name if report and report.recommended_profile else selected_profile_label
        selected_device = report.selected_device if report else self.workspace.ui_state.preferred_transcription_device
        selected_device_label = {"cpu": "Procesador", "gpu": "GPU", "auto": "Automatico"}.get(selected_device, "Automatico")
        compute_type_label = report.compute_type if report and report.compute_type else "No verificado"
        benchmark_age_label = f"{report.benchmark_age_seconds:.0f} s" if report and report.benchmark_age_seconds is not None else None
        available_disk_bytes = getattr(report, "available_disk_bytes", None) if report is not None else None
        disk_label = f"{available_disk_bytes} bytes libres" if available_disk_bytes is not None else None

        status = LocalComponentsStatusViewModel(
            readiness=report.readiness if report else "unknown",
            can_transcribe_now=bool(report.can_transcribe_now) if report else False,
            title="Componentes locales",
            primary_message=report.primary_message if report else "No se pudo evaluar la disponibilidad local.",
            secondary_message=report.secondary_message if report else "Se requiere resolver la configuracion local.",
            selected_profile_label=selected_profile_label,
            recommended_profile_label=recommended_profile_label,
            selected_device_label=selected_device_label,
            compute_type_label=compute_type_label,
            ffmpeg_summary=ffmpeg_summary,
            runtime_summary=runtime_summary,
            model_summary=model_summary,
            gpu_summary=gpu_summary,
            component_cards=cards,
            profile_options=profile_options,
            suggested_actions=suggested_actions,
            download_tasks=self._download_tasks(),
            technical_summary=report.technical_summary if report else None,
            benchmark_age_label=benchmark_age_label,
            disk_label=disk_label,
            summary_details=tuple(report.blockers if report else ()),
            execution_plan=execution_plan,
            capability_report=report,
            component_status=component_status,
        )
        self._last_status = status
        return status

    def refresh_after_task(self) -> LocalComponentsStatusViewModel:
        return self.refresh_status()

    def execute_available_action(self, action_id: str) -> bool:
        status = self._last_status or self.refresh_status()
        action = next((item for item in status.suggested_actions if item.action_id == action_id), None)
        if action is None or not action.available_now:
            return False
        if action.action_type == "choose_profile" and action.target_profile:
            self.workspace.set_transcription_preferences(profile=action.target_profile)
            return True
        if action.action_type == "use_cpu":
            self.workspace.set_transcription_preferences(device="cpu")
            return True
        if action.action_type == "use_gpu":
            self.workspace.set_transcription_preferences(device="gpu")
            return True
        if action.action_type == "run_gpu_benchmark":
            self.workspace.run_transcription_benchmark(
                profile=self.workspace.ui_state.transcription_profile,
                preferred_device="gpu",
                persist_result=True,
            )
            return True
        if action.action_type in {"retry_health_check", "verify_component"}:
            self.refresh_status()
            return True
        if action.action_type == "continue_limited":
            return True
        return False

    def open_local_install(self) -> bool:
        return False
