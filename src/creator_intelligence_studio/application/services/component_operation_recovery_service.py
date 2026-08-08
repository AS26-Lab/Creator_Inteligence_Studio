"""Recovery helpers for local component operations."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from creator_intelligence_studio.presentation.desktop.ui_state import BackgroundTaskRecord
from creator_intelligence_studio.shared.paths import ProjectPaths


TERMINAL_TASK_STATES = {"completed", "completed_with_warnings", "failed", "cancelled", "interrupted"}
ACTIVE_TASK_STATES = {"queued", "pending", "preparing", "running", "cancel_requested", "cancellation_pending"}


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _task_payload(task: BackgroundTaskRecord) -> dict[str, object]:
    payload = getattr(task, "payload", {}) or {}
    return payload if isinstance(payload, dict) else {}


@dataclass(frozen=True, slots=True)
class ComponentOperationExecution:
    operation_id: str
    operation_type: str
    component_id: str | None
    installation_id: str | None = None
    task_id: str | None = None
    requested_at: str | None = None
    started_at: str | None = None
    last_heartbeat_at: str | None = None
    terminal_at: str | None = None
    lifecycle_state: str = "queued"
    can_cancel: bool = False
    cancellation_requested: bool = False
    recovery_policy: str = "reconcile_and_preserve_previous"
    staging_reference: str | None = None
    safe_error_category: str | None = None
    safe_error_message: str | None = None
    previous_active_installation: str | None = None
    result_reference: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "operation_id": self.operation_id,
            "operation_type": self.operation_type,
            "component_id": self.component_id,
            "installation_id": self.installation_id,
            "task_id": self.task_id,
            "requested_at": self.requested_at,
            "started_at": self.started_at,
            "last_heartbeat_at": self.last_heartbeat_at,
            "terminal_at": self.terminal_at,
            "lifecycle_state": self.lifecycle_state,
            "can_cancel": self.can_cancel,
            "cancellation_requested": self.cancellation_requested,
            "recovery_policy": self.recovery_policy,
            "staging_reference": self.staging_reference,
            "safe_error_category": self.safe_error_category,
            "safe_error_message": self.safe_error_message,
            "previous_active_installation": self.previous_active_installation,
            "result_reference": self.result_reference,
        }


@dataclass(frozen=True, slots=True)
class ComponentOperationRecoveryReport:
    interrupted_tasks: tuple[ComponentOperationExecution, ...] = ()
    recovered_download_tasks: tuple[str, ...] = ()
    cleaned_staging_paths: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    last_reconciled_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, object]:
        return {
            "interrupted_tasks": [item.to_dict() for item in self.interrupted_tasks],
            "recovered_download_tasks": list(self.recovered_download_tasks),
            "cleaned_staging_paths": list(self.cleaned_staging_paths),
            "notes": list(self.notes),
            "last_reconciled_at": self.last_reconciled_at,
        }


class ComponentOperationRecoveryService:
    """Reconciles stale component tasks, downloads, and staging after startup."""

    def __init__(self, workspace) -> None:
        self.workspace = workspace

    def _is_component_task(self, task: BackgroundTaskRecord) -> bool:
        return bool(_task_payload(task).get("kind") in {"component_action", "component_download"})

    def _active_component_task_message(self, task: BackgroundTaskRecord) -> str:
        payload = _task_payload(task)
        action_type = str(payload.get("action_type") or "").strip().lower()
        kind = str(payload.get("kind") or "").strip().lower()
        if kind == "component_download":
            return "La descarga se interrumpio. Puedes continuarla."
        if action_type == "install_component":
            return "La instalacion se interrumpio antes de completarse. La version anterior se conservo."
        if action_type == "run_gpu_benchmark":
            return "La prueba se interrumpio y no se usara como resultado de compatibilidad."
        if action_type == "verify_component":
            return "La comprobacion se interrumpio. Puedes intentarlo de nuevo."
        if action_type == "repair_component":
            return "La reparacion se interrumpio. El componente anterior se conserva."
        if action_type == "remove_component":
            return "No se pudo terminar de eliminar el componente. Revisa su estado antes de continuar."
        return "La operacion se interrumpio y puede reintentarse."

    def _task_execution(self, task: BackgroundTaskRecord) -> ComponentOperationExecution:
        payload = _task_payload(task)
        operation_type = str(payload.get("action_type") or payload.get("kind") or task.title).strip() or "unknown"
        component_id = payload.get("component_id")
        terminal_at = task.completed_at or task.cancelled_at or task.interrupted_at
        lifecycle_state = str(task.status or "queued")
        return ComponentOperationExecution(
            operation_id=str(task.action_id or task.task_id),
            operation_type=operation_type,
            component_id=str(component_id) if component_id else None,
            task_id=task.task_id,
            requested_at=task.created_at,
            started_at=task.created_at,
            last_heartbeat_at=task.last_heartbeat_at or task.updated_at,
            terminal_at=terminal_at,
            lifecycle_state=lifecycle_state,
            can_cancel=bool(task.cancellable),
            cancellation_requested=lifecycle_state in {"cancel_requested", "cancellation_pending"},
            staging_reference=str(payload.get("local_source") or payload.get("source_context") or "") or None,
            safe_error_category=str(payload.get("error_category") or "") or None,
            safe_error_message=task.error or task.message,
            previous_active_installation=str(payload.get("previous_active_installation") or "") or None,
            result_reference=str(payload.get("download_id") or payload.get("result_reference") or "") or None,
        )

    def _cleanup_staging_root(self, root: Path) -> list[str]:
        cleaned: list[str] = []
        if not root.exists():
            return cleaned
        for path in sorted(root.rglob("*")):
            if not path.is_dir():
                continue
            name = path.name.lower()
            if not (name.startswith(".staging") or ".staging" in name):
                continue
            try:
                shutil.rmtree(path, ignore_errors=True)
                cleaned.append(str(path))
            except Exception:
                continue
        return cleaned

    def _cleanup_staging_dirs(self) -> list[str]:
        cleaned: list[str] = []
        component_root = getattr(self.workspace.component_manager_service, "paths", None)
        paths = component_root if isinstance(component_root, ProjectPaths) else getattr(self.workspace, "paths", None)
        if paths is None:
            return cleaned
        cleaned.extend(self._cleanup_staging_root(paths.components_directory / "ffmpeg"))
        cleaned.extend(self._cleanup_staging_root(paths.components_directory / "transcription-runtime"))
        cleaned.extend(self._cleanup_staging_root(paths.models_directory / "transcription" / "faster-whisper"))
        return cleaned

    def _recover_tasks(self) -> tuple[ComponentOperationExecution, ...]:
        updated: list[ComponentOperationExecution] = []
        for task in self.workspace.background_tasks():
            if not self._is_component_task(task):
                continue
            if task.status not in ACTIVE_TASK_STATES:
                continue
            message = self._active_component_task_message(task)
            interrupted = self.workspace.interrupt_background_task(task.task_id, message)
            if interrupted is None:
                continue
            payload = _task_payload(interrupted)
            payload["recovered_at"] = _now()
            self.workspace.update_background_task(
                interrupted.task_id,
                status="interrupted",
                message=message,
                cancellable=False,
                interrupted_at=interrupted.interrupted_at or _now(),
                last_heartbeat_at=_now(),
                payload=payload,
            )
            task_view = self.workspace.background_tasks()
            recovered_task = next((item for item in task_view if item.task_id == interrupted.task_id), interrupted)
            updated.append(self._task_execution(recovered_task))
        return tuple(updated)

    def recover_startup_state(self) -> ComponentOperationRecoveryReport:
        recovered_downloads: tuple[str, ...] = ()
        download_service = getattr(self.workspace, "download_service", None)
        if download_service is not None:
            try:
                recovered = download_service.recover_interrupted_downloads()
                recovered_downloads = tuple(record.download_id for record in recovered)
            except Exception:
                recovered_downloads = ()
        interrupted_tasks = self._recover_tasks()
        cleaned_staging_paths = tuple(self._cleanup_staging_dirs())
        notes: list[str] = []
        if recovered_downloads:
            notes.append("Descargas interrumpidas reconciliadas.")
        if cleaned_staging_paths:
            notes.append("Se limpio staging obsoleto de operaciones interrumpidas.")
        return ComponentOperationRecoveryReport(
            interrupted_tasks=interrupted_tasks,
            recovered_download_tasks=recovered_downloads,
            cleaned_staging_paths=cleaned_staging_paths,
            notes=tuple(notes),
        )
