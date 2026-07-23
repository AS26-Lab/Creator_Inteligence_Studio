"""Persistencia ligera de preferencias y tareas de la interfaz."""

from __future__ import annotations

import base64
import json
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime
from pathlib import Path
from typing import Any

from creator_intelligence_studio.shared.dates import from_iso_z, to_iso_z, utc_now


@dataclass(frozen=True, slots=True)
class BackgroundTaskRecord:
    task_id: str
    title: str
    status: str
    stage_name: str | None = None
    video_id: str | None = None
    video_title: str | None = None
    action_id: str | None = None
    progress_percent: float = 0.0
    message: str | None = None
    error: str | None = None
    cancellable: bool = True
    created_at: str = field(default_factory=lambda: to_iso_z(utc_now()))
    updated_at: str = field(default_factory=lambda: to_iso_z(utc_now()))
    interrupted_at: str | None = None
    completed_at: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "status": self.status,
            "stage_name": self.stage_name,
            "video_id": self.video_id,
            "video_title": self.video_title,
            "action_id": self.action_id,
            "progress_percent": self.progress_percent,
            "message": self.message,
            "error": self.error,
            "cancellable": self.cancellable,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "interrupted_at": self.interrupted_at,
            "completed_at": self.completed_at,
            "payload": dict(self.payload),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "BackgroundTaskRecord":
        return cls(
            task_id=str(payload.get("task_id") or ""),
            title=str(payload.get("title") or ""),
            status=str(payload.get("status") or "pending"),
            stage_name=payload.get("stage_name"),
            video_id=payload.get("video_id"),
            video_title=payload.get("video_title"),
            action_id=payload.get("action_id"),
            progress_percent=float(payload.get("progress_percent") or 0.0),
            message=payload.get("message"),
            error=payload.get("error"),
            cancellable=bool(payload.get("cancellable", True)),
            created_at=str(payload.get("created_at") or to_iso_z(utc_now())),
            updated_at=str(payload.get("updated_at") or to_iso_z(utc_now())),
            interrupted_at=payload.get("interrupted_at"),
            completed_at=payload.get("completed_at"),
            payload=dict(payload.get("payload") or {}),
        )


@dataclass(frozen=True, slots=True)
class WorkspaceUiState:
    active_creator_id: str | None = None
    active_project_id: str | None = None
    last_page: str = "home"
    onboarding_seen: bool = False
    show_technical_details: bool = True
    preferred_transcription_device: str = "auto"
    transcription_profile: str = "balanced"
    ranking_profile: str = "balanced"
    confirm_destructive_actions: bool = True
    preferred_data_directory: str | None = None
    preferred_models_directory: str | None = None
    preferred_exports_directory: str | None = None
    window_geometry: str | None = None
    window_state: str | None = None
    tasks: tuple[BackgroundTaskRecord, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "active_creator_id": self.active_creator_id,
            "active_project_id": self.active_project_id,
            "last_page": self.last_page,
            "onboarding_seen": self.onboarding_seen,
            "show_technical_details": self.show_technical_details,
            "preferred_transcription_device": self.preferred_transcription_device,
            "transcription_profile": self.transcription_profile,
            "ranking_profile": self.ranking_profile,
            "confirm_destructive_actions": self.confirm_destructive_actions,
            "preferred_data_directory": self.preferred_data_directory,
            "preferred_models_directory": self.preferred_models_directory,
            "preferred_exports_directory": self.preferred_exports_directory,
            "window_geometry": self.window_geometry,
            "window_state": self.window_state,
            "tasks": [task.to_dict() for task in self.tasks],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "WorkspaceUiState":
        tasks = tuple(BackgroundTaskRecord.from_dict(item) for item in payload.get("tasks", []))
        return cls(
            active_creator_id=payload.get("active_creator_id"),
            active_project_id=payload.get("active_project_id"),
            last_page=str(payload.get("last_page") or "home"),
            onboarding_seen=bool(payload.get("onboarding_seen", False)),
            show_technical_details=bool(payload.get("show_technical_details", True)),
            preferred_transcription_device=str(payload.get("preferred_transcription_device") or "auto"),
            transcription_profile=str(payload.get("transcription_profile") or "balanced"),
            ranking_profile=str(payload.get("ranking_profile") or "balanced"),
            confirm_destructive_actions=bool(payload.get("confirm_destructive_actions", True)),
            preferred_data_directory=payload.get("preferred_data_directory"),
            preferred_models_directory=payload.get("preferred_models_directory"),
            preferred_exports_directory=payload.get("preferred_exports_directory"),
            window_geometry=payload.get("window_geometry"),
            window_state=payload.get("window_state"),
            tasks=tasks,
        )


class WorkspaceUiStateStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> WorkspaceUiState:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return WorkspaceUiState()
        except Exception:
            return WorkspaceUiState()
        if not isinstance(payload, dict):
            return WorkspaceUiState()
        return WorkspaceUiState.from_dict(payload)

    def save(self, state: WorkspaceUiState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(state.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    def update(self, state: WorkspaceUiState, **changes: Any) -> WorkspaceUiState:
        updated = replace(state, **changes)
        self.save(updated)
        return updated

    @staticmethod
    def encode_blob(data: bytes | None) -> str | None:
        if data is None:
            return None
        return base64.b64encode(data).decode("ascii")

    @staticmethod
    def decode_blob(data: str | None) -> bytes | None:
        if not data:
            return None
        return base64.b64decode(data.encode("ascii"))
