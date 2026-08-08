"""Explicit local component action dispatch for the desktop UI."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from uuid import uuid4

from creator_intelligence_studio.application.services.component_manager_service import ComponentManagerService
from creator_intelligence_studio.domain.components.entities import ComponentInstallation, ComponentInstallationStatus
from creator_intelligence_studio.presentation.desktop.ui_state import BackgroundTaskRecord
from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


@dataclass(frozen=True, slots=True)
class ComponentActionRequest:
    action_type: str
    component_id: str | None = None
    installation_id: str | None = None
    profile: str | None = None
    local_source: str | None = None
    user_confirmation: bool = False
    source_context: str | None = None
    request_id: str = field(default_factory=lambda: uuid4().hex)
    artifact_id: str | None = None


@dataclass(frozen=True, slots=True)
class ComponentActionExecution:
    action_id: str
    task_id: str
    status: str
    component_id: str | None
    operation: str
    started_at: str
    finished_at: str | None
    terminal_result: dict[str, object] | None
    safe_error: str | None
    suggested_next_action: str | None
    cancellable: bool
    task_status: str
    progress_percent: float


class _CancellationToken:
    def __init__(self) -> None:
        self._cancelled = False
        self._lock = Lock()

    def cancel(self) -> None:
        with self._lock:
            self._cancelled = True

    def cancelled(self) -> bool:
        with self._lock:
            return self._cancelled


class LocalComponentActionService:
    """Executes validated local component actions and records task lifecycle."""

    def __init__(self, workspace: WorkspaceViewModel) -> None:
        self.workspace = workspace
        self.component_manager_service: ComponentManagerService | None = workspace.component_manager_service
        self._component_locks: dict[str, Lock] = {}
        self._active_tokens: dict[str, _CancellationToken] = {}
        self._lock = Lock()

    def _component_lock(self, component_id: str) -> Lock:
        normalized = component_id.strip().lower()
        with self._lock:
            lock = self._component_locks.get(normalized)
            if lock is None:
                lock = Lock()
                self._component_locks[normalized] = lock
            return lock

    def _component_status_map(self) -> dict[str, ComponentInstallation]:
        if self.component_manager_service is None:
            return {}
        status = self.workspace.component_manager_status(
            profile=self.workspace.ui_state.transcription_profile,
            preferred_device=self.workspace.ui_state.preferred_transcription_device,
        )
        return {installation.component_id: installation for installation in status.installations}

    def _current_installation(self, component_id: str | None) -> ComponentInstallation | None:
        if component_id is None:
            return None
        return self._component_status_map().get(component_id.strip().lower())

    def _current_report(self):
        return self.workspace.transcription_capability(
            profile=self.workspace.ui_state.transcription_profile,
            preferred_device=self.workspace.ui_state.preferred_transcription_device,
        )

    def _profile_revision(self, profile_id: str | None) -> str | None:
        if self.component_manager_service is None or not profile_id:
            return None
        profile = self.component_manager_service.repository.get_transcription_profile(profile_id)
        return getattr(profile, "model_revision", None) if profile is not None else None

    def _current_action(self, request: ComponentActionRequest):
        report = self._current_report()
        if report is None:
            return None
        if request.action_type in {"choose_profile", "use_cpu", "use_gpu", "continue_limited"}:
            return None
        component_id = (request.component_id or "").strip().lower() or None
        for action in report.structured_suggested_actions:
            if action.action_type != request.action_type:
                continue
            if component_id is not None and action.target_component is not None and action.target_component.strip().lower() != component_id:
                continue
            if request.profile is not None and action.target_profile is not None and action.target_profile.strip().lower() != request.profile.strip().lower():
                continue
            if not action.available_now:
                continue
            return action
        return None

    def _task_title(self, request: ComponentActionRequest) -> str:
        label = {
            "verify_component": "Comprobar componente",
            "run_gpu_benchmark": "Probar GPU",
            "install_component": "Instalar componente",
            "repair_component": "Reparar componente",
            "remove_component": "Eliminar componente",
            "choose_profile": "Cambiar perfil",
            "use_cpu": "Usar procesador",
            "use_gpu": "Usar GPU",
            "continue_limited": "Continuar en modo limitado",
        }.get(request.action_type, request.action_type.replace("_", " ").title())
        return label

    def _safe_error(self, category: str, default: str) -> str:
        return {
            "action_no_longer_available": "La accion ya no esta disponible.",
            "component_changed": "El componente cambió y la accion se revalido.",
            "component_in_use": "El componente esta siendo utilizado por otra tarea.",
            "source_required": "Se necesita un archivo o carpeta local para continuar.",
            "operation_not_supported": "Esta accion no esta soportada para este componente.",
            "repair_source_unavailable": "Se necesita el archivo de instalacion para reparar este componente.",
            "invalid_source": "El archivo seleccionado no es valido para este componente.",
            "health_check_failed": "La instalacion termino, pero el componente no pudo verificarse.",
            "activation_failed": "No se pudo activar el componente. La instalacion anterior se conservó.",
            "component_locked": "Hay otra operacion en curso sobre este componente.",
        }.get(category, default)

    def _register_task(self, request: ComponentActionRequest, *, cancellable: bool) -> str:
        now = _now()
        task = self.workspace.register_background_task(
            title=self._task_title(request),
            status="running",
            stage_name="preparing",
            action_id=request.request_id,
            progress_percent=0.0,
            message="Preparando la accion local.",
            cancellable=cancellable,
            payload={
                "kind": "component_action",
                "action_type": request.action_type,
                "component_id": request.component_id,
                "profile": request.profile,
                "source_context": request.source_context,
                "request_id": request.request_id,
                "operation_id": request.request_id,
                "requested_at": now,
                "last_heartbeat_at": now,
                "cancellable": cancellable,
            },
        )
        return task.task_id

    def _update_task(self, task_id: str, *, stage_name: str, progress_percent: float, message: str, cancellable: bool | None = None) -> None:
        changes = dict(stage_name=stage_name, progress_percent=progress_percent, message=message)
        if cancellable is not None:
            changes["cancellable"] = cancellable
        self.workspace.update_background_task(task_id, **changes)

    def _finish_task(self, task_id: str, *, message: str, status: str = "completed") -> None:
        if status == "completed":
            self.workspace.complete_background_task(task_id, message)
        elif status == "cancelled":
            self.workspace.update_background_task(
                task_id,
                status="cancelled",
                progress_percent=100.0,
                message=message,
                cancellable=False,
                cancelled_at=_now(),
            )
        elif status == "failed":
            self.workspace.fail_background_task(task_id, message)
        else:
            self.workspace.interrupt_background_task(task_id, message)

    def _token_for(self, task_id: str) -> _CancellationToken:
        with self._lock:
            token = self._active_tokens.get(task_id)
            if token is None:
                token = _CancellationToken()
                self._active_tokens[task_id] = token
            return token

    def request_cancellation(self, task_id: str) -> BackgroundTaskRecord | None:
        with self._lock:
            token = self._active_tokens.get(task_id)
        task = next((item for item in self.workspace.background_tasks() if item.task_id == task_id), None)
        if task is None or not getattr(task, "cancellable", False):
            return None
        payload = dict(getattr(task, "payload", {}) or {})
        payload["cancellation_requested"] = True
        payload["last_heartbeat_at"] = _now()
        if token is not None:
            token.cancel()
        return self.workspace.update_background_task(
            task_id,
            status="cancel_requested",
            message="Estamos esperando a que la operacion llegue a un punto seguro para cancelarse.",
            cancellable=True,
            cancel_requested_at=_now(),
            last_heartbeat_at=_now(),
            payload=payload,
        )

    def execute(self, request: ComponentActionRequest) -> ComponentActionExecution:
        if self.component_manager_service is None:
            return ComponentActionExecution(
                action_id=request.request_id,
                task_id=request.request_id,
                status="failed",
                component_id=request.component_id,
                operation=request.action_type,
                started_at=_now(),
                finished_at=_now(),
                terminal_result=None,
                safe_error="El servicio de componentes locales no esta disponible.",
                suggested_next_action=None,
                cancellable=False,
                task_status="failed",
                progress_percent=0.0,
            )

        action = self._current_action(request)
        if request.action_type not in {"choose_profile", "use_cpu", "use_gpu", "continue_limited"} and action is None:
            safe_error = self._safe_error("action_no_longer_available", "La accion ya no esta disponible.")
            return ComponentActionExecution(
                action_id=request.request_id,
                task_id=request.request_id,
                status="failed",
                component_id=request.component_id,
                operation=request.action_type,
                started_at=_now(),
                finished_at=_now(),
                terminal_result=None,
                safe_error=safe_error,
                suggested_next_action=None,
                cancellable=False,
                task_status="failed",
                progress_percent=0.0,
            )
        if request.action_type in {"install_component", "repair_component", "remove_component"} and not request.user_confirmation:
            safe_error = "La accion requiere confirmacion explicita."
            return ComponentActionExecution(
                action_id=request.request_id,
                task_id=request.request_id,
                status="failed",
                component_id=request.component_id,
                operation=request.action_type,
                started_at=_now(),
                finished_at=_now(),
                terminal_result=None,
                safe_error=safe_error,
                suggested_next_action=None,
                cancellable=False,
                task_status="failed",
                progress_percent=0.0,
            )

        component_id = (request.component_id or (action.target_component if action else None) or "").strip().lower() or None
        current_installation = self._current_installation(component_id)
        if request.action_type in {"repair_component", "remove_component"} and current_installation is not None and not current_installation.managed:
            safe_error = self._safe_error("operation_not_supported", "Esta accion no esta soportada para este componente.")
            return ComponentActionExecution(
                action_id=request.request_id,
                task_id=request.request_id,
                status="failed",
                component_id=component_id,
                operation=request.action_type,
                started_at=_now(),
                finished_at=_now(),
                terminal_result=None,
                safe_error=safe_error,
                suggested_next_action=None,
                cancellable=False,
                task_status="failed",
                progress_percent=0.0,
            )
        lock = self._component_lock(component_id) if component_id else None
        if lock is not None and not lock.acquire(blocking=False):
            safe_error = self._safe_error("component_locked", "Hay otra operacion en curso sobre este componente.")
            return ComponentActionExecution(
                action_id=request.request_id,
                task_id=request.request_id,
                status="failed",
                component_id=component_id,
                operation=request.action_type,
                started_at=_now(),
                finished_at=_now(),
                terminal_result=None,
                safe_error=safe_error,
                suggested_next_action=None,
                cancellable=False,
                task_status="failed",
                progress_percent=0.0,
            )

        task_id = request.request_id
        started_at = _now()
        task_status = "running"
        terminal_result: dict[str, object] | None = None
        safe_error: str | None = None
        suggested_next_action: str | None = None
        cancellable = request.action_type == "run_gpu_benchmark"
        benchmark_token = None
        try:
            task_id = self._register_task(request, cancellable=cancellable)
            if request.action_type == "run_gpu_benchmark":
                benchmark_token = self._token_for(task_id)
            self._update_task(task_id, stage_name="validating", progress_percent=5.0, message="Revalidando la accion solicitada.")
            if request.action_type == "choose_profile":
                self.workspace.set_transcription_preferences(profile=request.profile)
                terminal_result = {"profile": request.profile}
            elif request.action_type == "use_cpu":
                self.workspace.set_transcription_preferences(device="cpu")
                terminal_result = {"device": "cpu"}
            elif request.action_type == "use_gpu":
                self.workspace.set_transcription_preferences(device="gpu")
                terminal_result = {"device": "gpu"}
            elif request.action_type == "continue_limited":
                terminal_result = {"mode": "limited"}
            elif request.action_type == "run_gpu_benchmark":
                self._update_task(task_id, stage_name="benchmarking", progress_percent=25.0, message="Probando la GPU.")
                result = self.workspace.run_transcription_benchmark(
                    profile=request.profile or self.workspace.ui_state.transcription_profile,
                    preferred_device="gpu",
                    persist_result=True,
                    cancellation_token=benchmark_token,
                )
                terminal_result = result.to_dict() if hasattr(result, "to_dict") else {"result": str(result)}
                if getattr(result, "status", None) == "cancelled":
                    self._finish_task(task_id, message="La prueba de GPU fue cancelada.", status="cancelled")
                    return ComponentActionExecution(
                        action_id=request.request_id,
                        task_id=task_id,
                        status="cancelled",
                        component_id=component_id,
                        operation=request.action_type,
                        started_at=started_at,
                        finished_at=_now(),
                        terminal_result=terminal_result,
                        safe_error="La prueba de GPU fue cancelada.",
                        suggested_next_action="run_gpu_benchmark",
                        cancellable=True,
                        task_status="cancelled",
                        progress_percent=100.0,
                    )
                self._update_task(task_id, stage_name="verifying", progress_percent=90.0, message="Guardando evidencia de la prueba de GPU.")
            elif request.action_type == "verify_component":
                if component_id == "ffmpeg":
                    result = self.component_manager_service.ffmpeg_verify_local()
                elif component_id and component_id.startswith("transcription-runtime."):
                    result = self.component_manager_service.transcription_runtime_verify_local(component_id)
                elif component_id and component_id.startswith("transcription-model."):
                    result = self.component_manager_service.transcription_model_verify_local(component_id)
                else:
                    safe_error = self._safe_error("operation_not_supported", "Esta accion no esta soportada para este componente.")
                    task_status = "failed"
                    terminal_result = None
                    raise RuntimeError(safe_error)
                terminal_result = result.to_dict()
                if getattr(result, "state", "") in {"failed", "source_missing", "missing"}:
                    safe_error = result.reason or result.errors[0] if getattr(result, "errors", ()) else self._safe_error("health_check_failed", "La instalacion termino, pero el componente no pudo verificarse.")
            elif request.action_type == "install_component":
                if not request.local_source:
                    safe_error = self._safe_error("source_required", "Se necesita un archivo o carpeta local para continuar.")
                    raise ValueError(safe_error)
                source = Path(request.local_source)
                if not source.exists():
                    safe_error = self._safe_error("invalid_source", "El archivo seleccionado no es valido para este componente.")
                    raise FileNotFoundError(safe_error)
                self._update_task(task_id, stage_name="verifying_source", progress_percent=15.0, message="Verificando el origen local.")
                if component_id == "ffmpeg":
                    self._update_task(task_id, stage_name="copying", progress_percent=35.0, message="Copiando y extrayendo el componente multimedia.")
                    result = self.component_manager_service.ffmpeg_install_local(source)
                elif component_id and component_id.startswith("transcription-runtime."):
                    self._update_task(task_id, stage_name="copying", progress_percent=35.0, message="Copiando y extrayendo el runtime local.")
                    result = self.component_manager_service.transcription_runtime_install_local(component_id, source, revision="1")
                elif component_id and component_id.startswith("transcription-model."):
                    revision = self._profile_revision(request.profile) or "1"
                    self._update_task(task_id, stage_name="copying", progress_percent=35.0, message="Copiando y extrayendo el modelo local.")
                    result = self.component_manager_service.transcription_model_install_local(component_id, source, revision=revision)
                else:
                    safe_error = self._safe_error("operation_not_supported", "Esta accion no esta soportada para este componente.")
                    raise RuntimeError(safe_error)
                terminal_result = result.to_dict()
                if getattr(result, "state", "") == "failed":
                    safe_error = result.reason or (result.errors[0] if getattr(result, "errors", ()) else None)
            elif request.action_type == "repair_component":
                source = Path(request.local_source) if request.local_source else None
                self._update_task(task_id, stage_name="repairing", progress_percent=35.0, message="Reparando el componente local.")
                if component_id == "ffmpeg":
                    result = self.component_manager_service.ffmpeg_repair_local(source)
                elif component_id and component_id.startswith("transcription-runtime."):
                    result = self.component_manager_service.transcription_runtime_repair_local(component_id, source, revision=request.profile or "1")
                elif component_id and component_id.startswith("transcription-model."):
                    revision = self._profile_revision(request.profile) or "1"
                    result = self.component_manager_service.transcription_model_repair_local(component_id, source, revision=revision)
                else:
                    safe_error = self._safe_error("operation_not_supported", "Esta accion no esta soportada para este componente.")
                    raise RuntimeError(safe_error)
                terminal_result = result.to_dict()
                if getattr(result, "state", "") == "failed":
                    safe_error = result.reason or (result.errors[0] if getattr(result, "errors", ()) else None)
            elif request.action_type == "remove_component":
                self._update_task(task_id, stage_name="removing", progress_percent=40.0, message="Eliminando el componente administrado.")
                if component_id == "ffmpeg":
                    result = self.component_manager_service.ffmpeg_remove()
                elif component_id and component_id.startswith("transcription-runtime."):
                    result = self.component_manager_service.transcription_runtime_remove_local(component_id)
                elif component_id and component_id.startswith("transcription-model."):
                    result = self.component_manager_service.transcription_model_remove_local(component_id)
                else:
                    safe_error = self._safe_error("operation_not_supported", "Esta accion no esta soportada para este componente.")
                    raise RuntimeError(safe_error)
                terminal_result = result.to_dict()
                if getattr(result, "state", "") == "in_use":
                    safe_error = self._safe_error("component_in_use", "El componente esta siendo utilizado por otra tarea.")
                elif getattr(result, "state", "") == "failed":
                    safe_error = result.reason or (result.errors[0] if getattr(result, "errors", ()) else None)
            else:
                safe_error = self._safe_error("operation_not_supported", "Esta accion no esta soportada para este componente.")
                raise RuntimeError(safe_error)

            self._update_task(task_id, stage_name="finalizing", progress_percent=95.0, message="Actualizando el estado local.")
            task_status = "completed" if safe_error is None else "failed"
            if safe_error is None:
                self._finish_task(task_id, message="Accion local completada.")
                return ComponentActionExecution(
                    action_id=request.request_id,
                    task_id=task_id,
                    status="completed",
                    component_id=component_id,
                    operation=request.action_type,
                    started_at=started_at,
                    finished_at=_now(),
                    terminal_result=terminal_result,
                    safe_error=None,
                    suggested_next_action=suggested_next_action,
                    cancellable=cancellable,
                    task_status="completed",
                    progress_percent=100.0,
                )
            self._finish_task(task_id, message=safe_error or "La accion local fallo.", status="failed")
            return ComponentActionExecution(
                action_id=request.request_id,
                task_id=task_id,
                status="failed",
                component_id=component_id,
                operation=request.action_type,
                started_at=started_at,
                finished_at=_now(),
                terminal_result=terminal_result,
                safe_error=safe_error,
                suggested_next_action=suggested_next_action,
                cancellable=cancellable,
                task_status=task_status,
                progress_percent=100.0,
            )
        except Exception as exc:
            safe_error = safe_error or str(exc)
            self._finish_task(task_id, message=safe_error, status="failed")
            return ComponentActionExecution(
                action_id=request.request_id,
                task_id=task_id,
                status="failed",
                component_id=component_id,
                operation=request.action_type,
                started_at=started_at,
                finished_at=_now(),
                terminal_result=terminal_result,
                safe_error=safe_error,
                suggested_next_action=suggested_next_action,
                cancellable=cancellable,
                task_status="failed",
                progress_percent=100.0,
            )
        finally:
            with self._lock:
                self._active_tokens.pop(task_id, None)
            if lock is not None:
                lock.release()
