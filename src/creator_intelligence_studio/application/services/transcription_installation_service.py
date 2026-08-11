"""Instaladores administrados para runtime y modelos de transcripcion."""

from __future__ import annotations

import hashlib
import importlib
import logging
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from creator_intelligence_studio.domain.components.downloads import VerifiedComponentArtifact
from creator_intelligence_studio.domain.components.entities import (
    ComponentEvent,
    ComponentEventType,
    ComponentInstallKind,
    ComponentInstallation,
    ComponentInstallationStatus,
    RuntimeCheckRecord,
    RuntimeCheckStatus,
)
from creator_intelligence_studio.domain.components.repositories import ComponentManagerRepository
from creator_intelligence_studio.domain.transcription.errors import TranscriptionBackendError
from creator_intelligence_studio.domain.transcription.value_objects import TranscriptionModelInfo, TranscriptionModelStatus
from creator_intelligence_studio.infrastructure.components.archive_security import copy_directory_tree, safe_extract_zip
from creator_intelligence_studio.infrastructure.transcription.model_manager import TranscriptionModelManager
from creator_intelligence_studio.shared.dates import utc_now
from creator_intelligence_studio.shared.paths import ProjectPaths


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _safe_component_id(component_id: str) -> str:
    normalized = component_id.strip().lower()
    if not normalized:
        raise ValueError("Falta el identificador del componente.")
    return normalized


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_path_from_artifact(artifact: VerifiedComponentArtifact) -> Path:
    path = Path(artifact.verified_artifact_path)
    if not path.exists():
        raise FileNotFoundError(f"El artefacto verificado no existe: {path}")
    if artifact.sha256:
        actual = _sha256_file(path)
        if actual.lower() != artifact.sha256.lower():
            raise TranscriptionBackendError("El artefacto verificado fue modificado despues de validarse.")
    return path


def _materialize_source(source: Path, staging_root: Path) -> None:
    if source.is_dir():
        copy_directory_tree(source, staging_root)
        return
    if source.suffix.lower() == ".zip":
        safe_extract_zip(source, staging_root)
        return
    raise ValueError(f"Formato de origen no soportado: {source}")


def _repo_event(
    event_type: ComponentEventType,
    *,
    component_id: str,
    message_safe: str,
    payload: dict[str, object] | None = None,
    severity: str = "info",
) -> ComponentEvent:
    return ComponentEvent(
        event_type=event_type,
        component_id=component_id,
        message_safe=message_safe,
        severity=severity,
        payload=payload or {},
        created_at=_now(),
    )


@dataclass(frozen=True, slots=True)
class TranscriptionInstallResult:
    state: str
    component_id: str
    source_path: str | None
    staged_path: str | None
    active_path: str | None
    installation: ComponentInstallation | None
    health_status: str | None
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    reason: str | None = None
    revision: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "state": self.state,
            "component_id": self.component_id,
            "source_path": self.source_path,
            "staged_path": self.staged_path,
            "active_path": self.active_path,
            "installation": self.installation.to_dict() if self.installation else None,
            "health_status": self.health_status,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "reason": self.reason,
            "revision": self.revision,
        }


class _ImportPathGuard:
    def __init__(self, *paths: Path) -> None:
        self.paths = [str(path) for path in paths]
        self._previous: list[str] = []

    def __enter__(self):
        self._previous = list(sys.path)
        for path in reversed(self.paths):
            sys.path.insert(0, path)
        importlib.invalidate_caches()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        sys.path[:] = self._previous
        importlib.invalidate_caches()


class ManagedTranscriptionRuntimeInstaller:
    """Boundary administrado para instalar un bundle local de runtime."""

    def __init__(
        self,
        *,
        paths: ProjectPaths,
        repository: ComponentManagerRepository,
        logger: logging.Logger | None = None,
    ) -> None:
        self.paths = paths
        self.repository = repository
        self.logger = logger or logging.getLogger("creator_intelligence_studio.transcription.runtime")

    def _active_root(self, component_id: str, revision: str) -> Path:
        return self.paths.components_directory / "transcription-runtime" / component_id / revision

    def _staging_root(self, component_id: str) -> Path:
        return self.paths.components_directory / "transcription-runtime" / component_id / f".staging-{uuid4().hex}"

    def _validate_source_structure(self, root: Path, component_id: str) -> tuple[str, ...]:
        required = []
        if component_id.endswith("faster-whisper"):
            required.append("faster_whisper")
        if component_id.endswith("ctranslate2"):
            required.append("ctranslate2")
        missing: list[str] = []
        for package_name in required:
            package_dir = root / package_name
            if not package_dir.exists() or not package_dir.is_dir():
                missing.append(package_name)
                continue
            init_file = package_dir / "__init__.py"
            if not init_file.exists():
                missing.append(f"{package_name}/__init__.py")
        return tuple(missing)

    def _check_runtime(self, root: Path, component_id: str) -> tuple[bool, str | None]:
        module_name = "faster_whisper" if component_id.endswith("faster-whisper") else "ctranslate2"
        try:
            with _ImportPathGuard(root):
                module = importlib.import_module(module_name)
                _ = getattr(module, "__version__", None)
            return True, None
        except Exception as exc:
            return False, str(exc)

    def _persist_runtime_check(
        self,
        *,
        component_id: str,
        status: RuntimeCheckStatus,
        runtime_version: str | None,
        notes: str | None,
        error_code: str | None = None,
        error_message: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> RuntimeCheckRecord:
        now = _now()
        record = RuntimeCheckRecord(
            component_id=component_id,
            status=status,
            runtime_importable=status in {RuntimeCheckStatus.READY, RuntimeCheckStatus.DEGRADED},
            runtime_version=runtime_version,
            device_count=None,
            supported_compute_types=(),
            notes=notes,
            warning_message=None if status == RuntimeCheckStatus.READY else notes,
            error_code=error_code,
            error_message=error_message,
            metadata=metadata or {},
            checked_at=now,
            created_at=now,
            updated_at=now,
        )
        return self.repository.upsert_runtime_check(record)

    def verify_local(self, component_id: str) -> TranscriptionInstallResult:
        component_id = _safe_component_id(component_id)
        installation = self.repository.get_installation(component_id)
        if installation is None:
            return TranscriptionInstallResult(
                state="missing",
                component_id=component_id,
                source_path=None,
                staged_path=None,
                active_path=None,
                installation=None,
                health_status="missing",
                errors=("No existe una instalacion de runtime para verificar.",),
                reason="missing",
            )
        if not installation.location_path:
            runtime_version = installation.installed_version
            persisted = self._persist_runtime_check(
                component_id=component_id,
                status=RuntimeCheckStatus.NOT_CHECKED,
                runtime_version=runtime_version,
                notes="La instalacion no tiene ruta administrada para verificar.",
                error_code="source_missing",
                error_message="La instalacion no tiene ruta administrada para verificar.",
                metadata={"installation_type": installation.install_type.value if installation.install_type else None},
            )
            return TranscriptionInstallResult(
                state="source_missing",
                component_id=component_id,
                source_path=None,
                staged_path=None,
                active_path=None,
                installation=installation,
                health_status=persisted.status.value,
                errors=(persisted.error_message or "La instalacion no tiene ruta administrada para verificar.",),
                reason="source_missing",
            )
        root = Path(installation.location_path)
        ok, error = self._check_runtime(root, component_id)
        if ok:
            version = installation.installed_version
            refreshed = ComponentInstallation(
                component_id=installation.component_id,
                installation_status=ComponentInstallationStatus.READY,
                installed_version=installation.installed_version,
                revision=installation.revision,
                install_type=installation.install_type,
                location_path=installation.location_path,
                location_reference=installation.location_reference,
                detected_at=installation.detected_at,
                verified_at=_now(),
                health_status=RuntimeCheckStatus.READY,
                source=installation.source,
                managed=installation.managed,
                last_error_code=None,
                last_error_message=None,
                metadata=dict(installation.metadata),
                created_at=installation.created_at,
                updated_at=_now(),
            )
            refreshed = self.repository.upsert_installation(refreshed)
            persisted = self._persist_runtime_check(
                component_id=component_id,
                status=RuntimeCheckStatus.READY,
                runtime_version=version,
                notes="El runtime administrado fue verificado correctamente.",
                metadata={"location_path": installation.location_path, "verification": "local"},
            )
            return TranscriptionInstallResult(
                state="ready",
                component_id=component_id,
                source_path=installation.source,
                staged_path=None,
                active_path=installation.location_path,
                installation=refreshed,
                health_status=persisted.status.value,
                revision=installation.revision,
            )
        persisted = self._persist_runtime_check(
            component_id=component_id,
            status=RuntimeCheckStatus.FAILED,
            runtime_version=installation.installed_version,
            notes="El runtime administrado no pudo verificarse.",
            error_code="health_check_failed",
            error_message=error,
            metadata={"location_path": installation.location_path, "verification": "local"},
        )
        refreshed = ComponentInstallation(
            component_id=installation.component_id,
            installation_status=ComponentInstallationStatus.REPAIR_REQUIRED,
            installed_version=installation.installed_version,
            revision=installation.revision,
            install_type=installation.install_type,
            location_path=installation.location_path,
            location_reference=installation.location_reference,
            detected_at=installation.detected_at,
            verified_at=installation.verified_at,
            health_status=RuntimeCheckStatus.FAILED,
            source=installation.source,
            managed=installation.managed,
            last_error_code="health_check_failed",
            last_error_message=error,
            metadata=dict(installation.metadata),
            created_at=installation.created_at,
            updated_at=_now(),
        )
        refreshed = self.repository.upsert_installation(refreshed)
        return TranscriptionInstallResult(
            state="failed",
            component_id=component_id,
            source_path=installation.source,
            staged_path=None,
            active_path=installation.location_path,
            installation=refreshed,
            health_status=persisted.status.value,
            errors=(error or "El runtime local no pudo verificarse.",),
            reason="health_check_failed",
            revision=installation.revision,
        )

    def install_local(
        self,
        component_id: str,
        source_path: str | Path,
        *,
        revision: str = "1",
        artifact: VerifiedComponentArtifact | None = None,
    ) -> TranscriptionInstallResult:
        component_id = _safe_component_id(component_id)
        source = _source_path_from_artifact(artifact) if artifact is not None else Path(source_path)
        if not source.exists():
            raise FileNotFoundError(f"La fuente local no existe: {source}")
        if artifact is not None and artifact.component_id and artifact.component_id.strip().lower() != component_id:
            raise TranscriptionBackendError("El artefacto no corresponde al componente solicitado.")
        self.repository.append_event(_repo_event(ComponentEventType.TRANSCRIPTION_RUNTIME_INSTALL_REQUESTED, component_id=component_id, message_safe="Se solicitó la instalación administrada del runtime.", payload={"revision": revision}))
        self.repository.append_event(_repo_event(ComponentEventType.TRANSCRIPTION_RUNTIME_INSTALL_STARTED, component_id=component_id, message_safe="Se inició la instalación administrada del runtime.", payload={"revision": revision}))
        staging_root = self._staging_root(component_id)
        staging_root.parent.mkdir(parents=True, exist_ok=True)
        active_root = self._active_root(component_id, revision)
        try:
            _materialize_source(source, staging_root)
            missing = self._validate_source_structure(staging_root, component_id)
            if missing:
                raise TranscriptionBackendError(f"Faltan archivos requeridos del runtime: {', '.join(missing)}")
            self.repository.append_event(_repo_event(ComponentEventType.TRANSCRIPTION_RUNTIME_HEALTH_CHECK_STARTED, component_id=component_id, message_safe="Se inició la verificación del runtime administrado.", payload={"revision": revision}))
            ok, error = self._check_runtime(staging_root, component_id)
            if not ok:
                raise TranscriptionBackendError(error or "El runtime local no pudo verificarse.")
            active_root.parent.mkdir(parents=True, exist_ok=True)
            if active_root.exists():
                shutil.rmtree(active_root, ignore_errors=True)
            staging_root.replace(active_root)
            installation = ComponentInstallation(
                component_id=component_id,
                installation_status=ComponentInstallationStatus.READY,
                installed_version=revision,
                revision=revision,
                install_type=ComponentInstallKind.MANAGED,
                location_path=str(active_root),
                location_reference="managed_root",
                detected_at=_now(),
                verified_at=_now(),
                health_status=RuntimeCheckStatus.READY,
                source=str(source),
                managed=True,
                metadata={"installation_type": "managed", "revision": revision, "source_kind": "local"},
                created_at=_now(),
                updated_at=_now(),
            )
            self.repository.upsert_installation(installation)
            self.repository.append_event(_repo_event(ComponentEventType.TRANSCRIPTION_RUNTIME_HEALTH_CHECK_COMPLETED, component_id=component_id, message_safe="El runtime administrado fue verificado.", payload={"revision": revision}))
            self.repository.append_event(_repo_event(ComponentEventType.TRANSCRIPTION_RUNTIME_ACTIVATED, component_id=component_id, message_safe="El runtime administrado quedó activado.", payload={"revision": revision}))
            return TranscriptionInstallResult(
                state="ready",
                component_id=component_id,
                source_path=str(source),
                staged_path=str(staging_root),
                active_path=str(active_root),
                installation=installation,
                health_status="ready",
                revision=revision,
            )
        except Exception as exc:
            self.logger.warning("No se pudo instalar el runtime %s: %s", component_id, exc)
            shutil.rmtree(staging_root, ignore_errors=True)
            installation = ComponentInstallation(
                component_id=component_id,
                installation_status=ComponentInstallationStatus.INVALID,
                installed_version=None,
                revision=revision,
                install_type=ComponentInstallKind.MANAGED,
                location_path=str(active_root),
                location_reference="managed_root",
                detected_at=_now(),
                verified_at=None,
                health_status=RuntimeCheckStatus.FAILED,
                source=str(source),
                managed=True,
                last_error_message=str(exc),
                metadata={"installation_type": "managed", "revision": revision, "source_kind": "local"},
                created_at=_now(),
                updated_at=_now(),
            )
            self.repository.upsert_installation(installation)
            self.repository.append_event(_repo_event(ComponentEventType.TRANSCRIPTION_RUNTIME_INSTALL_FAILED, component_id=component_id, message_safe="Falló la instalación administrada del runtime.", payload={"revision": revision}, severity="error"))
            return TranscriptionInstallResult(
                state="failed",
                component_id=component_id,
                source_path=str(source),
                staged_path=str(staging_root),
                active_path=str(active_root),
                installation=installation,
                health_status="failed",
                errors=(str(exc),),
                reason=str(exc),
                revision=revision,
            )
        finally:
            shutil.rmtree(staging_root, ignore_errors=True)

    def repair_local(
        self,
        component_id: str,
        source_path: str | Path | None = None,
        *,
        revision: str = "1",
        artifact: VerifiedComponentArtifact | None = None,
    ) -> TranscriptionInstallResult:
        component_id = _safe_component_id(component_id)
        installation = self.repository.get_installation(component_id)
        if installation is None:
            return TranscriptionInstallResult(
                state="missing",
                component_id=component_id,
                source_path=None,
                staged_path=None,
                active_path=None,
                installation=None,
                health_status="missing",
                errors=("No existe una instalacion administrada para reparar.",),
                reason="missing",
            )
        if not installation.managed:
            return TranscriptionInstallResult(
                state="not_supported",
                component_id=component_id,
                source_path=installation.source,
                staged_path=None,
                active_path=installation.location_path,
                installation=installation,
                health_status=installation.health_status.value,
                errors=("Solo las instalaciones administradas pueden repararse.",),
                reason="not_supported",
                revision=installation.revision,
            )
        if source_path is None and artifact is None and installation.source:
            source_path = installation.source
        return self.install_local(component_id, source_path or installation.source or "", revision=revision or (installation.revision or "1"), artifact=artifact)

    def remove_local(self, component_id: str) -> TranscriptionInstallResult:
        component_id = _safe_component_id(component_id)
        installation = self.repository.get_installation(component_id)
        if installation is None:
            return TranscriptionInstallResult(
                state="missing",
                component_id=component_id,
                source_path=None,
                staged_path=None,
                active_path=None,
                installation=None,
                health_status="missing",
                errors=("No existe una instalacion administrada para eliminar.",),
                reason="missing",
            )
        if not installation.managed:
            return TranscriptionInstallResult(
                state="not_supported",
                component_id=component_id,
                source_path=installation.source,
                staged_path=None,
                active_path=installation.location_path,
                installation=installation,
                health_status=installation.health_status.value,
                errors=("Solo las instalaciones administradas pueden eliminarse.",),
                reason="not_supported",
                revision=installation.revision,
            )
        if installation.location_path:
            shutil.rmtree(Path(installation.location_path), ignore_errors=True)
        missing = ComponentInstallation(
            component_id=component_id,
            installation_status=ComponentInstallationStatus.MISSING,
            installed_version=None,
            revision=None,
            install_type=ComponentInstallKind.MANAGED,
            location_path=None,
            location_reference=None,
            detected_at=_now(),
            verified_at=_now(),
            health_status=RuntimeCheckStatus.NOT_CHECKED,
            source=None,
            managed=True,
            last_error_code="removed",
            last_error_message="La instalacion administrada fue eliminada.",
            metadata={"removed_from": installation.location_path},
            created_at=installation.created_at,
            updated_at=_now(),
        )
        missing = self.repository.upsert_installation(missing)
        self._persist_runtime_check(
            component_id=component_id,
            status=RuntimeCheckStatus.NOT_CHECKED,
            runtime_version=None,
            notes="El runtime administrado fue eliminado.",
            error_code="removed",
            error_message="La instalacion administrada fue eliminada.",
            metadata={"removed_from": installation.location_path},
        )
        return TranscriptionInstallResult(
            state="removed",
            component_id=component_id,
            source_path=installation.source,
            staged_path=None,
            active_path=None,
            installation=missing,
            health_status="removed",
            revision=installation.revision,
        )


class ManagedTranscriptionModelInstaller:
    """Boundary administrado para instalar modelos locales o artefactos verificados."""

    def __init__(
        self,
        *,
        paths: ProjectPaths,
        repository: ComponentManagerRepository,
        model_manager: TranscriptionModelManager,
        logger: logging.Logger | None = None,
    ) -> None:
        self.paths = paths
        self.repository = repository
        self.model_manager = model_manager
        self.logger = logger or logging.getLogger("creator_intelligence_studio.transcription.model")

    def _staging_root(self, component_id: str) -> Path:
        return self.paths.models_directory / "transcription" / "faster-whisper" / component_id / f".staging-{uuid4().hex}"

    def _install_root(self, component_id: str, revision: str) -> Path:
        return self.model_manager.managed_version_root(component_id, revision)

    def _component_name(self, component_id: str) -> str:
        prefix = "transcription-model."
        return component_id[len(prefix):] if component_id.startswith(prefix) else component_id

    def _validate(self, root: Path, component_id: str, revision: str) -> TranscriptionModelInfo:
        model_name = self._component_name(component_id)
        return self.model_manager.inspect_model_bundle(
            root,
            model_name=model_name,
            installation_type="managed",
            managed=True,
            revision=revision,
            allow_verification=True,
        )

    def _persist_installation(
        self,
        *,
        component_id: str,
        revision: str,
        root: Path,
        source: str,
        install_type: ComponentInstallKind,
        status: ComponentInstallationStatus,
        health_status: RuntimeCheckStatus,
        error_message: str | None = None,
    ) -> ComponentInstallation:
        return self.repository.upsert_installation(
            ComponentInstallation(
                component_id=component_id,
                installation_status=status,
                installed_version=revision,
                revision=revision,
                install_type=install_type,
                location_path=str(root),
                location_reference="managed_root" if install_type == ComponentInstallKind.MANAGED else "legacy_cache",
                detected_at=_now(),
                verified_at=_now() if status == ComponentInstallationStatus.READY else None,
                health_status=health_status,
                source=source,
                managed=install_type == ComponentInstallKind.MANAGED,
                last_error_message=error_message,
                metadata={"installation_type": install_type.value, "revision": revision, "source": source},
                created_at=_now(),
                updated_at=_now(),
            )
        )

    def verify_local(self, component_id: str) -> TranscriptionInstallResult:
        component_id = _safe_component_id(component_id)
        installation = self.repository.get_installation(component_id)
        if installation is None:
            return TranscriptionInstallResult(
                state="missing",
                component_id=component_id,
                source_path=None,
                staged_path=None,
                active_path=None,
                installation=None,
                health_status="missing",
                errors=("No existe una instalacion de modelo para verificar.",),
                reason="missing",
            )
        model_name = self._component_name(component_id)
        verified = self.model_manager.verify_model(model_name)
        if verified.installed:
            updated = self._persist_installation(
                component_id=component_id,
                revision=installation.revision or verified.revision or "1",
                root=Path(verified.path or installation.location_path or self._install_root(component_id, installation.revision or verified.revision or "1")),
                source=installation.source or verified.source or "",
                install_type=ComponentInstallKind.MANAGED if verified.managed else installation.install_type,
                status=ComponentInstallationStatus.READY,
                health_status=RuntimeCheckStatus.READY,
            )
            return TranscriptionInstallResult(
                state="ready",
                component_id=component_id,
                source_path=installation.source,
                staged_path=None,
                active_path=verified.path,
                installation=updated,
                health_status="ready",
                revision=updated.revision,
            )
        updated = self._persist_installation(
            component_id=component_id,
            revision=installation.revision or verified.revision or "1",
            root=Path(installation.location_path or verified.path or self._install_root(component_id, installation.revision or verified.revision or "1")),
            source=installation.source or verified.source or "",
            install_type=installation.install_type,
            status=ComponentInstallationStatus.REPAIR_REQUIRED if installation.managed else ComponentInstallationStatus.INVALID,
            health_status=RuntimeCheckStatus.FAILED if verified.status != TranscriptionModelStatus.INCOMPATIBLE else RuntimeCheckStatus.INCOMPATIBLE,
            error_message=verified.error_message or verified.notes,
        )
        return TranscriptionInstallResult(
            state="failed",
            component_id=component_id,
            source_path=installation.source,
            staged_path=None,
            active_path=installation.location_path or verified.path,
            installation=updated,
            health_status="failed",
            errors=(verified.error_message or verified.notes or "El modelo local no pudo verificarse.",),
            reason="health_check_failed",
            revision=updated.revision,
        )

    def install_local(
        self,
        component_id: str,
        source_path: str | Path,
        *,
        revision: str,
        artifact: VerifiedComponentArtifact | None = None,
    ) -> TranscriptionInstallResult:
        component_id = _safe_component_id(component_id)
        source = _source_path_from_artifact(artifact) if artifact is not None else Path(source_path)
        if artifact is not None and artifact.component_id and artifact.component_id.strip().lower() != component_id:
            raise TranscriptionBackendError("El artefacto no corresponde al componente solicitado.")
        if not source.exists():
            raise FileNotFoundError(f"La fuente local no existe: {source}")
        self.repository.append_event(_repo_event(ComponentEventType.TRANSCRIPTION_MODEL_INSTALL_REQUESTED, component_id=component_id, message_safe="Se solicitó la instalación administrada del modelo.", payload={"revision": revision}))
        self.repository.append_event(_repo_event(ComponentEventType.TRANSCRIPTION_MODEL_INSTALL_STARTED, component_id=component_id, message_safe="Se inició la instalación administrada del modelo.", payload={"revision": revision}))
        staging_root = self._staging_root(component_id)
        staging_root.parent.mkdir(parents=True, exist_ok=True)
        install_root = self._install_root(component_id, revision)
        try:
            _materialize_source(source, staging_root)
            self.repository.append_event(_repo_event(ComponentEventType.TRANSCRIPTION_MODEL_VALIDATION_STARTED, component_id=component_id, message_safe="Se inició la validación del modelo.", payload={"revision": revision}))
            validation = self._validate(staging_root, component_id, revision)
            if validation.status not in {TranscriptionModelStatus.INSTALLED, TranscriptionModelStatus.LEGACY_CACHE}:
                raise TranscriptionBackendError(validation.error_message or validation.notes or "El modelo local no pudo verificarse.")
            self.repository.append_event(_repo_event(ComponentEventType.TRANSCRIPTION_MODEL_VALIDATION_COMPLETED, component_id=component_id, message_safe="La validación del modelo terminó correctamente.", payload={"revision": revision}))
            self.repository.append_event(_repo_event(ComponentEventType.TRANSCRIPTION_MODEL_HEALTH_CHECK_STARTED, component_id=component_id, message_safe="Se inició la verificación de salud del modelo.", payload={"revision": revision}))
            install_root.parent.mkdir(parents=True, exist_ok=True)
            if install_root.exists():
                shutil.rmtree(install_root, ignore_errors=True)
            temp_active = install_root.with_name(f".{install_root.name}.active-{uuid4().hex}")
            snapshot_root = staging_root / f"models--Systran--faster-whisper-{self._component_name(component_id)}" / "snapshots" / revision
            activation_source = snapshot_root if snapshot_root.exists() else staging_root
            if not self.model_manager._root_has_required_files(activation_source):
                repo_cache_dir = staging_root / f"models--Systran--faster-whisper-{self._component_name(component_id)}"
                snapshot_dir = self.model_manager._snapshot_dir(repo_cache_dir) if repo_cache_dir.exists() else None
                if snapshot_dir is not None:
                    activation_source = snapshot_dir
            if not self.model_manager._root_has_required_files(activation_source):
                raise TranscriptionBackendError("El modelo local no pudo materializarse en una raiz valida.")
            copy_directory_tree(activation_source, temp_active)
            final_result = self.model_manager.activate_managed_model(
                model_name=self._component_name(component_id),
                revision=revision,
                staged_root=temp_active,
                source=str(source),
            )
            installation = self._persist_installation(
                component_id=component_id,
                revision=revision,
                root=Path(final_result.path or install_root),
                source=str(source),
                install_type=ComponentInstallKind.MANAGED,
                status=ComponentInstallationStatus.READY,
                health_status=RuntimeCheckStatus.READY,
            )
            self.repository.append_event(_repo_event(ComponentEventType.TRANSCRIPTION_MODEL_HEALTH_CHECK_COMPLETED, component_id=component_id, message_safe="El modelo administrado fue verificado.", payload={"revision": revision}))
            self.repository.append_event(_repo_event(ComponentEventType.TRANSCRIPTION_MODEL_ACTIVATED, component_id=component_id, message_safe="El modelo administrado quedó activado.", payload={"revision": revision}))
            return TranscriptionInstallResult(
                state="ready",
                component_id=component_id,
                source_path=str(source),
                staged_path=str(staging_root),
                active_path=final_result.path,
                installation=installation,
                health_status="ready",
                revision=revision,
            )
        except Exception as exc:
            self.logger.warning("No se pudo instalar el modelo %s: %s", component_id, exc)
            shutil.rmtree(staging_root, ignore_errors=True)
            installation = self._persist_installation(
                component_id=component_id,
                revision=revision,
                root=install_root,
                source=str(source),
                install_type=ComponentInstallKind.MANAGED,
                status=ComponentInstallationStatus.INVALID,
                health_status=RuntimeCheckStatus.FAILED,
                error_message=str(exc),
            )
            self.repository.append_event(_repo_event(ComponentEventType.TRANSCRIPTION_MODEL_INSTALL_FAILED, component_id=component_id, message_safe="Falló la instalación administrada del modelo.", payload={"revision": revision}, severity="error"))
            return TranscriptionInstallResult(
                state="failed",
                component_id=component_id,
                source_path=str(source),
                staged_path=str(staging_root),
                active_path=str(install_root),
                installation=installation,
                health_status="failed",
                errors=(str(exc),),
                reason=str(exc),
                revision=revision,
            )
        finally:
            shutil.rmtree(staging_root, ignore_errors=True)

    def repair_local(
        self,
        component_id: str,
        source_path: str | Path | None = None,
        *,
        revision: str,
        artifact: VerifiedComponentArtifact | None = None,
    ) -> TranscriptionInstallResult:
        component_id = _safe_component_id(component_id)
        installation = self.repository.get_installation(component_id)
        if installation is None:
            return TranscriptionInstallResult(
                state="missing",
                component_id=component_id,
                source_path=None,
                staged_path=None,
                active_path=None,
                installation=None,
                health_status="missing",
                errors=("No existe una instalacion administrada para reparar.",),
                reason="missing",
            )
        if not installation.managed:
            return TranscriptionInstallResult(
                state="not_supported",
                component_id=component_id,
                source_path=installation.source,
                staged_path=None,
                active_path=installation.location_path,
                installation=installation,
                health_status=installation.health_status.value,
                errors=("Solo las instalaciones administradas pueden repararse.",),
                reason="not_supported",
                revision=installation.revision,
            )
        if source_path is None and artifact is None and installation.source:
            source_path = installation.source
        return self.install_local(component_id, source_path or installation.source or "", revision=revision or (installation.revision or "1"), artifact=artifact)

    def remove_local(self, component_id: str) -> TranscriptionInstallResult:
        component_id = _safe_component_id(component_id)
        installation = self.repository.get_installation(component_id)
        model_name = self._component_name(component_id)
        if installation is None:
            return TranscriptionInstallResult(
                state="missing",
                component_id=component_id,
                source_path=None,
                staged_path=None,
                active_path=None,
                installation=None,
                health_status="missing",
                errors=("No existe una instalacion de modelo para eliminar.",),
                reason="missing",
            )
        if not installation.managed:
            return TranscriptionInstallResult(
                state="not_supported",
                component_id=component_id,
                source_path=installation.source,
                staged_path=None,
                active_path=installation.location_path,
                installation=installation,
                health_status=installation.health_status.value,
                errors=("Solo las instalaciones administradas pueden eliminarse.",),
                reason="not_supported",
                revision=installation.revision,
            )
        removed = self.model_manager.remove_model(model_name)
        missing = self._persist_installation(
            component_id=component_id,
            revision=installation.revision if installation and installation.revision else "1",
            root=Path(installation.location_path) if installation and installation.location_path else self._install_root(component_id, installation.revision if installation and installation.revision else "1"),
            source=installation.source if installation else model_name,
            install_type=installation.install_type if installation else ComponentInstallKind.MANAGED,
            status=ComponentInstallationStatus.MISSING,
            health_status=RuntimeCheckStatus.NOT_CHECKED,
            error_message="La instalacion administrada fue eliminada." if removed else None,
        )
        return TranscriptionInstallResult(
            state="removed",
            component_id=component_id,
            source_path=installation.source if installation else None,
            staged_path=None,
            active_path=None,
            installation=missing,
            health_status="removed",
            revision=missing.revision,
        )
